"""
GraphQL mutations for Tenants domain.
"""

import strawberry
from app.tenants.graphql.types import TenantType, CreateTenantInput
from app.tenants.service import TenantService
from app.tenants.rest.schemas import TenantCreate


@strawberry.type
class TenantMutation:
    """GraphQL mutations for Tenants"""
    
    @strawberry.mutation
    async def create_tenant(
        self,
        info: strawberry.Info,
        input: CreateTenantInput
    ) -> TenantType:
        """
        Create a new tenant.
        
        Args:
            input: Tenant creation data
        
        Returns:
            Created tenant
        
        Raises:
            ConflictError: If tenant with same name already exists
        """
        # Get service from FastAPI dependency injection context
        service: TenantService = info.context["tenant_service"]
        
        # Convert GraphQL input to Pydantic DTO
        tenant_data = TenantCreate(
            name=input.name,
            description=input.description
        )
        
        # Call service layer (service will raise ConflictError if duplicate)
        tenant = await service.create_tenant(tenant_data)
        
        # Convert entity to GraphQL type
        return TenantType.from_entity(tenant)
