"""
Tenant repository implementation - data access layer.
Handles all database queries for tenant operations.
"""

from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.tenants.models import TenantEntity
from app.tenants.interfaces import ITenantRepository


class TenantRepository(ITenantRepository):
    """
    Concrete implementation of ITenantRepository.
    Provides all database operations for tenant entities.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
    async def get_by_id(self, tenant_id: int) -> TenantEntity | None:
        """
        Get tenant by ID (active or inactive).
        
        Args:
            tenant_id: Tenant primary key
            
        Returns:
            TenantEntity or None if not found
        """
        stmt = select(TenantEntity).where(TenantEntity.id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> TenantEntity | None:
        """
        Get active tenant by name.
        
        Args:
            name: Tenant name (case-sensitive)
            
        Returns:
            TenantEntity or None if not found or inactive
        """
        stmt = select(TenantEntity).where(
            and_(
                TenantEntity.name == name,
                TenantEntity.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
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
        
        Args:
            skip: Pagination offset
            limit: Maximum items per page (default 50)
            is_active: Filter by active status (None = no filter)
            created_date_start: Filter by creation date start (inclusive)
            created_date_end: Filter by creation date end (inclusive)
            
        Returns:
            Tuple of (tenant list, total count)
        """
        # Build filters
        filters = []
        
        if is_active is not None:
            filters.append(TenantEntity.is_active == is_active)
        
        if created_date_start is not None:
            filters.append(TenantEntity.created_at >= created_date_start)
        
        if created_date_end is not None:
            filters.append(TenantEntity.created_at <= created_date_end)
        
        # Build base statement with filters
        where_clause = and_(*filters) if filters else True
        
        # Get total count
        count_stmt = select(func.count(TenantEntity.id)).where(where_clause)
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Get paginated results
        stmt = (
            select(TenantEntity)
            .where(where_clause)
            .order_by(TenantEntity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        tenants = result.scalars().all()
        
        return tenants, total_count
    
    async def create(self, tenant: TenantEntity) -> TenantEntity:
        """
        Create new tenant in database.
        
        Args:
            tenant: TenantEntity to create
            
        Returns:
            Created TenantEntity with id populated
        """
        self.session.add(tenant)
        await self.session.flush()
        await self.session.commit()
        return tenant
    
    async def update(self, tenant: TenantEntity) -> TenantEntity:
        """
        Update existing tenant.
        
        Args:
            tenant: TenantEntity with updated values
            
        Returns:
            Updated TenantEntity
        """
        self.session.add(tenant)
        await self.session.flush()
        await self.session.commit()
        return tenant
    
    async def soft_delete(self, tenant: TenantEntity) -> TenantEntity:
        """
        Soft delete tenant by setting is_active to False.
        Preserves data for auditing and referential integrity.
        
        Args:
            tenant: TenantEntity to soft delete
            
        Returns:
            Updated TenantEntity with is_active=False
        """
        tenant.is_active = False
        self.session.add(tenant)
        await self.session.flush()
        await self.session.commit()
        return tenant
    
    async def exists_by_name(self, name: str) -> bool:
        """
        Check if tenant with name exists (active or inactive).
        Used for duplicate detection.
        
        Args:
            name: Tenant name to check
            
        Returns:
            True if tenant exists, False otherwise
        """
        stmt = select(func.count(TenantEntity.id)).where(TenantEntity.name == name)
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return count > 0
