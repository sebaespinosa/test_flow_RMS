"""
Invoice entity - represents an invoice in the multi-tenant system.
"""

from decimal import Decimal
from datetime import date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    Text,
    Index,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.common.base_models import TimestampMixin


class InvoiceEntity(Base, TimestampMixin):
    """
    Invoice entity - represents an invoice within a tenant's scope.
    Each invoice belongs to a tenant and optionally links to a vendor and transaction.
    """
    
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True)
    
    # Tenant relationship (multi-tenancy enforcement)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Vendor relationship (nullable - vendor domain may not exist yet)
    vendor_id = Column(Integer, nullable=True, index=True)
    
    # Invoice identification
    invoice_number = Column(String(100), nullable=True)
    
    # Financial details
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Dates
    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default="open",
        index=True
    )
    
    # Transaction matching (nullable - will become FK later when transactions domain exists)
    matched_transaction_id = Column(Integer, nullable=True)
    
    # Relationships
    # tenant = relationship("TenantEntity", back_populates="invoices")  # Uncomment when needed
    
    __table_args__ = (
        # Tenant isolation - critical for multi-tenant queries
        Index("ix_invoices_tenant_id", "tenant_id"),
        
        # Status filtering
        Index("ix_invoices_status", "status"),
        
        # Date range queries
        Index("ix_invoices_invoice_date", "invoice_date"),
        
        # Unique invoice number per tenant
        Index("ix_invoices_tenant_invoice_number", "tenant_id", "invoice_number", unique=True),
        
        # Common query pattern: filter by tenant and status
        Index("ix_invoices_tenant_status", "tenant_id", "status"),
        
        # Validate status values
        CheckConstraint(
            "status IN ('open', 'matched', 'paid')",
            name="ck_invoices_status_valid"
        ),
        
        # Validate currency code length
        CheckConstraint(
            "length(currency) = 3",
            name="ck_invoices_currency_length"
        ),
        
        # Ensure amount is positive
        CheckConstraint(
            "amount > 0",
            name="ck_invoices_amount_positive"
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<InvoiceEntity(id={self.id}, tenant_id={self.tenant_id}, "
            f"invoice_number='{self.invoice_number}', amount={self.amount}, "
            f"status='{self.status}')>"
        )
