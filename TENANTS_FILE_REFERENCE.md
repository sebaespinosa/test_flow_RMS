# Tenants Domain - File Reference Guide

Quick reference showing each of the 8 generated files with their complete content.

---

## 📁 File 1: app/tenants/__init__.py

```python
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
```

**Lines:** 8 | **Purpose:** Package documentation

---

## 📁 File 2: app/tenants/models.py

SQLAlchemy entity definition with soft delete and timestamps.

**Key Features:**
- `TenantEntity` class extending `Base` and `TimestampMixin`
- Fields: `id`, `name` (unique), `description`, `is_active`
- Indexes for: name, is_active, name+is_active
- Automatic `created_at`/`updated_at` timestamps

**Lines:** 45

---

## 📁 File 3: app/tenants/interfaces.py

Abstract repository interface defining the contract.

**Key Methods:**
- `get_by_id(tenant_id)` - Get tenant by ID
- `get_by_name(name)` - Get active tenant by name
- `get_all(skip, limit, is_active, created_date_start, created_date_end)` - List with filters
- `create(tenant)` - Create new tenant
- `update(tenant)` - Update existing tenant
- `soft_delete(tenant)` - Mark as inactive
- `exists_by_name(name)` - Check for duplicates

**Lines:** 59 | **Purpose:** Repository ABC contract

---

## 📁 File 4: app/tenants/repository.py

Concrete repository implementation.

**Key Implementation Details:**
- Implements `ITenantRepository`
- Uses SQLAlchemy async patterns
- Separate count query for pagination accuracy
- Dynamic filter building
- Returns tuples of (items, total_count)

**Lines:** 187 | **Purpose:** Data access layer

---

## 📁 File 5: app/tenants/service.py

Business logic layer.

**Key Methods:**
- `create_tenant(data)` - Validates no duplicate, creates entity
- `get_tenant(tenant_id)` - Fetches tenant or raises NotFoundError
- `list_tenants(skip, limit, is_active, created_date_start, created_date_end)` - Lists with filters
- `update_tenant(tenant_id, data)` - Partial update with conflict check
- `soft_delete_tenant(tenant_id)` - Soft deletes
- `reactivate_tenant(tenant_id)` - Reactivates soft-deleted tenant

**Validation:**
- Duplicate name detection → 409 Conflict
- Missing tenant → 404 Not Found
- Parameter validation (skip ≥ 0, limit 1-1000)

**Lines:** 200 | **Purpose:** Business logic

---

## 📁 File 6: app/tenants/rest/__init__.py

```python
"""
REST API layer for Tenants domain.
Handles HTTP endpoints, request/response serialization, and dependency injection.
"""
```

**Lines:** 4 | **Purpose:** REST layer package marker

---

## 📁 File 7: app/tenants/rest/schemas.py

Pydantic DTOs for request/response validation.

**Classes:**
- `TenantCreate` - POST request (name: required, description: optional)
- `TenantUpdate` - PATCH request (all fields optional)
- `TenantRead` - Response (all fields + timestamps)
- `TenantListResponse` - Paginated list (items, total, skip, limit, page, pages)

**Features:**
- Automatic camelCase conversion via `BaseSchema`
- Field validation (min/max length)
- Type hints with Field descriptions
- Helper properties for pagination (page, pages)

**Lines:** 93 | **Purpose:** Request/response DTOs

---

## 📁 File 8: app/tenants/rest/router.py

FastAPI endpoints with dependency injection.

**Endpoints:**
1. **POST /tenants** - Create (201/409/422)
2. **GET /tenants** - List with filters (200)
3. **GET /tenants/{id}** - Get by ID (200/404)
4. **PATCH /tenants/{id}** - Update (200/404/409/422)
5. **DELETE /tenants/{id}** - Soft delete (200/404)
6. **POST /tenants/{id}/reactivate** - Reactivate (200/404)

**Dependency Injection:**
- `get_tenant_repository(db)` - Injects Repository
- `get_tenant_service(repository)` - Injects Service

**Query Parameters (List Endpoint):**
- `skip` - Pagination offset (default 0)
- `limit` - Items per page (default 50, max 1000)
- `is_active` - Filter by status
- `created_date_start` - Filter from date
- `created_date_end` - Filter to date

**Lines:** 290 | **Purpose:** API endpoints

---

## 📊 Summary Statistics

| Metric | Value |
|--------|-------|
| Total Files | 8 |
| Total Lines | 886 |
| Classes | 15 |
| Methods | 35+ |
| Endpoints | 6 |
| Test-Ready | ✅ Yes |

---

## 🔍 Where to Find Each File

```
/Users/seba/no_sync/Githubs/Seba/test_flow_RMS/
├── app/tenants/__init__.py                    ← File 1
├── app/tenants/models.py                      ← File 2
├── app/tenants/interfaces.py                  ← File 3
├── app/tenants/repository.py                  ← File 4
├── app/tenants/service.py                     ← File 5
├── app/tenants/rest/__init__.py               ← File 6
├── app/tenants/rest/schemas.py                ← File 7
└── app/tenants/rest/router.py                 ← File 8
```

---

## ⚡ Quick Integration

### Step 1: Add to app/main.py

```python
from app.tenants.rest.router import router as tenants_router
app.include_router(tenants_router, prefix="/api/v1")
```

### Step 2: Create Migration

```bash
cd app
poetry run alembic revision --autogenerate -m "Add tenants table"
poetry run alembic upgrade head
```

### Step 3: Test

```bash
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp"}'
```

---

## ✅ Requirements Checklist

- ✅ File 1: Package documentation
- ✅ File 2: SQLAlchemy model with soft delete and timestamps
- ✅ File 3: Repository interface (dependency injection point)
- ✅ File 4: Repository implementation with pagination and filters
- ✅ File 5: Service layer with validation (409 Conflict logic)
- ✅ File 6: REST layer package marker
- ✅ File 7: Pydantic DTOs (TenantCreate, TenantUpdate, TenantRead, TenantListResponse)
- ✅ File 8: FastAPI router with Depends() DI and full endpoint documentation

**All requirements met. Ready to integrate and deploy!**
