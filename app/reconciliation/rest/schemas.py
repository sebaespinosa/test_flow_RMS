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


class ExplanationResponse(BaseSchema):
    """Response from AI explanation endpoint"""

    ai_explanation: Optional[str] = None
    ai_confidence: Optional[int] = None  # 0-100 AI confidence score
    heuristic_reason: str
    heuristic_score: int  # 0-100 match score from reconciliation algorithm
    source: str  # "ai", "heuristic", or "fallback"
    ai_error_message: Optional[str] = None  # Error details if AI failed
