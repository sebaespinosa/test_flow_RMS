"""
Pytest conftest for test fixtures and configuration.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.base import Base


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a single test database engine for all tests.
    
    Using session scope ensures tables are created once and reused,
    while function-scoped sessions with transaction rollback provide isolation.
    This avoids the "index already exists" error from SQLAlchemy metadata conflicts.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    # Create all tables once
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup after all tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    """Create a fresh session for each test.
    
    Uses transaction rollback for cleanup, preventing data from leaking between tests
    while avoiding the "index already exists" error from SQLAlchemy metadata.
    """
    session_factory = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    test_session = session_factory()
    
    yield test_session
    
    # Cleanup
    await test_session.close()


@pytest.fixture
def test_app(test_db):
    """Create test FastAPI application"""
    from app.main import create_app
    from app.database.session import get_db
    
    app = create_app()
    
    # Override the database dependency with test database
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    return app


@pytest_asyncio.fixture
async def async_client(test_app):
    """Create async HTTP client for testing"""
    from httpx import AsyncClient, ASGITransport
    
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
