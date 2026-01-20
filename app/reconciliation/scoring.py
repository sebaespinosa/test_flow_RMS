"""
Scoring module for invoice-transaction match calculation.
Implements weighted scoring algorithm to determine match confidence.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import TypedDict, Optional

from app.invoices.models import InvoiceEntity
from app.bank_transactions.models import BankTransactionEntity


class ScoringResult(TypedDict):
    """Result of scoring calculation"""
    score: Decimal
    reason: str


def calculate_match_score(
    invoice: InvoiceEntity,
    transaction: BankTransactionEntity,
    vendor_name: Optional[str] = None,
) -> ScoringResult:
    """
    Calculate match score between invoice and transaction using weighted scoring.
    
    Scoring Logic:
    - Identifier Match (Silver Bullet): invoice_number == external_id → 100 points
    - Amount Match (Mandatory): exact match → 50 points, otherwise → 0
    - Date Proximity: 0-3 days → 20 pts, 4-7 days → 10 pts, 8+ days → 0 pts
    - Invoice Number Reference: found in description → 25 points
    - Vendor Name Reference: found in description → 15 points
    - Currency Mismatch: penalty → -50 points
    
    Args:
        invoice: InvoiceEntity to match
        transaction: BankTransactionEntity to match
        vendor_name: Optional vendor name to check against transaction description
    
    Returns:
        ScoringResult with score (0-100) and reason breakdown
    """
    
    # 1. Check for identifier match (silver bullet - highest confidence)
    if invoice.invoice_number and transaction.external_id:
        if invoice.invoice_number == transaction.external_id:
            return ScoringResult(
                score=Decimal("100"),
                reason="Exact identifier match (invoice_number == external_id)"
            )
    
    score = Decimal("0")
    reason_parts = []
    
    # 2. Amount matching (mandatory - if amounts don't match, no match possible)
    if invoice.amount == transaction.amount:
        score += Decimal("50")
        reason_parts.append("Exact amount match (+50)")
    else:
        return ScoringResult(
            score=Decimal("0"),
            reason="Amount mismatch - no match possible"
        )
    
    # 3. Date proximity (optional but valuable)
    if invoice.invoice_date and transaction.posted_at:
        days_diff = abs(
            (transaction.posted_at.date() - invoice.invoice_date).days
        )
        if days_diff <= 3:
            score += Decimal("20")
            reason_parts.append(f"Date within 3 days (+20)")
        elif days_diff <= 7:
            score += Decimal("10")
            reason_parts.append(f"Date within 7 days (+10)")
    
    # 4. Invoice number in description (reference match)
    if (
        invoice.invoice_number
        and transaction.description
        and invoice.invoice_number in transaction.description
    ):
        score += Decimal("25")
        reason_parts.append("Invoice number found in description (+25)")
    
    # 5. Vendor name in description (optional)
    if (
        vendor_name
        and transaction.description
        and vendor_name.lower() in transaction.description.lower()
    ):
        score += Decimal("15")
        reason_parts.append("Vendor name found in description (+15)")
    
    # 6. Currency mismatch penalty (strong negative signal)
    if invoice.currency != transaction.currency:
        score = max(Decimal("0"), score - Decimal("50"))
        reason_parts.append("Currency mismatch (-50)")
    
    # Cap score at 100
    final_score = min(score, Decimal("100"))
    
    return ScoringResult(
        score=final_score,
        reason=" | ".join(reason_parts) if reason_parts else "No matching criteria"
    )
