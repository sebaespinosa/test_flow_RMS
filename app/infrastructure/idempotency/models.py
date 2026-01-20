"""
Idempotency record entity with automatic TTL expiration.
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
from datetime import datetime, timedelta
from app.database.base import Base


class IdempotencyRecordEntity(Base):
    """
    Stores idempotency key state with automatic expiration (48 hours).
    Prevents duplicate operations on retry or race conditions.
    """
    
    __tablename__ = "idempotency_records"
    
    id = Column(Integer, primary_key=True)
    
    # Composite key: idempotency_key + tenant_id (multi-tenant isolation)
    idempotency_key = Column(String(255), nullable=False)
    tenant_id = Column(Integer, nullable=False)
    
    # Operation metadata for conflict detection
    endpoint = Column(String(255), nullable=False)  # POST /invoices/import
    request_payload_hash = Column(String(64), nullable=False)  # SHA256
    
    # Result caching (for immediate retry response)
    response_body = Column(JSON, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    
    # Lifecycle tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        # Prevent duplicate operations per tenant (unique constraint)
        Index(
            "ix_idempotency_unique_per_tenant",
            "idempotency_key",
            "tenant_id",
            unique=True
        ),
        # Enable fast cleanup of expired records (background job)
        Index("ix_idempotency_expires_at", "expires_at"),
        # Fast lookup by tenant + key
        Index("ix_idempotency_lookup", "tenant_id", "idempotency_key"),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if idempotency record has expired"""
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def from_request(
        cls,
        key: str,
        tenant_id: int,
        endpoint: str,
        request_hash: str,
        ttl_hours: int = 48
    ):
        """Factory method to create new idempotency record"""
        return cls(
            idempotency_key=key,
            tenant_id=tenant_id,
            endpoint=endpoint,
            request_payload_hash=request_hash,
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours)
        )
