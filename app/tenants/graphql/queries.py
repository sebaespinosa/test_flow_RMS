"""
GraphQL queries for Tenants domain.
"""

import strawberry
from typing import List
from fastapi import Depends
from app.tenants.graphql.types import TenantType
from app.tenants.service import TenantService
from app.tenants.rest.router import get_tenant_service


@strawberry.type
class TenantQuery:
    """GraphQL queries for Tenants"""
    
    @strawberry.field
    async def tenants(
        self,
        info: strawberry.Info,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None
    ) -> List[TenantType]:
        """
        Query all tenants with optional filtering and pagination.
        
        Args:
            skip: Number of records to skip (default: 0)
            limit: Maximum records to return (default: 50)
            is_active: Filter by active status (optional)
        
        Returns:
            List of tenants
        """
        # Get service from FastAPI dependency injection context
        service: TenantService = info.context["tenant_service"]
        
        # Call service layer
        tenants, _ = await service.list_tenants(
            skip=skip,
            limit=limit,
            is_active=is_active
        )
        
        # Convert entities to GraphQL types
        return [TenantType.from_entity(tenant) for tenant in tenants]
