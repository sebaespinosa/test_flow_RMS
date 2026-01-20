"""
Service layer for reconciliation business logic.
Orchestrates match generation, confirmation, and score calculation.
"""

from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.reconciliation.models import MatchEntity
from app.reconciliation.repository import MatchRepository
from app.reconciliation.scoring import calculate_match_score
from app.ai.service import AIExplanationService
from app.invoices.repository import InvoiceRepository
from app.bank_transactions.repository import BankTransactionRepository
from app.config.exceptions import NotFoundError, ConflictError
from app.config.settings import Settings


class ReconciliationService:
    """Service for invoice-transaction reconciliation"""

    def __init__(
        self,
        match_repo: MatchRepository,
        invoice_repo: InvoiceRepository,
        transaction_repo: BankTransactionRepository,
        ai_service: Optional[AIExplanationService] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize with repository dependencies"""
        self.match_repo = match_repo
        self.invoice_repo = invoice_repo
        self.transaction_repo = transaction_repo
        self.ai_service = ai_service
        self.settings = settings

    async def run_reconciliation(
        self,
        tenant_id: int,
        top: int = 5,
        min_score: Decimal = Decimal("60"),
    ) -> dict:
        """
        Run reconciliation and return match candidates.
        
        Strategy:
        1. Skip invoices that already have confirmed matches
        2. For each unmatched invoice, score against all unmatched transactions
        3. Generate match records for proposed candidates
        4. Return top candidates sorted by score descending
        
        Args:
            tenant_id: Tenant to reconcile
            top: Maximum number of candidates to return (default 5)
            min_score: Minimum score threshold (default 60)
        
        Returns:
            Dict with total count and returned candidates
        """
        # Get all unconfirmed invoices for tenant
        invoices = await self.invoice_repo.list_by_tenant(
            tenant_id,
            skip=0,
            limit=None,
        )

        # Filter out already-matched invoices
        unmatched_invoices = [
            inv for inv in invoices
            if inv.status != "matched" and not inv.matched_transaction_id
        ]

        if not unmatched_invoices:
            return {
                "total": 0,
                "returned": 0,
                "candidates": [],
            }

        # Get all unconfirmed transactions for tenant
        transactions = await self.transaction_repo.list_by_tenant(
            tenant_id,
            skip=0,
            limit=None,
        )

        # For each unmatched invoice, score against all transactions
        match_scores = []
        for invoice in unmatched_invoices:
            for transaction in transactions:
                # Skip if already confirmed match exists
                existing = await self.match_repo.get_confirmed_for_invoice(
                    invoice.id, tenant_id
                )
                if existing:
                    continue

                # Calculate match score
                scoring_result = calculate_match_score(invoice, transaction)
                
                if scoring_result["score"] > 0:
                    match_scores.append({
                        "invoice_id": invoice.id,
                        "transaction_id": transaction.id,
                        "score": scoring_result["score"],
                        "reason": scoring_result["reason"],
                    })

        # Create match records for all scored pairs
        for match_data in match_scores:
            try:
                match_entity = MatchEntity(
                    tenant_id=tenant_id,
                    invoice_id=match_data["invoice_id"],
                    bank_transaction_id=match_data["transaction_id"],
                    score=match_data["score"],
                    reason=match_data["reason"],
                    status="proposed",
                )
                await self.match_repo.create(match_entity)
            except Exception:
                # Duplicate matches may exist; skip if unique constraint violated
                pass

        # Get proposed candidates sorted by score
        candidates, total = await self.match_repo.get_proposed_candidates(
            tenant_id,
            top=top,
            min_score=min_score,
        )

        return {
            "total": total,
            "returned": len(candidates),
            "candidates": candidates,
        }

    async def confirm_match(self, match_id: int, tenant_id: int) -> MatchEntity:
        """
        Confirm a proposed match.
        
        Side effects:
        - Update match status to 'confirmed'
        - Update invoice status to 'matched'
        - Set invoice.matched_transaction_id
        - Reject other proposed matches for that invoice
        
        Args:
            match_id: Match ID to confirm
            tenant_id: Tenant ID for isolation
        
        Returns:
            Updated MatchEntity
        
        Raises:
            NotFoundError: If match not found
            ConflictError: If invoice already matched
        """
        # Get the match
        match = await self.match_repo.get_by_id(match_id, tenant_id)
        if not match:
            raise NotFoundError(detail=f"Match {match_id} not found")

        # Get the invoice
        invoice = await self.invoice_repo.get_by_id(match.invoice_id, tenant_id)
        if not invoice:
            raise NotFoundError(detail=f"Invoice {match.invoice_id} not found")

        # Check if invoice already has a different confirmed match
        existing_match = await self.match_repo.get_confirmed_for_invoice(
            match.invoice_id, tenant_id
        )
        if existing_match and existing_match.id != match_id:
            raise ConflictError(
                detail=f"Invoice already matched to transaction {existing_match.bank_transaction_id}"
            )

        # Confirm this match
        match = await self.match_repo.update_status(
            match_id,
            tenant_id,
            "confirmed",
            confirmed_at=datetime.utcnow(),
        )

        # Update invoice status and matched_transaction_id
        invoice.status = "matched"
        invoice.matched_transaction_id = match.bank_transaction_id

        # Reject other proposed matches for this invoice
        other_matches = await self.match_repo.get_by_invoice(
            match.invoice_id,
            tenant_id,
            status="proposed",
        )
        for other_match in other_matches:
            if other_match.id != match_id:
                await self.match_repo.update_status(
                    other_match.id,
                    tenant_id,
                    "rejected",
                )

        return match

    async def explain_match(self, match_id: int, tenant_id: int) -> dict:
        """
        Generate AI explanation for why a match was proposed.
        
        Strategy:
        1. Get the match record
        2. Get the invoice and transaction details
        3. Try to get AI explanation using AIExplanationService
        4. Fall back to heuristic reason if AI fails or is disabled
        5. Return explanation with confidence and source
        
        Args:
            match_id: Match ID to explain
            tenant_id: Tenant ID for isolation
        
        Returns:
            Dict with: ai_explanation, ai_confidence, heuristic_reason, 
            heuristic_score, source, ai_error_message
        
        Raises:
            NotFoundError: If match, invoice, or transaction not found
        """
        # Get the match
        match = await self.match_repo.get_by_id(match_id, tenant_id)
        if not match:
            raise NotFoundError(detail=f"Match {match_id} not found")

        # Get the invoice
        invoice = await self.invoice_repo.get_by_id(match.invoice_id, tenant_id)
        if not invoice:
            raise NotFoundError(detail=f"Invoice {match.invoice_id} not found")

        # Get the transaction
        transaction = await self.transaction_repo.get_by_id(
            match.bank_transaction_id, tenant_id
        )
        if not transaction:
            raise NotFoundError(
                detail=f"Transaction {match.bank_transaction_id} not found"
            )

        # Prepare context for AI
        context = {
            "invoice": {
                "id": invoice.id,
                "amount": float(invoice.amount),
                "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                "vendor_id": invoice.vendor_id,
                "description": invoice.description,
            },
            "transaction": {
                "id": transaction.id,
                "amount": float(transaction.amount),
                "posted_at": transaction.posted_at.isoformat() if transaction.posted_at else None,
                "description": transaction.description,
            },
            "match": {
                "score": float(match.score),
                "reason": match.reason,
            }
        }

        # Try AI explanation
        ai_explanation = None
        ai_confidence = None
        ai_error_message = None
        source = "heuristic"

        if self.ai_service and self.settings and self.settings.ai_enabled:
            try:
                result = await self.ai_service.generate_explanation(context)
                ai_explanation = result.get("explanation")
                ai_confidence = result.get("confidence", 0)
                source = "ai"
            except Exception as e:
                # Fall back to heuristic
                ai_error_message = str(e)
                source = "fallback"

        return {
            "ai_explanation": ai_explanation,
            "ai_confidence": ai_confidence,
            "heuristic_reason": match.reason or "Amount and date match",
            "heuristic_score": int(match.score),
            "source": source,
            "ai_error_message": ai_error_message,
        }
