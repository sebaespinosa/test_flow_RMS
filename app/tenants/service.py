"""
Tenant service - business logic layer.
Handles tenant operations and validations independent of delivery mechanism (REST/GraphQL).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from app.tenants.models import TenantEntity
from app.tenants.interfaces import ITenantRepository
from app.config.exceptions import ConflictError, NotFoundError

if TYPE_CHECKING:
    from app.tenants.rest.schemas import TenantCreate, TenantUpdate


class TenantService:
    """
    Service layer for tenant operations.
    Encapsulates business logic and delegates to repository.
    """
    
    def __init__(self, repository: ITenantRepository):
        """
        Initialize service with repository dependency.
        
        Args:
            repository: ITenantRepository implementation
        """
        self.repository = repository
    
    async def create_tenant(self, data: 'TenantCreate') -> TenantEntity:
        """
        Create new tenant with validation.
        
        Args:
            data: TenantCreate DTO with tenant details
            
        Returns:
            Created TenantEntity
            
        Raises:
            ConflictError: If tenant name already exists
        """
        # Check for duplicate name
        if await self.repository.exists_by_name(data.name):
            raise ConflictError(
                detail=f"Tenant with name '{data.name}' already exists"
            )
        
        # Create entity and save
        tenant = TenantEntity(
            name=data.name,
            description=data.description,
            is_active=True
        )
        
        return await self.repository.create(tenant)
    
    async def get_tenant(self, tenant_id: int) -> TenantEntity:
        """
        Get tenant by ID.
        
        Args:
            tenant_id: Tenant primary key
            
        Returns:
            TenantEntity
            
        Raises:
            NotFoundError: If tenant not found
        """
        tenant = await self.repository.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(detail=f"Tenant with id {tenant_id} not found")
        return tenant
    
    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
        created_date_start: datetime | None = None,
        created_date_end: datetime | None = None
    ) -> tuple[list[TenantEntity], int]:
        """
        List tenants with pagination and filtering.
        
        Args:
            skip: Pagination offset (default 0)
            limit: Items per page (default 50)
            is_active: Filter by active status (None = no filter)
            created_date_start: Filter creation date start (inclusive)
            created_date_end: Filter creation date end (inclusive)
            
        Returns:
            Tuple of (tenant list, total count)
        """
        # Validate pagination parameters
        if skip < 0:
            skip = 0
        if limit < 1:
            limit = 50
        if limit > 1000:  # Cap maximum limit for performance
            limit = 1000
        
        return await self.repository.get_all(
            skip=skip,
            limit=limit,
            is_active=is_active,
            created_date_start=created_date_start,
            created_date_end=created_date_end
        )
    
    async def update_tenant(
        self,
        tenant_id: int,
        data: 'TenantUpdate'
    ) -> TenantEntity:
        """
        Update tenant details.
        
        Args:
            tenant_id: Tenant to update
            data: TenantUpdate DTO with new values
            
        Returns:
            Updated TenantEntity
            
        Raises:
            NotFoundError: If tenant not found
            ConflictError: If new name conflicts with existing tenant
        """
        # Get existing tenant
        tenant = await self.repository.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(detail=f"Tenant with id {tenant_id} not found")
        
        # Check for name conflict if changing name
        if data.name and data.name != tenant.name:
            if await self.repository.exists_by_name(data.name):
                raise ConflictError(
                    detail=f"Tenant with name '{data.name}' already exists"
                )
            tenant.name = data.name
        
        # Update description if provided
        if data.description is not None:
            tenant.description = data.description
        
        return await self.repository.update(tenant)
    
    async def soft_delete_tenant(self, tenant_id: int) -> TenantEntity:
        """
        Soft delete tenant (set is_active to False).
        Preserves data for auditing and referential integrity.
        
        Args:
            tenant_id: Tenant to delete
            
        Returns:
            Soft-deleted TenantEntity
            
        Raises:
            NotFoundError: If tenant not found
        """
        tenant = await self.repository.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(detail=f"Tenant with id {tenant_id} not found")
        
        return await self.repository.soft_delete(tenant)
    
    async def reactivate_tenant(self, tenant_id: int) -> TenantEntity:
        """
        Reactivate a soft-deleted tenant.
        
        Args:
            tenant_id: Tenant to reactivate
            
        Returns:
            Reactivated TenantEntity
            
        Raises:
            NotFoundError: If tenant not found
        """
        tenant = await self.repository.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(detail=f"Tenant with id {tenant_id} not found")
        
        tenant.is_active = True
        return await self.repository.update(tenant)
