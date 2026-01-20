"""
Repository interface for Invoice operations.
Defines the contract for data access layer.
"""

from typing import Protocol
from app.invoices.models import InvoiceEntity


class IInvoiceRepository(Protocol):
    """
    Protocol defining the contract for invoice data access.
    All implementations must provide these methods.
    """
    
    async def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        """
        Persist a new invoice entity.
        
        Args:
            entity: InvoiceEntity to create
            
        Returns:
            Created InvoiceEntity with generated ID
        """
        ...
    
    async def get_by_id(self, invoice_id: int, tenant_id: int) -> InvoiceEntity | None:
        """
        Retrieve invoice by ID within tenant scope.
        
        Args:
            invoice_id: Invoice primary key
            tenant_id: Tenant ID for isolation
            
        Returns:
            InvoiceEntity if found, None otherwise
        """
        ...
    
    async def get_all(
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
        Retrieve all invoices for a tenant with optional filtering.
        
        Args:
            tenant_id: Tenant ID for isolation
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
        """
        ...
    
    async def update(self, entity: InvoiceEntity) -> InvoiceEntity:
        """
        Update an existing invoice entity.
        
        Args:
            entity: InvoiceEntity with updated fields
            
        Returns:
            Updated InvoiceEntity
        """
        ...
    
    async def delete(self, invoice_id: int, tenant_id: int) -> bool:
        """
        Delete an invoice by ID within tenant scope.
        
        Args:
            invoice_id: Invoice primary key
            tenant_id: Tenant ID for isolation
            
        Returns:
            True if deleted, False if not found
        """
        ...
    
    async def exists_by_invoice_number(
        self,
        invoice_number: str,
        tenant_id: int,
        exclude_id: int | None = None
    ) -> bool:
        """
        Check if an invoice number exists within a tenant.
        
        Args:
            invoice_number: Invoice number to check
            tenant_id: Tenant ID for isolation
            exclude_id: Optional invoice ID to exclude (for updates)
            
        Returns:
            True if exists, False otherwise
        """
        ...
