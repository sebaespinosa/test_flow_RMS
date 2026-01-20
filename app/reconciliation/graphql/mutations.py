"""
GraphQL mutation resolvers for reconciliation.
"""

from decimal import Decimal

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.reconciliation.service import ReconciliationService
from app.reconciliation.repository import MatchRepository
from app.reconciliation.graphql.types import (
    ReconciliationResultType,
    MatchType,
    ReconciliationInput,
)
from app.invoices.repository import InvoiceRepository
from app.bank_transactions.repository import BankTransactionRepository
from app.config.exceptions import NotFoundError, ConflictError


@strawberry.type
class Mutation:
    """Reconciliation mutation resolvers"""

    @strawberry.mutation
    async def reconcile(
        self,
        tenant_id: int,
        input: ReconciliationInput | None = None,
    ) -> ReconciliationResultType:
        """
        Run reconciliation and return match candidates.

        Args:
            tenant_id: Tenant ID for multi-tenancy isolation
            input: Optional reconciliation parameters (top, min_score)

        Returns:
            ReconciliationResultType with list of candidates
        """
        from app.database.session import get_async_engine

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            # Use input parameters or defaults
            top = input.top if input else 5
            min_score = input.min_score if input else Decimal("60")

            # Create service
            match_repo = MatchRepository(session)
            invoice_repo = InvoiceRepository(session)
            transaction_repo = BankTransactionRepository(session)
            service = ReconciliationService(match_repo, invoice_repo, transaction_repo)

            # Run reconciliation
            result = await service.run_reconciliation(
                tenant_id,
                top=top,
                min_score=min_score,
            )

            # Convert to GraphQL types
            candidates = [MatchType.from_entity(match) for match in result["candidates"]]

            return ReconciliationResultType(
                total=result["total"],
                returned=result["returned"],
                candidates=candidates,
            )

    @strawberry.mutation
    async def confirm_match(
        self,
        tenant_id: int,
        match_id: int,
    ) -> MatchType:
        """
        Confirm a proposed match.

        Args:
            tenant_id: Tenant ID for multi-tenancy isolation
            match_id: ID of match to confirm

        Returns:
            MatchType with confirmed match details

        Raises:
            NotFoundError: If match not found
            ConflictError: If invoice already matched
        """
        from app.database.session import get_async_engine

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            match_repo = MatchRepository(session)
            invoice_repo = InvoiceRepository(session)
            transaction_repo = BankTransactionRepository(session)
            service = ReconciliationService(match_repo, invoice_repo, transaction_repo)

            try:
                match = await service.confirm_match(match_id, tenant_id)
            except NotFoundError as e:
                raise NotFoundError(detail=e.detail)
            except ConflictError as e:
                raise ConflictError(detail=e.detail)

            return MatchType.from_entity(match)
