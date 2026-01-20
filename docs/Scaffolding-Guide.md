# Scaffolding Guide

**Version:** v1.0  
**Last Updated:** January 20, 2026

## Overview

This guide provides ready-to-use code templates and step-by-step instructions for scaffolding a new FastAPI + GraphQL + SQLAlchemy project or adding new domains to an existing one.

---

## Table of Contents

1. [Project Initialization](#project-initialization)
2. [Base Infrastructure Setup](#base-infrastructure-setup)
3. [Adding a New Domain](#adding-a-new-domain)
4. [Domain Checklist](#domain-checklist)
5. [Code Templates](#code-templates)

---

## Project Initialization

### 1. Create Project Structure

```bash
# Create main directories
mkdir -p app/{config,common,database}
mkdir -p tests
mkdir -p docs

# Create __init__.py files
touch app/__init__.py
touch app/config/__init__.py
touch app/common/__init__.py
touch app/database/__init__.py
touch tests/__init__.py
```

### 2. Install Core Dependencies

```bash
# Using Poetry (recommended)
poetry add fastapi uvicorn[standard] sqlalchemy[asyncio] alembic
poetry add strawberry-graphql[fastapi]
poetry add pydantic pydantic-settings
poetry add asyncpg  # PostgreSQL driver
poetry add aiosqlite  # SQLite driver (for dev/testing)

# Authentication & Security
poetry add pyjwt passlib[argon2] python-multipart

# Infrastructure
poetry add loguru opentelemetry-instrumentation-fastapi
poetry add asgi-correlation-id slowapi

# Development dependencies
poetry add --group dev pytest pytest-asyncio pytest-mock httpx
poetry add --group dev mypy ruff black pre-commit
```

---

## Base Infrastructure Setup

### Database Configuration

```python
# app/config/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from app.config.settings import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before using
    pool_size=10,
    max_overflow=20
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,         # Manual flush control
    autocommit=False         # Manual commit control
)

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for request"""
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

### Settings Configuration

```python
# app/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    app_name: str = "FastAPI GraphQL App"
    debug: bool = False
    environment: str = "production"
    
    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/dbname"
    
    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # AI / External Services
    openai_api_key: str | None = None
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

# Global settings instance
settings = Settings()
```

### Logging Configuration

```python
# app/config/logging.py
import sys
from loguru import logger
from app.config.settings import settings

def configure_logging():
    """Configure structured logging with Loguru"""
    
    # Remove default handler
    logger.remove()
    
    # Console handler with appropriate level
    log_level = "DEBUG" if settings.debug else "INFO"
    
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # File handler for production
    if not settings.debug:
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # New file at midnight
            retention="30 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        )
    
    return logger
```

### Exception Handlers

```python
# app/config/exceptions.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)

class ConflictError(AppException):
    """Resource conflict (e.g., duplicate key)"""
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)

class ForbiddenError(AppException):
    """Access forbidden"""
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)

# Exception handlers
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    logger.error(f"Application error: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )
```

### Middleware Setup

```python
# app/config/middleware.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from asgi_correlation_id import CorrelationIdMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config.settings import settings

# Global rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

def setup_middleware(app: FastAPI):
    """Configure all middleware"""
    
    # OpenTelemetry - must be first
    FastAPIInstrumentor.instrument_app(app)
    
    # Request correlation IDs
    app.add_middleware(CorrelationIdMiddleware)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Response compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Central Model Registry

```python
# app/database/base.py
from sqlalchemy.orm import declarative_base

# Base class for all models
Base = declarative_base()

# Import all models here for Alembic to detect
# from app.tenants.models import TenantEntity
# from app.invoices.models import InvoiceEntity
# ... add more as you create domains
```

### Main Application Entry Point

```python
# app/main.py
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.config.settings import settings
from app.config.logging import configure_logging
from app.config.middleware import setup_middleware
from app.config.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler
)

# Configure logging
logger = configure_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# Setup middleware
setup_middleware(app)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Register routers (add as you create domains)
# from app.tenants.rest.router import router as tenants_router
# app.include_router(tenants_router, prefix="/api/v1")

# GraphQL endpoint (add after creating schema)
# from strawberry.fastapi import GraphQLRouter
# from app.graphql.schema import schema
# graphql_app = GraphQLRouter(schema)
# app.include_router(graphql_app, prefix="/graphql")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
```

### Infrastructure: Idempotency Folder

The idempotency infrastructure is self-contained and reusable across all domains:

```bash
mkdir -p app/infrastructure/{idempotency,__init__.py}
```

**Step 1: Create Entity Model**

```python
# app/infrastructure/idempotency/models.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
from datetime import datetime, timedelta
from app.database.base import Base

class IdempotencyRecordEntity(Base):
    __tablename__ = "idempotency_records"
    
    id = Column(Integer, primary_key=True)
    idempotency_key = Column(String(255), nullable=False)
    tenant_id = Column(Integer, nullable=False)
    endpoint = Column(String(255), nullable=False)
    request_payload_hash = Column(String(64), nullable=False)
    response_body = Column(JSON, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index("ix_idempotency_unique", "idempotency_key", "tenant_id", unique=True),
        Index("ix_idempotency_expires", "expires_at"),
    )
    
    @classmethod
    def from_request(cls, key: str, tenant_id: int, endpoint: str, request_hash: str):
        return cls(
            idempotency_key=key,
            tenant_id=tenant_id,
            endpoint=endpoint,
            request_payload_hash=request_hash,
            expires_at=datetime.utcnow() + timedelta(hours=48)
        )
```

**Step 2: Register in Alembic Base**

```python
# app/database/base.py (add import)
from app.infrastructure.idempotency.models import IdempotencyRecordEntity

# Now Alembic detects IdempotencyRecordEntity
```

**Step 3: Create Repository**

```python
# app/infrastructure/idempotency/repository.py
from sqlalchemy import select, delete
from datetime import datetime
from app.common.exceptions import ConflictError

class IdempotencyRepository:
    def __init__(self, session):
        self.session = session
    
    async def get_by_key(self, key: str, tenant_id: int):
        """Get unexpired idempotency record"""
        stmt = select(IdempotencyRecordEntity).where(
            IdempotencyRecordEntity.idempotency_key == key,
            IdempotencyRecordEntity.tenant_id == tenant_id,
            IdempotencyRecordEntity.expires_at > datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, record):
        """Store record, raise ConflictError on duplicate key"""
        try:
            self.session.add(record)
            await self.session.flush()
            return record
        except IntegrityError:
            existing = await self.get_by_key(record.idempotency_key, record.tenant_id)
            if existing and existing.request_payload_hash != record.request_payload_hash:
                raise ConflictError("Idempotency key reused with different payload")
            raise
    
    async def update_response(self, key: str, tenant_id: int, body: dict, code: int):
        """Cache operation response"""
        record = await self.get_by_key(key, tenant_id)
        if record:
            record.response_body = body
            record.response_status_code = code
            await self.session.flush()
    
    async def cleanup_expired(self) -> int:
        """Delete expired records (run as background task)"""
        stmt = delete(IdempotencyRecordEntity).where(
            IdempotencyRecordEntity.expires_at <= datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        return result.rowcount
```

**Step 4: Create Dependency Wrapper**

```python
# app/infrastructure/idempotency/dependency.py
import hashlib
from fastapi import Request, Header, Depends
from app.database.session import get_db

class IdempotencyCheckResult:
    def __init__(self, is_retry: bool, cached: dict | None = None):
        self.is_retry = is_retry
        self.cached_response = cached

async def check_idempotency(
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db = Depends(get_db)
) -> IdempotencyCheckResult | None:
    """Dependency that runs BEFORE route handler"""
    if not idempotency_key:
        return None
    
    tenant_id = request.scope.get("tenant_id")
    body = await request.body()
    request_hash = hashlib.sha256(body).hexdigest()
    
    repo = IdempotencyRepository(db)
    existing = await repo.get_by_key(idempotency_key, tenant_id)
    
    if existing:
        if existing.request_payload_hash != request_hash:
            raise ConflictError("Idempotency key reused with different payload")
        return IdempotencyCheckResult(is_retry=True, cached=existing.response_body)
    
    return IdempotencyCheckResult(is_retry=False)
```

**Step 5: Register Cleanup Task (Celery or APScheduler)**

```python
# app/infrastructure/idempotency/tasks.py
from celery import shared_task
from app.database.session import get_db
from app.infrastructure.idempotency.repository import IdempotencyRepository

@shared_task
async def cleanup_expired_idempotency_keys():
    """Remove idempotency records older than 48 hours"""
    async with get_db() as db:
        repo = IdempotencyRepository(db)
        deleted = await repo.cleanup_expired()
        return {"deleted_count": deleted}

# In app/main.py (Celery Beat schedule)
# tasks.cleanup_expired_idempotency_keys.apply_async(countdown=3600)  # every hour
```

**Step 6: Update Main App to Include Alembic Discovery**

```python
# app/database/base.py
from sqlalchemy.orm import declarative_base
from app.infrastructure.idempotency.models import IdempotencyRecordEntity  # Register

Base = declarative_base()
```

### Common Base Classes

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
            datetime: lambda v: v.isoformat()
        }
    )

class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    created_at: datetime
    updated_at: datetime | None = None

class TenantScopedSchema(BaseSchema):
    """Schema for tenant-scoped resources"""
    tenant_id: int = Field(..., description="Tenant identifier")
```

```python
# app/common/base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    """Abstract base for all repositories"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: int, tenant_id: int) -> T | None:
        """Get entity by ID (tenant-scoped)"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: int, tenant_id: int) -> bool:
        """Delete entity"""
        pass
    
    @abstractmethod
    async def list(
        self,
        tenant_id: int,
        limit: int = 20,
        offset: int = 0,
        **filters: Any
    ) -> list[T]:
        """List entities with filters"""
        pass
```

```python
# app/common/mixins.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import declared_attr
from datetime import datetime

class TenantScopedMixin:
    """Mixin for tenant-scoped entities"""
    
    @declared_attr
    def tenant_id(cls):
        return Column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        )

class TimestampMixin:
    """Mixin for created_at/updated_at timestamps"""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

---

## Adding a New Domain

Follow these steps to add a new domain (e.g., `invoices`):

### Step 1: Create Domain Folder Structure

```bash
# Create domain folder
mkdir -p app/invoices/{rest,graphql}

# Create __init__.py files
touch app/invoices/__init__.py
touch app/invoices/rest/__init__.py
touch app/invoices/graphql/__init__.py
```

### Step 2: Create Model

```python
# app/invoices/models.py
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.common.mixins import TenantScopedMixin, TimestampMixin

class InvoiceEntity(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True)
    # tenant_id from TenantScopedMixin
    
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    invoice_number = Column(String(50), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(20), default="open", nullable=False)
    description = Column(String(500), nullable=True)
    
    # Relationships
    vendor = relationship("VendorEntity", back_populates="invoices")
    
    # created_at, updated_at from TimestampMixin
```

### Step 3: Register Model

```python
# app/database/base.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Add import for new model
from app.invoices.models import InvoiceEntity
```

### Step 4: Create Repository Interface

```python
# app/invoices/interfaces.py
from abc import ABC, abstractmethod
from app.invoices.models import InvoiceEntity

class InvoiceRepository(ABC):
    """Abstract interface for invoice repository"""
    
    @abstractmethod
    async def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        pass
    
    @abstractmethod
    async def get_by_id(self, invoice_id: int, tenant_id: int) -> InvoiceEntity | None:
        pass
    
    @abstractmethod
    async def get_open_invoices(self, tenant_id: int) -> list[InvoiceEntity]:
        """Domain-specific query"""
        pass
    
    # Add more abstract methods as needed
```

### Step 5: Implement Repository

```python
# app/invoices/repository.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from app.common.base_repository import BaseRepository
from app.invoices.models import InvoiceEntity
from app.invoices.interfaces import InvoiceRepository as IInvoiceRepository

class InvoiceRepositoryImpl(BaseRepository[InvoiceEntity], IInvoiceRepository):
    """Concrete invoice repository implementation"""
    
    async def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
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
                InvoiceEntity.tenant_id == tenant_id
            )
            .options(joinedload(InvoiceEntity.vendor))
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()
    
    async def update(self, entity: InvoiceEntity) -> InvoiceEntity:
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
        **filters
    ) -> list[InvoiceEntity]:
        stmt = select(InvoiceEntity).where(
            InvoiceEntity.tenant_id == tenant_id
        )
        
        # Apply filters
        if "status" in filters:
            stmt = stmt.where(InvoiceEntity.status == filters["status"])
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars())
    
    async def get_open_invoices(self, tenant_id: int) -> list[InvoiceEntity]:
        """Domain-specific query"""
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

### Step 6: Create Service

```python
# app/invoices/service.py
from app.invoices.repository import InvoiceRepositoryImpl
from app.invoices.models import InvoiceEntity
from app.invoices.rest.schemas import InvoiceCreate, InvoiceUpdate
from app.config.exceptions import NotFoundError

class InvoiceService:
    """Business logic for invoices"""
    
    def __init__(self, repository: InvoiceRepositoryImpl):
        self.repository = repository
    
    async def create_invoice(
        self,
        data: InvoiceCreate,
        tenant_id: int
    ) -> InvoiceEntity:
        """Create new invoice"""
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
        """Get invoice by ID"""
        invoice = await self.repository.get_by_id(invoice_id, tenant_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        return invoice
    
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

### Step 7: Create REST Schemas

```python
# app/invoices/rest/schemas.py
from decimal import Decimal
from app.common.base_models import BaseSchema, TimestampSchema

class InvoiceCreate(BaseSchema):
    """Schema for creating invoice"""
    vendor_id: int | None = None
    invoice_number: str | None = None
    total_amount: Decimal
    currency: str = "USD"
    description: str | None = None

class InvoiceUpdate(BaseSchema):
    """Schema for updating invoice"""
    total_amount: Decimal | None = None
    status: str | None = None
    description: str | None = None

class InvoiceRead(TimestampSchema):
    """Schema for reading invoice"""
    id: int
    tenant_id: int
    vendor_id: int | None
    invoice_number: str | None
    total_amount: Decimal
    currency: str
    status: str
    description: str | None
```

### Step 8: Create REST Router

```python
# app/invoices/rest/router.py
from fastapi import APIRouter, Depends, status
from app.invoices.service import InvoiceService
from app.invoices.dependencies import get_invoice_service
from app.invoices.rest.schemas import InvoiceCreate, InvoiceRead, InvoiceUpdate
from app.auth.dependencies import get_current_tenant_id

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    service: InvoiceService = Depends(get_invoice_service)
):
    """Create new invoice"""
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

@router.get("/", response_model=list[InvoiceRead])
async def list_invoices(
    tenant_id: int = Depends(get_current_tenant_id),
    service: InvoiceService = Depends(get_invoice_service),
    limit: int = 20,
    offset: int = 0,
    status: str | None = None
):
    """List invoices"""
    entities = await service.list_invoices(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        status=status
    )
    return [InvoiceRead.model_validate(e) for e in entities]
```

### Step 9: Create Dependencies

```python
# app/invoices/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db
from app.invoices.repository import InvoiceRepositoryImpl
from app.invoices.service import InvoiceService

def get_invoice_repository(
    session: AsyncSession = Depends(get_db)
) -> InvoiceRepositoryImpl:
    """Provide invoice repository"""
    return InvoiceRepositoryImpl(session)

def get_invoice_service(
    repository: InvoiceRepositoryImpl = Depends(get_invoice_repository)
) -> InvoiceService:
    """Provide invoice service"""
    return InvoiceService(repository)
```

### Step 10: Register Router in Main App

```python
# app/main.py (add these lines)
from app.invoices.rest.router import router as invoices_router

app.include_router(invoices_router, prefix="/api/v1")
```

### Step 11: Create GraphQL Types (Optional)

```python
# app/invoices/graphql/types.py
import strawberry
from decimal import Decimal

@strawberry.type
class InvoiceType:
    id: int
    tenant_id: int
    vendor_id: int | None
    invoice_number: str | None
    total_amount: Decimal
    currency: str
    status: str
    description: str | None
    
    @classmethod
    def from_entity(cls, entity):
        """Convert Entity to GraphQL Type"""
        return cls(
            id=entity.id,
            tenant_id=entity.tenant_id,
            vendor_id=entity.vendor_id,
            invoice_number=entity.invoice_number,
            total_amount=entity.amount,
            currency=entity.currency,
            status=entity.status,
            description=entity.description
        )
```

### Step 12: Create Migration

```bash
# Generate migration
poetry run alembic revision --autogenerate -m "Add invoices table"

# Review generated file in alembic/versions/
# Edit if needed

# Apply migration
poetry run alembic upgrade head
```

---

## Domain Checklist

When adding a new domain, ensure you've created:

- [ ] Domain folder: `app/{domain}/`
- [ ] `__init__.py` in domain folder and subfolders
- [ ] `models.py` - SQLAlchemy Entity
- [ ] `interfaces.py` - Repository interface (ABC)
- [ ] `repository.py` - Repository implementation
- [ ] `service.py` - Business logic
- [ ] `dependencies.py` - FastAPI dependency providers
- [ ] `rest/schemas.py` - Pydantic DTOs
- [ ] `rest/router.py` - FastAPI endpoints
- [ ] Registered model in `app/database/base.py`
- [ ] Registered router in `app/main.py`
- [ ] Created and applied Alembic migration
- [ ] (Optional) `graphql/types.py` - Strawberry types
- [ ] (Optional) `graphql/queries.py` - GraphQL queries
- [ ] (Optional) `graphql/mutations.py` - GraphQL mutations
- [ ] (Optional) `graphql/dataloaders.py` - DataLoaders for N+1 prevention

---

## Code Templates

### Quick Domain Template

Use this as a starting point and customize:

```bash
# Create domain structure
DOMAIN="invoices"
mkdir -p app/$DOMAIN/{rest,graphql}
touch app/$DOMAIN/__init__.py
touch app/$DOMAIN/models.py
touch app/$DOMAIN/interfaces.py
touch app/$DOMAIN/repository.py
touch app/$DOMAIN/service.py
touch app/$DOMAIN/dependencies.py
touch app/$DOMAIN/rest/{__init__.py,schemas.py,router.py}
touch app/$DOMAIN/graphql/{__init__.py,types.py,queries.py,mutations.py}
```

### Testing Template

```python
# tests/{domain}/test_service.py
import pytest
from pytest_mock import MockerFixture
from app.{domain}.service import {Domain}Service

@pytest.mark.asyncio
async def test_create_{domain}(mocker: MockerFixture):
    """Test {domain} creation"""
    mock_repo = mocker.Mock()
    mock_repo.create = mocker.AsyncMock(return_value=mock_entity)
    
    service = {Domain}Service(repository=mock_repo)
    result = await service.create_{domain}(data, tenant_id=1)
    
    mock_repo.create.assert_called_once()
    assert result.id is not None
```

---

## Next Steps

1. **Review** [Architecture.md](../Architecture.md) for system design
2. **Reference** [Definitions/Patterns.md](./Definitions/Patterns.md) for implementation patterns
3. **Follow** [.copilot-instructions.md](../../.copilot-instructions.md) for coding standards

---

**Remember**: Start with one domain, get it working end-to-end, then replicate the pattern for additional domains.
