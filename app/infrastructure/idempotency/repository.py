"""
Repository for idempotency records with conflict detection and TTL.
"""

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.config.exceptions import ConflictError
from app.infrastructure.idempotency.models import IdempotencyRecordEntity


class IdempotencyRepository:
    """Manages idempotency record storage and expiration"""
    
    def __init__(self, session):
        self.session = session
    
    async def get_by_key(
        self,
        key: str,
        tenant_id: int
    ) -> IdempotencyRecordEntity | None:
        """Retrieve idempotency record if it exists and hasn't expired"""
        stmt = select(IdempotencyRecordEntity).where(
            IdempotencyRecordEntity.idempotency_key == key,
            IdempotencyRecordEntity.tenant_id == tenant_id,
            # Expired records treated as non-existent
            IdempotencyRecordEntity.expires_at > datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(
        self,
        record: IdempotencyRecordEntity
    ) -> IdempotencyRecordEntity:
        """
        Store idempotency record. Raises ConflictError if:
        - Same key exists for tenant (operation in progress or duplicate)
        - Payload hash differs (key reused with different params)
        """
        try:
            self.session.add(record)
            await self.session.flush()  # Force constraint check
            return record
        except IntegrityError:
            # Unique constraint violation: record already exists
            existing = await self.get_by_key(
                record.idempotency_key,
                record.tenant_id
            )
            if existing and existing.request_payload_hash != record.request_payload_hash:
                raise ConflictError(
                    detail="Idempotency key reused with different request payload"
                )
            raise
    
    async def update_response(
        self,
        key: str,
        tenant_id: int,
        response_body: dict,
        status_code: int
    ) -> None:
        """Cache operation response for retry delivery"""
        record = await self.get_by_key(key, tenant_id)
        if record:
            record.response_body = response_body
            record.response_status_code = status_code
            await self.session.flush()
    
    async def cleanup_expired(self) -> int:
        """Delete idempotency records older than 48 hours (background task)"""
        stmt = delete(IdempotencyRecordEntity).where(
            IdempotencyRecordEntity.expires_at <= datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        return result.rowcount
