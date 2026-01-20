"""
Base classes and shared patterns for all domains.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declared_attr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class BaseSchema(BaseModel):
    """Base for all Pydantic DTOs - handles camelCase/snake_case conversion"""
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    
    created_at: datetime
    updated_at: datetime | None = None


class TenantScopedSchema(BaseSchema):
    """Schema for tenant-scoped resources"""
    
    tenant_id: int = Field(..., description="Tenant identifier")


# SQLAlchemy base classes
class TimestampMixin:
    """Mixin for created_at and updated_at timestamp columns"""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            server_default=func.now(),
            onupdate=func.now(),
            nullable=True
        )


class BaseRepository:
    """Base repository with common async CRUD operations"""
    
    def __init__(self, session: AsyncSession, entity_class):
        self.session = session
        self.entity_class = entity_class
    
    async def get_by_id(self, id: int):
        """Get entity by primary key"""
        stmt = select(self.entity_class).where(self.entity_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, entity):
        """Create and return entity"""
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def update(self, entity):
        """Update entity"""
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def delete(self, entity):
        """Delete entity"""
        await self.session.delete(entity)
        await self.session.flush()
    
    async def bulk_create(self, entities: list):
        """Create multiple entities"""
        self.session.add_all(entities)
        await self.session.flush()
        return entities


class BaseService:
    """Base service for common patterns"""
    
    def __init__(self, repository):
        self.repository = repository
