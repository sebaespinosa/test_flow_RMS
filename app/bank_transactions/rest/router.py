"""
FastAPI router for bank transaction bulk import with idempotency support.
"""

import hashlib
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.bank_transactions.repository import BankTransactionRepository
from app.bank_transactions.service import BankTransactionService
from app.bank_transactions.rest.schemas import (
    BankTransactionImportRequest,
    BankTransactionImportResponse,
    BankTransactionRead,
)
from app.tenants.repository import TenantRepository
from app.infrastructure.idempotency.repository import IdempotencyRepository
from app.infrastructure.idempotency.models import IdempotencyRecordEntity
from app.config.exceptions import ConflictError


router = APIRouter(
    prefix="/tenants/{tenant_id}/bank-transactions",
    tags=["bank-transactions"],
)


def get_bank_transaction_service(db: Annotated[AsyncSession, Depends(get_db)]) -> BankTransactionService:
    """Dependency injection for BankTransactionService."""
    repository = BankTransactionRepository(db)
    tenant_repository = TenantRepository(db)
    return BankTransactionService(
        repository=repository,
        tenant_repository=tenant_repository,
    )


@router.post(
    "/import",
    response_model=BankTransactionImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk import bank transactions with idempotency",
    description=(
        "Import multiple bank transactions. Supports idempotency via Idempotency-Key header. "
        "posted_at must be a Unix timestamp (seconds or milliseconds); invalid formats return 422. "
        "Empty strings for description/externalId are accepted and preserved as provided."
    ),
)
async def import_bank_transactions(
    tenant_id: int,
    data: BankTransactionImportRequest,
    request: Request,
    service: Annotated[BankTransactionService, Depends(get_bank_transaction_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> BankTransactionImportResponse:
    """
    Bulk import bank transactions with idempotency support.
    
    Idempotency behavior:
    - If Idempotency-Key header is provided:
      - First request: Imports transactions and caches response
      - Retry with same key + same payload: Returns cached response (200 OK with 201 status in body)
      - Retry with same key + different payload: Returns 409 Conflict
    - If no Idempotency-Key: Import happens every time (not recommended for production)
    
    Args:
        tenant_id: Tenant ID from path
        data: Import request with list of transactions
        idempotency_key: Optional header for idempotency protection
        
    Returns:
        Import response with count and created transactions
    """
    # Handle idempotency if key provided
    if idempotency_key:
        idempotency_repo = IdempotencyRepository(db)
        
        # Compute request hash for conflict detection
        body = await request.body()
        request_hash = hashlib.sha256(body).hexdigest()
        
        # Check if operation already executed
        existing = await idempotency_repo.get_by_key(idempotency_key, tenant_id)
        
        if existing:
            # Verify payload hasn't changed
            if existing.request_payload_hash != request_hash:
                raise ConflictError(
                    detail="Idempotency key reused with different request payload"
                )
            
            # Return cached response (retry detected)
            if existing.response_body:
                return BankTransactionImportResponse(**existing.response_body)
        
        # Create idempotency record BEFORE executing operation
        record = IdempotencyRecordEntity.from_request(
            key=idempotency_key,
            tenant_id=tenant_id,
            endpoint=request.url.path,
            request_hash=request_hash,
        )
        
        try:
            await idempotency_repo.create(record)
            await db.commit()  # Commit idempotency record
        except ConflictError:
            # Race condition: another request with same key just started
            # Retry lookup to get cached result
            existing = await idempotency_repo.get_by_key(idempotency_key, tenant_id)
            if existing and existing.response_body:
                return BankTransactionImportResponse(**existing.response_body)
            raise
    
    # Execute import operation
    transactions = await service.bulk_import_transactions(
        items=data.transactions,
        tenant_id=tenant_id,
    )
    
    # Build response
    response_data = BankTransactionImportResponse(
        imported_count=len(transactions),
        transactions=[BankTransactionRead.from_entity(tx) for tx in transactions],
    )
    
    # Cache response for idempotency if key provided
    if idempotency_key:
        await idempotency_repo.update_response(
            key=idempotency_key,
            tenant_id=tenant_id,
            response_body=response_data.model_dump(mode="json"),
            status_code=201,
        )
    
    # Commit transaction (includes both bank transactions and idempotency cache)
    await db.commit()
    
    return response_data
