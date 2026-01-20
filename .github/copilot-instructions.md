# Copilot Development Instructions

**Version:** v1.0  
**Last Updated:** January 20, 2026

## Quick Reference for AI-Assisted Development

This file contains the core principles, patterns, and guidelines for developing in this FastAPI + GraphQL + SQLAlchemy codebase. Follow these rules for all code generation and modifications.

---

## Core Principles

### SOLID Principles

All code must adhere to SOLID principles:

- **Single Responsibility**: Each class/function has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Subtypes must be substitutable for base types
- **Interface Segregation**: Many specific interfaces over one general interface
- **Dependency Inversion**: Depend on abstractions, not concretions

### Architectural Patterns

1. **Repository Pattern**: Always use repositories for data access, even with SQLAlchemy
2. **Service Layer**: Business logic lives in service classes, injected into routes
3. **Dependency Injection**: First-class citizen - use constructor injection for all dependencies
4. **Separation of Concerns**: Clear boundaries between layers (API → Service → Repository → Models)

---

## Project Structure (Vertical Slices)

Each domain is self-contained with all its layers:

```
app/
├── config/                      # Global config, security, auth utilities
│   ├── logging.py              # Logging configurations
│   ├── middleware.py           # Middleware setup
│   └── exceptions.py           # Exception handlers
├── [domain]/                    # e.g., "tenants", "invoices", "reconciliation"
│   ├── __init__.py             # Package marker (REQUIRED)
│   ├── models.py               # SQLAlchemy Entities (suffix: Entity)
│   ├── interfaces.py           # Repository ABCs/Protocols
│   ├── repository.py           # Repository implementations
│   ├── service.py              # Business logic (delivery-agnostic)
│   ├── rest/
│   │   ├── router.py           # FastAPI endpoints
│   │   └── schemas.py          # Pydantic DTOs (suffix: Create/Read/Update)
│   └── graphql/
│       ├── types.py            # Strawberry types (suffix: Type)
│       ├── queries.py          # GraphQL query resolvers
│       ├── mutations.py        # GraphQL mutation resolvers
│       └── dataloaders.py      # DataLoaders for batch operations
└── main.py                      # Application entry point
```

---

## Naming Conventions

### Python Code (PEP 8 Strict)

- **Classes**: `PascalCase`
  - SQLAlchemy: `UserEntity`, `InvoiceEntity`
  - Pydantic: `UserCreate`, `UserRead`, `UserUpdate`
  - Strawberry: `UserType`, `InvoiceType`
  - Services: `UserService`, `ReconciliationService`
  - Repositories: `UserRepository`, `InvoiceRepository`
- **Functions/Methods/Variables**: `snake_case`
  - Examples: `get_user_by_id()`, `user_id`, `is_active`
- **Constants**: `UPPER_SNAKE_CASE`
  - Examples: `MAX_LOGIN_ATTEMPTS`, `DATABASE_URL`
- **Files/Folders**: `lowercase` (avoid underscores)
  - Examples: `models.py`, `service.py`, `users/`, `invoices/`

### API Notation Bridge

- **Python (Internal)**: Always use `snake_case`
- **JSON/GraphQL (External)**: Use `camelCase`
- **Bridge**: Use Pydantic's `alias_generator=to_camel` in base schema
- **Database**: Always use `snake_case` for tables and columns

---

## Data Layer Guidelines

### Model Separation

**NEVER mix concerns:**

- **SQLAlchemy Entities** (`models.py`): The single source of truth for database structure
- **Pydantic DTOs** (`rest/schemas.py`): Request/response validation for REST API
- **Strawberry Types** (`graphql/types.py`): GraphQL schema types

### Entity Naming

Always use the `Entity` suffix for SQLAlchemy models:

```python
# ✅ Correct
class UserEntity(Base):
    __tablename__ = "users"

# ❌ Wrong
class User(Base):  # Too generic, causes import conflicts
```

### N+1 Prevention

**ALWAYS** use eager loading in repositories:

- **One-to-Many / Many-to-Many**: Use `selectinload()` (separate query with IN clause)
- **Many-to-One / One-to-One**: Use `joinedload()` (SQL JOIN)
- **Never** rely on lazy loading in production code

```python
# ✅ Correct
stmt = select(InvoiceEntity).options(
    selectinload(InvoiceEntity.transactions),
    joinedload(InvoiceEntity.vendor)
)

# ❌ Wrong
stmt = select(InvoiceEntity)  # Will cause N+1 queries
```

### When to Bypass ORM

Use SQLAlchemy Core or Raw SQL for:

1. **Complex Aggregations**: `GROUP BY`, `HAVING`, window functions
2. **Bulk Operations**: Mass updates/inserts (use `update()` or `insert()` statements)
3. **Recursive Queries**: Tree structures (use CTEs)
4. **Performance-Critical Queries**: When ORM overhead is measurable

---

## Service Layer Pattern

### Responsibilities

The service layer:

1. Receives Pydantic DTOs or primitives
2. Performs business logic and validations
3. Converts DTOs to SQLAlchemy Entities
4. Calls repository methods
5. Returns Entities (NOT DTOs)

### Anti-Patterns to Avoid

- ❌ Service depending on REST schemas or GraphQL types
- ❌ Service returning Pydantic models
- ❌ Business logic in controllers/routers
- ❌ Direct database access in controllers

```python
# ✅ Correct Service Method
async def create_invoice(
    self,
    data: InvoiceCreate,  # Pydantic DTO
    tenant_id: int
) -> InvoiceEntity:  # Returns Entity
    entity = InvoiceEntity(
        tenant_id=tenant_id,
        amount=data.amount,
        # ... map fields
    )
    return await self.repository.create(entity)
```

---

## Dependency Injection Strategy

### Constructor Injection (Preferred)

```python
class InvoiceService:
    def __init__(
        self,
        repository: InvoiceRepository,
        vendor_service: VendorService
    ):
        self.repository = repository
        self.vendor_service = vendor_service
```

### FastAPI Dependencies

```python
def get_invoice_service(
    db: AsyncSession = Depends(get_db),
) -> InvoiceService:
    repository = InvoiceRepository(db)
    return InvoiceService(repository)
```

---

## GraphQL-Specific Rules

### Avoid N+1 with DataLoaders

**ALWAYS** use DataLoaders for relationships:

```python
# graphql/dataloaders.py
async def load_vendors(keys: list[int]) -> list[VendorEntity]:
    # Batch load all vendors in one query
    stmt = select(VendorEntity).where(VendorEntity.id.in_(keys))
    result = await session.execute(stmt)
    vendors_dict = {v.id: v for v in result.scalars()}
    return [vendors_dict.get(k) for k in keys]
```

### Resolver Delegation

GraphQL resolvers should delegate to the service layer:

```python
# ✅ Correct
@strawberry.mutation
async def create_invoice(
    self,
    info: Info,
    input: InvoiceCreateInput
) -> InvoiceType:
    service = get_invoice_service()
    entity = await service.create_invoice(input, tenant_id)
    return InvoiceType.from_entity(entity)

# ❌ Wrong - business logic in resolver
```

---

## Middleware vs Dependencies

### Use Middleware For:

- ✅ OpenTelemetry / Distributed Tracing
- ✅ Logging / Request ID correlation
- ✅ CORS headers
- ✅ Compression (GZip)
- ✅ Global rate limiting

### Use Dependencies For:

- ✅ Authentication / Authorization
- ✅ Database sessions
- ✅ Current user injection
- ✅ **Idempotency checks** (intercept before route)
- ✅ Per-route rate limiting
- ✅ Feature flags

**Rule of Thumb**: Middleware = Passive/Universal, Dependencies = Active/Logic-dependent

### Idempotency-Specific Guidelines

- ✅ Use as FastAPI Dependency, not middleware
- ✅ Check BEFORE route handler executes
- ✅ Return cached response if retry detected (short-circuit)
- ✅ Wrap operation logic in explicit transaction with idempotency storage
- ✅ Store idempotency record in SAME transaction as operation
- ✅ Require `X-Idempotency-Key` header for POST/PATCH endpoints that modify data
- ❌ Don't store idempotency keys indefinitely (set 24-48 hour TTL)
- ❌ Don't check idempotency for GET/DELETE endpoints (already idempotent by HTTP)

---

## Database & Migration Strategy

### Central Model Registration

Keep models in domain folders but register centrally for Alembic discovery:

```python
# app/database/base.py
from app.tenants.models import TenantEntity
from app.invoices.models import InvoiceEntity
from app.auth.models import TokenEntity
from app.infrastructure.idempotency.models import IdempotencyRecordEntity  # Infrastructure models

# Now Alembic can detect ALL models (domains + infrastructure) for migrations
```

### Multi-Tenancy Enforcement

**Every query must filter by `tenant_id`:**

```python
# ✅ Correct
async def get_invoices(self, tenant_id: int):
    stmt = select(InvoiceEntity).where(
        InvoiceEntity.tenant_id == tenant_id
    )
    return await self.session.execute(stmt)
```

### Idempotency & Transactions

**Unit of Work Pattern:** When implementing idempotency, both the business operation AND idempotency key storage must occur in the same transaction. Use `async with session.begin()` to ensure atomicity:

```python
# ✅ Correct - Atomic operation + key storage
async with self.session.begin():
    # 1. Perform operation
    result = await self.repository.create(entity)
    # 2. Store idempotency key in same transaction
    await idempotency_repo.store(key, result)
    # Both succeed or both fail (no duplicates on retry)

# ❌ Wrong - Key stored outside transaction (causes duplicates on retry)
result = await self.repository.create(entity)
await idempotency_repo.store(key, result)  # Separate transaction = risk of duplicate
```

---

## Python 3.13 Specifics

### Type Hints

Use new Python 3.13 features:

```python
from typing import TypeIs

def is_valid_user(user: UserEntity | None) -> TypeIs[UserEntity]:
    return user is not None and user.is_active
```

### Async Performance

- Use `asyncpg` driver for PostgreSQL
- Leverage improved event loop performance
- Use async context managers consistently

### Package Requirements

- Maintain `__init__.py` in ALL directories for proper import resolution
- Required for: mypy, pytest, FastAPI dependency injection

---

## Testing Guidelines

### Tools

- `pytest` for test framework
- `pytest-mock` for mocking
- `pytest-asyncio` for async tests

### Test Structure

```python
# tests/[domain]/test_service.py
async def test_create_invoice(mock_repository):
    service = InvoiceService(repository=mock_repository)
    result = await service.create_invoice(data, tenant_id=1)
    
    mock_repository.create.assert_called_once()
    assert result.amount == data.amount
```

### Mock at Service Boundaries

- Mock repositories when testing services
- Mock services when testing controllers
- Use real database for integration tests

---

## Common Anti-Patterns to Avoid

1. ❌ Using generic names like `Model`, `Schema`, `Type` without suffixes
2. ❌ Putting business logic in routers/controllers
3. ❌ Direct SQL in service layer (use repository)
4. ❌ Lazy loading in production (always eager load)
5. ❌ Forgetting `tenant_id` filters
6. ❌ Mixing camelCase in Python code
7. ❌ Skipping `__init__.py` files
8. ❌ Service returning Pydantic models instead of Entities
9. ❌ **Storing idempotency record OUTSIDE the operation transaction** (causes duplicates on retry)
10. ❌ **Checking idempotency in middleware instead of as a dependency** (can't differentiate GraphQL operations)
11. ❌ **Keeping idempotency keys indefinitely** (unbounded database growth)
12. ❌ **Trusting client-provided cached responses** (always store YOUR response)

---

## Quick Decision Matrix

| Need to... | Use... | Location |
|------------|--------|----------|
| Add database table | SQLAlchemy Entity | `models.py` |
| Define REST input | Pydantic Model | `rest/schemas.py` |
| Define GraphQL type | Strawberry Type | `graphql/types.py` |
| Add business logic | Service method | `service.py` |
| Query database | Repository method | `repository.py` |
| Add REST endpoint | Router function | `rest/router.py` |
| Add GraphQL query | Query resolver | `graphql/queries.py` |
| Prevent N+1 (REST) | Eager loading | `repository.py` |
| Prevent N+1 (GraphQL) | DataLoader | `graphql/dataloaders.py` |
| Add tracing | Middleware | `config/middleware.py` |
| Add auth check | Dependency | `auth/dependencies.py` |
| **Add idempotency** | **Dependency + Service** | **`infrastructure/idempotency/` + `service.py`** |
| **Prevent duplicate writes** | **Unit of Work transaction** | **Service layer with explicit `async with session.begin()`** |

---

**Remember**: Clean architecture is about maintaining boundaries. When in doubt, add a layer rather than breaking an existing boundary.
