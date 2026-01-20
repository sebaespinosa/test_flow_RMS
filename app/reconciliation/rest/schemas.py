"""
Pydantic DTOs for reconciliation REST API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.common.base_models import BaseSchema, TimestampSchema


class MatchRead(BaseSchema):
    """Match record for API responses"""

    id: int
    invoice_id: int
    bank_transaction_id: int
    score: Decimal
    status: str
    reason: Optional[str] = None
    created_at: datetime


class ReconciliationResponse(BaseSchema):
    """Response from reconciliation endpoint"""

    total: int
    returned: int
    candidates: list[MatchRead]


class ConfirmMatchRequest(BaseSchema):
    """Request to confirm a match (no body required)"""

    pass
