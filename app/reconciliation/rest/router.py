"""
REST API endpoints for reconciliation.
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.reconciliation.service import ReconciliationService
from app.ai.service import AIExplanationService
from app.reconciliation.repository import MatchRepository
from app.reconciliation.rest.schemas import (
    ReconciliationResponse,
    MatchRead,
    ConfirmMatchRequest,
    ExplanationResponse,
)
from app.invoices.repository import InvoiceRepository
from app.bank_transactions.repository import BankTransactionRepository
from app.config.exceptions import NotFoundError, ConflictError
from app.config.settings import get_settings


def get_reconciliation_service(
    db: AsyncSession = Depends(get_db),
) -> ReconciliationService:
    """Dependency to provide reconciliation service"""
    settings = get_settings()
    match_repo = MatchRepository(db)
    invoice_repo = InvoiceRepository(db)
    transaction_repo = BankTransactionRepository(db)
    ai_service = AIExplanationService(settings) if settings.ai_enabled else None
    return ReconciliationService(
        match_repo, 
        invoice_repo, 
        transaction_repo, 
        ai_service=ai_service,
        settings=settings,
    )


router = APIRouter(prefix="/api/v1/tenants", tags=["reconciliation"])


@router.post(
    "/{tenant_id}/reconcile",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_200_OK,
)
async def reconcile(
    tenant_id: int,
    top: int = 5,
    min_score: Decimal = Decimal("60"),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationResponse:
    """
    Run reconciliation and return match candidates.
    
    Query Parameters:
    - top: Maximum number of candidates to return (default 5)
    - min_score: Minimum score threshold (default 60)
    
    Returns:
    - total: Total count of proposed matches for tenant
    - returned: Number of candidates returned (up to 'top')
    - candidates: List of match candidates sorted by score descending
    """
    result = await service.run_reconciliation(
        tenant_id,
        top=top,
        min_score=min_score,
    )

    candidates = [
        MatchRead(
            id=match.id,
            invoice_id=match.invoice_id,
            bank_transaction_id=match.bank_transaction_id,
            score=match.score,
            status=match.status,
            reason=match.reason,
            created_at=match.created_at,
        )
        for match in result["candidates"]
    ]

    return ReconciliationResponse(
        total=result["total"],
        returned=result["returned"],
        candidates=candidates,
    )


@router.post(
    "/{tenant_id}/matches/{match_id}/confirm",
    response_model=MatchRead,
    status_code=status.HTTP_200_OK,
)
async def confirm_match(
    tenant_id: int,
    match_id: int,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> MatchRead:
    """
    Confirm a proposed match.
    
    Side effects:
    - Updates match status to 'confirmed'
    - Updates invoice status to 'matched'
    - Rejects other proposed matches for that invoice
    
    Raises:
    - 404: If match not found
    - 409: If invoice already matched to different transaction
    """
    try:
        match = await service.confirm_match(match_id, tenant_id)
    except NotFoundError as e:
        raise NotFoundError(detail=e.detail)
    except ConflictError as e:
        raise ConflictError(detail=e.detail)

    return MatchRead(
        id=match.id,
        invoice_id=match.invoice_id,
        bank_transaction_id=match.bank_transaction_id,
        score=match.score,
        status=match.status,
        reason=match.reason,
        created_at=match.created_at,
    )


@router.get(
    "/{tenant_id}/matches/{match_id}/explain",
    response_model=ExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def explain_match(
    tenant_id: int,
    match_id: int,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ExplanationResponse:
    """
    Get AI explanation for why a match was proposed.
    
    Returns both AI explanation (if available) and heuristic reason:
    - ai_explanation: LLM-generated explanation if AI is enabled
    - ai_confidence: Confidence score (0-100) for AI explanation
    - heuristic_reason: Rule-based reason from scoring algorithm
    - heuristic_score: Score (0-100) from heuristic matching
    - source: "ai" (AI enabled), "heuristic" (fallback), "fallback" (AI error)
    - ai_error_message: Error details if AI failed
    
    Raises:
    - 404: If match, invoice, or transaction not found
    """
    try:
        explanation = await service.explain_match(match_id, tenant_id)
    except NotFoundError as e:
        raise NotFoundError(detail=e.detail)

    return ExplanationResponse(
        ai_explanation=explanation["ai_explanation"],
        ai_confidence=explanation["ai_confidence"],
        heuristic_reason=explanation["heuristic_reason"],
        heuristic_score=explanation["heuristic_score"],
        source=explanation["source"],
        ai_error_message=explanation["ai_error_message"],
    )
