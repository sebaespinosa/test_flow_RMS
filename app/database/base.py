"""
SQLAlchemy base and central model registry.
All domain models must be imported here for Alembic to discover them.

Note: Model imports happen in a lazy function to avoid circular imports at module load time.
"""

from sqlalchemy.orm import declarative_base

# Central registry - all models must import and use this
Base = declarative_base()


def register_models():
    """
    Register all models with SQLAlchemy Base.
    Called by Alembic and at app startup.
    Must be called AFTER Base is created.
    """
    # Domain models
    from app.tenants.models import TenantEntity  # noqa: F401
    from app.invoices.models import InvoiceEntity  # noqa: F401
    from app.bank_transactions.models import BankTransactionEntity  # noqa: F401
    from app.reconciliation.models import MatchEntity  # noqa: F401

    # Infrastructure models (always required)
    from app.infrastructure.idempotency.models import IdempotencyRecordEntity  # noqa: F401
    
    return [TenantEntity, InvoiceEntity, BankTransactionEntity, MatchEntity, IdempotencyRecordEntity]


__all__ = ["Base", "register_models"]
