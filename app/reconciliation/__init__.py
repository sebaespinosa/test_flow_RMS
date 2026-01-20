"""
Reconciliation domain - Match proposals and confirmations between invoices and bank transactions.

Vertical slice structure:
- models.py: SQLAlchemy entities
- scoring.py: Scoring algorithm
- interfaces.py: Repository ABCs
- repository.py: Database access layer
- service.py: Business logic
- rest/schemas.py: Pydantic DTOs (request/response)
- rest/router.py: FastAPI endpoints
"""
