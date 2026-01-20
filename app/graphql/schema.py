"""
GraphQL schema combining all domain queries and mutations.
"""

import strawberry
from app.tenants.graphql.queries import TenantQuery
from app.tenants.graphql.mutations import TenantMutation
from app.invoices.graphql.queries import InvoiceQuery
from app.invoices.graphql.mutations import InvoiceMutation
from app.bank_transactions.graphql.queries import BankTransactionQuery
from app.bank_transactions.graphql.mutations import BankTransactionMutation


@strawberry.type
class Query(TenantQuery, InvoiceQuery, BankTransactionQuery):
    """Root GraphQL Query combining all domain queries"""
    pass


@strawberry.type
class Mutation(TenantMutation, InvoiceMutation, BankTransactionMutation):
    """Root GraphQL Mutation combining all domain mutations"""
    pass


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
