"""
GraphQL schema combining all domain queries and mutations.
"""

import strawberry
from app.tenants.graphql.queries import TenantQuery
from app.tenants.graphql.mutations import TenantMutation


@strawberry.type
class Query(TenantQuery):
    """Root GraphQL Query combining all domain queries"""
    pass


@strawberry.type
class Mutation(TenantMutation):
    """Root GraphQL Mutation combining all domain mutations"""
    pass


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
