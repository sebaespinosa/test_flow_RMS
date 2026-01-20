"""
Pydantic DTOs for Tenants REST API.
Handles request/response validation and serialization.
"""

from datetime import datetime
from pydantic import Field
from app.common.base_models import BaseSchema, TimestampSchema


class TenantCreate(BaseSchema):
    """
    DTO for creating a tenant.
    Minimal required fields only.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique tenant name"
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional tenant description"
    )


class TenantUpdate(BaseSchema):
    """
    DTO for updating a tenant.
    All fields optional (partial update).
    """
    
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Tenant name"
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Tenant description"
    )


class TenantRead(TimestampSchema):
    """
    DTO for reading a tenant (full entity response).
    Includes all fields and timestamps.
    """
    
    id: int = Field(..., description="Tenant ID")
    name: str = Field(..., description="Tenant name")
    description: str | None = Field(default=None, description="Tenant description")
    is_active: bool = Field(..., description="Soft delete flag (true = active)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class TenantListResponse(BaseSchema):
    """
    DTO for paginated list response.
    Includes items and pagination metadata.
    """
    
    items: list[TenantRead] = Field(..., description="Tenant items in this page")
    total: int = Field(..., description="Total number of tenants (across all pages)")
    skip: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Items per page")
    
    @property
    def page(self) -> int:
        """Calculate current page number (1-indexed)"""
        return (self.skip // self.limit) + 1
    
    @property
    def pages(self) -> int:
        """Calculate total number of pages"""
        return (self.total + self.limit - 1) // self.limit
