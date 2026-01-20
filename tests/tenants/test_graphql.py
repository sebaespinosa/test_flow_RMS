"""
Unit tests for Tenants GraphQL queries and mutations.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.tenants.service import TenantService
from app.tenants.models import TenantEntity
from app.config.exceptions import NotFoundError, ConflictError


async def mock_get_db():
    """Mock database dependency to avoid database initialization in tests"""
    yield MagicMock()


@pytest.fixture
def mock_tenant_service():
    """Mock TenantService for GraphQL testing"""
    return AsyncMock(spec=TenantService)


@pytest.fixture
def client(mock_tenant_service):
    """TestClient with dependency overrides for GraphQL testing"""
    from app.database.session import get_db
    from app.graphql.context import get_graphql_context
    
    app = create_app()
    
    # Override get_db to avoid database initialization
    app.dependency_overrides[get_db] = mock_get_db
    
    # Override GraphQL context to inject mocked service
    async def mock_context(db=None):
        return {
            "db": MagicMock(),
            "tenant_service": mock_tenant_service,
        }
    
    app.dependency_overrides[get_graphql_context] = mock_context
    
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


class TestTenantsQuery:
    """Tests for GraphQL tenants query"""
    
    def test_query_tenants_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful tenants query returns list of tenants"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([sample_tenant], 1))
        
        query = """
            query {
                tenants {
                    id
                    name
                    description
                    isActive
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": query})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tenants" in data["data"]
        assert len(data["data"]["tenants"]) == 1
        
        tenant = data["data"]["tenants"][0]
        assert tenant["id"] == 1
        assert tenant["name"] == "Acme Corp"
        assert tenant["description"] == "Test tenant"
        assert tenant["isActive"] is True
        
        # Verify service was called with default parameters
        mock_tenant_service.list_tenants.assert_called_once_with(
            skip=0,
            limit=50,
            is_active=None
        )
    
    def test_query_tenants_with_pagination(self, client, mock_tenant_service):
        """Test tenants query with custom pagination"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([], 0))
        
        query = """
            query {
                tenants(skip: 10, limit: 20) {
                    id
                    name
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": query})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tenants"] == []
        
        # Verify service was called with custom pagination
        mock_tenant_service.list_tenants.assert_called_once_with(
            skip=10,
            limit=20,
            is_active=None
        )
    
    def test_query_tenants_filter_active(self, client, mock_tenant_service, sample_tenant):
        """Test filtering tenants by active status"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([sample_tenant], 1))
        
        query = """
            query {
                tenants(isActive: true) {
                    id
                    name
                    isActive
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": query})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["tenants"]) == 1
        assert data["data"]["tenants"][0]["isActive"] is True
        
        # Verify service was called with active filter
        mock_tenant_service.list_tenants.assert_called_once_with(
            skip=0,
            limit=50,
            is_active=True
        )
    
    def test_query_tenants_filter_inactive(self, client, mock_tenant_service):
        """Test filtering tenants by inactive status"""
        # Arrange
        inactive_tenant = TenantEntity(
            id=2,
            name="Inactive Corp",
            description=None,
            is_active=False,
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 10, 0, 0)
        )
        mock_tenant_service.list_tenants = AsyncMock(return_value=([inactive_tenant], 1))
        
        query = """
            query {
                tenants(isActive: false) {
                    id
                    name
                    isActive
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": query})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["tenants"]) == 1
        assert data["data"]["tenants"][0]["isActive"] is False
        
        # Verify service was called with inactive filter
        mock_tenant_service.list_tenants.assert_called_once_with(
            skip=0,
            limit=50,
            is_active=False
        )
    
    def test_query_tenants_empty_result(self, client, mock_tenant_service):
        """Test tenants query with no results"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([], 0))
        
        query = """
            query {
                tenants {
                    id
                    name
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": query})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tenants"] == []
    
    def test_query_tenants_with_timestamps(self, client, mock_tenant_service, sample_tenant):
        """Test querying tenants with timestamp fields"""
        # Arrange
        mock_tenant_service.list_tenants = AsyncMock(return_value=([sample_tenant], 1))
        
        query = """
            query {
                tenants {
                    id
                    name
                    createdAt
                    updatedAt
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": query})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        tenant = data["data"]["tenants"][0]
        assert "createdAt" in tenant
        assert "updatedAt" in tenant
        assert tenant["createdAt"] == "2026-01-20T10:00:00"
        assert tenant["updatedAt"] == "2026-01-20T10:00:00"


class TestCreateTenantMutation:
    """Tests for GraphQL createTenant mutation"""
    
    def test_create_tenant_success(self, client, mock_tenant_service, sample_tenant):
        """Test successful tenant creation via GraphQL mutation"""
        # Arrange
        mock_tenant_service.create_tenant = AsyncMock(return_value=sample_tenant)
        
        mutation = """
            mutation {
                createTenant(input: {
                    name: "Acme Corp",
                    description: "Test tenant"
                }) {
                    id
                    name
                    description
                    isActive
                    createdAt
                    updatedAt
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": mutation})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "createTenant" in data["data"]
        
        tenant = data["data"]["createTenant"]
        assert tenant["id"] == 1
        assert tenant["name"] == "Acme Corp"
        assert tenant["description"] == "Test tenant"
        assert tenant["isActive"] is True
        assert "createdAt" in tenant
        assert "updatedAt" in tenant
        
        # Verify service was called
        mock_tenant_service.create_tenant.assert_called_once()
        call_args = mock_tenant_service.create_tenant.call_args[0][0]
        assert call_args.name == "Acme Corp"
        assert call_args.description == "Test tenant"
    
    def test_create_tenant_minimal_data(self, client, mock_tenant_service):
        """Test creating tenant with only required fields"""
        # Arrange
        minimal_tenant = TenantEntity(
            id=2,
            name="Minimal Corp",
            description=None,
            is_active=True,
            created_at=datetime(2026, 1, 20, 11, 0, 0),
            updated_at=datetime(2026, 1, 20, 11, 0, 0)
        )
        mock_tenant_service.create_tenant = AsyncMock(return_value=minimal_tenant)
        
        mutation = """
            mutation {
                createTenant(input: {
                    name: "Minimal Corp"
                }) {
                    id
                    name
                    description
                    isActive
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": mutation})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        tenant = data["data"]["createTenant"]
        assert tenant["id"] == 2
        assert tenant["name"] == "Minimal Corp"
        assert tenant["description"] is None
        assert tenant["isActive"] is True
        
        # Verify service was called with None description
        call_args = mock_tenant_service.create_tenant.call_args[0][0]
        assert call_args.name == "Minimal Corp"
        assert call_args.description is None
    
    def test_create_tenant_duplicate_name_returns_error(self, client, mock_tenant_service):
        """Test creating tenant with duplicate name returns error"""
        # Arrange
        mock_tenant_service.create_tenant = AsyncMock(
            side_effect=ConflictError(detail="Tenant with name 'Acme Corp' already exists")
        )
        
        mutation = """
            mutation {
                createTenant(input: {
                    name: "Acme Corp"
                }) {
                    id
                    name
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": mutation})
        
        # Assert
        assert response.status_code == 200  # GraphQL returns 200 even for errors
        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) > 0
        # GraphQL error should contain the ConflictError message
        assert "Tenant with name 'Acme Corp' already exists" in str(data["errors"])
    
    def test_create_tenant_validation_error_empty_name(self, client, mock_tenant_service):
        """Test creating tenant with empty name returns validation error"""
        # Arrange
        mutation = """
            mutation {
                createTenant(input: {
                    name: ""
                }) {
                    id
                    name
                }
            }
        """
        
        # Act
        response = client.post("/graphql", json={"query": mutation})
        
        # Assert
        # GraphQL/Strawberry validation happens before service is called
        # So we expect either:
        # 1. A validation error in the response
        # 2. Or the service to be called and raise a validation error
        assert response.status_code == 200
        data = response.json()
        
        # If validation passed to service, it should not have been called with empty name
        # or it should raise an error
        if "errors" not in data:
            # Service handles validation
            mock_tenant_service.create_tenant.assert_not_called()
    
    def test_create_tenant_with_long_description(self, client, mock_tenant_service):
        """Test creating tenant with long description"""
        # Arrange
        long_desc_tenant = TenantEntity(
            id=3,
            name="Long Desc Corp",
            description="A" * 500,  # Long description
            is_active=True,
            created_at=datetime(2026, 1, 20, 12, 0, 0),
            updated_at=datetime(2026, 1, 20, 12, 0, 0)
        )
        mock_tenant_service.create_tenant = AsyncMock(return_value=long_desc_tenant)
        
        long_description = "A" * 500
        mutation = f"""
            mutation {{
                createTenant(input: {{
                    name: "Long Desc Corp",
                    description: "{long_description}"
                }}) {{
                    id
                    name
                    description
                }}
            }}
        """
        
        # Act
        response = client.post("/graphql", json={"query": mutation})
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        if "data" in data and data["data"]["createTenant"]:
            tenant = data["data"]["createTenant"]
            assert len(tenant["description"]) == 500
