"""
Pytest conftest for test fixtures and configuration.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.base import Base


@pytest_asyncio.fixture
async def test_db():
    """Create test database session"""
    
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    async with session_factory() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
def test_app():
    """Create test FastAPI application"""
    from app.main import create_app
    from fastapi.testclient import TestClient
    
    app = create_app()
    
    # Note: TestClient doesn't support async, use httpx.AsyncClient for async tests
    return app


@pytest_asyncio.fixture
async def async_client(test_app):
    """Create async HTTP client for testing"""
    from httpx import AsyncClient
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
