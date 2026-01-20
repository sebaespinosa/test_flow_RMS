"""
Tenant entity - represents a customer/organization in the multi-tenant system.
"""

from sqlalchemy import Column, Integer, String, Boolean, Index
from app.database.base import Base
from app.common.base_models import TimestampMixin


class TenantEntity(Base, TimestampMixin):
    """
    Tenant entity - root entity for multi-tenancy.
    Each tenant is isolated and can have multiple invoices, vendors, users, etc.
    """
    
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True)
    
    # Tenant identification
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String(1000), nullable=True)
    
    # Soft delete
    is_active = Column(Boolean, default=True, nullable=False)
    
    __table_args__ = (
        # Fast lookup by name
        Index("ix_tenants_name", "name"),
        # Fast filtering by status
        Index("ix_tenants_is_active", "is_active"),
        # Unique constraint on name for active tenants
        Index("ix_tenants_name_active", "name", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<TenantEntity(id={self.id}, name='{self.name}', is_active={self.is_active})>"
