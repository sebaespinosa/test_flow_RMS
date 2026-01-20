"""
Unit tests for Bank Transactions REST API endpoint.
Tests bulk import with idempotency support.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app
from app.bank_transactions.models import BankTransactionEntity
from app.bank_transactions.service import BankTransactionService
from app.infrastructure.idempotency.models import IdempotencyRecordEntity
from app.config.exceptions import ConflictError, NotFoundError, ValidationError


async def mock_get_db():
    """Mock database dependency to avoid DB initialization."""
    yield MagicMock()


@pytest.fixture
def mock_bank_transaction_service():
    """Mocked BankTransactionService."""
    return AsyncMock(spec=BankTransactionService)


@pytest.fixture
def mock_idempotency_repo():
    """Mocked IdempotencyRepository."""
    repo = MagicMock()
    repo.get_by_key = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update_response = AsyncMock()
    return repo


@pytest.fixture
def client(mock_bank_transaction_service, mock_idempotency_repo):
    """TestClient with dependency overrides."""
    from app.database.session import get_db
    from app.bank_transactions.rest.router import get_bank_transaction_service

    app = create_app()

    # Mock database session that supports commit
    mock_db = MagicMock()
    mock_db.commit = AsyncMock()

    async def get_mock_db():
        yield mock_db

    app.dependency_overrides[get_db] = get_mock_db
    app.dependency_overrides[get_bank_transaction_service] = lambda: mock_bank_transaction_service

    # Patch IdempotencyRepository to return our mock
    with patch('app.bank_transactions.rest.router.IdempotencyRepository', return_value=mock_idempotency_repo):
        yield TestClient(app)


@pytest.fixture
def sample_transactions():
    """Sample bank transaction entities."""
    return [
        BankTransactionEntity(
            id=1,
            tenant_id=1,
            external_id="TX-001",
            posted_at=datetime(2026, 1, 15, 10, 0, 0),
            amount=Decimal("150.00"),
            currency="USD",
            description="Payment received",
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 10, 0, 0),
        ),
        BankTransactionEntity(
            id=2,
            tenant_id=1,
            external_id="TX-002",
            posted_at=datetime(2026, 1, 16, 14, 30, 0),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Payment sent",
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 10, 0, 0),
        ),
    ]


class TestImportBankTransactions:
    """Tests for POST /api/v1/tenants/{tenant_id}/bank-transactions/import."""

    def test_import_success_without_idempotency_key(
        self, client, mock_bank_transaction_service, sample_transactions
    ):
        """Import transactions successfully without idempotency key."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            return_value=sample_transactions
        )

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,  # 2026-01-15T10:00:00Z
                    "amount": "150.00",
                    "currency": "USD",
                    "description": "Payment received",
                },
                {
                    "externalId": "TX-002",
                    "postedAt": 1768593000,  # 2026-01-16T14:30:00Z
                    "amount": "-50.00",
                    "currency": "USD",
                    "description": "Payment sent",
                },
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["importedCount"] == 2
        assert len(data["transactions"]) == 2
        assert data["transactions"][0]["externalId"] == "TX-001"
        assert float(data["transactions"][0]["amount"]) == 150.0
        assert data["transactions"][1]["externalId"] == "TX-002"
        assert float(data["transactions"][1]["amount"]) == -50.0

    def test_import_success_with_idempotency_key(
        self, client, mock_bank_transaction_service, mock_idempotency_repo, sample_transactions
    ):
        """Import transactions with idempotency key creates record."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            return_value=sample_transactions
        )
        mock_idempotency_repo.get_by_key = AsyncMock(return_value=None)

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": "150.00",
                    "currency": "USD",
                }
            ]
        }

        response = client.post(
            "/api/v1/tenants/1/bank-transactions/import",
            json=payload,
            headers={"Idempotency-Key": "import-123"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["importedCount"] == 2

        # Verify idempotency record was created and response cached
        mock_idempotency_repo.create.assert_called_once()
        mock_idempotency_repo.update_response.assert_called_once()

    def test_import_retry_with_same_key_returns_cached_response(
        self, client, mock_idempotency_repo
    ):
        """Retry with same idempotency key and payload returns cached response."""
        cached_response = {
            "importedCount": 2,
            "transactions": [
                {
                    "id": 1,
                    "tenantId": 1,
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": 150.0,
                    "currency": "USD",
                    "description": "Payment received",
                    "createdAt": "2026-01-20T10:00:00",
                    "updatedAt": "2026-01-20T10:00:00",
                }
            ],
        }

        existing_record = MagicMock(spec=IdempotencyRecordEntity)
        existing_record.request_payload_hash = "abc123"
        existing_record.response_body = cached_response
        mock_idempotency_repo.get_by_key = AsyncMock(return_value=existing_record)

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": "150.00",
                    "currency": "USD",
                    "description": "Payment received",
                }
            ]
        }

        # Mock hashlib to return consistent hash
        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "abc123"
            response = client.post(
                "/api/v1/tenants/1/bank-transactions/import",
                json=payload,
                headers={"Idempotency-Key": "import-123"},
            )

        # Cached responses still return 201 (original status code)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["importedCount"] == 2
        assert len(data["transactions"]) == 1

    def test_import_retry_with_different_payload_returns_409(
        self, client, mock_idempotency_repo
    ):
        """Retry with same idempotency key but different payload returns 409."""
        existing_record = MagicMock(spec=IdempotencyRecordEntity)
        existing_record.request_payload_hash = "original_hash"
        existing_record.response_body = {"importedCount": 1, "transactions": []}
        mock_idempotency_repo.get_by_key = AsyncMock(return_value=existing_record)

        payload = {
            "transactions": [
                {
                    "externalId": "TX-DIFFERENT",
                    "postedAt": 1768471200,
                    "amount": "999.00",
                    "currency": "USD",
                }
            ]
        }

        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "different_hash"
            response = client.post(
                "/api/v1/tenants/1/bank-transactions/import",
                json=payload,
                headers={"Idempotency-Key": "import-123"},
            )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "different request payload" in data["detail"].lower()

    def test_import_empty_transactions_returns_422(
        self, client, mock_bank_transaction_service
    ):
        """Empty transactions list returns validation error."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            side_effect=ValidationError(detail="Cannot import empty transaction list")
        )

        payload = {"transactions": []}

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_import_duplicate_external_ids_in_batch_returns_422(
        self, client, mock_bank_transaction_service
    ):
        """Duplicate external_ids in batch returns validation error."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            side_effect=ValidationError(detail="Duplicate external_ids found in import batch")
        )

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": "100.00",
                },
                {
                    "externalId": "TX-001",
                    "postedAt": 1768509600,
                    "amount": "200.00",
                },
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "duplicate" in data["detail"].lower()

    def test_import_existing_external_ids_returns_409(
        self, client, mock_bank_transaction_service
    ):
        """Transactions with existing external_ids return conflict error."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            side_effect=ConflictError(
                detail="Transactions with external_ids already exist: TX-001"
            )
        )

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already exist" in data["detail"]

    def test_import_tenant_not_found_returns_404(
        self, client, mock_bank_transaction_service
    ):
        """Import for non-existent tenant returns 404."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            side_effect=NotFoundError(detail="Tenant with id 999 not found")
        )

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/999/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_import_inactive_tenant_returns_422(
        self, client, mock_bank_transaction_service
    ):
        """Import for inactive tenant returns validation error."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            side_effect=ValidationError(detail="Tenant with id 1 is not active")
        )

        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    "postedAt": 1768471200,
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "not active" in data["detail"].lower()

    def test_import_without_external_id_is_allowed(
        self, client, mock_bank_transaction_service, sample_transactions
    ):
        """Transactions without external_id can be imported."""
        tx_without_external_id = BankTransactionEntity(
            id=3,
            tenant_id=1,
            external_id=None,
            posted_at=datetime(2026, 1, 15, 10, 0, 0),
            amount=Decimal("100.00"),
            currency="USD",
            description="Manual entry",
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 10, 0, 0),
        )

        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            return_value=[tx_without_external_id]
        )

        payload = {
            "transactions": [
                {
                    "postedAt": 1768471200,
                    "amount": "100.00",
                    "description": "Manual entry",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["importedCount"] == 1
        assert data["transactions"][0]["externalId"] is None

    def test_import_validates_required_fields(self, client):
        """Missing required fields returns validation error."""
        payload = {
            "transactions": [
                {
                    "externalId": "TX-001",
                    # Missing postedAt and amount
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_import_validates_currency_length(self, client):
        """Invalid currency code length returns validation error."""
        payload = {
            "transactions": [
                {
                    "postedAt": "2026-01-15T10:00:00",
                    "amount": "100.00",
                    "currency": "US",  # Too short
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_import_accepts_empty_string_fields(
        self, client, mock_bank_transaction_service, sample_transactions
    ):
        """Empty string fields are accepted and stored as-is."""
        tx_with_empty_fields = BankTransactionEntity(
            id=1,
            tenant_id=1,
            external_id="",  # Empty string (different from None)
            posted_at=datetime(2026, 1, 15, 10, 0, 0),
            amount=Decimal("100.00"),
            currency="USD",
            description="",  # Empty string (different from None)
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 10, 0, 0),
        )

        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            return_value=[tx_with_empty_fields]
        )

        payload = {
            "transactions": [
                {
                    "externalId": "",  # Explicitly empty
                    "postedAt": 1768471200,
                    "amount": "100.00",
                    "description": "",  # Explicitly empty
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["importedCount"] == 1
        # Empty strings are preserved (not converted to null)
        assert data["transactions"][0]["externalId"] == ""
        assert data["transactions"][0]["description"] == ""

    def test_import_accepts_millisecond_timestamp(
        self, client, mock_bank_transaction_service, sample_transactions
    ):
        """postedAt supports Unix timestamp in milliseconds."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            return_value=sample_transactions
        )

        payload = {
            "transactions": [
                {
                    "externalId": "TX-123",
                    "postedAt": 1768471200000,  # milliseconds
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_201_CREATED

    def test_import_rejects_invalid_datetime_format(self, client):
        """Non-timestamp postedAt returns 422 validation error."""
        payload = {
            "transactions": [
                {
                    "postedAt": "2026-01-15T10:00:00Z",  # ISO not allowed now
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_import_accepts_numeric_string_timestamp(
        self, client, mock_bank_transaction_service, sample_transactions
    ):
        """Numeric string timestamp is accepted (happy path)."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock(
            return_value=sample_transactions
        )

        payload = {
            "transactions": [
                {
                    "postedAt": "1768471200",  # string form of seconds timestamp
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        mock_bank_transaction_service.bulk_import_transactions.assert_awaited_once()

    def test_import_rejects_datetime_string_without_timestamp(
        self, client, mock_bank_transaction_service
    ):
        """Datetime string (non-timestamp) returns 422 (unhappy path)."""
        mock_bank_transaction_service.bulk_import_transactions = AsyncMock()

        payload = {
            "transactions": [
                {
                    "postedAt": "01/15/2026 10:00:00",  # not a Unix timestamp
                    "amount": "100.00",
                }
            ]
        }

        response = client.post("/api/v1/tenants/1/bank-transactions/import", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_bank_transaction_service.bulk_import_transactions.assert_not_awaited()
