"""
Service layer for bank transaction operations.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Sequence
from app.bank_transactions.models import BankTransactionEntity
from app.bank_transactions.interfaces import IBankTransactionRepository
from app.tenants.interfaces import ITenantRepository
from app.config.exceptions import ConflictError, NotFoundError, ValidationError

if TYPE_CHECKING:
    from app.bank_transactions.rest.schemas import BankTransactionImportItem


class BankTransactionService:
    """Business logic for bank transaction imports with idempotency."""

    def __init__(
        self,
        repository: IBankTransactionRepository,
        tenant_repository: ITenantRepository,
    ):
        self.repository = repository
        self.tenant_repository = tenant_repository

    async def _validate_tenant_exists(self, tenant_id: int) -> None:
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(detail=f"Tenant with id {tenant_id} not found")
        if not tenant.is_active:
            raise ValidationError(detail=f"Tenant with id {tenant_id} is not active")

    async def bulk_import_transactions(
        self,
        items: list['BankTransactionImportItem'],
        tenant_id: int,
    ) -> Sequence[BankTransactionEntity]:
        """
        Import bank transactions in bulk.
        
        Validates:
        - Tenant exists and is active
        - No duplicate external_ids within the batch
        - Transactions with existing external_ids are skipped
        """
        await self._validate_tenant_exists(tenant_id)

        if not items:
            raise ValidationError(detail="Cannot import empty transaction list")

        # Check for duplicates in the batch
        external_ids = [item.external_id for item in items if item.external_id]
        if len(external_ids) != len(set(external_ids)):
            raise ValidationError(detail="Duplicate external_ids found in import batch")

        # Check for existing transactions with same external_ids
        if external_ids:
            existing = await self.repository.get_by_external_ids(tenant_id, external_ids)
            if existing:
                existing_ids = {tx.external_id for tx in existing}
                raise ConflictError(
                    detail=f"Transactions with external_ids already exist: {', '.join(existing_ids)}"
                )

        # Create entities
        entities = [
            BankTransactionEntity(
                tenant_id=tenant_id,
                external_id=item.external_id,
                posted_at=item.posted_at,
                amount=item.amount,
                currency=item.currency,
                description=item.description,
            )
            for item in items
        ]

        return await self.repository.bulk_create(entities)
