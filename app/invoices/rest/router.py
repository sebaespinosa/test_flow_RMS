"""
FastAPI router for Invoice REST endpoints.
Delegates to service layer for business logic.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.invoices.repository import InvoiceRepository
from app.invoices.service import InvoiceService
from app.invoices.rest.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceRead,
    InvoiceFilters,
)
from app.tenants.repository import TenantRepository


router = APIRouter(
    prefix="/tenants/{tenant_id}/invoices",
    tags=["invoices"]
)


def get_invoice_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> InvoiceService:
    """
    Dependency injection for InvoiceService.
    
    Args:
        db: Database session from FastAPI dependency
        
    Returns:
        Configured InvoiceService instance
    """
    invoice_repository = InvoiceRepository(db)
    tenant_repository = TenantRepository(db)
    return InvoiceService(
        repository=invoice_repository,
        tenant_repository=tenant_repository
    )


@router.post(
    "",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new invoice",
    description="Create a new invoice for the specified tenant"
)
async def create_invoice(
    tenant_id: int,
    data: InvoiceCreate,
    service: Annotated[InvoiceService, Depends(get_invoice_service)]
) -> InvoiceRead:
    """
    Create new invoice.
    
    Args:
        tenant_id: Tenant ID from path parameter
        data: Invoice creation data
        service: Injected InvoiceService
        
    Returns:
        Created invoice
    """
    invoice = await service.create_invoice(data, tenant_id)
    return InvoiceRead.from_entity(invoice)


@router.get(
    "/{invoice_id}",
    response_model=InvoiceRead,
    summary="Get invoice by ID",
    description="Retrieve a single invoice by ID within tenant scope"
)
async def get_invoice(
    tenant_id: int,
    invoice_id: int,
    service: Annotated[InvoiceService, Depends(get_invoice_service)]
) -> InvoiceRead:
    """
    Get invoice by ID.
    
    Args:
        tenant_id: Tenant ID from path parameter
        invoice_id: Invoice ID from path parameter
        service: Injected InvoiceService
        
    Returns:
        Invoice details
    """
    invoice = await service.get_invoice(invoice_id, tenant_id)
    return InvoiceRead.from_entity(invoice)


@router.get(
    "",
    response_model=list[InvoiceRead],
    summary="List invoices",
    description="List all invoices for tenant with optional filtering"
)
async def list_invoices(
    tenant_id: int,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    status: Annotated[str | None, Query()] = None,
    vendor_id: Annotated[int | None, Query()] = None,
    min_amount: Annotated[float | None, Query(ge=0)] = None,
    max_amount: Annotated[float | None, Query(ge=0)] = None,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
    service: Annotated[InvoiceService, Depends(get_invoice_service)] = None
) -> list[InvoiceRead]:
    """
    List invoices with optional filtering.
    
    Args:
        tenant_id: Tenant ID from path parameter
        skip: Number of records to skip (pagination)
        limit: Maximum records to return
        status: Filter by status
        vendor_id: Filter by vendor ID
        min_amount: Minimum amount filter
        max_amount: Maximum amount filter
        start_date: Start date for invoice_date range (ISO format)
        end_date: End date for invoice_date range (ISO format)
        service: Injected InvoiceService
        
    Returns:
        List of invoices
    """
    invoices = await service.list_invoices(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        status=status,
        vendor_id=vendor_id,
        min_amount=min_amount,
        max_amount=max_amount,
        start_date=start_date,
        end_date=end_date,
    )
    return [InvoiceRead.from_entity(inv) for inv in invoices]


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceRead,
    summary="Update invoice",
    description="Partially update an invoice (PATCH)"
)
async def update_invoice(
    tenant_id: int,
    invoice_id: int,
    data: InvoiceUpdate,
    service: Annotated[InvoiceService, Depends(get_invoice_service)]
) -> InvoiceRead:
    """
    Update invoice with partial data.
    
    Args:
        tenant_id: Tenant ID from path parameter
        invoice_id: Invoice ID from path parameter
        data: Fields to update
        service: Injected InvoiceService
        
    Returns:
        Updated invoice
    """
    invoice = await service.update_invoice(invoice_id, data, tenant_id)
    return InvoiceRead.from_entity(invoice)


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete invoice",
    description="Delete an invoice by ID"
)
async def delete_invoice(
    tenant_id: int,
    invoice_id: int,
    service: Annotated[InvoiceService, Depends(get_invoice_service)]
) -> None:
    """
    Delete invoice.
    
    Args:
        tenant_id: Tenant ID from path parameter
        invoice_id: Invoice ID from path parameter
        service: Injected InvoiceService
    """
    await service.delete_invoice(invoice_id, tenant_id)
