"""
Strawberry GraphQL mutations for bank transactions.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

import strawberry
from sqlalchemy import select

from app.bank_transactions.graphql.types import (
    BankTransactionType,
    BankTransactionsImportInput,
)
from app.bank_transactions.rest.schemas import (
    BankTransactionImportRequest,
    BankTransactionImportItem,
)
from app.bank_transactions.service import BankTransactionService
from app.bank_transactions.repository import BankTransactionRepository
from app.config.exceptions import ConflictError, ValidationError


@strawberry.type
class BankTransactionImportResponse:
    """Response from bank transaction import mutation."""

    success: bool
    count: int
    message: str
    transaction_ids: list[int]


@strawberry.type
class BankTransactionMutation:
    """GraphQL mutations for bank transactions."""

    @strawberry.mutation
    async def import_bank_transactions(
        self,
        info,
        tenant_id: int,
        input: BankTransactionsImportInput,
        x_idempotency_key: Optional[str] = None,
    ) -> BankTransactionImportResponse:
        """
        Import bulk bank transactions for a tenant.
        
        Args:
            tenant_id: The tenant ID
            input: List of transactions to import
            x_idempotency_key: Optional idempotency key for deduplication
        
        Returns:
            Import result with count and transaction IDs
        """
        from app.database.session import SessionLocal
        from app.infrastructure.idempotency.service import IdempotencyService
        from app.infrastructure.idempotency.repository import IdempotencyRepository

        # Convert GraphQL input to Pydantic schema for validation
        items = []
        for tx in input.transactions:
            items.append({
                "externalId": tx.external_id,
                "postedAt": tx.posted_at,  # Will be parsed as timestamp
                "amount": tx.amount,
                "currency": tx.currency,
                "description": tx.description,
            })

        # Validate through Pydantic schema
        try:
            validated = BankTransactionImportRequest(transactions=items)
        except Exception as e:
            raise ValidationError(detail=str(e))

        async with SessionLocal() as session:
            # Initialize repositories and services
            repo = BankTransactionRepository(session)
            idempotency_repo = IdempotencyRepository(session)

            # Check idempotency if key provided
            if x_idempotency_key:
                existing = await idempotency_repo.get_by_key(x_idempotency_key)
                if existing:
                    # Return cached response
                    return BankTransactionImportResponse(
                        success=True,
                        count=len(input.transactions),
                        message="Imported from cache (idempotent)",
                        transaction_ids=existing.response.get("transaction_ids", []),
                    )

            service = BankTransactionService(repo)

            # Process import
            transaction_ids = []
            async with session.begin():
                for item in validated.transactions:
                    entity = await service.create_transaction(
                        item, tenant_id=tenant_id
                    )
                    transaction_ids.append(entity.id)

                # Store idempotency record if key provided
                if x_idempotency_key:
                    response_data = {
                        "transaction_ids": transaction_ids,
                        "count": len(transaction_ids),
                    }
                    await idempotency_repo.store(
                        x_idempotency_key, response_data, ttl_hours=24
                    )

            return BankTransactionImportResponse(
                success=True,
                count=len(transaction_ids),
                message=f"Successfully imported {len(transaction_ids)} transactions",
                transaction_ids=transaction_ids,
            )
