"""
Strawberry GraphQL types for reconciliation.
"""

from datetime import datetime
from decimal import Decimal

import strawberry


@strawberry.type
class MatchType:
    """Match record in GraphQL"""

    id: int
    invoice_id: int
    bank_transaction_id: int
    score: Decimal
    status: str  # proposed, confirmed, rejected
    reason: str | None = None
    confirmed_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_entity(cls, entity):
        """Convert MatchEntity to MatchType"""
        return cls(
            id=entity.id,
            invoice_id=entity.invoice_id,
            bank_transaction_id=entity.bank_transaction_id,
            score=entity.score,
            status=entity.status,
            reason=entity.reason,
            confirmed_at=entity.confirmed_at,
            created_at=entity.created_at,
        )


@strawberry.type
class ReconciliationResultType:
    """Results from reconciliation query"""

    total: int
    returned: int
    candidates: list[MatchType]


@strawberry.type
class ExplanationType:
    """Explanation of why a match was scored"""

    score: Decimal
    reason: str
    invoice_id: int
    transaction_id: int


@strawberry.input
class ReconciliationInput:
    """Input for reconciliation mutation"""

    top: int = 5
    min_score: Decimal = Decimal("60")
