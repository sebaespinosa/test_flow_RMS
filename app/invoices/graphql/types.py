"""
Strawberry GraphQL types for Invoices domain.
"""

from datetime import datetime, date
from typing import Optional
import strawberry
from app.invoices.models import InvoiceEntity


@strawberry.type
class InvoiceType:
    """GraphQL type representing an invoice."""
    id: int
    tenant_id: int
    vendor_id: Optional[int]
    invoice_number: Optional[str]
    amount: float
    currency: str
    invoice_date: Optional[date]
    due_date: Optional[date]
    description: Optional[str]
    status: str
    matched_transaction_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    @staticmethod
    def from_entity(entity: InvoiceEntity) -> "InvoiceType":
        """Convert InvoiceEntity to InvoiceType."""
        return InvoiceType(
            id=entity.id,
            tenant_id=entity.tenant_id,
            vendor_id=entity.vendor_id,
            invoice_number=entity.invoice_number,
            amount=float(entity.amount),
            currency=entity.currency,
            invoice_date=entity.invoice_date,
            due_date=entity.due_date,
            description=entity.description,
            status=entity.status,
            matched_transaction_id=entity.matched_transaction_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@strawberry.input
class InvoiceFilterInput:
    """Filtering options for invoices query."""
    status: Optional[str] = None
    vendor_id: Optional[int] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@strawberry.input
class CreateInvoiceInput:
    """Input payload for creating an invoice."""
    amount: float
    vendor_id: Optional[int] = None
    invoice_number: Optional[str] = None
    currency: Optional[str] = "USD"
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[str] = "open"
