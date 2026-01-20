"""
Pydantic schemas for seed, cleanup, and status responses.
"""

from datetime import date, datetime
from pydantic import Field

from app.common.base_models import BaseSchema


class TableCounts(BaseSchema):
    tenants: int = Field(..., ge=0, description="Tenant rows affected or present")
    invoices: int = Field(..., ge=0, description="Invoice rows affected or present")
    bank_transactions: int = Field(..., ge=0, description="Bank transaction rows affected or present")
    matches: int = Field(..., ge=0, description="Match rows affected or present")


class DateRange(BaseSchema):
    min: date | None = Field(None, description="Earliest invoice date in dataset")
    max: date | None = Field(None, description="Latest invoice date in dataset")

    @classmethod
    def from_bounds(cls, bounds: tuple[date | None, date | None] | None):
        if not bounds:
            return None
        min_date, max_date = bounds
        if min_date is None and max_date is None:
            return None
        return cls(min=min_date, max=max_date)


class DateTimeRange(BaseSchema):
    min: datetime | None = Field(None, description="Earliest posted_at in dataset")
    max: datetime | None = Field(None, description="Latest posted_at in dataset")

    @classmethod
    def from_bounds(cls, bounds: tuple[datetime | None, datetime | None] | None):
        if not bounds:
            return None
        min_date, max_date = bounds
        if min_date is None and max_date is None:
            return None
        return cls(min=min_date, max=max_date)


class SeedResponse(BaseSchema):
    deleted: TableCounts = Field(..., description="Rows removed before seeding")
    inserted: TableCounts = Field(..., description="Rows inserted by seed run")
    totals: TableCounts = Field(..., description="Current totals after seed completes")
    invoice_date_range: DateRange | None = Field(None, description="Min/max invoice_date after seed")
    posted_at_range: DateTimeRange | None = Field(None, description="Min/max posted_at after seed")


class CleanupResponse(BaseSchema):
    deleted: TableCounts = Field(..., description="Rows removed by cleanup")
    totals: TableCounts = Field(..., description="Totals after cleanup completes")
    invoice_date_range: DateRange | None = Field(None, description="Min/max invoice_date after cleanup")
    posted_at_range: DateTimeRange | None = Field(None, description="Min/max posted_at after cleanup")


class SeedStatusResponse(BaseSchema):
    totals: TableCounts = Field(..., description="Current totals without mutation")
    invoice_date_range: DateRange | None = Field(None, description="Min/max invoice_date currently in DB")
    posted_at_range: DateTimeRange | None = Field(None, description="Min/max posted_at currently in DB")
