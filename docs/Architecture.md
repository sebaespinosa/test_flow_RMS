# System Architecture

**Version:** v1.0  
**Last Updated:** January 20, 2026

## Overview

This document defines the architecture for a FastAPI + GraphQL (Strawberry) + SQLAlchemy system built on **Vertical Slice Architecture** principles. Each domain (feature) is organized as a self-contained vertical slice with clear separation between delivery mechanisms (REST/GraphQL), business logic (Services), and data access (Repositories).

---

## Architectural Principles

### 1. Vertical Slice Organization

Unlike traditional layered architecture where all controllers are in one folder, all services in another, etc., we organize by **feature/domain**:

- Each domain folder contains its complete stack: Models → Repository → Service → REST → GraphQL
- Reduces coupling between features
- Makes it easier to understand and modify a single feature
- Enables independent deployment and testing of features

### 2. Multi-Layer Design

Every request flows through these layers in order:

```
┌─────────────────────────────────────────────────────────────┐
│  Delivery Layer (REST/GraphQL)                              │
│  - FastAPI routers (rest/router.py)                         │
│  - Strawberry resolvers (graphql/queries.py, mutations.py)  │
│  - Input validation via Pydantic/Strawberry                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer (Delivery-Agnostic Business Logic)           │
│  - Orchestrates business operations                         │
│  - Converts DTOs to Entities                                │
│  - Enforces business rules                                  │
│  - NO knowledge of HTTP/GraphQL                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Repository Layer (Data Access Interface)                   │
│  - Abstract interface (interfaces.py)                       │
│  - SQL implementation (repository.py)                       │
│  - Query optimization (eager loading)                       │
│  - Multi-tenant filtering                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Data Layer (SQLAlchemy Entities)                           │
│  - Database schema (models.py)                              │
│  - Relationships and constraints                            │
│  - Logic-light (no business rules)                          │
└─────────────────────────────────────────────────────────────┘
```

### 3. Dependency Rule

**Dependencies point inward:**

- Delivery depends on Service
- Service depends on Repository Interface (not implementation)
- Repository depends on Models
- Models depend on nothing (pure data structures)

**Forbidden dependencies:**

- ❌ Models depending on Services
- ❌ Services depending on REST schemas or GraphQL types
- ❌ Repositories depending on Services

---

## Folder Structure Reference

```
app/
├── config/                          # Infrastructure & Cross-Cutting Concerns
│   ├── __init__.py
│   ├── database.py                  # Database connection, session factory
│   ├── settings.py                  # Environment variables, configuration
│   ├── logging.py                   # Structured logging setup
│   ├── middleware.py                # Middleware registration
│   └── exceptions.py                # Global exception handlers
│
├── common/                          # Shared Utilities (Use Sparingly)
│   ├── __init__.py
│   ├── base_models.py               # Base Pydantic schemas
│   ├── base_repository.py           # Repository ABC
│   └── utils.py                     # Generic helpers
│
├── database/                        # Central Model Registry
│   ├── __init__.py
│   └── base.py                      # Import all models for Alembic
│
├── [domain]/                        # Example: tenants, invoices, reconciliation
│   ├── __init__.py                  # REQUIRED - Package marker
│   │
│   ├── models.py                    # SQLAlchemy Entities
│   │   # Classes: TenantEntity, InvoiceEntity, etc.
│   │
│   ├── interfaces.py                # Repository Protocols/ABCs
│   │   # Abstract: TenantRepository, InvoiceRepository
│   │
│   ├── repository.py                # Concrete Repository Implementation
│   │   # Classes: TenantRepositoryImpl, InvoiceRepositoryImpl
│   │
│   ├── service.py                   # Business Logic
│   │   # Classes: TenantService, InvoiceService
│   │
│   ├── dependencies.py              # FastAPI dependency providers
│   │   # Functions: get_tenant_service(), get_current_tenant()
│   │
│   ├── rest/
│   │   ├── __init__.py
│   │   ├── router.py                # FastAPI endpoints
│   │   └── schemas.py               # Pydantic DTOs (Create, Read, Update)
│   │
│   └── graphql/
│       ├── __init__.py
│       ├── types.py                 # Strawberry object types
│       ├── queries.py               # Query resolvers
│       ├── mutations.py             # Mutation resolvers
│       └── dataloaders.py           # Batch loading for N+1 prevention
│
├── main.py                          # Application entry point
└── alembic/                         # Database migrations
    └── versions/
```

---

## Multi-Tenancy Architecture

### Tenant Isolation Strategy

Every piece of data (except `tenants` table itself) is scoped to a tenant:

1. **Database Level**: All tables (except `tenants`) have a `tenant_id` foreign key
2. **Repository Level**: Every query automatically filters by `tenant_id`
3. **Service Level**: Services receive `tenant_id` as a required parameter
4. **API Level**: Tenant context is extracted from JWT token or path parameter

### Enforcement Pattern

```python
# repository.py
class InvoiceRepositoryImpl(InvoiceRepository):
    async def get_by_id(self, invoice_id: int, tenant_id: int) -> InvoiceEntity | None:
        stmt = select(InvoiceEntity).where(
            InvoiceEntity.id == invoice_id,
            InvoiceEntity.tenant_id == tenant_id  # ALWAYS filter by tenant
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

### Security Boundary

The `tenant_id` must be:

- ✅ Extracted from authenticated user's JWT token
- ✅ Validated before any database operation
- ❌ NEVER accepted directly from request body (security risk)

---

## Database Session & Transaction Management

### Session Lifecycle

Use FastAPI dependencies to manage database sessions:

```python
# config/database.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Transaction Boundaries

**General Rule**: One HTTP request = One database transaction

- Service methods don't manage transactions (no explicit commit/rollback)
- Transactions are handled at the dependency level
- For multi-step operations, use service orchestration within a single transaction

### Explicit Transaction Control

For complex operations requiring manual control:

```python
# service.py
async def reconcile_invoices(self, tenant_id: int) -> list[MatchEntity]:
    async with self.session.begin():  # Explicit transaction
        # Step 1: Load invoices
        invoices = await self.invoice_repo.get_open_invoices(tenant_id)
        
        # Step 2: Load transactions
        transactions = await self.transaction_repo.get_unmatched(tenant_id)
        
        # Step 3: Create matches
        matches = self._compute_matches(invoices, transactions)
        
        # Step 4: Persist
        for match in matches:
            await self.match_repo.create(match)
        
        return matches
        # Auto-commit when context exits
```

---

## Idempotency Strategy

### Design Principles

1. **Idempotency is Infrastructure** - Wraps service logic, not embedded in it
2. **Atomic Transactions (Unit of Work)** - Operation AND idempotency key storage must succeed/fail together
3. **Multi-Tenant Isolation** - Keys scoped by tenant to prevent cross-organization collisions
4. **Payload Verification** - Detect when same key reused with different payloads (409 Conflict)
5. **TTL Expiration** - Keep keys for 24-48 hours; auto-expire to prevent unbounded growth

### Storage Strategy

**Database (Recommended for Initial Setup)**
- ✅ Simple, auditable, integrates with transactions
- ❌ Adds write overhead, grows unbounded without cleanup
- **Use when**: < 1000 requests/hour

**Redis (Recommended for Production)**
- ✅ Fast, automatic TTL expiration, minimal overhead
- ❌ Requires Redis infrastructure, eventual consistency
- **Use when**: > 1000 requests/hour or multi-instance deployment

### Pattern: Idempotency Record Entity with TTL

```python
# app/infrastructure/idempotency/models.py
from datetime import datetime, timedelta

class IdempotencyRecordEntity(Base):
    """Stores idempotency keys with automatic expiration"""
    __tablename__ = "idempotency_records"
    
    id = Column(Integer, primary_key=True)
    
    # Composite unique key
    key = Column(String(255), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(255), nullable=False)  # POST /invoices/import
    
    # Request validation
    request_hash = Column(String(64), nullable=False)  # SHA256 of body
    
    # Response caching
    response_status_code = Column(Integer, nullable=False)  # 200, 201, etc.
    response_body = Column(JSON, nullable=True)  # Cached response
    
    # Lifecycle with TTL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(hours=48),
        nullable=False,
        index=True  # For cleanup queries
    )
    
    __table_args__ = (
        Index("ix_idempotency_unique", "key", "tenant_id", "endpoint", unique=True),
        Index("ix_idempotency_expires", "expires_at"),
    )
```

### Critical Pattern: Unit of Work Transaction

**Why it matters**: Both the operation AND the idempotency key must succeed/fail together. If operation succeeds but key storage fails, retries create duplicates.

```python
# app/bank_transactions/service.py
class BankTransactionService:
    def __init__(self, transaction_repo, session: AsyncSession):
        self.transaction_repo = transaction_repo
        self.session = session
    
    async def import_transactions(
        self,
        data: list[TransactionCreate],
        tenant_id: int,
        idempotency_key: str | None = None
    ) -> ImportResult:
        """
        CRITICAL: Atomic transaction ensures idempotency.
        """
        # Explicit transaction - both operations succeed or both fail
        async with self.session.begin():
            # Step 1: Execute the import
            imported = await self.transaction_repo.bulk_create(
                [BankTransactionEntity(
                    tenant_id=tenant_id,
                    amount=item.amount,
                    description=item.description
                ) for item in data]
            )
            
            result = ImportResult(count=len(imported))
            
            # Step 2: Store idempotency record (SAME TRANSACTION)
            if idempotency_key:
                idempotency_repo = IdempotencyRepository(self.session)
                await idempotency_repo.store(
                    key=idempotency_key,
                    tenant_id=tenant_id,
                    endpoint="POST /bank-transactions/import",
                    request_hash=self._hash_request(data),
                    response_status_code=200,
                    response_body=result.model_dump()
                )
            
            return result
        # Commits here; on error, entire transaction rolls back
```

### Dependency: Check Before Route Executes

**Key insight**: Idempotency check happens at FastAPI dependency level, BEFORE route handler is called.

```python
# app/infrastructure/idempotency/dependency.py
async def check_idempotency(
    request: Request,
    idempotency_key: str = Header(None, alias="X-Idempotency-Key"),
    session = Depends(get_db)
) -> dict | None:
    """
    Intercept request and check for previous execution.
    Return cached response if found, None if new request.
    """
    if not idempotency_key:
        return None  # No key = not idempotent
    
    body = await request.body()
    request_hash = hashlib.sha256(body).hexdigest()
    
    repo = IdempotencyRepository(session)
    tenant_id = getattr(request.state, "tenant_id")
    
    existing = await repo.get_by_key(
        key=idempotency_key,
        tenant_id=tenant_id,
        endpoint=request.url.path
    )
    
    if existing:
        # Verify same payload
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Payload mismatch")
        
        # Return cached response (short-circuit route)
        return {"status_code": existing.response_status_code, "body": existing.response_body}
    
    return None  # Proceed to route
```

### REST Endpoint Integration

```python
# app/bank_transactions/rest/router.py
@router.post("/import")
async def import_transactions(
    data: list[TransactionCreate],
    tenant_id: int = Depends(get_current_tenant_id),
    cached: dict | None = Depends(check_idempotency),  # Runs first
    service = Depends(get_transaction_service)
):
    # Short-circuit: Return cached if retry
    if cached:
        return Response(
            content=json.dumps(cached["body"]),
            status_code=cached["status_code"]
        )
    
    # New request: Process normally
    idempotency_key = request.headers.get("X-Idempotency-Key")
    result = await service.import_transactions(data, tenant_id, idempotency_key)
    return result
```

---

## N+1 Query Prevention

### The Problem

Loading a list of invoices, then fetching the vendor for each invoice in a loop:

```python
# ❌ BAD - Causes N+1 queries
invoices = await session.execute(select(InvoiceEntity))
for invoice in invoices.scalars():
    vendor = invoice.vendor  # Lazy load - separate query per invoice!
```

### Solution 1: Eager Loading (REST APIs)

Use SQLAlchemy's relationship loading strategies:

```python
# ✅ GOOD - Single query with JOIN
stmt = select(InvoiceEntity).options(
    joinedload(InvoiceEntity.vendor)  # Many-to-one: Use JOIN
)
invoices = await session.execute(stmt)
```

```python
# ✅ GOOD - Two queries (main + IN clause)
stmt = select(InvoiceEntity).options(
    selectinload(InvoiceEntity.line_items)  # One-to-many: Use SELECT IN
)
invoices = await session.execute(stmt)
```

**When to use which:**

- `joinedload`: Many-to-one, One-to-one (creates JOIN in SQL)
- `selectinload`: One-to-many, Many-to-many (executes two queries with IN clause)

### Solution 2: DataLoaders (GraphQL)

For GraphQL, use Strawberry's DataLoader pattern:

```python
# graphql/dataloaders.py
from strawberry.dataloader import DataLoader

async def load_vendors(keys: list[int], session: AsyncSession) -> list[VendorEntity | None]:
    stmt = select(VendorEntity).where(VendorEntity.id.in_(keys))
    result = await session.execute(stmt)
    vendors_dict = {v.id: v for v in result.scalars()}
    return [vendors_dict.get(key) for key in keys]

# Usage in resolver
@strawberry.type
class InvoiceType:
    @strawberry.field
    async def vendor(self, info: Info) -> VendorType | None:
        loader = info.context["vendor_loader"]
        vendor_entity = await loader.load(self.vendor_id)
        return VendorType.from_entity(vendor_entity) if vendor_entity else None
```

---

## Central Model Registration

### The Challenge

Alembic (migration tool) needs to discover all SQLAlchemy models to generate migrations. If models are scattered across domain folders, Alembic won't find them.

### Solution: Central Import Point

```python
# app/database/base.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import ALL models here so Alembic can detect them
from app.tenants.models import TenantEntity
from app.invoices.models import InvoiceEntity, InvoiceLineItemEntity
from app.vendors.models import VendorEntity
from app.bank_transactions.models import BankTransactionEntity
from app.reconciliation.models import MatchEntity
from app.auth.models import TokenEntity, IdempotencyKeyEntity

# Alembic will use: Base.metadata
```

```python
# alembic/env.py
from app.database.base import Base

target_metadata = Base.metadata  # Now Alembic knows about all models
```

---

## SQLAlchemy Strategy Selector

### When to Use ORM vs Core vs Raw SQL

| Scenario | Use | Reason |
|----------|-----|--------|
| CRUD operations | **ORM** | Type-safe, relationship handling, simple |
| Simple queries with filters | **ORM** | `select(Entity).where(...)` is clean |
| Complex aggregations | **Core** | `GROUP BY`, `HAVING`, window functions |
| Bulk operations | **Core** | `update()` or `insert()` statements |
| Recursive queries (CTEs) | **Raw SQL** | ORM doesn't support recursive CTEs well |
| Performance-critical paths | **Core/Raw** | Eliminate ORM overhead |

### Example: Complex Aggregation

```python
# repository.py - Use Core for aggregations
from sqlalchemy import select, func

async def get_invoice_summary_by_vendor(
    self, tenant_id: int
) -> list[dict]:
    stmt = (
        select(
            VendorEntity.name,
            func.count(InvoiceEntity.id).label("invoice_count"),
            func.sum(InvoiceEntity.amount).label("total_amount")
        )
        .join(InvoiceEntity.vendor)
        .where(InvoiceEntity.tenant_id == tenant_id)
        .group_by(VendorEntity.name)
    )
    
    result = await self.session.execute(stmt)
    return [
        {"vendor": row.name, "count": row.invoice_count, "total": row.total_amount}
        for row in result
    ]
```

---

## AI Integration Architecture

### Design Principles

1. **Isolation**: AI is a black box service, not core business logic
2. **Resilience**: System must function if AI is unavailable
3. **Security**: Only send tenant-authorized data to AI
4. **Testability**: AI layer must be mockable

### Layer Placement

```python
# ai/service.py
class AIExplanationService:
    """Isolated AI integration - not part of core reconciliation logic"""
    
    def __init__(self, api_key: str | None = None):
        self.client = self._create_client(api_key)
    
    async def explain_match(
        self,
        invoice: InvoiceEntity,
        transaction: BankTransactionEntity,
        score: float
    ) -> str:
        if not self.client:
            return self._fallback_explanation(invoice, transaction, score)
        
        try:
            prompt = self._build_prompt(invoice, transaction, score)
            response = await self.client.complete(prompt)
            return response.text
        except Exception as e:
            logger.warning(f"AI explanation failed: {e}")
            return self._fallback_explanation(invoice, transaction, score)
    
    def _fallback_explanation(self, invoice, transaction, score) -> str:
        """Deterministic fallback when AI unavailable"""
        return f"Match score {score:.2f}: Amount match within tolerance, transaction date within 3 days of invoice date."
```

### Usage in Service

```python
# reconciliation/service.py
class ReconciliationService:
    def __init__(
        self,
        match_repo: MatchRepository,
        ai_service: AIExplanationService  # Injected dependency
    ):
        self.match_repo = match_repo
        self.ai_service = ai_service
    
    async def explain_match(
        self,
        match_id: int,
        tenant_id: int
    ) -> str:
        match = await self.match_repo.get_by_id(match_id, tenant_id)
        return await self.ai_service.explain_match(
            match.invoice,
            match.transaction,
            match.score
        )
```

---

## Recommended Technology Stack

### Core Framework

- **Python**: 3.13 (required)
- **FastAPI**: REST API framework
- **Strawberry GraphQL**: GraphQL implementation
- **SQLAlchemy**: 2.0+ with async support
- **Alembic**: Database migrations

### Database

- **PostgreSQL**: Production database (use `asyncpg` driver)
- **SQLite**: Local development/testing (use `aiosqlite` driver)

### Infrastructure & Cross-Cutting

| Purpose | Library | Usage |
|---------|---------|-------|
| Rate Limiting | `slowapi` | Global request throttling |
| Authentication | `pyjwt` | JWT token validation |
| Logging | `loguru` | Structured logging |
| Tracing | `opentelemetry-instrumentation-fastapi` | Distributed tracing |
| Correlation IDs | `asgi-correlation-id` | Request tracking |
| Password Hashing | `passlib[argon2]` | Secure password storage |

### Testing

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **httpx**: Async HTTP client for API tests
- **faker**: Test data generation

### Development Tools

- **mypy**: Static type checking
- **ruff**: Fast Python linter
- **black**: Code formatting
- **pre-commit**: Git hooks for quality checks

---

## Middleware vs Dependency Decision Matrix

### Middleware (Infrastructure Concerns)

Use for **passive, universal** operations that apply to every request:

```python
# config/middleware.py
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from asgi_correlation_id import CorrelationIdMiddleware

def setup_middleware(app: FastAPI):
    # Distributed tracing
    FastAPIInstrumentor.instrument_app(app)
    
    # Request correlation IDs
    app.add_middleware(CorrelationIdMiddleware)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
    )
    
    # Response compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Middleware Use Cases:**

- ✅ OpenTelemetry / Distributed tracing
- ✅ Logging / Request ID correlation
- ✅ CORS configuration
- ✅ GZip compression
- ✅ Global rate limiting (per IP)

### Dependencies (Application Concerns)

Use for **active, logic-dependent** operations that vary by endpoint:

```python
# auth/dependencies.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserEntity:
    user = await auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# Usage in router
@router.get("/me")
async def get_my_profile(
    current_user: UserEntity = Depends(get_current_user)
):
    return UserRead.from_entity(current_user)
```

**Dependency Use Cases:**

- ✅ Authentication / Current user injection
- ✅ Authorization / Permission checks
- ✅ Database session management
- ✅ Per-user rate limiting
- ✅ Feature flags
- ✅ Tenant context extraction

### Why Not Mix?

- **Middleware** runs on HTTP level - cannot differentiate GraphQL operations
- **Dependencies** are type-safe and appear in OpenAPI docs
- **Dependencies** can be selectively applied; middleware applies to everything

---

## Performance Optimization Guidelines

### Query Optimization

1. **Use database indexes** on frequently queried columns:
   - `tenant_id` (on every table)
   - Foreign keys
   - Status fields used in WHERE clauses
   - Date fields used for range queries

2. **Avoid SELECT \***: Only fetch columns you need

```python
# ✅ GOOD
stmt = select(InvoiceEntity.id, InvoiceEntity.amount, InvoiceEntity.status)

# ❌ BAD (if you only need 3 fields)
stmt = select(InvoiceEntity)
```

3. **Use pagination** for list endpoints:

```python
async def get_invoices(
    self,
    tenant_id: int,
    limit: int = 20,
    offset: int = 0
) -> list[InvoiceEntity]:
    stmt = (
        select(InvoiceEntity)
        .where(InvoiceEntity.tenant_id == tenant_id)
        .limit(limit)
        .offset(offset)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars())
```

### Caching Strategy

- **Read-heavy data**: Cache tenant metadata, configuration
- **Cache invalidation**: Use event-driven invalidation when entities update
- **Tools**: Redis for distributed caching, `functools.lru_cache` for in-memory

### Background Tasks

For long-running operations (e.g., bulk reconciliation):

```python
from fastapi import BackgroundTasks

@router.post("/reconcile")
async def start_reconciliation(
    tenant_id: int,
    background_tasks: BackgroundTasks,
    service: ReconciliationService = Depends(get_reconciliation_service)
):
    background_tasks.add_task(service.reconcile_all, tenant_id)
    return {"status": "started"}
```

---

## Security Considerations

### Input Validation

- **Never trust user input**: Pydantic validates everything at API boundary
- **SQL Injection**: Use SQLAlchemy ORM/Core (never raw string concatenation)
- **Tenant isolation**: Always filter by `tenant_id` from authenticated context

### Authentication Flow

```
1. User sends request with JWT in Authorization header
2. Dependency extracts and validates token
3. Dependency loads user from database
4. Dependency extracts tenant_id from user
5. Service receives tenant_id as trusted parameter
```

### Secrets Management

- Use environment variables for secrets
- Never commit API keys to version control
- Use `.env` files locally, secret managers in production

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str | None = None
    jwt_secret: str
    
    class Config:
        env_file = ".env"
```

---

## Deployment Considerations

### Containerization

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

# Copy application
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Run migrations and start server
CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### Environment Separation

- **Local**: SQLite, debug mode, verbose logging
- **Staging**: PostgreSQL, production-like config
- **Production**: PostgreSQL with connection pooling, optimized logging, monitoring

---

## Migration Strategy

### Alembic Workflow

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "Add invoices table"

# Review the generated migration file
# Edit if needed (autogenerate isn't perfect)

# Apply migration
poetry run alembic upgrade head

# Rollback if needed
poetry run alembic downgrade -1
```

### Multi-Tenancy & Migrations

All tenants share the same schema. Migrations apply globally:

- No per-tenant schemas (adds complexity)
- Tenant isolation is at row level (via `tenant_id`)
- Simpler to manage, scales well

---

## Monitoring & Observability

### Key Metrics to Track

- **Request duration** (per endpoint)
- **Database query duration** (per query type)
- **Error rates** (4xx, 5xx)
- **Rate limit hits**
- **Active database connections**
- **Background task queue depth**

### Logging Best Practices

```python
from loguru import logger

# Structured logging with context
logger.info(
    "Invoice created",
    extra={
        "tenant_id": tenant_id,
        "invoice_id": invoice.id,
        "amount": invoice.amount
    }
)
```

### Distributed Tracing

OpenTelemetry automatically creates spans for:

- HTTP requests
- Database queries (with SQLAlchemy instrumentation)
- Outbound HTTP calls

---

## Next Steps

1. Review [Definitions/Patterns.md](./Definitions/Patterns.md) for detailed implementation patterns
2. Use [Scaffolding-Guide.md](./Scaffolding-Guide.md) to generate base classes and folder structure
3. Follow [.copilot-instructions.md](../.copilot-instructions.md) for day-to-day development guidelines

---

**Remember**: Architecture is about making the right tradeoffs. Start simple, add complexity only when needed.
