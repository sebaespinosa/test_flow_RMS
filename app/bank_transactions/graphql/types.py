"""
Strawberry GraphQL types for bank transactions.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

import strawberry

from app.bank_transactions.models import BankTransactionEntity


@strawberry.type
class BankTransactionType:
    """GraphQL type representing a bank transaction."""

    id: int
    tenant_id: int
    external_id: Optional[str]
    posted_at: datetime
    amount: Decimal
    currency: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, entity: BankTransactionEntity) -> "BankTransactionType":
        """Convert SQLAlchemy entity to GraphQL type."""
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


@strawberry.input
class BankTransactionImportInput:
    """Input type for importing a single bank transaction."""

    external_id: Optional[str] = None
    posted_at: str  # Accept as string for timestamp parsing
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None


@strawberry.input
class BankTransactionsImportInput:
    """Input type for bulk bank transaction import."""

    transactions: list[BankTransactionImportInput]
