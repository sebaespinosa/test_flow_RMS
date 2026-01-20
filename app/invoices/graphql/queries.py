"""
GraphQL queries for Invoices domain.
"""

from typing import List
import strawberry
from app.invoices.graphql.types import InvoiceType, InvoiceFilterInput
from app.invoices.service import InvoiceService


@strawberry.type
class InvoiceQuery:
    """GraphQL queries for invoices."""

    @strawberry.field
    async def invoices(
        self,
        info: strawberry.Info,
        tenant_id: int,
        filters: InvoiceFilterInput | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[InvoiceType]:
        """List invoices for a tenant with optional filters and pagination."""
        service: InvoiceService = info.context["invoice_service"]

        invoices = await service.list_invoices(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            status=filters.status if filters else None,
            vendor_id=filters.vendor_id if filters else None,
            min_amount=filters.min_amount if filters else None,
            max_amount=filters.max_amount if filters else None,
            start_date=filters.start_date if filters else None,
            end_date=filters.end_date if filters else None,
        )

        return [InvoiceType.from_entity(inv) for inv in invoices]
