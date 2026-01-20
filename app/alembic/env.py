"""Alembic migration environment for async SQLAlchemy"""

from logging.config import fileConfig
import asyncio
import sys
from pathlib import Path

# Add project root to Python path so app modules can be imported
# alembic/env.py is at app/alembic/env.py, so go up 2 levels to project root
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import pool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so they're registered in Base.metadata
from app.database.base import Base
target_metadata = Base.metadata

# Get database URL from environment
from app.config.settings import get_settings
settings = get_settings()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url
    
    context.configure(
        url=configuration["sqlalchemy.url"],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations against a connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True
    )
    
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo
    )
    
    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)
    
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
