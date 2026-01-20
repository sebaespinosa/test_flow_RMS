"""
Pydantic DTOs for Invoices REST API.
Handles request/response validation and serialization.
"""

from datetime import datetime, date
from decimal import Decimal
from pydantic import Field, field_validator
from app.common.base_models import BaseSchema, TimestampSchema


class InvoiceCreate(BaseSchema):
    """
    DTO for creating an invoice.
    Only amount is required, all other fields are optional.
    """
    
    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Invoice amount (must be a positive integer, no cents allowed)"
    )
    
    vendor_id: int | None = Field(
        default=None,
        description="Vendor ID (optional - vendor domain may not exist yet)"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_is_integer(cls, v: Decimal) -> Decimal:
        """Ensure amount is an integer with no decimal places."""
        if v % 1 != 0:
            raise ValueError("amount must be an integer (no cents allowed)")
        return v
    
    invoice_number: str | None = Field(
        default=None,
        max_length=100,
        description="Unique invoice number within tenant"
    )
    
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="3-letter currency code (ISO 4217)"
    )
    
    invoice_date: date | None = Field(
        default=None,
        description="Invoice issue date (Unix timestamp seconds/milliseconds or ISO date)"
    )

    due_date: date | None = Field(
        default=None,
        description="Payment due date (Unix timestamp seconds/milliseconds or ISO date)"
    )
    
    description: str | None = Field(
        default=None,
        description="Invoice description or notes"
    )
    
    status: str | None = Field(
        default="open",
        description="Invoice status (open, matched, paid)"
    )
    
    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase"""
        return v.upper()

    @field_validator("invoice_date", "due_date", mode="before")
    @classmethod
    def parse_dates(cls, v):
        return _parse_unix_date(v)
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of allowed values"""
        if v is not None:
            allowed = ["open", "matched", "paid"]
            if v not in allowed:
                raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class InvoiceUpdate(BaseSchema):
    """
    DTO for updating an invoice.
    All fields optional (partial update via PATCH).
    """
    
    vendor_id: int | None = Field(
        default=None,
        description="Vendor ID"
    )
    
    invoice_number: str | None = Field(
        default=None,
        max_length=100,
        description="Invoice number"
    )
    
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        description="Invoice amount (must be a positive integer, no cents allowed)"
    )
    
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description="3-letter currency code"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_is_integer(cls, v: Decimal | None) -> Decimal | None:
        """Ensure amount is an integer with no decimal places."""
        if v is not None and v % 1 != 0:
            raise ValueError("amount must be an integer (no cents allowed)")
        return v
    
    invoice_date: date | None = Field(
        default=None,
        description="Invoice issue date (Unix timestamp seconds/milliseconds or ISO date)"
    )

    due_date: date | None = Field(
        default=None,
        description="Payment due date (Unix timestamp seconds/milliseconds or ISO date)"
    )
    
    description: str | None = Field(
        default=None,
        description="Invoice description"
    )
    
    status: str | None = Field(
        default=None,
        description="Invoice status (open, matched, paid)"
    )
    
    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        """Ensure currency is uppercase"""
        return v.upper() if v else None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of allowed values"""
        if v is not None:
            allowed = ["open", "matched", "paid"]
            if v not in allowed:
                raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v

    @field_validator("invoice_date", "due_date", mode="before")
    @classmethod
    def parse_dates(cls, v):
        return _parse_unix_date(v)


class InvoiceRead(TimestampSchema):
    """
    DTO for reading an invoice.
    Includes all fields with camelCase aliases for JSON output.
    """
    
    id: int
    tenant_id: int
    vendor_id: int | None
    invoice_number: str | None
    amount: Decimal
    currency: str
    invoice_date: date | None
    due_date: date | None
    description: str | None
    status: str
    matched_transaction_id: int | None
    
    @classmethod
    def from_entity(cls, entity) -> "InvoiceRead":
        """
        Create DTO from InvoiceEntity.
        
        Args:
            entity: InvoiceEntity instance
            
        Returns:
            InvoiceRead DTO
        """
        return cls(
            id=entity.id,
            tenant_id=entity.tenant_id,
            vendor_id=entity.vendor_id,
            invoice_number=entity.invoice_number,
            amount=entity.amount,
            currency=entity.currency,
            invoice_date=entity.invoice_date,
            due_date=entity.due_date,
            description=entity.description,
            status=entity.status,
            matched_transaction_id=entity.matched_transaction_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class InvoiceFilters(BaseSchema):
    """
    DTO for invoice list filtering.
    All fields are optional query parameters.
    """
    
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum records to return")
    status: str | None = Field(default=None, description="Filter by status")
    vendor_id: int | None = Field(default=None, description="Filter by vendor ID")
    min_amount: float | None = Field(default=None, ge=0, description="Minimum amount")
    max_amount: float | None = Field(default=None, ge=0, description="Maximum amount")
    start_date: date | None = Field(
        default=None,
        description="Start date (Unix timestamp seconds/milliseconds or ISO date)"
    )
    end_date: date | None = Field(
        default=None,
        description="End date (Unix timestamp seconds/milliseconds or ISO date)"
    )

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_filter_dates(cls, v):
        return _parse_unix_date(v)


def _parse_unix_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(".", "", 1).isdigit()):
        numeric = float(value)
        if numeric > 1e12:
            numeric = numeric / 1000.0
        return datetime.utcfromtimestamp(numeric).date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            # Preserve original to surface validation error upstream
            raise ValueError("Date fields must be Unix timestamp (seconds or milliseconds) or ISO date string")
    raise ValueError("Date fields must be Unix timestamp (seconds or milliseconds) or ISO date string")
