"""
Unit tests for Reconciliation REST API endpoints.
Tests reconciliation (match proposal) and match confirmation.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app
from app.reconciliation.models import MatchEntity
from app.reconciliation.service import ReconciliationService
from app.invoices.models import InvoiceEntity
from app.bank_transactions.models import BankTransactionEntity


async def mock_get_db():
    """Mock database dependency to avoid database initialization in tests."""
    yield MagicMock()


@pytest.fixture
def mock_reconciliation_service():
    """Mock ReconciliationService for unit testing."""
    return AsyncMock(spec=ReconciliationService)


@pytest.fixture
def client(mock_reconciliation_service):
    """FastAPI test client with dependency overrides for reconciliation endpoints."""
    from app.database.session import get_db
    from app.reconciliation.rest.router import get_reconciliation_service

    app = create_app()

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_reconciliation_service] = lambda: mock_reconciliation_service

    return TestClient(app)


@pytest.fixture
def sample_invoice():
    """Sample invoice entity for testing."""
    return InvoiceEntity(
        id=10,
        tenant_id=1,
        vendor_id=2,
        invoice_number="INV-500",
        amount=Decimal("1000"),
        currency="USD",
        invoice_date=date(2026, 1, 15),
        due_date=date(2026, 2, 15),
        description="Test invoice",
        status="open",
        matched_transaction_id=None,
        created_at=datetime(2026, 1, 20, 10, 0, 0),
        updated_at=datetime(2026, 1, 20, 10, 0, 0),
    )


@pytest.fixture
def sample_transaction():
    """Sample bank transaction entity for testing."""
    return BankTransactionEntity(
        id=25,
        tenant_id=1,
        external_id=None,
        posted_at=datetime(2026, 1, 17, 10, 30, 0),
        amount=Decimal("1000"),
        currency="USD",
        description="Payment for INV-500",
        created_at=datetime(2026, 1, 17, 10, 0, 0),
        updated_at=datetime(2026, 1, 17, 10, 0, 0),
    )


@pytest.fixture
def sample_match():
    """Sample match entity for testing."""
    return MatchEntity(
        id=1,
        tenant_id=1,
        invoice_id=10,
        bank_transaction_id=25,
        score=Decimal("95"),
        status="proposed",
        reason="Exact amount match + 2 days apart + INV-500 in description",
        confirmed_at=None,
        created_at=datetime(2026, 1, 20, 10, 0, 0),
        updated_at=datetime(2026, 1, 20, 10, 0, 0),
    )


class TestReconcileEndpoint:
    """Tests for POST /tenants/{tenant_id}/reconcile endpoint."""

    def test_reconcile_returns_candidates_sorted_by_score(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that reconciliation returns candidates sorted by score descending."""
        mock_match_2 = MatchEntity(
            id=2,
            tenant_id=1,
            invoice_id=11,
            bank_transaction_id=26,
            score=Decimal("75"),
            status="proposed",
            reason="Amount match + vendor in description",
            confirmed_at=None,
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 10, 0, 0),
        )

        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 5,
                "returned": 2,
                "candidates": [sample_match, mock_match_2],  # Sorted by score desc
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["returned"] == 2
        assert len(data["candidates"]) == 2
        assert float(data["candidates"][0]["score"]) == 95  # Higher score first (as string in JSON)
        assert float(data["candidates"][1]["score"]) == 75  # Lower score second
        assert data["candidates"][0]["status"] == "proposed"

    def test_reconcile_with_top_parameter(self, client, mock_reconciliation_service, sample_match):
        """Test that 'top' query parameter limits results."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 10,
                "returned": 5,
                "candidates": [sample_match],  # Only 5 returned (top=5 is default)
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile?top=5")

        assert response.status_code == status.HTTP_200_OK
        # The router calls service.run_reconciliation(tenant_id, top=top, min_score=min_score)
        # with positional arg for tenant_id
        mock_reconciliation_service.run_reconciliation.assert_called_once_with(
            1,  # tenant_id passed as positional arg
            top=5,
            min_score=Decimal("60"),
        )

    def test_reconcile_with_custom_top_value(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test custom top value parameter."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 20,
                "returned": 10,
                "candidates": [sample_match],
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile?top=10")

        assert response.status_code == status.HTTP_200_OK
        mock_reconciliation_service.run_reconciliation.assert_called_once_with(
            1,  # tenant_id as positional arg
            top=10,
            min_score=Decimal("60"),
        )

    def test_reconcile_with_min_score_parameter(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that 'min_score' query parameter filters by confidence."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 20,
                "returned": 2,
                "candidates": [sample_match],  # Only high-confidence matches
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile?min_score=80")

        assert response.status_code == status.HTTP_200_OK
        mock_reconciliation_service.run_reconciliation.assert_called_once_with(
            1,  # tenant_id as positional arg
            top=5,
            min_score=Decimal("80"),
        )

    def test_reconcile_with_both_parameters(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test reconciliation with both top and min_score parameters."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 30,
                "returned": 3,
                "candidates": [sample_match],
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile?top=3&min_score=85")

        assert response.status_code == status.HTTP_200_OK
        mock_reconciliation_service.run_reconciliation.assert_called_once_with(
            1,  # tenant_id as positional arg
            top=3,
            min_score=Decimal("85"),
        )

    def test_reconcile_returns_empty_when_no_candidates(
        self, client, mock_reconciliation_service
    ):
        """Test reconciliation returns empty list when no matches found."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 0,
                "returned": 0,
                "candidates": [],
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["returned"] == 0
        assert data["candidates"] == []

    def test_reconcile_returns_all_when_fewer_than_top(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that if results < top, all are returned."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 3,
                "returned": 3,
                "candidates": [sample_match],  # Only 3 total, top=5 requested
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile?top=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert data["returned"] == 3

    def test_reconcile_match_includes_reason(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that match reason is included in response."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 1,
                "returned": 1,
                "candidates": [sample_match],
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        match = data["candidates"][0]
        assert "reason" in match
        assert "Exact amount match" in match["reason"]

    def test_reconcile_includes_match_metadata(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that match includes all required fields."""
        mock_reconciliation_service.run_reconciliation = AsyncMock(
            return_value={
                "total": 1,
                "returned": 1,
                "candidates": [sample_match],
            }
        )

        response = client.post("/api/v1/tenants/1/reconcile")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        match = data["candidates"][0]
        assert match["id"] == 1
        assert match["invoiceId"] == 10  # camelCase due to alias_generator
        assert match["bankTransactionId"] == 25
        assert match["score"] == "95"  # Decimal serialized as string
        assert match["status"] == "proposed"
        assert "createdAt" in match


class TestConfirmMatchEndpoint:
    """Tests for POST /tenants/{tenant_id}/matches/{match_id}/confirm endpoint."""

    def test_confirm_match_success(self, client, mock_reconciliation_service, sample_match):
        """Test successfully confirming a proposed match."""
        confirmed_match = sample_match
        confirmed_match.status = "confirmed"
        confirmed_match.confirmed_at = datetime(2026, 1, 20, 11, 0, 0)

        mock_reconciliation_service.confirm_match = AsyncMock(
            return_value=confirmed_match
        )

        response = client.post("/api/v1/tenants/1/matches/1/confirm")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "confirmed"
        assert data["id"] == 1
        assert data["invoiceId"] == 10  # camelCase
        assert data["bankTransactionId"] == 25
        mock_reconciliation_service.confirm_match.assert_called_once_with(1, 1)

    def test_confirm_match_returns_match_details(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that confirm endpoint returns full match details."""
        sample_match.status = "confirmed"
        mock_reconciliation_service.confirm_match = AsyncMock(
            return_value=sample_match
        )

        response = client.post("/api/v1/tenants/1/matches/1/confirm")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["score"] == "95"  # Decimal serialized as string
        assert data["reason"] is not None
        assert "createdAt" in data

    def test_confirm_match_not_found_returns_404(self, client, mock_reconciliation_service):
        """Test that confirming non-existent match returns 404."""
        from app.config.exceptions import NotFoundError

        mock_reconciliation_service.confirm_match = AsyncMock(
            side_effect=NotFoundError(detail="Match 999 not found")
        )

        response = client.post("/api/v1/tenants/1/matches/999/confirm")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Match" in data["detail"]

    def test_confirm_match_invoice_already_matched_returns_409(
        self, client, mock_reconciliation_service
    ):
        """Test that confirming match for already-matched invoice returns 409."""
        from app.config.exceptions import ConflictError

        mock_reconciliation_service.confirm_match = AsyncMock(
            side_effect=ConflictError(
                detail="Invoice already matched to transaction 99"
            )
        )

        response = client.post("/api/v1/tenants/1/matches/1/confirm")

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already matched" in data["detail"]

    def test_confirm_match_uses_correct_tenant_id(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test that confirm_match is called with correct tenant isolation."""
        mock_reconciliation_service.confirm_match = AsyncMock(
            return_value=sample_match
        )

        response = client.post("/api/v1/tenants/5/matches/42/confirm")

        assert response.status_code == status.HTTP_200_OK
        mock_reconciliation_service.confirm_match.assert_called_once_with(42, 5)

    def test_confirm_match_multiple_invoices(
        self, client, mock_reconciliation_service, sample_match
    ):
        """Test confirming matches for different invoices."""
        mock_reconciliation_service.confirm_match = AsyncMock(
            return_value=sample_match
        )

        # Confirm match for invoice 10
        response1 = client.post("/api/v1/tenants/1/matches/1/confirm")
        assert response1.status_code == status.HTTP_200_OK

        # Confirm match for invoice 11
        sample_match.invoice_id = 11
        response2 = client.post("/api/v1/tenants/1/matches/2/confirm")
        assert response2.status_code == status.HTTP_200_OK

        assert mock_reconciliation_service.confirm_match.call_count == 2
