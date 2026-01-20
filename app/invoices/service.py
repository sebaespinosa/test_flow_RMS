"""
Invoice service - business logic layer.
Handles invoice operations and validations independent of delivery mechanism (REST/GraphQL).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from app.invoices.models import InvoiceEntity
from app.invoices.interfaces import IInvoiceRepository
from app.tenants.interfaces import ITenantRepository
from app.config.exceptions import ConflictError, NotFoundError, ValidationError

if TYPE_CHECKING:
    from app.invoices.rest.schemas import InvoiceCreate, InvoiceUpdate


class InvoiceService:
    """
    Service layer for invoice operations.
    Encapsulates business logic and delegates to repository.
    """
    
    def __init__(
        self,
        repository: IInvoiceRepository,
        tenant_repository: ITenantRepository
    ):
        """
        Initialize service with repository dependencies.
        
        Args:
            repository: IInvoiceRepository implementation
            tenant_repository: ITenantRepository implementation for tenant validation
        """
        self.repository = repository
        self.tenant_repository = tenant_repository
    
    async def _validate_tenant_exists(self, tenant_id: int) -> None:
        """
        Validate that tenant exists.
        
        Args:
            tenant_id: Tenant ID to validate
            
        Raises:
            NotFoundError: If tenant not found
        """
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError(detail=f"Tenant with id {tenant_id} not found")
        if not tenant.is_active:
            raise ValidationError(detail=f"Tenant with id {tenant_id} is not active")
    
    async def create_invoice(
        self,
        data: 'InvoiceCreate',
        tenant_id: int
    ) -> InvoiceEntity:
        """
        Create new invoice with validation.
        
        Args:
            data: InvoiceCreate DTO with invoice details
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            Created InvoiceEntity
            
        Raises:
            NotFoundError: If tenant not found
            ConflictError: If invoice_number already exists for tenant
            ValidationError: If tenant is not active
        """
        # Validate tenant exists and is active
        await self._validate_tenant_exists(tenant_id)
        
        # Check for duplicate invoice number within tenant
        if data.invoice_number:
            if await self.repository.exists_by_invoice_number(
                data.invoice_number,
                tenant_id
            ):
                raise ConflictError(
                    detail=f"Invoice with number '{data.invoice_number}' already exists for this tenant"
                )
        
        # Validate business rules
        if data.due_date and data.invoice_date:
            if data.due_date < data.invoice_date:
                raise ValidationError(
                    detail="Due date cannot be before invoice date"
                )
        
        # Create entity and save
        invoice = InvoiceEntity(
            tenant_id=tenant_id,
            vendor_id=data.vendor_id,
            invoice_number=data.invoice_number,
            amount=data.amount,
            currency=data.currency,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            description=data.description,
            status=data.status if data.status else "open"
        )
        
        return await self.repository.create(invoice)
    
    async def get_invoice(self, invoice_id: int, tenant_id: int) -> InvoiceEntity:
        """
        Get invoice by ID within tenant scope.
        
        Args:
            invoice_id: Invoice primary key
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            InvoiceEntity
            
        Raises:
            NotFoundError: If invoice not found
        """
        invoice = await self.repository.get_by_id(invoice_id, tenant_id)
        if not invoice:
            raise NotFoundError(
                detail=f"Invoice with id {invoice_id} not found for tenant {tenant_id}"
            )
        return invoice
    
    async def list_invoices(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        vendor_id: int | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[InvoiceEntity]:
        """
        List all invoices for a tenant with optional filtering.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            status: Filter by invoice status
            vendor_id: Filter by vendor ID
            min_amount: Minimum amount filter
            max_amount: Maximum amount filter
            start_date: Start date for invoice_date range (ISO format)
            end_date: End date for invoice_date range (ISO format)
            
        Returns:
            List of InvoiceEntity objects
            
        Raises:
            ValidationError: If filter parameters are invalid
        """
        # Validate pagination
        if skip < 0:
            raise ValidationError(detail="Skip must be non-negative")
        if limit < 1 or limit > 100:
            raise ValidationError(detail="Limit must be between 1 and 100")
        
        # Validate status if provided
        if status and status not in ["open", "matched", "paid"]:
            raise ValidationError(
                detail=f"Invalid status '{status}'. Must be one of: open, matched, paid"
            )
        
        # Validate amount range
        if min_amount is not None and max_amount is not None:
            if min_amount > max_amount:
                raise ValidationError(
                    detail="Minimum amount cannot be greater than maximum amount"
                )
        
        return await self.repository.get_all(
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
    
    async def update_invoice(
        self,
        invoice_id: int,
        data: 'InvoiceUpdate',
        tenant_id: int
    ) -> InvoiceEntity:
        """
        Update invoice with partial data (PATCH).
        
        Args:
            invoice_id: Invoice primary key
            data: InvoiceUpdate DTO with fields to update
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            Updated InvoiceEntity
            
        Raises:
            NotFoundError: If invoice not found
            ConflictError: If invoice_number conflicts with existing invoice
            ValidationError: If business rules violated
        """
        # Get existing invoice (validates tenant ownership)
        invoice = await self.get_invoice(invoice_id, tenant_id)
        
        # Check for duplicate invoice number if changing
        if data.invoice_number is not None and data.invoice_number != invoice.invoice_number:
            if await self.repository.exists_by_invoice_number(
                data.invoice_number,
                tenant_id,
                exclude_id=invoice_id
            ):
                raise ConflictError(
                    detail=f"Invoice with number '{data.invoice_number}' already exists for this tenant"
                )
        
        # Apply updates (only non-None fields)
        if data.vendor_id is not None:
            invoice.vendor_id = data.vendor_id
        
        if data.invoice_number is not None:
            invoice.invoice_number = data.invoice_number
        
        if data.amount is not None:
            invoice.amount = data.amount
        
        if data.currency is not None:
            invoice.currency = data.currency
        
        if data.invoice_date is not None:
            invoice.invoice_date = data.invoice_date
        
        if data.due_date is not None:
            invoice.due_date = data.due_date
        
        if data.description is not None:
            invoice.description = data.description
        
        if data.status is not None:
            invoice.status = data.status
        
        # Validate business rules after updates
        if invoice.due_date and invoice.invoice_date:
            if invoice.due_date < invoice.invoice_date:
                raise ValidationError(
                    detail="Due date cannot be before invoice date"
                )
        
        return await self.repository.update(invoice)
    
    async def delete_invoice(self, invoice_id: int, tenant_id: int) -> bool:
        """
        Delete invoice by ID within tenant scope.
        
        Args:
            invoice_id: Invoice primary key
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If invoice not found
        """
        deleted = await self.repository.delete(invoice_id, tenant_id)
        if not deleted:
            raise NotFoundError(
                detail=f"Invoice with id {invoice_id} not found for tenant {tenant_id}"
            )
        return deleted
