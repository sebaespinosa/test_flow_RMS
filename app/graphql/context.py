"""
GraphQL context for dependency injection.
"""

from typing import Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.tenants.service import TenantService
from app.tenants.repository import TenantRepository


async def get_graphql_context(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Build GraphQL context with injected dependencies.
    
    This function provides services to GraphQL resolvers through the info.context.
    Pattern: Get services from FastAPI dependency system and pass to GraphQL.
    
    Args:
        db: Database session from FastAPI dependency
    
    Returns:
        Context dictionary with services
    """
    # Create services using constructor injection pattern
    tenant_repository = TenantRepository(db)
    tenant_service = TenantService(tenant_repository)
    
    return {
        "db": db,
        "tenant_service": tenant_service,
    }
