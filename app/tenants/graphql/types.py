"""
Strawberry GraphQL types for Tenants domain.
"""

from datetime import datetime
import strawberry
from app.tenants.models import TenantEntity


@strawberry.type
class TenantType:
    """GraphQL type for Tenant"""
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @staticmethod
    def from_entity(entity: TenantEntity) -> "TenantType":
        """Convert TenantEntity to TenantType"""
        return TenantType(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


@strawberry.input
class CreateTenantInput:
    """Input type for creating a tenant"""
    name: str
    description: str | None = None
