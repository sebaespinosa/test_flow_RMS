"""
GraphQL mutations for Invoices domain.
"""

import strawberry
from app.invoices.graphql.types import InvoiceType, CreateInvoiceInput
from app.invoices.service import InvoiceService
from app.invoices.rest.schemas import InvoiceCreate


@strawberry.type
class InvoiceMutation:
    """GraphQL mutations for invoices."""

    @strawberry.mutation
    async def create_invoice(
        self,
        info: strawberry.Info,
        tenant_id: int,
        input: CreateInvoiceInput,
    ) -> InvoiceType:
        """Create a new invoice for a tenant."""
        service: InvoiceService = info.context["invoice_service"]

        invoice_data = InvoiceCreate(
            amount=input.amount,
            vendor_id=input.vendor_id,
            invoice_number=input.invoice_number,
            currency=input.currency or "USD",
            invoice_date=input.invoice_date,
            due_date=input.due_date,
            description=input.description,
            status=input.status,
        )

        invoice = await service.create_invoice(invoice_data, tenant_id)
        return InvoiceType.from_entity(invoice)

    @strawberry.mutation
    async def delete_invoice(
        self,
        info: strawberry.Info,
        tenant_id: int,
        invoice_id: int,
    ) -> bool:
        """Delete an invoice by ID for a tenant."""
        service: InvoiceService = info.context["invoice_service"]
        return await service.delete_invoice(invoice_id, tenant_id)
