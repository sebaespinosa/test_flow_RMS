"""
Repository for destructive seed operations.
Handles bulk deletes, inserts, and aggregated stats across domains.
"""

from datetime import date, datetime
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenants.models import TenantEntity
from app.invoices.models import InvoiceEntity
from app.bank_transactions.models import BankTransactionEntity
from app.reconciliation.models import MatchEntity


class SeedRepository:
    """Data access for seed operations spanning multiple tables."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_matches(self) -> int:
        result = await self.session.execute(delete(MatchEntity))
        return result.rowcount or 0

    async def delete_bank_transactions(self) -> int:
        result = await self.session.execute(delete(BankTransactionEntity))
        return result.rowcount or 0

    async def delete_invoices(self) -> int:
        result = await self.session.execute(delete(InvoiceEntity))
        return result.rowcount or 0

    async def delete_tenants(self) -> int:
        result = await self.session.execute(delete(TenantEntity))
        return result.rowcount or 0

    async def add_tenant(self, tenant: TenantEntity) -> TenantEntity:
        self.session.add(tenant)
        await self.session.flush()
        return tenant

    async def add_invoices(self, invoices: list[InvoiceEntity]) -> list[InvoiceEntity]:
        self.session.add_all(invoices)
        await self.session.flush()
        return invoices

    async def add_bank_transactions(
        self, transactions: list[BankTransactionEntity]
    ) -> list[BankTransactionEntity]:
        self.session.add_all(transactions)
        await self.session.flush()
        return transactions

    async def add_matches(self, matches: list[MatchEntity]) -> list[MatchEntity]:
        self.session.add_all(matches)
        await self.session.flush()
        return matches

    async def get_counts(self) -> dict[str, int]:
        tenants_result = await self.session.execute(
            select(func.count(TenantEntity.id))
        )
        invoices_result = await self.session.execute(
            select(func.count(InvoiceEntity.id))
        )
        transactions_result = await self.session.execute(
            select(func.count(BankTransactionEntity.id))
        )
        matches_result = await self.session.execute(
            select(func.count(MatchEntity.id))
        )
        return {
            "tenants": tenants_result.scalar_one(),
            "invoices": invoices_result.scalar_one(),
            "bank_transactions": transactions_result.scalar_one(),
            "matches": matches_result.scalar_one(),
        }

    async def get_invoice_date_bounds(self) -> tuple[date | None, date | None]:
        result = await self.session.execute(
            select(
                func.min(InvoiceEntity.invoice_date),
                func.max(InvoiceEntity.invoice_date),
            )
        )
        return result.one()

    async def get_transaction_posted_bounds(
        self,
    ) -> tuple[datetime | None, datetime | None]:
        result = await self.session.execute(
            select(
                func.min(BankTransactionEntity.posted_at),
                func.max(BankTransactionEntity.posted_at),
            )
        )
        return result.one()
