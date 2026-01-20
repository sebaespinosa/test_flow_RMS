"""
Tenants domain - Multi-tenant support and tenant management.

Vertical slice structure:
- models.py: SQLAlchemy entities
- interfaces.py: Repository ABCs
- repository.py: Database access layer
- service.py: Business logic
- rest/schemas.py: Pydantic DTOs (request/response)
- rest/router.py: FastAPI endpoints
"""
