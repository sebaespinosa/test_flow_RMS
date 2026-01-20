"""
Invoice repository - data access layer implementation.
Handles all database operations for invoices.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.invoices.models import InvoiceEntity
from app.invoices.interfaces import IInvoiceRepository


class InvoiceRepository(IInvoiceRepository):
    """
    Concrete implementation of invoice repository.
    Uses SQLAlchemy async session for database operations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        """
        Persist a new invoice entity.
        
        Args:
            entity: InvoiceEntity to create
            
        Returns:
            Created InvoiceEntity with generated ID
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, invoice_id: int, tenant_id: int) -> InvoiceEntity | None:
        """
        Retrieve invoice by ID within tenant scope.
        CRITICAL: Always filters by tenant_id for multi-tenant isolation.
        
        Args:
            invoice_id: Invoice primary key
            tenant_id: Tenant ID for isolation
            
        Returns:
            InvoiceEntity if found, None otherwise
        """
        stmt = select(InvoiceEntity).where(
            and_(
                InvoiceEntity.id == invoice_id,
                InvoiceEntity.tenant_id == tenant_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
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
        CRITICAL: Always filters by tenant_id for multi-tenant isolation.
        
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
        # Build base query with tenant filter
        stmt = select(InvoiceEntity).where(InvoiceEntity.tenant_id == tenant_id)
        
        # Apply optional filters
        if status is not None:
            stmt = stmt.where(InvoiceEntity.status == status)
        
        if vendor_id is not None:
            stmt = stmt.where(InvoiceEntity.vendor_id == vendor_id)
        
        if min_amount is not None:
            stmt = stmt.where(InvoiceEntity.amount >= min_amount)
        
        if max_amount is not None:
            stmt = stmt.where(InvoiceEntity.amount <= max_amount)
        
        if start_date is not None:
            stmt = stmt.where(InvoiceEntity.invoice_date >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(InvoiceEntity.invoice_date <= end_date)
        
        # Apply pagination and ordering
        stmt = stmt.order_by(InvoiceEntity.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(self, entity: InvoiceEntity) -> InvoiceEntity:
        """
        Update an existing invoice entity.
        Entity must already be attached to session.
        
        Args:
            entity: InvoiceEntity with updated fields
            
        Returns:
            Updated InvoiceEntity
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, invoice_id: int, tenant_id: int) -> bool:
        """
        Delete an invoice by ID within tenant scope.
        CRITICAL: Always filters by tenant_id for multi-tenant isolation.
        
        Args:
            invoice_id: Invoice primary key
            tenant_id: Tenant ID for isolation
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(invoice_id, tenant_id)
        if not entity:
            return False
        
        await self.session.delete(entity)
        await self.session.flush()
        return True
    
    async def exists_by_invoice_number(
        self,
        invoice_number: str,
        tenant_id: int,
        exclude_id: int | None = None
    ) -> bool:
        """
        Check if an invoice number exists within a tenant.
        CRITICAL: Always filters by tenant_id for multi-tenant isolation.
        
        Args:
            invoice_number: Invoice number to check
            tenant_id: Tenant ID for isolation
            exclude_id: Optional invoice ID to exclude (for updates)
            
        Returns:
            True if exists, False otherwise
        """
        stmt = select(func.count(InvoiceEntity.id)).where(
            and_(
                InvoiceEntity.invoice_number == invoice_number,
                InvoiceEntity.tenant_id == tenant_id
            )
        )
        
        if exclude_id is not None:
            stmt = stmt.where(InvoiceEntity.id != exclude_id)
        
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return count > 0
