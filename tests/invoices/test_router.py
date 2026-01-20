"""
Unit tests for Invoices REST API endpoints.
Covers create, get, list, update, and delete operations using mocked service layer.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app
from app.invoices.models import InvoiceEntity
from app.invoices.service import InvoiceService
from app.config.exceptions import ConflictError, NotFoundError, ValidationError


async def mock_get_db():
    """Mock database dependency to avoid database initialization in tests."""
    yield MagicMock()


@pytest.fixture
def mock_invoice_service():
    """Mock InvoiceService for unit testing."""
    return AsyncMock(spec=InvoiceService)


@pytest.fixture
def client(mock_invoice_service):
    """FastAPI test client with dependency overrides for invoices endpoints."""
    from app.database.session import get_db
    from app.invoices.rest.router import get_invoice_service

    app = create_app()

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service

    return TestClient(app)


@pytest.fixture
def sample_invoice():
    """Sample invoice entity for testing."""
    return InvoiceEntity(
        id=1,
        tenant_id=1,
        vendor_id=2,
        invoice_number="INV-001",
        amount=Decimal("100.50"),
        currency="USD",
        invoice_date=date(2026, 1, 15),
        due_date=date(2026, 2, 15),
        description="Test invoice",
        status="open",
        matched_transaction_id=None,
        created_at=datetime(2026, 1, 20, 10, 0, 0),
        updated_at=datetime(2026, 1, 20, 10, 0, 0),
    )


class TestCreateInvoice:
    """Tests for POST /api/v1/tenants/{tenant_id}/invoices."""

    def test_create_invoice_success(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.create_invoice = AsyncMock(return_value=sample_invoice)

        payload = {
            "vendorId": 2,
            "invoiceNumber": "INV-001",
            "amount": "100.50",
            "currency": "usd",
            "invoiceDate": "2026-01-15",
            "dueDate": "2026-02-15",
            "description": "Test invoice",
            "status": "open",
        }

        response = client.post("/api/v1/tenants/1/invoices", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == 1
        assert data["tenantId"] == 1
        assert data["vendorId"] == 2
        assert data["invoiceNumber"] == "INV-001"
        assert float(data["amount"]) == 100.5
        assert data["currency"] == "USD"
        assert data["status"] == "open"
        assert data["invoiceDate"] == "2026-01-15"
        assert data["dueDate"] == "2026-02-15"
        assert data["description"] == "Test invoice"
        assert "createdAt" in data
        assert "updatedAt" in data

    def test_create_invoice_minimal_data(self, client, mock_invoice_service, sample_invoice):
        sample_invoice.vendor_id = None
        sample_invoice.invoice_number = None
        sample_invoice.description = None
        sample_invoice.amount = Decimal("50.00")
        mock_invoice_service.create_invoice = AsyncMock(return_value=sample_invoice)

        payload = {
            "amount": "50.00"
        }

        response = client.post("/api/v1/tenants/1/invoices", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["vendorId"] is None
        assert data["invoiceNumber"] is None
        assert data["description"] is None
        assert float(data["amount"]) == 50.0
        assert data["currency"] == "USD"
        assert data["status"] == "open"

    def test_create_invoice_duplicate_number_returns_409(self, client, mock_invoice_service):
        mock_invoice_service.create_invoice = AsyncMock(
            side_effect=ConflictError(detail="Invoice number already exists")
        )

        payload = {
            "amount": "100.00",
            "invoiceNumber": "DUP-1"
        }

        response = client.post("/api/v1/tenants/1/invoices", json=payload)

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already exists" in data["detail"]

    def test_create_invoice_validation_due_date_before_invoice_date(self, client, mock_invoice_service):
        mock_invoice_service.create_invoice = AsyncMock(
            side_effect=ValidationError(detail="Due date cannot be before invoice date")
        )

        payload = {
            "amount": "100.00",
            "invoiceDate": "2026-02-01",
            "dueDate": "2026-01-01"
        }

        response = client.post("/api/v1/tenants/1/invoices", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Due date" in data["detail"]

    def test_create_invoice_request_validation_missing_amount(self, client):
        response = client.post("/api/v1/tenants/1/invoices", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetInvoice:
    """Tests for GET /api/v1/tenants/{tenant_id}/invoices/{id}."""

    def test_get_invoice_success(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.get_invoice = AsyncMock(return_value=sample_invoice)

        response = client.get("/api/v1/tenants/1/invoices/1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["tenantId"] == 1
        assert data["invoiceNumber"] == "INV-001"

    def test_get_invoice_not_found_returns_404(self, client, mock_invoice_service):
        mock_invoice_service.get_invoice = AsyncMock(
            side_effect=NotFoundError(detail="Invoice not found")
        )

        response = client.get("/api/v1/tenants/1/invoices/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_invoice_invalid_id_returns_422(self, client):
        response = client.get("/api/v1/tenants/1/invoices/invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListInvoices:
    """Tests for GET /api/v1/tenants/{tenant_id}/invoices."""

    def test_list_invoices_success(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.list_invoices = AsyncMock(return_value=[sample_invoice])

        response = client.get("/api/v1/tenants/1/invoices")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["invoiceNumber"] == "INV-001"

    def test_list_invoices_with_filters(self, client, mock_invoice_service):
        mock_invoice_service.list_invoices = AsyncMock(return_value=[])

        response = client.get(
            "/api/v1/tenants/1/invoices?"
            "status=paid&vendor_id=5&min_amount=10&max_amount=200&"
            "start_date=2026-01-01&end_date=2026-12-31&skip=5&limit=10"
        )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_invoice_service.list_invoices.call_args.kwargs
        assert call_kwargs["tenant_id"] == 1
        assert call_kwargs["status"] == "paid"
        assert call_kwargs["vendor_id"] == 5
        assert call_kwargs["min_amount"] == 10.0
        assert call_kwargs["max_amount"] == 200.0
        assert call_kwargs["start_date"] == "2026-01-01"
        assert call_kwargs["end_date"] == "2026-12-31"
        assert call_kwargs["skip"] == 5
        assert call_kwargs["limit"] == 10

    def test_list_invoices_empty_result(self, client, mock_invoice_service):
        mock_invoice_service.list_invoices = AsyncMock(return_value=[])

        response = client.get("/api/v1/tenants/1/invoices")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_invoices_invalid_pagination(self, client):
        response = client.get("/api/v1/tenants/1/invoices?skip=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_invoices_service_validation_error(self, client, mock_invoice_service):
        mock_invoice_service.list_invoices = AsyncMock(
            side_effect=ValidationError(detail="Minimum amount cannot be greater than maximum amount")
        )

        response = client.get(
            "/api/v1/tenants/1/invoices?min_amount=200&max_amount=100"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "minimum amount" in data["detail"].lower()


class TestUpdateInvoice:
    """Tests for PATCH /api/v1/tenants/{tenant_id}/invoices/{id}."""

    def test_update_invoice_success(self, client, mock_invoice_service, sample_invoice):
        sample_invoice.description = "Updated"
        mock_invoice_service.update_invoice = AsyncMock(return_value=sample_invoice)

        payload = {
            "description": "Updated"
        }

        response = client.patch("/api/v1/tenants/1/invoices/1", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated"

    def test_update_invoice_partial_fields(self, client, mock_invoice_service, sample_invoice):
        sample_invoice.amount = Decimal("150.00")
        sample_invoice.currency = "EUR"
        mock_invoice_service.update_invoice = AsyncMock(return_value=sample_invoice)

        payload = {
            "amount": "150.00",
            "currency": "EUR"
        }

        response = client.patch("/api/v1/tenants/1/invoices/1", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert float(data["amount"]) == 150.0
        assert data["currency"] == "EUR"

    def test_update_invoice_not_found_returns_404(self, client, mock_invoice_service):
        mock_invoice_service.update_invoice = AsyncMock(
            side_effect=NotFoundError(detail="Invoice not found")
        )

        response = client.patch("/api/v1/tenants/1/invoices/999", json={"description": "x"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_invoice_conflict_returns_409(self, client, mock_invoice_service):
        mock_invoice_service.update_invoice = AsyncMock(
            side_effect=ConflictError(detail="Invoice number exists")
        )

        response = client.patch("/api/v1/tenants/1/invoices/1", json={"invoiceNumber": "INV-001"})

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_invoice_validation_error(self, client, mock_invoice_service):
        mock_invoice_service.update_invoice = AsyncMock(
            side_effect=ValidationError(detail="Due date cannot be before invoice date")
        )

        payload = {
            "invoiceDate": "2026-02-10",
            "dueDate": "2026-02-01"
        }

        response = client.patch("/api/v1/tenants/1/invoices/1", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "due date" in data["detail"].lower()


class TestDeleteInvoice:
    """Tests for DELETE /api/v1/tenants/{tenant_id}/invoices/{id}."""

    def test_delete_invoice_success(self, client, mock_invoice_service):
        mock_invoice_service.delete_invoice = AsyncMock(return_value=True)

        response = client.delete("/api/v1/tenants/1/invoices/1")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

    def test_delete_invoice_not_found_returns_404(self, client, mock_invoice_service):
        mock_invoice_service.delete_invoice = AsyncMock(
            side_effect=NotFoundError(detail="Invoice not found")
        )

        response = client.delete("/api/v1/tenants/1/invoices/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

