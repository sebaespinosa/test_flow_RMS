"""
GraphQL schema combining all domain queries and mutations.
"""

import strawberry
from app.tenants.graphql.queries import TenantQuery
from app.tenants.graphql.mutations import TenantMutation
from app.invoices.graphql.queries import InvoiceQuery
from app.invoices.graphql.mutations import InvoiceMutation


@strawberry.type
class Query(TenantQuery, InvoiceQuery):
    """Root GraphQL Query combining all domain queries"""
    pass


@strawberry.type
class Mutation(TenantMutation, InvoiceMutation):
    """Root GraphQL Mutation combining all domain mutations"""
    pass


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
