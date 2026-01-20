"""
Service layer for destructive seed operations across tenants, invoices,
bank transactions, and reconciliation matches.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.seed.repository import SeedRepository
from app.tenants.models import TenantEntity
from app.invoices.models import InvoiceEntity
from app.bank_transactions.models import BankTransactionEntity
from app.reconciliation.models import MatchEntity
from app.seed.rest.schemas import (
    TableCounts,
    DateRange,
    DateTimeRange,
    SeedResponse,
    CleanupResponse,
    SeedStatusResponse,
)


class SeedService:
    """Coordinates destructive seed, cleanup, and status operations."""

    def __init__(self, session: AsyncSession, repository: SeedRepository):
        self.session = session
        self.repository = repository

    async def seed(self) -> SeedResponse:
        """
        Wipe existing data, insert a curated demo dataset, and return a summary.
        All mutations run in a single transaction to keep state consistent on failure.
        """
        async with self.session.begin():
            deleted_counts = await self._delete_existing()
            tenant = await self._create_tenant()
            invoices = await self._create_invoices(tenant.id)
            transactions = await self._create_transactions(tenant.id)
            matches = await self._create_matches(tenant.id, invoices, transactions)

        totals = await self.repository.get_counts()
        invoice_bounds = await self.repository.get_invoice_date_bounds()
        posted_bounds = await self.repository.get_transaction_posted_bounds()

        inserted_counts = TableCounts(
            tenants=1,
            invoices=len(invoices),
            bank_transactions=len(transactions),
            matches=len(matches),
        )

        return SeedResponse(
            deleted=self._counts_from_dict(deleted_counts),
            inserted=inserted_counts,
            totals=self._counts_from_dict(totals),
            invoice_date_range=DateRange.from_bounds(invoice_bounds),
            posted_at_range=DateTimeRange.from_bounds(posted_bounds),
        )

    async def cleanup(self) -> CleanupResponse:
        """Delete all tenant-scoped data and return counts removed."""
        async with self.session.begin():
            deleted_counts = await self._delete_existing()

        totals = await self.repository.get_counts()
        invoice_bounds = await self.repository.get_invoice_date_bounds()
        posted_bounds = await self.repository.get_transaction_posted_bounds()

        return CleanupResponse(
            deleted=self._counts_from_dict(deleted_counts),
            totals=self._counts_from_dict(totals),
            invoice_date_range=DateRange.from_bounds(invoice_bounds),
            posted_at_range=DateTimeRange.from_bounds(posted_bounds),
        )

    async def status(self) -> SeedStatusResponse:
        """Summarize current dataset without mutating it."""
        totals = await self.repository.get_counts()
        invoice_bounds = await self.repository.get_invoice_date_bounds()
        posted_bounds = await self.repository.get_transaction_posted_bounds()

        return SeedStatusResponse(
            totals=self._counts_from_dict(totals),
            invoice_date_range=DateRange.from_bounds(invoice_bounds),
            posted_at_range=DateTimeRange.from_bounds(posted_bounds),
        )

    async def _delete_existing(self) -> dict[str, int]:
        deleted_matches = await self.repository.delete_matches()
        deleted_transactions = await self.repository.delete_bank_transactions()
        deleted_invoices = await self.repository.delete_invoices()
        deleted_tenants = await self.repository.delete_tenants()
        return {
            "matches": deleted_matches,
            "bank_transactions": deleted_transactions,
            "invoices": deleted_invoices,
            "tenants": deleted_tenants,
        }

    async def _create_tenant(self) -> TenantEntity:
        tenant = TenantEntity(
            name="Seed Demo Tenant",
            description="Demo data for reconciliation workflows",
            is_active=True,
        )
        return await self.repository.add_tenant(tenant)

    async def _create_invoices(self, tenant_id: int) -> list[InvoiceEntity]:
        today = datetime.now(timezone.utc).date()
        invoices = [
            InvoiceEntity(
                tenant_id=tenant_id,
                vendor_id=101,
                invoice_number="INV-1001",
                amount=Decimal("12000"),
                currency="USD",
                invoice_date=today - timedelta(days=30),
                due_date=today - timedelta(days=15),
                description="Quarterly services",
                status="matched",
            ),
            InvoiceEntity(
                tenant_id=tenant_id,
                vendor_id=102,
                invoice_number="INV-1002",
                amount=Decimal("8300"),
                currency="EUR",
                invoice_date=today - timedelta(days=18),
                due_date=today - timedelta(days=8),
                description="Software license renewal",
                status="open",
            ),
            InvoiceEntity(
                tenant_id=tenant_id,
                vendor_id=103,
                invoice_number="INV-1003",
                amount=Decimal("7600"),
                currency="USD",
                invoice_date=today - timedelta(days=10),
                due_date=today + timedelta(days=10),
                description="Implementation milestone",
                status="open",
            ),
            InvoiceEntity(
                tenant_id=tenant_id,
                vendor_id=104,
                invoice_number="INV-1004",
                amount=Decimal("4500"),
                currency="GBP",
                invoice_date=today - timedelta(days=5),
                due_date=today + timedelta(days=20),
                description="Advisory retainer",
                status="paid",
            ),
            InvoiceEntity(
                tenant_id=tenant_id,
                vendor_id=105,
                invoice_number="INV-1005",
                amount=Decimal("2200"),
                currency="USD",
                invoice_date=today - timedelta(days=2),
                due_date=today + timedelta(days=28),
                description="Expense reimbursement",
                status="open",
            ),
        ]
        return await self.repository.add_invoices(invoices)

    async def _create_transactions(
        self, tenant_id: int
    ) -> list[BankTransactionEntity]:
        now = datetime.now(timezone.utc)
        transactions = [
            BankTransactionEntity(
                tenant_id=tenant_id,
                external_id="TX-9001",
                posted_at=now - timedelta(days=29, hours=2),
                amount=Decimal("12000"),
                currency="USD",
                description="Payment from client for Q1 services",
            ),
            BankTransactionEntity(
                tenant_id=tenant_id,
                external_id="TX-9002",
                posted_at=now - timedelta(days=17, hours=3),
                amount=Decimal("8300"),
                currency="EUR",
                description="License renewal payment",
            ),
            BankTransactionEntity(
                tenant_id=tenant_id,
                external_id="TX-9003",
                posted_at=now - timedelta(days=9, hours=5),
                amount=Decimal("7550"),
                currency="USD",
                description="Implementation phase payment",
            ),
            BankTransactionEntity(
                tenant_id=tenant_id,
                external_id="TX-9004",
                posted_at=now - timedelta(days=4, hours=1),
                amount=Decimal("4500"),
                currency="GBP",
                description="Retainer payment received",
            ),
            BankTransactionEntity(
                tenant_id=tenant_id,
                external_id="TX-9005",
                posted_at=now - timedelta(days=1, hours=6),
                amount=Decimal("2200"),
                currency="USD",
                description="Reimbursement transfer",
            ),
        ]
        return await self.repository.add_bank_transactions(transactions)

    async def _create_matches(
        self,
        tenant_id: int,
        invoices: Sequence[InvoiceEntity],
        transactions: Sequence[BankTransactionEntity],
    ) -> list[MatchEntity]:
        invoice_lookup = {invoice.invoice_number: invoice for invoice in invoices}
        transaction_lookup = {tx.external_id: tx for tx in transactions}

        # Link confirmed invoice to its transaction
        confirmed_invoice = invoice_lookup["INV-1001"]
        confirmed_tx = transaction_lookup["TX-9001"]
        confirmed_invoice.matched_transaction_id = confirmed_tx.id

        matches = [
            MatchEntity(
                tenant_id=tenant_id,
                invoice_id=confirmed_invoice.id,
                bank_transaction_id=confirmed_tx.id,
                score=Decimal("92.5000"),
                status="confirmed",
                reason="Exact amount match with adjacent dates and aligned descriptions",
                confirmed_at=datetime.utcnow(),
            ),
            MatchEntity(
                tenant_id=tenant_id,
                invoice_id=invoice_lookup["INV-1002"].id,
                bank_transaction_id=transaction_lookup["TX-9003"].id,
                score=Decimal("78.2500"),
                status="proposed",
                reason="Amounts are within tolerance and descriptions mention implementation",
                confirmed_at=None,
            ),
            MatchEntity(
                tenant_id=tenant_id,
                invoice_id=invoice_lookup["INV-1003"].id,
                bank_transaction_id=transaction_lookup["TX-9005"].id,
                score=Decimal("45.0000"),
                status="rejected",
                reason="Amount variance and posted date outside expected window",
                confirmed_at=None,
            ),
        ]

        return await self.repository.add_matches(matches)

    def _counts_from_dict(self, counts: dict[str, int]) -> TableCounts:
        return TableCounts(
            tenants=counts.get("tenants", 0),
            invoices=counts.get("invoices", 0),
            bank_transactions=counts.get("bank_transactions", 0),
            matches=counts.get("matches", 0),
        )
