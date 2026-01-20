"""
Repository interfaces for the Tenants domain.
Defines the contract that implementations must fulfill.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from app.tenants.models import TenantEntity


class ITenantRepository(ABC):
    """
    Repository interface for Tenant operations.
    Abstracts database access logic for dependency injection and testing.
    """
    
    @abstractmethod
    async def get_by_id(self, tenant_id: int) -> TenantEntity | None:
        """Get tenant by ID"""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> TenantEntity | None:
        """Get active tenant by name"""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
        created_date_start: datetime | None = None,
        created_date_end: datetime | None = None
    ) -> tuple[list[TenantEntity], int]:
        """
        Get all tenants with pagination and filters.
        Returns tuple of (tenants, total_count)
        """
        pass
    
    @abstractmethod
    async def create(self, tenant: TenantEntity) -> TenantEntity:
        """Create new tenant"""
        pass
    
    @abstractmethod
    async def update(self, tenant: TenantEntity) -> TenantEntity:
        """Update existing tenant"""
        pass
    
    @abstractmethod
    async def soft_delete(self, tenant: TenantEntity) -> TenantEntity:
        """Soft delete tenant (set is_active to False)"""
        pass
    
    @abstractmethod
    async def exists_by_name(self, name: str) -> bool:
        """Check if tenant with name exists (active or inactive)"""
        pass
