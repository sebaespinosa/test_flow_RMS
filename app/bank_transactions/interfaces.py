"""
Repository protocol for bank transactions.
"""

from typing import Protocol, Sequence
from app.bank_transactions.models import BankTransactionEntity


class IBankTransactionRepository(Protocol):
    """Abstraction for bank transaction persistence."""

    async def bulk_create(self, entities: Sequence[BankTransactionEntity]) -> Sequence[BankTransactionEntity]:
        ...

    async def get_by_external_ids(self, tenant_id: int, external_ids: list[str]) -> list[BankTransactionEntity]:
        ...
