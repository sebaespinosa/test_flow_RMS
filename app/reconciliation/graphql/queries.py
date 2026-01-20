"""
GraphQL query resolvers for reconciliation.
"""

from decimal import Decimal

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.reconciliation.service import ReconciliationService
from app.reconciliation.repository import MatchRepository
from app.reconciliation.scoring import calculate_match_score
from app.reconciliation.graphql.types import (
    ExplanationType,
    ReconciliationResultType,
    MatchType,
)
from app.invoices.repository import InvoiceRepository
from app.bank_transactions.repository import BankTransactionRepository
from app.config.exceptions import NotFoundError


@strawberry.type
class Query:
    """Reconciliation query resolvers"""

    @strawberry.field
    async def explain_reconciliation(
        self,
        tenant_id: int,
        invoice_id: int,
        transaction_id: int,
    ) -> ExplanationType:
        """
        Explain the reconciliation score between an invoice and transaction.

        Args:
            tenant_id: Tenant ID for multi-tenancy isolation
            invoice_id: Invoice to score
            transaction_id: Bank transaction to score

        Returns:
            ExplanationType with score and reason breakdown
        """
        from app.database.session import get_async_engine

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            invoice_repo = InvoiceRepository(session)
            transaction_repo = BankTransactionRepository(session)

            # Fetch both entities
            invoice = await invoice_repo.get_by_id(invoice_id, tenant_id)
            transaction = await transaction_repo.get_by_id(transaction_id, tenant_id)

            if not invoice:
                raise NotFoundError(detail=f"Invoice {invoice_id} not found")
            if not transaction:
                raise NotFoundError(detail=f"Transaction {transaction_id} not found")

            # Calculate score
            result = calculate_match_score(invoice, transaction)

            return ExplanationType(
                score=result["score"],
                reason=result["reason"],
                invoice_id=invoice_id,
                transaction_id=transaction_id,
            )
