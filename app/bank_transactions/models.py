"""
Bank transaction entity for multi-tenant reconciliation system.
"""

from decimal import Decimal
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Text,
    Index,
    ForeignKey,
    CheckConstraint,
)
from app.database.base import Base
from app.common.base_models import TimestampMixin


class BankTransactionEntity(Base, TimestampMixin):
    """Represents a bank transaction belonging to a tenant."""

    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True)

    # Tenant scope
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External identifier for idempotency/duplicates from source system
    external_id = Column(String(100), nullable=True)

    posted_at = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    description = Column(Text, nullable=True)

    __table_args__ = (
        # Fast tenant filtering
        Index("ix_bank_transactions_tenant_id", "tenant_id"),
        # Unique external id per tenant when provided
        Index(
            "ix_bank_transactions_tenant_external",
            "tenant_id",
            "external_id",
            unique=True,
        ),
        # Date queries
        Index("ix_bank_transactions_posted_at", "posted_at"),
        # Validate currency and amount
        CheckConstraint("length(currency) = 3", name="ck_bank_tx_currency_len"),
        CheckConstraint("amount != 0", name="ck_bank_tx_amount_nonzero"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<BankTransactionEntity(id={self.id}, tenant_id={self.tenant_id}, "
            f"external_id={self.external_id}, amount={self.amount})>"
        )
