"""
Repository implementation for bank transactions.
"""

from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.bank_transactions.models import BankTransactionEntity
from app.bank_transactions.interfaces import IBankTransactionRepository


class BankTransactionRepository(IBankTransactionRepository):
    """SQLAlchemy repository for bank transactions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create(self, entities: Sequence[BankTransactionEntity]) -> Sequence[BankTransactionEntity]:
        self.session.add_all(list(entities))
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def get_by_external_ids(self, tenant_id: int, external_ids: list[str]) -> list[BankTransactionEntity]:
        if not external_ids:
            return []
        stmt = select(BankTransactionEntity).where(
            BankTransactionEntity.tenant_id == tenant_id,
            BankTransactionEntity.external_id.in_(external_ids),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
