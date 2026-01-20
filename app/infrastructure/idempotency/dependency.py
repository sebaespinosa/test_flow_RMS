"""
FastAPI dependency for checking idempotency before route handler execution.
"""

import hashlib
from fastapi import Request, Header, Depends
from app.database.session import get_db
from app.infrastructure.idempotency.repository import IdempotencyRepository


class IdempotencyCheckResult:
    """Result of idempotency check"""
    
    def __init__(self, is_retry: bool, cached_response: dict | None = None):
        self.is_retry = is_retry
        self.cached_response = cached_response


async def check_idempotency(
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db = Depends(get_db),
) -> IdempotencyCheckResult | None:
    """
    FastAPI Dependency that:
    1. Runs BEFORE route handler
    2. Returns cached response on retry (short-circuits route execution)
    3. Detects payload conflicts (409 Conflict)
    
    Usage:
        @router.post("/invoices/import")
        async def import_invoices(
            ...,
            idempotency_check: IdempotencyCheckResult | None = Depends(check_idempotency)
        ):
            if idempotency_check and idempotency_check.is_retry:
                return idempotency_check.cached_response
            # ... execute operation
    """
    
    if not idempotency_key:
        return None  # Header not provided, proceed without idempotency
    
    tenant_id = request.scope.get("tenant_id")
    if not tenant_id:
        # For now, default to 1 (update when auth is implemented)
        tenant_id = 1
    
    endpoint = request.url.path
    
    # Hash request body for conflict detection
    body = await request.body()
    request_hash = hashlib.sha256(body).hexdigest()
    
    repo = IdempotencyRepository(db)
    existing = await repo.get_by_key(idempotency_key, tenant_id)
    
    if existing:
        # Verify payload hasn't changed (conflict detection)
        if existing.request_payload_hash != request_hash:
            from app.config.exceptions import ConflictError
            raise ConflictError(
                detail="Idempotency key reused with different request payload"
            )
        
        # Return cached response (retry detected)
        return IdempotencyCheckResult(
            is_retry=True,
            cached_response=existing.response_body
        )
    
    return IdempotencyCheckResult(is_retry=False)
