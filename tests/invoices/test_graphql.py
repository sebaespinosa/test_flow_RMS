"""
Unit tests for Invoices GraphQL queries and mutations.
"""

from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.invoices.service import InvoiceService
from app.invoices.models import InvoiceEntity
from app.config.exceptions import ConflictError, NotFoundError, ValidationError


async def mock_get_db():
    """Mock database dependency to avoid DB initialization in GraphQL tests."""
    yield MagicMock()


@pytest.fixture
def mock_invoice_service():
    """Mocked InvoiceService for GraphQL tests."""
    return AsyncMock(spec=InvoiceService)


@pytest.fixture
def client(mock_invoice_service):
    """GraphQL TestClient with dependency overrides."""
    from app.database.session import get_db
    from app.graphql.context import get_graphql_context

    app = create_app()

    # Override DB dependency
    app.dependency_overrides[get_db] = mock_get_db

    # Override GraphQL context to inject mocked invoice service
    async def mock_context(db=None):
        return {
            "db": MagicMock(),
            "tenant_service": MagicMock(),
            "invoice_service": mock_invoice_service,
        }

    app.dependency_overrides[get_graphql_context] = mock_context

    return TestClient(app)


@pytest.fixture
def sample_invoice():
    """Sample invoice entity used across tests."""
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


class TestInvoicesQuery:
    """Tests for GraphQL invoices query."""

    def test_query_invoices_success(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.list_invoices = AsyncMock(return_value=[sample_invoice])

        query = """
            query {
                invoices(tenantId: 1) {
                    id
                    tenantId
                    vendorId
                    invoiceNumber
                    amount
                    currency
                    invoiceDate
                    dueDate
                    description
                    status
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        invoices = data["data"]["invoices"]
        assert len(invoices) == 1

        inv = invoices[0]
        assert inv["id"] == 1
        assert inv["tenantId"] == 1
        assert inv["invoiceNumber"] == "INV-001"
        assert inv["currency"] == "USD"
        assert inv["status"] == "open"

        mock_invoice_service.list_invoices.assert_called_once_with(
            tenant_id=1,
            skip=0,
            limit=50,
            status=None,
            vendor_id=None,
            min_amount=None,
            max_amount=None,
            start_date=None,
            end_date=None,
        )

    def test_query_invoices_with_filters_and_pagination(self, client, mock_invoice_service):
        mock_invoice_service.list_invoices = AsyncMock(return_value=[])

        query = """
            query {
                invoices(
                    tenantId: 2,
                    filters: { status: "paid", vendorId: 5, minAmount: 10, maxAmount: 200, startDate: "2026-01-01", endDate: "2026-12-31" },
                    skip: 5,
                    limit: 10
                ) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["invoices"] == []

        mock_invoice_service.list_invoices.assert_called_once_with(
            tenant_id=2,
            skip=5,
            limit=10,
            status="paid",
            vendor_id=5,
            min_amount=10,
            max_amount=200,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )

    def test_query_invoices_empty_result(self, client, mock_invoice_service):
        mock_invoice_service.list_invoices = AsyncMock(return_value=[])

        query = """
            query {
                invoices(tenantId: 3) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["invoices"] == []

    def test_query_invoices_validation_error(self, client, mock_invoice_service):
        mock_invoice_service.list_invoices = AsyncMock(
            side_effect=ValidationError(detail="Minimum amount cannot be greater than maximum amount")
        )

        query = """
            query {
                invoices(tenantId: 1, filters: { minAmount: 200, maxAmount: 100 }) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert "minimum amount" in data["errors"][0]["message"].lower()


class TestCreateInvoiceMutation:
    """Tests for GraphQL createInvoice mutation."""

    def test_create_invoice_success(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.create_invoice = AsyncMock(return_value=sample_invoice)

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: {
                        amount: 100.50,
                        vendorId: 2,
                        invoiceNumber: "INV-001",
                        currency: "USD",
                        invoiceDate: "2026-01-15",
                        dueDate: "2026-02-15",
                        description: "Test invoice",
                        status: "open"
                    }
                ) {
                    id
                    tenantId
                    invoiceNumber
                    amount
                    currency
                    status
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        inv = data["data"]["createInvoice"]
        assert inv["id"] == 1
        assert inv["tenantId"] == 1
        assert inv["invoiceNumber"] == "INV-001"
        assert inv["currency"] == "USD"

        mock_invoice_service.create_invoice.assert_called_once()
        call_args, call_kwargs = mock_invoice_service.create_invoice.call_args
        # The signature is (data, tenant_id)
        assert call_args[1] == 1

    def test_create_invoice_minimal_payload(self, client, mock_invoice_service, sample_invoice):
        sample_invoice.vendor_id = None
        sample_invoice.invoice_number = None
        sample_invoice.description = None
        sample_invoice.amount = Decimal("50.00")
        mock_invoice_service.create_invoice = AsyncMock(return_value=sample_invoice)

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: { amount: 50.00 }
                ) {
                    id
                    amount
                    vendorId
                    invoiceNumber
                    description
                    currency
                    status
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        inv = data["data"]["createInvoice"]
        assert inv["vendorId"] is None
        assert inv["invoiceNumber"] is None
        assert inv["description"] is None
        assert float(inv["amount"]) == 50.0
        assert inv["currency"] == "USD"
        assert inv["status"] == "open"
        mock_invoice_service.create_invoice.assert_called_once()

    def test_create_invoice_accepts_timestamp_seconds(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.create_invoice = AsyncMock(return_value=sample_invoice)

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: {
                        amount: 100.50,
                        invoiceDate: "1768471200",
                        dueDate: "1769810400"
                    }
                ) {
                    id
                    invoiceDate
                    dueDate
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        assert "errors" not in response.json()
        mock_invoice_service.create_invoice.assert_called_once()

    def test_create_invoice_accepts_timestamp_milliseconds(self, client, mock_invoice_service, sample_invoice):
        mock_invoice_service.create_invoice = AsyncMock(return_value=sample_invoice)

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: {
                        amount: 100.50,
                        invoiceDate: "1768471200000"
                    }
                ) {
                    id
                    invoiceDate
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        assert "errors" not in response.json()
        mock_invoice_service.create_invoice.assert_called_once()

    def test_create_invoice_rejects_invalid_date_format(self, client, mock_invoice_service):
        mock_invoice_service.create_invoice = AsyncMock()

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: {
                        amount: 100.50,
                        invoiceDate: "15/01/2026"
                    }
                ) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        assert "errors" in response.json()
        mock_invoice_service.create_invoice.assert_not_called()

    def test_create_invoice_conflict_error(self, client, mock_invoice_service):
        mock_invoice_service.create_invoice = AsyncMock(
            side_effect=ConflictError(detail="Invoice number already exists")
        )

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: { amount: 100.00, invoiceNumber: "DUP-1" }
                ) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert "already exists" in data["errors"][0]["message"].lower()

    def test_create_invoice_validation_error(self, client, mock_invoice_service):
        mock_invoice_service.create_invoice = AsyncMock(
            side_effect=ValidationError(detail="Due date cannot be before invoice date")
        )

        mutation = """
            mutation {
                createInvoice(
                    tenantId: 1,
                    input: {
                        amount: 100.00,
                        invoiceDate: "2026-02-10",
                        dueDate: "2026-02-01"
                    }
                ) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert "due date" in data["errors"][0]["message"].lower()


class TestDeleteInvoiceMutation:
    """Tests for GraphQL deleteInvoice mutation."""

    def test_delete_invoice_success(self, client, mock_invoice_service):
        mock_invoice_service.delete_invoice = AsyncMock(return_value=True)

        mutation = """
            mutation {
                deleteInvoice(tenantId: 1, invoiceId: 1)
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleteInvoice"] is True

    def test_delete_invoice_not_found(self, client, mock_invoice_service):
        mock_invoice_service.delete_invoice = AsyncMock(
            side_effect=NotFoundError(detail="Invoice not found")
        )

        mutation = """
            mutation {
                deleteInvoice(tenantId: 1, invoiceId: 999)
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert "not found" in data["errors"][0]["message"].lower()
