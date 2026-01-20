"""
SQLAlchemy base and central model registry.
All domain models must be imported here for Alembic to discover them.
"""

from sqlalchemy.orm import declarative_base

# Central registry - all models must import and use this
Base = declarative_base()

# Import all models to register them
# Domain models
# (Add imports as you create domains)
# from app.tenants.models import TenantEntity
# from app.invoices.models import InvoiceEntity

# Infrastructure models (always required)
from app.infrastructure.idempotency.models import IdempotencyRecordEntity

__all__ = ["Base", "IdempotencyRecordEntity"]
