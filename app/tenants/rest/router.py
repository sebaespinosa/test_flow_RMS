"""
FastAPI router for Tenants endpoints.
Implements REST API with dependency injection and validation.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.tenants.service import TenantService
from app.tenants.repository import TenantRepository
from app.tenants.rest.schemas import (
    TenantCreate,
    TenantUpdate,
    TenantRead,
    TenantListResponse
)

# Create router (without prefix - prefix will be added by app at registration)
router = APIRouter(tags=["tenants"])


# Dependency injection functions
def get_tenant_repository(db: AsyncSession = Depends(get_db)) -> TenantRepository:
    """
    Inject TenantRepository with database session.
    
    Args:
        db: AsyncSession dependency from FastAPI
        
    Returns:
        TenantRepository instance
    """
    return TenantRepository(db)


def get_tenant_service(
    repository: TenantRepository = Depends(get_tenant_repository)
) -> TenantService:
    """
    Inject TenantService with repository dependency.
    
    Args:
        repository: TenantRepository from dependency chain
        
    Returns:
        TenantService instance
    """
    return TenantService(repository)


# Endpoints

@router.post(
    "",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new tenant",
    description="Create a new tenant. Returns 409 Conflict if name already exists."
)
async def create_tenant(
    data: TenantCreate,
    service: TenantService = Depends(get_tenant_service)
) -> TenantRead:
    """
    Create a new tenant.
    
    Request body:
    - name: Unique tenant name (required)
    - description: Optional description
    
    Returns:
    - 201: Created tenant with ID and timestamps
    - 409: Name conflict (duplicate tenant name)
    - 422: Validation error
    """
    tenant = await service.create_tenant(data)
    return TenantRead.model_validate(tenant)


@router.get(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Get tenant by ID",
    description="Retrieve a specific tenant by its ID."
)
async def get_tenant(
    tenant_id: int,
    service: TenantService = Depends(get_tenant_service)
) -> TenantRead:
    """
    Get tenant by ID.
    
    Path parameters:
    - tenant_id: Tenant ID to retrieve
    
    Returns:
    - 200: Tenant details
    - 404: Tenant not found
    """
    tenant = await service.get_tenant(tenant_id)
    return TenantRead.model_validate(tenant)


@router.get(
    "",
    response_model=TenantListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tenants",
    description="List all tenants with pagination and filtering."
)
async def list_tenants(
    skip: int = Query(0, ge=0, description="Pagination offset (default 0)"),
    limit: int = Query(
        50,
        ge=1,
        le=1000,
        description="Items per page (default 50, max 1000)"
    ),
    is_active: bool | None = Query(
        None,
        description="Filter by active status (true/false/null for no filter)"
    ),
    created_date_start: datetime | None = Query(
        None,
        description="Filter by creation date start (ISO 8601 format, inclusive)"
    ),
    created_date_end: datetime | None = Query(
        None,
        description="Filter by creation date end (ISO 8601 format, inclusive)"
    ),
    service: TenantService = Depends(get_tenant_service)
) -> TenantListResponse:
    """
    List all tenants with pagination and filtering.
    
    Query parameters:
    - skip: Pagination offset (default 0)
    - limit: Items per page (default 50, max 1000)
    - is_active: Filter by active status (optional)
    - created_date_start: Filter from creation date (ISO format, optional)
    - created_date_end: Filter to creation date (ISO format, optional)
    
    Examples:
    - GET /tenants?skip=0&limit=50
    - GET /tenants?is_active=true
    - GET /tenants?created_date_start=2024-01-01T00:00:00
    - GET /tenants?is_active=true&limit=100&created_date_start=2025-01-01
    
    Returns:
    - 200: Paginated list of tenants with metadata
    """
    tenants, total = await service.list_tenants(
        skip=skip,
        limit=limit,
        is_active=is_active,
        created_date_start=created_date_start,
        created_date_end=created_date_end
    )
    
    return TenantListResponse(
        items=[TenantRead.model_validate(t) for t in tenants],
        total=total,
        skip=skip,
        limit=limit
    )


@router.patch(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Update tenant",
    description="Partially update a tenant (only provided fields are updated)."
)
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    service: TenantService = Depends(get_tenant_service)
) -> TenantRead:
    """
    Update tenant details (partial update).
    Only provided fields are updated, omitted fields remain unchanged.
    
    Path parameters:
    - tenant_id: Tenant ID to update
    
    Request body:
    - name: New tenant name (optional)
    - description: New description (optional)
    
    Returns:
    - 200: Updated tenant
    - 404: Tenant not found
    - 409: Name conflict (another tenant has this name)
    - 422: Validation error
    """
    tenant = await service.update_tenant(tenant_id, data)
    return TenantRead.model_validate(tenant)


@router.delete(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Soft delete tenant",
    description="Soft delete a tenant (sets is_active to False, preserves data)."
)
async def delete_tenant(
    tenant_id: int,
    service: TenantService = Depends(get_tenant_service)
) -> TenantRead:
    """
    Soft delete tenant.
    Sets is_active to False, preserving data for auditing and referential integrity.
    Deleted tenants can be reactivated if needed.
    
    Path parameters:
    - tenant_id: Tenant ID to delete
    
    Returns:
    - 200: Soft-deleted tenant (is_active=False)
    - 404: Tenant not found
    """
    tenant = await service.soft_delete_tenant(tenant_id)
    return TenantRead.model_validate(tenant)


@router.post(
    "/{tenant_id}/reactivate",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Reactivate tenant",
    description="Reactivate a soft-deleted tenant (sets is_active to True)."
)
async def reactivate_tenant(
    tenant_id: int,
    service: TenantService = Depends(get_tenant_service)
) -> TenantRead:
    """
    Reactivate a soft-deleted tenant.
    Sets is_active back to True.
    
    Path parameters:
    - tenant_id: Tenant ID to reactivate
    
    Returns:
    - 200: Reactivated tenant (is_active=True)
    - 404: Tenant not found
    """
    tenant = await service.reactivate_tenant(tenant_id)
    return TenantRead.model_validate(tenant)
