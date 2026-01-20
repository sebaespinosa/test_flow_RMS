"""
Pydantic DTOs for bank transaction import REST endpoint.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import Field
from app.common.base_models import BaseSchema, TimestampSchema


class BankTransactionImportItem(BaseSchema):
    """Single transaction within a bulk import request."""

    external_id: str | None = Field(
        None,
        max_length=100,
        description="External/source system transaction ID (for idempotency)"
    )
    posted_at: datetime = Field(..., description="Transaction posting timestamp")
    amount: Decimal = Field(..., decimal_places=2, description="Transaction amount (can be negative)")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="3-letter currency code")
    description: str | None = Field(None, description="Bank memo/description")


class BankTransactionImportRequest(BaseSchema):
    """Bulk import request payload."""

    transactions: list[BankTransactionImportItem] = Field(..., min_length=1, description="List of transactions to import")


class BankTransactionRead(TimestampSchema):
    """Response DTO for a single bank transaction."""

    id: int
    tenant_id: int
    external_id: str | None
    posted_at: datetime
    amount: Decimal
    currency: str
    description: str | None

    @classmethod
    def from_entity(cls, entity) -> "BankTransactionRead":
        return cls(
            id=entity.id,
            tenant_id=entity.tenant_id,
            external_id=entity.external_id,
            posted_at=entity.posted_at,
            amount=entity.amount,
            currency=entity.currency,
            description=entity.description,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class BankTransactionImportResponse(BaseSchema):
    """Bulk import response."""

    imported_count: int = Field(..., description="Number of transactions imported")
    transactions: list[BankTransactionRead] = Field(..., description="Imported transactions")
