"""
Match entity for invoice-transaction reconciliation.
Represents proposed or confirmed matches between invoices and bank transactions.
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


class MatchEntity(Base, TimestampMixin):
    """
    Represents a match between an invoice and a bank transaction.
    Supports proposed, confirmed, and rejected states.
    """

    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)

    # Tenant scope (required for multi-tenancy)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign keys to matched entities
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_transaction_id = Column(
        Integer,
        ForeignKey("bank_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Match confidence score (0.0000 to 100.0000)
    score = Column(Numeric(precision=7, scale=4), nullable=False)

    # Match status: proposed, confirmed, rejected
    status = Column(
        String(20),
        nullable=False,
        default="proposed",
        index=True,
    )

    # Scoring breakdown/reason for audit trail
    reason = Column(Text, nullable=True)

    # Timestamp when match was confirmed (null if still proposed/rejected)
    confirmed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # Tenant isolation
        Index("ix_matches_tenant_id", "tenant_id"),
        # Fast lookup by status
        Index("ix_matches_status", "status"),
        # Common query: find matches for a specific invoice
        Index("ix_matches_tenant_invoice", "tenant_id", "invoice_id"),
        # Common query: find matches for a specific transaction
        Index("ix_matches_tenant_transaction", "tenant_id", "bank_transaction_id"),
        # Composite for scoring/ranking
        Index("ix_matches_tenant_status_score", "tenant_id", "status", "score"),
        # Unique constraint: prevent duplicate matches for same invoice/transaction pair
        Index(
            "ix_matches_unique_pair",
            "tenant_id",
            "invoice_id",
            "bank_transaction_id",
            unique=True,
        ),
        # Validate status values
        CheckConstraint(
            "status IN ('proposed', 'confirmed', 'rejected')",
            name="ck_matches_status_valid",
        ),
        # Validate score range (0-100)
        CheckConstraint("score >= 0 AND score <= 100", name="ck_matches_score_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<MatchEntity(id={self.id}, invoice_id={self.invoice_id}, "
            f"transaction_id={self.bank_transaction_id}, score={self.score}, "
            f"status={self.status})>"
        )
