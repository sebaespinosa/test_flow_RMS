"""
Database engine and session factory.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config.settings import get_settings


def get_engine():
    """Create async SQLAlchemy engine"""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True,
        pool_pre_ping=True  # Verify connections before use
    )


def get_session_factory(engine):
    """Create async session factory"""
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )


# Global engine and session factory (initialized in app startup)
_engine = None
_session_factory = None


async def init_db():
    """Initialize database connection and create tables"""
    global _engine, _session_factory
    
    _engine = get_engine()
    _session_factory = get_session_factory(_engine)
    
    # Create all tables
    async with _engine.begin() as conn:
        from app.database.base import Base
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    global _engine
    if _engine:
        await _engine.dispose()


async def get_db() -> AsyncSession:
    """FastAPI dependency for database session"""
    global _session_factory
    
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() on app startup.")
    
    async with _session_factory() as session:
        yield session
