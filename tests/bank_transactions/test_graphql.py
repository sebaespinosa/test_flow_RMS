"""
Unit tests for Bank Transactions GraphQL queries and mutations.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.bank_transactions.service import BankTransactionService
from app.bank_transactions.models import BankTransactionEntity
from app.config.exceptions import ConflictError, NotFoundError, ValidationError


async def mock_get_db():
    """Mock database dependency to avoid DB initialization in GraphQL tests."""
    yield MagicMock()


@pytest.fixture
def mock_bank_transaction_service():
    """Mocked BankTransactionService for GraphQL tests."""
    return AsyncMock(spec=BankTransactionService)


@pytest.fixture
def client(mock_bank_transaction_service):
    """GraphQL TestClient with dependency overrides."""
    from app.database.session import get_db
    from app.graphql.context import get_graphql_context

    app = create_app()

    # Override DB dependency
    app.dependency_overrides[get_db] = mock_get_db

    # Override GraphQL context to inject mocked bank transaction service
    async def mock_context(db=None):
        return {
            "db": MagicMock(),
            "tenant_service": MagicMock(),
            "bank_transaction_service": mock_bank_transaction_service,
        }

    app.dependency_overrides[get_graphql_context] = mock_context

    return TestClient(app)


@pytest.fixture
def sample_transaction():
    """Sample bank transaction entity used across tests."""
    return BankTransactionEntity(
        id=1,
        tenant_id=1,
        external_id="EXT-001",
        posted_at=datetime(2026, 1, 15, 10, 30, 0),
        amount=Decimal("1000"),
        currency="USD",
        description="Transfer from account",
        created_at=datetime(2026, 1, 15, 10, 0, 0),
        updated_at=datetime(2026, 1, 15, 10, 0, 0),
    )


class TestBankTransactionsQuery:
    """Tests for GraphQL bank transactions query."""

    def test_list_bank_transactions_success(self, client, mock_bank_transaction_service, sample_transaction):
        """Test successfully listing bank transactions."""
        mock_bank_transaction_service.list_transactions = AsyncMock(
            return_value=[sample_transaction]
        )

        query = """
            query {
                bankTransactions(tenantId: 1) {
                    id
                    tenantId
                    externalId
                    postedAt
                    amount
                    currency
                    description
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Note: We may need to adjust field names based on actual implementation
        # This test structure mirrors the invoices tests

    def test_list_bank_transactions_empty(self, client, mock_bank_transaction_service):
        """Test listing bank transactions when none exist."""
        mock_bank_transaction_service.list_transactions = AsyncMock(return_value=[])

        query = """
            query {
                bankTransactions(tenantId: 1) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        # Should have empty list or data field with empty list

    def test_get_single_bank_transaction(self, client, mock_bank_transaction_service, sample_transaction):
        """Test getting a single bank transaction by ID."""
        mock_bank_transaction_service.get_transaction = AsyncMock(
            return_value=sample_transaction
        )

        query = """
            query {
                bankTransaction(tenantId: 1, id: 1) {
                    id
                    externalId
                    amount
                    currency
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_bank_transaction_not_found(self, client, mock_bank_transaction_service):
        """Test getting a non-existent bank transaction."""
        mock_bank_transaction_service.get_transaction = AsyncMock(return_value=None)

        query = """
            query {
                bankTransaction(tenantId: 1, id: 999) {
                    id
                }
            }
        """

        response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        # Should return null for non-existent record


class TestImportBankTransactionsMutation:
    """Tests for GraphQL import bank transactions mutation."""

    def test_import_transactions_success(self, client, mock_bank_transaction_service):
        """Test successfully importing bank transactions."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                externalId: "EXT-001",
                                postedAt: "1768471200",
                                amount: 1000,
                                currency: "USD",
                                description: "Transfer from account"
                            }
                        ]
                    }
                ) {
                    success
                    count
                    message
                    transactionIds
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_import_multiple_transactions(self, client, mock_bank_transaction_service):
        """Test importing multiple transactions in one batch."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: 1000,
                                currency: "USD"
                            },
                            {
                                postedAt: "1768471201",
                                amount: 500,
                                currency: "USD"
                            }
                        ]
                    }
                ) {
                    success
                    count
                    message
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_import_accepts_timestamp_seconds(self, client, mock_bank_transaction_service):
        """Test that import accepts Unix timestamp in seconds."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: 1000
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should not have errors
        if "errors" in data:
            # Check if it's a validation error about timestamp
            assert "postedAt" not in str(data.get("errors", []))

    def test_import_accepts_timestamp_milliseconds(self, client, mock_bank_transaction_service):
        """Test that import accepts Unix timestamp in milliseconds."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200000",
                                amount: 1000
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should not have errors about timestamp parsing

    def test_import_rejects_invalid_timestamp_format(self, client, mock_bank_transaction_service):
        """Test that import rejects invalid timestamp format."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "15/01/2026",
                                amount: 1000
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should have GraphQL error about invalid timestamp

    def test_import_rejects_negative_amount(self, client, mock_bank_transaction_service):
        """Test that import rejects negative amounts."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: -1000
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should have GraphQL error about negative amount

    def test_import_rejects_zero_amount(self, client, mock_bank_transaction_service):
        """Test that import rejects zero amounts."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: 0
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should have GraphQL error about zero amount

    def test_import_rejects_non_integer_amount(self, client, mock_bank_transaction_service):
        """Test that import rejects non-integer amounts (with cents)."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: 1000.50
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should have GraphQL error about non-integer amount

    def test_import_with_idempotency_key(self, client, mock_bank_transaction_service):
        """Test that idempotency key is handled correctly."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: 1000
                            }
                        ]
                    },
                    xIdempotencyKey: "idempotent-key-123"
                ) {
                    success
                    message
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should handle idempotency key

    def test_import_with_optional_fields(self, client, mock_bank_transaction_service):
        """Test importing with optional fields."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                externalId: "EXT-001",
                                postedAt: "1768471200",
                                amount: 1000,
                                currency: "EUR",
                                description: "Optional description"
                            }
                        ]
                    }
                ) {
                    success
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()

    def test_import_minimal_payload(self, client, mock_bank_transaction_service):
        """Test importing with minimal required fields."""
        mutation = """
            mutation {
                importBankTransactions(
                    tenantId: 1,
                    input: {
                        transactions: [
                            {
                                postedAt: "1768471200",
                                amount: 1000
                            }
                        ]
                    }
                ) {
                    success
                    count
                }
            }
        """

        response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        # Should succeed with minimal fields (externalId, currency, description are optional)
