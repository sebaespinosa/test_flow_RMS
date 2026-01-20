"""
Strawberry GraphQL queries for bank transactions.
"""

from typing import Optional

import strawberry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bank_transactions.models import BankTransactionEntity
from app.bank_transactions.graphql.types import BankTransactionType


@strawberry.type
class BankTransactionQuery:
    """GraphQL queries for bank transactions."""

    @strawberry.field
    async def bank_transactions(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BankTransactionType]:
        """
        List bank transactions for a tenant.
        
        Args:
            tenant_id: The tenant ID to filter by
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of bank transactions
        """
        from app.database.session import SessionLocal

        async with SessionLocal() as session:
            stmt = (
                select(BankTransactionEntity)
                .where(BankTransactionEntity.tenant_id == tenant_id)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            transactions = result.scalars().all()
            return [BankTransactionType.from_entity(t) for t in transactions]

    @strawberry.field
    async def bank_transaction(
        self,
        tenant_id: int,
        id: int,
    ) -> Optional[BankTransactionType]:
        """
        Get a single bank transaction by ID.
        
        Args:
            tenant_id: The tenant ID for isolation
            id: The transaction ID
        
        Returns:
            The bank transaction if found, None otherwise
        """
        from app.database.session import SessionLocal

        async with SessionLocal() as session:
            stmt = select(BankTransactionEntity).where(
                (BankTransactionEntity.id == id)
                & (BankTransactionEntity.tenant_id == tenant_id)
            )
            result = await session.execute(stmt)
            transaction = result.scalars().first()
            return BankTransactionType.from_entity(transaction) if transaction else None
