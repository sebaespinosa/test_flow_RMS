"""
Test idempotency repository functionality.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.infrastructure.idempotency.models import IdempotencyRecordEntity
from app.infrastructure.idempotency.repository import IdempotencyRepository
from app.config.exceptions import ConflictError


@pytest_asyncio.fixture
async def idempotency_db():
    """Create test database for idempotency tests"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    async with session_factory() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_first_request_creates_record(idempotency_db):
    """First request stores idempotency record"""
    repo = IdempotencyRepository(idempotency_db)
    
    record = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/api/v1/invoices/import",
        request_hash="abc123"
    )
    
    await repo.create(record)
    await idempotency_db.commit()
    
    # Verify record exists and hasn't expired
    retrieved = await repo.get_by_key("req-123", 1)
    assert retrieved is not None
    assert retrieved.idempotency_key == "req-123"
    assert retrieved.tenant_id == 1
    assert retrieved.response_body is None  # Not yet filled


@pytest.mark.asyncio
async def test_duplicate_key_conflict(idempotency_db):
    """Reusing key with different payload raises 409"""
    repo = IdempotencyRepository(idempotency_db)
    
    # First request
    record1 = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/api/v1/invoices/import",
        request_hash="abc123"
    )
    await repo.create(record1)
    await idempotency_db.commit()
    
    # Retry with different payload
    record2 = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/api/v1/invoices/import",
        request_hash="xyz789"  # Different payload
    )
    
    with pytest.raises(ConflictError):
        await repo.create(record2)


@pytest.mark.asyncio
async def test_ttl_expiration(idempotency_db):
    """Expired records treated as non-existent"""
    repo = IdempotencyRepository(idempotency_db)
    
    record = IdempotencyRecordEntity(
        idempotency_key="req-123",
        tenant_id=1,
        endpoint="/api/v1/invoices/import",
        request_payload_hash="abc123",
        # Already expired
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )
    idempotency_db.add(record)
    await idempotency_db.commit()
    
    # Should return None (expired = not found)
    retrieved = await repo.get_by_key("req-123", 1)
    assert retrieved is None


@pytest.mark.asyncio
async def test_cleanup_expired_records(idempotency_db):
    """Background task removes expired records"""
    repo = IdempotencyRepository(idempotency_db)
    
    # Create 3 expired records
    for i in range(3):
        record = IdempotencyRecordEntity(
            idempotency_key=f"req-{i}",
            tenant_id=1,
            endpoint="/api/v1/invoices/import",
            request_payload_hash="hash",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        idempotency_db.add(record)
    
    await idempotency_db.commit()
    
    # Run cleanup
    deleted = await repo.cleanup_expired()
    await idempotency_db.commit()
    
    assert deleted == 3
    
    # Verify all deleted
    result = await idempotency_db.execute(
        select(func.count(IdempotencyRecordEntity.id))
    )
    remaining = result.scalar()
    assert remaining == 0


@pytest.mark.asyncio
async def test_update_response_caching(idempotency_db):
    """Response data can be cached for retries"""
    repo = IdempotencyRepository(idempotency_db)
    
    # Create record
    record = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/api/v1/invoices/import",
        request_hash="abc123"
    )
    await repo.create(record)
    await idempotency_db.commit()
    
    # Update with response
    response_data = {"imported_count": 5, "ids": [1, 2, 3, 4, 5]}
    await repo.update_response("req-123", 1, response_data, 201)
    await idempotency_db.commit()
    
    # Verify response cached
    retrieved = await repo.get_by_key("req-123", 1)
    assert retrieved.response_body == response_data
    assert retrieved.response_status_code == 201
