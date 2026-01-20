"""
Pydantic DTOs for bank transaction import REST endpoint.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import Field, field_validator
from app.common.base_models import BaseSchema, TimestampSchema


class BankTransactionImportItem(BaseSchema):
    """Single transaction within a bulk import request."""

    external_id: str | None = Field(
        None,
        max_length=100,
        description="External/source system transaction ID (for idempotency)"
    )
    posted_at: datetime = Field(
        ...,
        description=(
            "Transaction posting timestamp as Unix epoch (seconds or milliseconds). "
            "Examples: 1768471200 or 1768471200000. Invalid formats return 422."
        )
    )
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Transaction amount (must be a positive integer, no cents allowed)")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="3-letter currency code")
    description: str | None = Field(None, description="Bank memo/description")


class BankTransactionImportRequest(BaseSchema):
    """Bulk import request payload."""

    transactions: list[BankTransactionImportItem] = Field(..., min_length=1, description="List of transactions to import")


    @field_validator("transactions", mode="before")
    @classmethod
    def validate_timestamps(cls, v):
        # Validate each posted_at to be a Unix timestamp (sec or ms)
        for item in v or []:
            ts = item.get("postedAt") if isinstance(item, dict) else None
            if ts is None:
                continue
            item["postedAt"] = cls._parse_timestamp(ts)
        return v

    @field_validator("transactions", mode="before")
    @classmethod
    def validate_amounts(cls, v):
        # Validate each amount to be a positive integer (no cents)
        for item in v or []:
            amount = item.get("amount") if isinstance(item, dict) else None
            if amount is None:
                continue
            # Convert to Decimal for validation
            if isinstance(amount, str):
                try:
                    amount = Decimal(amount)
                except:
                    raise ValueError("amount must be a valid number")
            elif isinstance(amount, (int, float)):
                amount = Decimal(str(amount))
            # Check if it's an integer (no decimal places)
            if amount % 1 != 0:
                raise ValueError("amount must be an integer (no cents allowed)")
            if amount <= 0:
                raise ValueError("amount must be greater than 0")
        return v

    @staticmethod
    def _parse_timestamp(value):
        if isinstance(value, datetime):
            return value
        # Accept int/float or numeric strings
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(".", "", 1).isdigit()):
            numeric = float(value)
            # Heuristic: ms if large
            if numeric > 1e12:
                numeric = numeric / 1000.0
            return datetime.utcfromtimestamp(numeric)
        raise ValueError("postedAt must be a Unix timestamp (seconds or milliseconds)")


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
