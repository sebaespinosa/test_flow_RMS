"""
Unit tests for Tenants REST API endpoints.
Tests all 6 endpoints with mocked service layer.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app
from app.tenants.models import TenantEntity
from app.tenants.service import TenantService
from app.config.exceptions import ConflictError, NotFoundError


async def mock_get_db():
    """Mock database dependency to avoid database initialization in tests"""
    yield MagicMock()


@pytest.fixture
def mock_tenant_service():
    """Mock TenantService for unit testing"""
    return AsyncMock(spec=TenantService)


@pytest.fixture
def client(mock_tenant_service):
    """FastAPI test client with dependency overrides"""
    from app.database.session import get_db
    from app.tenants.rest.router import get_tenant_service
    
    app = create_app()
    
    # Override dependencies to avoid database initialization
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service
    
    return TestClient(app)


@pytest.fixture
def sample_tenant():
    """Sample tenant entity for testing"""
    return TenantEntity(
        id=1,
        name="Acme Corp",
        description="Test tenant",
        is_active=True,
        created_at=datetime(2026, 1, 20, 10, 0, 0),
        updated_at=datetime(2026, 1, 20, 10, 0, 0)
    )


class TestCreateTenant:
    """Tests for POST /api/v1/tenants"""
    
    def test_create_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful tenant creation returns 201"""
        # Arrange
        mock_tenant_service.create_tenant = AsyncMock(return_value=sample_tenant)
        
        payload = {
            "name": "Acme Corp",
            "description": "Test tenant"
        }
        
        # Act
        response = client.post("/api/v1/tenants", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Acme Corp"
        assert data["description"] == "Test tenant"
        assert data["isActive"] is True
        assert "createdAt" in data
        assert "updatedAt" in data
    
    def test_create_tenant_minimal_data(self, client, mock_tenant_service, sample_tenant):
        """Test creating tenant with only required fields"""
        # Arrange
        sample_tenant.description = None
        mock_tenant_service.create_tenant = AsyncMock(return_value=sample_tenant)
        
        payload = {"name": "Minimal Corp"}
        
        # Act
        response = client.post("/api/v1/tenants", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Acme Corp"
        assert data["description"] is None
    
    def test_create_tenant_duplicate_name_returns_409(self, client, mock_tenant_service):
        """Test duplicate tenant name returns 409 Conflict"""
        # Arrange
        mock_tenant_service.create_tenant = AsyncMock(
            side_effect=ConflictError(detail="Tenant with name 'Acme Corp' already exists")
        )
        
        payload = {"name": "Acme Corp"}
        
        # Act
        response = client.post("/api/v1/tenants", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already exists" in data["detail"]
    
    def test_create_tenant_validation_error_empty_name(self, client):
        """Test validation error for empty name"""
        # Act
        response = client.post("/api/v1/tenants", json={"name": ""})
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_tenant_validation_error_missing_name(self, client):
        """Test validation error for missing name"""
        # Act
        response = client.post("/api/v1/tenants", json={})
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetTenant:
    """Tests for GET /api/v1/tenants/{id}"""
    
    def test_get_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful tenant retrieval returns 200"""
        # Arrange
        mock_tenant_service.get_tenant = AsyncMock(return_value=sample_tenant)
        
        # Act
        response = client.get("/api/v1/tenants/1")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Acme Corp"
        assert data["isActive"] is True
    
    def test_get_tenant_not_found_returns_404(self, client, mock_tenant_service):
        """Test getting non-existent tenant returns 404"""
        # Arrange
        mock_tenant_service.get_tenant = AsyncMock(
            side_effect=NotFoundError(detail="Tenant with id 999 not found")
        )
        
        # Act
        response = client.get("/api/v1/tenants/999")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_tenant_invalid_id_type(self, client):
        """Test invalid tenant ID type returns 422"""
        # Act
        response = client.get("/api/v1/tenants/invalid")
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListTenants:
    """Tests for GET /api/v1/tenants"""
    
    def test_list_tenants_default_pagination(self, client, mock_tenant_service, sample_tenant):
        """Test listing tenants with default pagination"""
        # Arrange
        tenants = [sample_tenant]
        mock_tenant_service.list_tenants = AsyncMock(return_value=(tenants, 1))
        
        # Act
        response = client.get("/api/v1/tenants")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["skip"] == 0
        assert data["limit"] == 50
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == 1
    
    def test_list_tenants_custom_pagination(self, client, mock_tenant_service, sample_tenant):
        """Test listing tenants with custom pagination"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([], 0))
        
        # Act
        response = client.get("/api/v1/tenants?skip=10&limit=20")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 20
        
        # Verify service was called with correct params
        mock_tenant_service.list_tenants.assert_called_once()
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["skip"] == 10
        assert call_kwargs["limit"] == 20
    
    def test_list_tenants_filter_by_active_status(self, client, mock_tenant_service):
        """Test filtering tenants by active status"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([], 0))
        
        # Act
        response = client.get("/api/v1/tenants?is_active=true")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["is_active"] is True
    
    def test_list_tenants_filter_by_date_range(self, client, mock_tenant_service):
        """Test filtering tenants by date range"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([], 0))
        
        # Act
        response = client.get(
            "/api/v1/tenants?"
            "created_date_start=2026-01-01T00:00:00&"
            "created_date_end=2026-01-31T23:59:59"
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_tenant_service.list_tenants.call_args.kwargs
        assert call_kwargs["created_date_start"] is not None
        assert call_kwargs["created_date_end"] is not None
    
    def test_list_tenants_empty_result(self, client, mock_tenant_service):
        """Test listing tenants returns empty list when no tenants exist"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([], 0))
        
        # Act
        response = client.get("/api/v1/tenants")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestUpdateTenant:
    """Tests for PATCH /api/v1/tenants/{id}"""
    
    def test_update_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful tenant update returns 200"""
        # Arrange
        sample_tenant.name = "Updated Corp"
        sample_tenant.description = "Updated description"
        mock_tenant_service.update_tenant = AsyncMock(return_value=sample_tenant)
        
        payload = {
            "name": "Updated Corp",
            "description": "Updated description"
        }
        
        # Act
        response = client.patch("/api/v1/tenants/1", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Updated Corp"
        assert data["description"] == "Updated description"
    
    def test_update_tenant_partial_update(self, client, mock_tenant_service, sample_tenant):
        """Test partial update (only name)"""
        # Arrange
        sample_tenant.name = "New Name"
        mock_tenant_service.update_tenant = AsyncMock(return_value=sample_tenant)
        
        payload = {"name": "New Name"}
        
        # Act
        response = client.patch("/api/v1/tenants/1", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Name"
    
    def test_update_tenant_not_found_returns_404(self, client, mock_tenant_service):
        """Test updating non-existent tenant returns 404"""
        # Arrange
        mock_tenant_service.update_tenant = AsyncMock(
            side_effect=NotFoundError(detail="Tenant with id 999 not found")
        )
        
        # Act
        response = client.patch("/api/v1/tenants/999", json={"name": "New Name"})
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_tenant_duplicate_name_returns_409(self, client, mock_tenant_service):
        """Test updating to duplicate name returns 409"""
        # Arrange
        mock_tenant_service.update_tenant = AsyncMock(
            side_effect=ConflictError(detail="Tenant with name 'Existing' already exists")
        )
        
        # Act
        response = client.patch("/api/v1/tenants/1", json={"name": "Existing"})
        
        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT


class TestSoftDeleteTenant:
    """Tests for DELETE /api/v1/tenants/{id}"""
    
    def test_soft_delete_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful soft delete returns 200"""
        # Arrange
        sample_tenant.is_active = False
        mock_tenant_service.soft_delete_tenant = AsyncMock(return_value=sample_tenant)
        
        # Act
        response = client.delete("/api/v1/tenants/1")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["isActive"] is False
    
    def test_soft_delete_tenant_not_found_returns_404(self, client, mock_tenant_service):
        """Test soft deleting non-existent tenant returns 404"""
        # Arrange
        mock_tenant_service.soft_delete_tenant = AsyncMock(
            side_effect=NotFoundError(detail="Tenant with id 999 not found")
        )
        
        # Act
        response = client.delete("/api/v1/tenants/999")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestReactivateTenant:
    """Tests for POST /api/v1/tenants/{id}/reactivate"""
    
    def test_reactivate_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful tenant reactivation returns 200"""
        # Arrange
        sample_tenant.is_active = True
        mock_tenant_service.reactivate_tenant = AsyncMock(return_value=sample_tenant)
        
        # Act
        response = client.post("/api/v1/tenants/1/reactivate")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["isActive"] is True
    
    def test_reactivate_tenant_not_found_returns_404(self, client, mock_tenant_service):
        """Test reactivating non-existent tenant returns 404"""
        # Arrange
        mock_tenant_service.reactivate_tenant = AsyncMock(
            side_effect=NotFoundError(detail="Tenant with id 999 not found")
        )
        
        # Act
        response = client.post("/api/v1/tenants/999/reactivate")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
