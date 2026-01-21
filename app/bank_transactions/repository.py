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

    async def list_by_tenant(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[BankTransactionEntity]:
        """
        Retrieve all bank transactions for a tenant.
        Used by reconciliation service.
        
        Args:
            tenant_id: Tenant ID for isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (None = no limit)
            
        Returns:
            List of BankTransactionEntity objects
        """
        stmt = select(BankTransactionEntity).where(
            BankTransactionEntity.tenant_id == tenant_id
        )
        
        if skip > 0:
            stmt = stmt.offset(skip)
        
        if limit is not None:
            stmt = stmt.limit(limit)
        else:
            stmt = stmt.limit(500)  # Default reasonable limit
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        transaction_id: int,
        tenant_id: int,
    ) -> BankTransactionEntity | None:
        """
        Retrieve a bank transaction by ID within tenant scope.
        CRITICAL: Always filters by tenant_id for multi-tenant isolation.
        
        Args:
            transaction_id: Transaction primary key
            tenant_id: Tenant ID for isolation
            
        Returns:
            BankTransactionEntity if found, None otherwise
        """
        from sqlalchemy import and_
        stmt = select(BankTransactionEntity).where(
            and_(
                BankTransactionEntity.id == transaction_id,
                BankTransactionEntity.tenant_id == tenant_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
