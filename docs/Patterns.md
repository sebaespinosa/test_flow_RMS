# Definitions & Implementation Patterns

**Version:** v1.0  
**Last Updated:** January 20, 2026

## Overview

This document provides detailed, reusable implementation patterns for common scenarios in FastAPI + GraphQL + SQLAlchemy projects. Each pattern includes working code examples that can be adapted to your specific domain.

---

## Table of Contents

1. [Naming Conventions & The Bridge Problem](#naming-conventions--the-bridge-problem)
2. [Base Classes & Configuration](#base-classes--configuration)
3. [Repository Pattern Implementation](#repository-pattern-implementation)
4. [Service Layer Pattern](#service-layer-pattern)
5. [Dependency Injection Strategies](#dependency-injection-strategies)
6. [Middleware vs Dependencies](#middleware-vs-dependencies)
7. [GraphQL DataLoader Pattern](#graphql-dataloader-pattern)
8. [Multi-Tenancy Enforcement](#multi-tenancy-enforcement)
9. [Idempotency Pattern](#idempotency-pattern)
10. [Testing Patterns](#testing-patterns)

---

## Naming Conventions & The Bridge Problem

### The Challenge

Frontend frameworks (React, Vue) and GraphQL use `camelCase`. Python uses `snake_case`. You need a seamless bridge between the two.

### The Solution: Pydantic Alias Generator

Create a base schema that automatically converts between conventions:

```python
# app/common/base_models.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class BaseSchema(BaseModel):
    """Base for all Pydantic DTOs - handles camelCase/snake_case conversion"""
    
    model_config = ConfigDict(
        alias_generator=to_camel,      # snake_case → camelCase for JSON
        populate_by_name=True,          # Accept both notations on input
        from_attributes=True,           # Allow .from_orm() / .model_validate()
        validate_assignment=True,       # Validate on field assignment
        use_enum_values=True            # Serialize enums as values
    )
```

### Usage Example

```python
# app/invoices/rest/schemas.py
from app.common.base_models import BaseSchema

class InvoiceCreate(BaseSchema):
    vendor_id: int              # Python: snake_case
    invoice_number: str
    total_amount: float
    is_paid: bool

# Python code
invoice = InvoiceCreate(
    vendor_id=123,
    invoice_number="INV-001",
    total_amount=1500.00,
    is_paid=False
)

# JSON output (automatic conversion)
"""
{
  "vendorId": 123,
  "invoiceNumber": "INV-001",
  "totalAmount": 1500.00,
  "isPaid": false
}
"""

# JSON input (accepts both)
# ✅ Works: {"vendorId": 123, ...}
# ✅ Works: {"vendor_id": 123, ...}
```

### GraphQL: Strawberry Auto-Conversion

Strawberry automatically converts `snake_case` to `camelCase`:

```python
# app/invoices/graphql/types.py
import strawberry

@strawberry.type
class InvoiceType:
    id: int
    vendor_id: int          # GraphQL sees: vendorId
    invoice_number: str     # GraphQL sees: invoiceNumber
    total_amount: float     # GraphQL sees: totalAmount
```

**No manual conversion needed** - Strawberry handles it automatically.

### Naming Standards Reference

| Context | Convention | Example |
|---------|------------|---------|
| Python Classes | `PascalCase` | `UserService`, `InvoiceEntity` |
| Python Functions/Variables | `snake_case` | `get_user_by_id`, `total_amount` |
| Python Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| JSON API Keys | `camelCase` | `userId`, `totalAmount` |
| GraphQL Fields | `camelCase` | `userId`, `totalAmount` |
| Database Tables | `snake_case` | `users`, `invoice_line_items` |
| Database Columns | `snake_case` | `created_at`, `is_active` |
| Files/Folders | `lowercase` | `models.py`, `users/` |

---

## Base Classes & Configuration

### Base Pydantic Schema (Expanded)

```python
# app/common/base_models.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class BaseSchema(BaseModel):
    """Base for all Pydantic DTOs"""
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()  # ISO-8601 dates
        }
    )

class TimestampSchema(BaseSchema):
    """Adds created_at/updated_at for read schemas"""
    created_at: datetime
    updated_at: datetime | None = None

class TenantScopedSchema(BaseSchema):
    """For entities that belong to a tenant"""
    tenant_id: int = Field(..., description="Tenant identifier")
```

### Base Repository Interface

```python
# app/common/base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")  # Entity type

class BaseRepository(ABC, Generic[T]):
    """Abstract base for all repositories"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: int, tenant_id: int) -> T | None:
        """Get entity by ID (tenant-scoped)"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: int, tenant_id: int) -> bool:
        """Delete entity (returns True if deleted)"""
        pass
    
    @abstractmethod
    async def list(
        self,
        tenant_id: int,
        limit: int = 20,
        offset: int = 0,
        **filters: Any
    ) -> list[T]:
        """List entities with pagination and filters"""
        pass
```

### Base Service Class

```python
# app/common/base_service.py
from typing import Generic, TypeVar

T = TypeVar("T")  # Repository type

class BaseService(Generic[T]):
    """Abstract base for all services"""
    
    def __init__(self, repository: T):
        self.repository = repository
```

---

## Repository Pattern Implementation

### Concrete Repository Example

```python
# app/invoices/repository.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from app.common.base_repository import BaseRepository
from app.invoices.models import InvoiceEntity

class InvoiceRepository(BaseRepository[InvoiceEntity]):
    """Invoice-specific repository implementation"""
    
    async def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        self.session.add(entity)
        await self.session.flush()  # Get ID without committing
        await self.session.refresh(entity)  # Reload from DB
        return entity
    
    async def get_by_id(
        self,
        invoice_id: int,
        tenant_id: int
    ) -> InvoiceEntity | None:
        stmt = (
            select(InvoiceEntity)
            .where(
                InvoiceEntity.id == invoice_id,
                InvoiceEntity.tenant_id == tenant_id  # ALWAYS filter
            )
            .options(
                joinedload(InvoiceEntity.vendor),  # Eager load vendor
                selectinload(InvoiceEntity.line_items)  # Eager load items
            )
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()
    
    async def update(self, entity: InvoiceEntity) -> InvoiceEntity:
        # Entity already tracked by session from get_by_id
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, invoice_id: int, tenant_id: int) -> bool:
        entity = await self.get_by_id(invoice_id, tenant_id)
        if not entity:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True
    
    async def list(
        self,
        tenant_id: int,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        vendor_id: int | None = None
    ) -> list[InvoiceEntity]:
        stmt = select(InvoiceEntity).where(
            InvoiceEntity.tenant_id == tenant_id
        )
        
        # Apply optional filters
        if status:
            stmt = stmt.where(InvoiceEntity.status == status)
        if vendor_id:
            stmt = stmt.where(InvoiceEntity.vendor_id == vendor_id)
        
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return list(result.scalars())
    
    # Domain-specific query methods
    async def get_open_invoices(self, tenant_id: int) -> list[InvoiceEntity]:
        """Get all unmatched invoices for reconciliation"""
        stmt = (
            select(InvoiceEntity)
            .where(
                InvoiceEntity.tenant_id == tenant_id,
                InvoiceEntity.status == "open"
            )
            .options(joinedload(InvoiceEntity.vendor))
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars())
```

---

## Service Layer Pattern

### Service Implementation Example

```python
# app/invoices/service.py
from app.invoices.repository import InvoiceRepository
from app.invoices.models import InvoiceEntity
from app.invoices.rest.schemas import InvoiceCreate, InvoiceUpdate
from app.common.exceptions import NotFoundError, ForbiddenError

class InvoiceService:
    """Business logic for invoice operations"""
    
    def __init__(self, repository: InvoiceRepository):
        self.repository = repository
    
    async def create_invoice(
        self,
        data: InvoiceCreate,
        tenant_id: int
    ) -> InvoiceEntity:
        """Create a new invoice"""
        # Convert DTO to Entity
        entity = InvoiceEntity(
            tenant_id=tenant_id,
            vendor_id=data.vendor_id,
            invoice_number=data.invoice_number,
            amount=data.total_amount,
            status="open"
        )
        
        return await self.repository.create(entity)
    
    async def get_invoice(
        self,
        invoice_id: int,
        tenant_id: int
    ) -> InvoiceEntity:
        """Get invoice by ID - raises if not found"""
        invoice = await self.repository.get_by_id(invoice_id, tenant_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        return invoice
    
    async def update_invoice(
        self,
        invoice_id: int,
        data: InvoiceUpdate,
        tenant_id: int
    ) -> InvoiceEntity:
        """Update existing invoice"""
        invoice = await self.get_invoice(invoice_id, tenant_id)
        
        # Apply updates
        if data.total_amount is not None:
            invoice.amount = data.total_amount
        if data.status is not None:
            invoice.status = data.status
        
        return await self.repository.update(invoice)
    
    async def delete_invoice(
        self,
        invoice_id: int,
        tenant_id: int
    ) -> bool:
        """Delete invoice"""
        return await self.repository.delete(invoice_id, tenant_id)
    
    async def list_invoices(
        self,
        tenant_id: int,
        limit: int = 20,
        offset: int = 0,
        **filters
    ) -> list[InvoiceEntity]:
        """List invoices with filters"""
        return await self.repository.list(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            **filters
        )
```

---

## Dependency Injection Strategies

### FastAPI Dependency Providers

```python
# app/invoices/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db
from app.invoices.repository import InvoiceRepository
from app.invoices.service import InvoiceService

def get_invoice_repository(
    session: AsyncSession = Depends(get_db)
) -> InvoiceRepository:
    """Provide invoice repository"""
    return InvoiceRepository(session)

def get_invoice_service(
    repository: InvoiceRepository = Depends(get_invoice_repository)
) -> InvoiceService:
    """Provide invoice service"""
    return InvoiceService(repository)
```

### Usage in REST Router

```python
# app/invoices/rest/router.py
from fastapi import APIRouter, Depends, status
from app.invoices.service import InvoiceService
from app.invoices.dependencies import get_invoice_service
from app.invoices.rest.schemas import InvoiceCreate, InvoiceRead
from app.auth.dependencies import get_current_tenant_id

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    service: InvoiceService = Depends(get_invoice_service)
):
    """Create a new invoice"""
    entity = await service.create_invoice(data, tenant_id)
    return InvoiceRead.model_validate(entity)

@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    service: InvoiceService = Depends(get_invoice_service)
):
    """Get invoice by ID"""
    entity = await service.get_invoice(invoice_id, tenant_id)
    return InvoiceRead.model_validate(entity)
```

---

## Middleware vs Dependencies

### Middleware: Infrastructure Concerns

```python
# app/config/middleware.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from asgi_correlation_id import CorrelationIdMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Global rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

def setup_middleware(app: FastAPI):
    """Configure all middleware"""
    
    # 1. OpenTelemetry - Distributed Tracing
    FastAPIInstrumentor.instrument_app(app)
    
    # 2. Request Correlation IDs
    app.add_middleware(CorrelationIdMiddleware)
    
    # 3. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Configure per env
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 4. Response Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 5. Trusted Hosts (security)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.example.com", "localhost"]
    )
    
    # 6. Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Dependencies: Application Logic

```python
# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.service import AuthService
from app.auth.dependencies import get_auth_service
from app.tenants.models import TenantEntity

oauth2_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """Extract and validate user from JWT token"""
    token = credentials.credentials
    payload = await auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload

async def get_current_tenant_id(
    user: dict = Depends(get_current_user)
) -> int:
    """Extract tenant ID from authenticated user"""
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a tenant"
        )
    return tenant_id

async def require_admin(
    user: dict = Depends(get_current_user)
) -> dict:
    """Require admin role"""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
```

### Decision Matrix

| Use Case | Tool | Location | Example |
|----------|------|----------|---------|
| Distributed tracing | Middleware | `config/middleware.py` | OpenTelemetry |
| Request logging | Middleware | `config/middleware.py` | Correlation IDs |
| CORS headers | Middleware | `config/middleware.py` | CORSMiddleware |
| Response compression | Middleware | `config/middleware.py` | GZipMiddleware |
| Global rate limit | Middleware | `config/middleware.py` | SlowAPI |
| Authentication | Dependency | `auth/dependencies.py` | `get_current_user` |
| Tenant extraction | Dependency | `auth/dependencies.py` | `get_current_tenant_id` |
| Permission checks | Dependency | `auth/dependencies.py` | `require_admin` |
| DB session | Dependency | `config/database.py` | `get_db` |
| Per-user rate limit | Dependency | `auth/dependencies.py` | Custom limiter |

---

## GraphQL DataLoader Pattern

### The Problem

GraphQL resolvers can cause N+1 queries when loading related data:

```python
# ❌ BAD - N+1 Problem
@strawberry.type
class InvoiceType:
    @strawberry.field
    async def vendor(self, info: Info) -> VendorType:
        # This runs a separate query for EACH invoice!
        vendor = await get_vendor_by_id(self.vendor_id)
        return VendorType.from_entity(vendor)
```

### The Solution: DataLoader

```python
# app/vendors/graphql/dataloaders.py
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.vendors.models import VendorEntity

async def load_vendors_batch(
    keys: list[int],
    session: AsyncSession
) -> list[VendorEntity | None]:
    """Batch load vendors by IDs"""
    # Single query for all requested vendor IDs
    stmt = select(VendorEntity).where(VendorEntity.id.in_(keys))
    result = await session.execute(stmt)
    
    # Map vendors by ID
    vendors_dict = {vendor.id: vendor for vendor in result.scalars()}
    
    # Return in same order as keys (important!)
    return [vendors_dict.get(key) for key in keys]
```

### DataLoader Factory

```python
# app/graphql/context.py
from strawberry.dataloader import DataLoader
from sqlalchemy.ext.asyncio import AsyncSession

def create_dataloaders(session: AsyncSession) -> dict:
    """Create all dataloaders for GraphQL context"""
    
    from app.vendors.graphql.dataloaders import load_vendors_batch
    from app.invoices.graphql.dataloaders import load_invoices_batch
    
    return {
        "vendor_loader": DataLoader(
            load_fn=lambda keys: load_vendors_batch(keys, session)
        ),
        "invoice_loader": DataLoader(
            load_fn=lambda keys: load_invoices_batch(keys, session)
        ),
    }
```

### Usage in Resolver

```python
# app/invoices/graphql/types.py
import strawberry
from strawberry.types import Info
from app.vendors.graphql.types import VendorType

@strawberry.type
class InvoiceType:
    id: int
    vendor_id: int
    amount: float
    
    @strawberry.field
    async def vendor(self, info: Info) -> VendorType | None:
        """Load vendor using DataLoader - batches queries"""
        loader = info.context["vendor_loader"]
        vendor_entity = await loader.load(self.vendor_id)
        
        if not vendor_entity:
            return None
        
        return VendorType.from_entity(vendor_entity)
```

### GraphQL Context Setup

```python
# app/main.py
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema
from app.graphql.context import create_dataloaders
from app.config.database import get_db

async def get_graphql_context(session: AsyncSession = Depends(get_db)):
    """Create GraphQL context with dataloaders"""
    return {
        "session": session,
        **create_dataloaders(session)
    }

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context
)

app.include_router(graphql_app, prefix="/graphql")
```

---

## Multi-Tenancy Enforcement

### Pattern: Tenant Filter Mixin

```python
# app/common/mixins.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declared_attr

class TenantScopedMixin:
    """Mixin for tenant-scoped entities"""
    
    @declared_attr
    def tenant_id(cls):
        return Column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True  # Performance: always indexed
        )
```

### Usage in Models

```python
# app/invoices/models.py
from sqlalchemy import Column, Integer, String, Numeric
from app.database.base import Base
from app.common.mixins import TenantScopedMixin

class InvoiceEntity(Base, TenantScopedMixin):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True)
    # tenant_id inherited from TenantScopedMixin
    invoice_number = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
```

### Repository-Level Enforcement

```python
# app/common/base_repository.py
from sqlalchemy import select

class TenantScopedRepository(BaseRepository[T]):
    """Base repository with automatic tenant filtering"""
    
    def _apply_tenant_filter(self, stmt, tenant_id: int):
        """Apply tenant filter to any statement"""
        return stmt.where(self.model.tenant_id == tenant_id)
    
    async def get_by_id(self, entity_id: int, tenant_id: int) -> T | None:
        stmt = select(self.model).where(self.model.id == entity_id)
        stmt = self._apply_tenant_filter(stmt, tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

---

## Idempotency Pattern

### Entity Model with TTL

```python
# app/infrastructure/idempotency/models.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index, Text
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta
from app.database.base import Base

class IdempotencyRecordEntity(Base):
    """
    Stores idempotency key state with automatic expiration (48 hours).
    Prevents duplicate operations on retry or race conditions.
    """
    __tablename__ = "idempotency_records"
    
    id = Column(Integer, primary_key=True)
    # Composite key: idempotency_key + tenant_id (multi-tenant isolation)
    idempotency_key = Column(String(255), nullable=False)
    tenant_id = Column(Integer, nullable=False)
    
    # Operation metadata for conflict detection
    endpoint = Column(String(255), nullable=False)  # POST /invoices/import
    request_payload_hash = Column(String(64), nullable=False)  # SHA256
    
    # Result caching (for immediate retry response)
    response_body = Column(JSON, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    
    # Lifecycle tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        # Prevent duplicate operations per tenant (unique constraint)
        Index(
            "ix_idempotency_unique_per_tenant",
            "idempotency_key",
            "tenant_id",
            unique=True
        ),
        # Enable fast cleanup of expired records (background job)
        Index("ix_idempotency_expires_at", "expires_at"),
        # Fast lookup by tenant + key
        Index("ix_idempotency_lookup", "tenant_id", "idempotency_key"),
    )
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if idempotency record has expired"""
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def from_request(
        cls,
        key: str,
        tenant_id: int,
        endpoint: str,
        request_hash: str,
        ttl_hours: int = 48
    ):
        """Factory method to create new idempotency record"""
        return cls(
            idempotency_key=key,
            tenant_id=tenant_id,
            endpoint=endpoint,
            request_payload_hash=request_hash,
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours)
        )
```

### Repository with Conflict Detection

```python
# app/infrastructure/idempotency/repository.py
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.common.exceptions import ConflictError

class IdempotencyRepository:
    def __init__(self, session):
        self.session = session
    
    async def get_by_key(
        self,
        key: str,
        tenant_id: int
    ) -> IdempotencyRecordEntity | None:
        """Retrieve idempotency record if it exists and hasn't expired"""
        stmt = select(IdempotencyRecordEntity).where(
            IdempotencyRecordEntity.idempotency_key == key,
            IdempotencyRecordEntity.tenant_id == tenant_id,
            # Expired records treated as non-existent
            IdempotencyRecordEntity.expires_at > datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(
        self,
        record: IdempotencyRecordEntity
    ) -> IdempotencyRecordEntity:
        """
        Store idempotency record. Raises ConflictError if:
        - Same key exists for tenant (operation in progress or duplicate)
        - Payload hash differs (key reused with different params)
        """
        try:
            self.session.add(record)
            await self.session.flush()  # Force constraint check
            return record
        except IntegrityError:
            # Unique constraint violation: record already exists
            existing = await self.get_by_key(
                record.idempotency_key,
                record.tenant_id
            )
            if existing and existing.request_payload_hash != record.request_payload_hash:
                raise ConflictError(
                    detail="Idempotency key reused with different request payload",
                    status_code=409
                )
            raise
    
    async def update_response(
        self,
        key: str,
        tenant_id: int,
        response_body: dict,
        status_code: int
    ) -> None:
        """Cache operation response for retry delivery"""
        record = await self.get_by_key(key, tenant_id)
        if record:
            record.response_body = response_body
            record.response_status_code = status_code
            await self.session.flush()
    
    async def cleanup_expired(self) -> int:
        """Delete idempotency records older than 48 hours (background task)"""
        stmt = delete(IdempotencyRecordEntity).where(
            IdempotencyRecordEntity.expires_at <= datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        return result.rowcount
```

### Dependency: Intercept Before Route Handler

```python
# app/infrastructure/idempotency/dependency.py
import hashlib
import json
from fastapi import Request, Header
from app.infrastructure.idempotency.repository import IdempotencyRepository
from app.database.session import get_db

class IdempotencyCheckResult:
    def __init__(self, is_retry: bool, cached_response: dict | None = None):
        self.is_retry = is_retry
        self.cached_response = cached_response

async def check_idempotency(
    request: Request,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
    db = Depends(get_db),
) -> IdempotencyCheckResult | None:
    """
    FastAPI Dependency that:
    1. Runs BEFORE route handler
    2. Returns cached response on retry (short-circuits route execution)
    3. Detects payload conflicts (409 Conflict)
    
    Usage:
        @router.post("/invoices/import")
        async def import_invoices(
            ...,
            idempotency_check: IdempotencyCheckResult = Depends(check_idempotency)
        ):
            if idempotency_check and idempotency_check.is_retry:
                return idempotency_check.cached_response
            # ... execute operation
    """
    
    if not idempotency_key:
        return None  # Header not provided, proceed without idempotency
    
    tenant_id = request.scope.get("tenant_id")
    endpoint = request.url.path
    
    # Hash request body for conflict detection
    body = await request.body()
    request_hash = hashlib.sha256(body).hexdigest()
    
    repo = IdempotencyRepository(db)
    existing = await repo.get_by_key(idempotency_key, tenant_id)
    
    if existing:
        # Verify payload hasn't changed (conflict detection)
        if existing.request_payload_hash != request_hash:
            raise ConflictError(
                detail="Idempotency key reused with different request payload",
                status_code=409
            )
        
        # Return cached response (retry detected)
        return IdempotencyCheckResult(
            is_retry=True,
            cached_response=existing.response_body
        )
    
    return IdempotencyCheckResult(is_retry=False)
```

### Service: Unit of Work Pattern (Atomic Operation + Key Storage)

```python
# app/bank_transactions/service.py
import hashlib
from app.infrastructure.idempotency.repository import IdempotencyRepository
from app.bank_transactions.models import BankTransactionEntity

class BankTransactionService:
    def __init__(
        self,
        repository: BankTransactionRepository,
        idempotency_repo: IdempotencyRepository,
        session: AsyncSession
    ):
        self.repository = repository
        self.idempotency_repo = idempotency_repo
        self.session = session
    
    async def import_transactions(
        self,
        data: list[TransactionCreate],
        tenant_id: int,
        idempotency_key: str = None
    ) -> dict:
        """
        Import transactions with idempotency guarantee.
        Unit of Work: Operation + idempotency record stored in same transaction.
        If either fails, both rollback (no duplicates on retry).
        """
        
        # Deterministic payload hash for conflict detection
        request_hash = self._compute_request_hash(data)
        endpoint = "/api/bank_transactions/import"
        
        # Create idempotency record (will fail if duplicate key exists)
        if idempotency_key:
            idempotency_record = IdempotencyRecordEntity.from_request(
                key=idempotency_key,
                tenant_id=tenant_id,
                endpoint=endpoint,
                request_hash=request_hash,
                ttl_hours=48
            )
        
        # **CRITICAL**: Unit of Work - both operation and key storage in same transaction
        async with self.session.begin():
            # 1. Execute business logic
            entities = [
                BankTransactionEntity(
                    tenant_id=tenant_id,
                    amount=item.amount,
                    reference=item.reference,
                )
                for item in data
            ]
            result = await self.repository.bulk_create(entities)
            
            # 2. Store idempotency record in same transaction
            if idempotency_key:
                await self.idempotency_repo.create(idempotency_record)
                await self.idempotency_repo.update_response(
                    key=idempotency_key,
                    tenant_id=tenant_id,
                    response_body={
                        "imported_count": len(result),
                        "transaction_ids": [t.id for t in result]
                    },
                    status_code=201
                )
        
        # Both succeed or both fail - never partial state
        return {
            "imported_count": len(result),
            "transaction_ids": [t.id for t in result]
        }
    
    def _compute_request_hash(self, data: list[TransactionCreate]) -> str:
        """Deterministic hash of request payload (sorted for consistency)"""
        json_data = json.dumps(
            [d.model_dump(mode="json", exclude_none=True) for d in data],
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(json_data.encode()).hexdigest()
```

### REST Endpoint Integration

```python
# app/bank_transactions/rest/router.py
from fastapi import APIRouter, Header, Depends, Response, status
from app.infrastructure.idempotency.dependency import IdempotencyCheckResult

router = APIRouter(prefix="/api/bank_transactions", tags=["transactions"])

@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import bank transactions (idempotent)"
)
async def import_transactions(
    req: list[TransactionCreate],
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    idempotency_check: IdempotencyCheckResult = Depends(check_idempotency),
    tenant_id: int = Depends(get_current_tenant_id),
    service: BankTransactionService = Depends(get_transaction_service),
):
    """
    Import transactions with automatic deduplication.
    
    **Idempotency:**
    - Required header: `Idempotency-Key: <uuid>`
    - First request: Executes transaction, stores key
    - Retry (same key): Returns cached response
    - Conflict (different payload): Returns 409 Conflict
    
    **TTL:** Records expire after 48 hours
    """
    
    # If retry detected, return cached response (short-circuit)
    if idempotency_check and idempotency_check.is_retry:
        return idempotency_check.cached_response
    
    # Execute operation (unit of work: operation + key storage atomic)
    result = await service.import_transactions(req, tenant_id, idempotency_key)
    return result
```

### Testing Idempotency

```python
# tests/infrastructure/test_idempotency.py
import pytest
from app.infrastructure.idempotency.models import IdempotencyRecordEntity
from app.infrastructure.idempotency.repository import IdempotencyRepository
from app.common.exceptions import ConflictError

@pytest.mark.asyncio
async def test_first_request_creates_record(db_session):
    """First request stores idempotency record"""
    repo = IdempotencyRepository(db_session)
    
    record = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/import",
        request_hash="abc123"
    )
    
    await repo.create(record)
    
    # Verify record exists and hasn't expired
    retrieved = await repo.get_by_key("req-123", 1)
    assert retrieved is not None
    assert retrieved.response_body is None  # Filled after operation

@pytest.mark.asyncio
async def test_duplicate_key_conflict(db_session):
    """Reusing key with different payload raises 409"""
    repo = IdempotencyRepository(db_session)
    
    # First request
    record1 = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/import",
        request_hash="abc123"
    )
    await repo.create(record1)
    
    # Retry with different payload
    record2 = IdempotencyRecordEntity.from_request(
        key="req-123",
        tenant_id=1,
        endpoint="/import",
        request_hash="xyz789"  # Different payload
    )
    
    with pytest.raises(ConflictError):
        await repo.create(record2)

@pytest.mark.asyncio
async def test_ttl_expiration(db_session):
    """Expired records treated as non-existent"""
    from datetime import datetime, timedelta
    
    repo = IdempotencyRepository(db_session)
    
    record = IdempotencyRecordEntity(
        idempotency_key="req-123",
        tenant_id=1,
        endpoint="/import",
        request_payload_hash="abc123",
        # Already expired
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )
    db_session.add(record)
    await db_session.commit()
    
    # Should return None (expired = not found)
    retrieved = await repo.get_by_key("req-123", 1)
    assert retrieved is None

@pytest.mark.asyncio
async def test_cleanup_expired_records(db_session):
    """Background task removes expired records"""
    from datetime import datetime, timedelta
    
    repo = IdempotencyRepository(db_session)
    
    # Create 3 expired records
    for i in range(3):
        record = IdempotencyRecordEntity(
            idempotency_key=f"req-{i}",
            tenant_id=1,
            endpoint="/import",
            request_payload_hash="hash",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        db_session.add(record)
    
    await db_session.commit()
    
    # Run cleanup
    deleted = await repo.cleanup_expired()
    
    assert deleted == 3
    
    # Verify all deleted
    remaining = await db_session.execute(
        select(func.count(IdempotencyRecordEntity.id))
    )
    assert remaining.scalar() == 0
```

### Storage Decision: Database vs Redis

**Database (SQLAlchemy):**
- ✅ For < 1,000 requests/hour
- ✅ Single storage location with other domain data
- ✅ Automatic TTL via indexes (cleanup task)
- ✅ Multi-tenant isolation via tenant_id column
- ✅ Conflict detection via unique constraint
- ❌ Slower for very high-frequency operations

**Redis:**
- ✅ For > 10,000 requests/hour
- ✅ Sub-millisecond lookup times
- ✅ Automatic TTL via EXPIRE command
- ✅ Separate cache layer (decouples from main DB)
- ❌ Requires separate infrastructure
- ❌ Eventual consistency on failover

**Recommendation:** Start with database, migrate to Redis if load testing shows > 1000 req/hr on idempotent endpoints.

---

## Testing Patterns

### Repository Testing (With Real DB)

```python
# tests/invoices/test_repository.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.invoices.repository import InvoiceRepository
from app.invoices.models import InvoiceEntity

@pytest.fixture
async def db_session():
    """Create test database session"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_invoice(db_session):
    """Test invoice creation"""
    repo = InvoiceRepository(db_session)
    
    entity = InvoiceEntity(
        tenant_id=1,
        vendor_id=10,
        invoice_number="INV-001",
        amount=1500.00,
        status="open"
    )
    
    result = await repo.create(entity)
    
    assert result.id is not None
    assert result.invoice_number == "INV-001"
```

### Service Testing (With Mocked Repository)

```python
# tests/invoices/test_service.py
import pytest
from pytest_mock import MockerFixture
from app.invoices.service import InvoiceService
from app.invoices.rest.schemas import InvoiceCreate

@pytest.mark.asyncio
async def test_create_invoice_service(mocker: MockerFixture):
    """Test service layer with mocked repository"""
    # Mock repository
    mock_repo = mocker.Mock()
    mock_repo.create = mocker.AsyncMock(return_value=InvoiceEntity(
        id=1,
        tenant_id=1,
        vendor_id=10,
        invoice_number="INV-001",
        amount=1500.00
    ))
    
    service = InvoiceService(repository=mock_repo)
    
    # Test service method
    data = InvoiceCreate(
        vendor_id=10,
        invoice_number="INV-001",
        total_amount=1500.00
    )
    
    result = await service.create_invoice(data, tenant_id=1)
    
    # Assertions
    mock_repo.create.assert_called_once()
    assert result.id == 1
    assert result.amount == 1500.00
```

### API Testing (Integration)

```python
# tests/invoices/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_invoice_endpoint():
    """Test REST endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/invoices/",
            json={
                "vendorId": 10,
                "invoiceNumber": "INV-001",
                "totalAmount": 1500.00
            },
            headers={"Authorization": "Bearer test-token"}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["invoiceNumber"] == "INV-001"
    assert data["totalAmount"] == 1500.00
```

### GraphQL Testing

```python
# tests/invoices/test_graphql.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_invoice_mutation():
    """Test GraphQL mutation"""
    query = """
        mutation CreateInvoice($input: InvoiceCreateInput!) {
            createInvoice(input: $input) {
                id
                invoiceNumber
                totalAmount
            }
        }
    """
    
    variables = {
        "input": {
            "vendorId": 10,
            "invoiceNumber": "INV-001",
            "totalAmount": 1500.00
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": variables},
            headers={"Authorization": "Bearer test-token"}
        )
    
    assert response.status_code == 200
    data = response.json()["data"]["createInvoice"]
    assert data["invoiceNumber"] == "INV-001"
```

---

## Summary

These patterns provide a solid foundation for building scalable, maintainable FastAPI + GraphQL applications:

1. **Use Pydantic's `alias_generator`** for seamless camelCase/snake_case bridging
2. **Implement base classes** to enforce consistency across domains
3. **Use DataLoaders** for GraphQL to prevent N+1 queries
4. **Enforce multi-tenancy** at every layer with automatic filtering
5. **Implement idempotency** for critical operations like bulk imports
6. **Test at every layer** with appropriate mocking strategies

Refer to [Architecture.md](../Architecture.md) for system-level design and [Scaffolding-Guide.md](./Scaffolding-Guide.md) for code generation templates.
