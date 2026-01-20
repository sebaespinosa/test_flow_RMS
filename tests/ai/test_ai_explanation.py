"""
Tests for AI explanation service and explain_match functionality.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.bank_transactions.models import BankTransactionEntity
from app.config.exceptions import NotFoundError
from app.config.settings import Settings
from app.invoices.models import InvoiceEntity
from app.reconciliation.models import MatchEntity
from app.reconciliation.service import ReconciliationService
from app.ai.service import AIExplanationService


@pytest.fixture
def mock_settings():
    """Mock settings with AI enabled"""
    settings = MagicMock(spec=Settings)
    settings.ai_enabled = True
    settings.gemini_api_key = "test-api-key"
    settings.ai_system_prompt = "You are a financial reconciliation expert."
    settings.ai_temperature = 0.7
    settings.ai_max_tokens = 500
    return settings


@pytest.fixture
def mock_match_repo():
    """Mock match repository"""
    return AsyncMock()


@pytest.fixture
def mock_invoice_repo():
    """Mock invoice repository"""
    return AsyncMock()


@pytest.fixture
def mock_transaction_repo():
    """Mock transaction repository"""
    return AsyncMock()


@pytest.fixture
def mock_ai_service():
    """Mock AI explanation service"""
    return AsyncMock(spec=AIExplanationService)


@pytest.fixture
def reconciliation_service(
    mock_match_repo,
    mock_invoice_repo,
    mock_transaction_repo,
    mock_ai_service,
    mock_settings,
):
    """Create reconciliation service with mocked dependencies"""
    return ReconciliationService(
        match_repo=mock_match_repo,
        invoice_repo=mock_invoice_repo,
        transaction_repo=mock_transaction_repo,
        ai_service=mock_ai_service,
        settings=mock_settings,
    )


@pytest.fixture
def sample_match():
    """Sample match entity"""
    return MatchEntity(
        id=1,
        tenant_id=1,
        invoice_id=10,
        bank_transaction_id=20,
        score=Decimal("92.5"),
        status="proposed",
        reason="Amount matches, date within 2 days",
        created_at=datetime.utcnow(),
        confirmed_at=None,
    )


@pytest.fixture
def sample_invoice():
    """Sample invoice entity"""
    return InvoiceEntity(
        id=10,
        tenant_id=1,
        vendor_id=100,
        amount=Decimal("1500.00"),
        invoice_date=datetime(2024, 1, 15).date(),
        description="Office supplies",
        status="unmatched",
        matched_transaction_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_transaction():
    """Sample bank transaction entity"""
    return BankTransactionEntity(
        id=20,
        tenant_id=1,
        amount=Decimal("1500.00"),
        posted_at=datetime(2024, 1, 16),
        description="Payment to vendor",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestExplainMatch:
    """Tests for explain_match service method"""

    @pytest.mark.asyncio
    async def test_explain_match_with_ai_success(
        self,
        reconciliation_service,
        mock_match_repo,
        mock_invoice_repo,
        mock_transaction_repo,
        mock_ai_service,
        sample_match,
        sample_invoice,
        sample_transaction,
    ):
        """Test explain_match returns AI explanation when successful"""
        mock_match_repo.get_by_id.return_value = sample_match
        mock_invoice_repo.get_by_id.return_value = sample_invoice
        mock_transaction_repo.get_by_id.return_value = sample_transaction
        mock_ai_service.generate_explanation.return_value = {
            "explanation": "Both invoice and transaction are for $1,500 and within 2 days of each other.",
            "confidence": 95,
        }

        result = await reconciliation_service.explain_match(1, 1)

        assert result["ai_explanation"] is not None
        assert result["ai_confidence"] == 95
        assert result["source"] == "ai"
        assert result["ai_error_message"] is None
        assert result["heuristic_score"] == 92

        mock_match_repo.get_by_id.assert_called_once_with(1, 1)
        mock_invoice_repo.get_by_id.assert_called_once_with(10, 1)
        mock_transaction_repo.get_by_id.assert_called_once_with(20, 1)
        mock_ai_service.generate_explanation.assert_called_once()

    @pytest.mark.asyncio
    async def test_explain_match_ai_fallback_on_error(
        self,
        reconciliation_service,
        mock_match_repo,
        mock_invoice_repo,
        mock_transaction_repo,
        mock_ai_service,
        sample_match,
        sample_invoice,
        sample_transaction,
    ):
        """Test explain_match falls back to heuristic when AI fails"""
        mock_match_repo.get_by_id.return_value = sample_match
        mock_invoice_repo.get_by_id.return_value = sample_invoice
        mock_transaction_repo.get_by_id.return_value = sample_transaction
        mock_ai_service.generate_explanation.side_effect = Exception("API timeout")

        result = await reconciliation_service.explain_match(1, 1)

        assert result["ai_explanation"] is None
        assert result["ai_confidence"] is None
        assert result["source"] == "fallback"
        assert result["ai_error_message"] == "API timeout"
        assert result["heuristic_reason"] is not None

    @pytest.mark.asyncio
    async def test_explain_match_ai_disabled(
        self,
        mock_match_repo,
        mock_invoice_repo,
        mock_transaction_repo,
        mock_ai_service,
        mock_settings,
        sample_match,
        sample_invoice,
        sample_transaction,
    ):
        """Test explain_match uses heuristic when AI is disabled"""
        mock_settings.ai_enabled = False
        service = ReconciliationService(
            match_repo=mock_match_repo,
            invoice_repo=mock_invoice_repo,
            transaction_repo=mock_transaction_repo,
            ai_service=None,
            settings=mock_settings,
        )

        mock_match_repo.get_by_id.return_value = sample_match
        mock_invoice_repo.get_by_id.return_value = sample_invoice
        mock_transaction_repo.get_by_id.return_value = sample_transaction

        result = await service.explain_match(1, 1)

        assert result["ai_explanation"] is None
        assert result["ai_confidence"] is None
        assert result["source"] == "heuristic"
        assert result["ai_error_message"] is None
        assert result["heuristic_reason"] is not None

    @pytest.mark.asyncio
    async def test_explain_match_not_found(
        self,
        reconciliation_service,
        mock_match_repo,
    ):
        """Test explain_match raises NotFoundError when match doesn't exist"""
        mock_match_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await reconciliation_service.explain_match(999, 1)

    @pytest.mark.asyncio
    async def test_explain_match_invoice_not_found(
        self,
        reconciliation_service,
        mock_match_repo,
        mock_invoice_repo,
        sample_match,
    ):
        """Test explain_match raises NotFoundError when invoice doesn't exist"""
        mock_match_repo.get_by_id.return_value = sample_match
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await reconciliation_service.explain_match(1, 1)

    @pytest.mark.asyncio
    async def test_explain_match_transaction_not_found(
        self,
        reconciliation_service,
        mock_match_repo,
        mock_invoice_repo,
        mock_transaction_repo,
        sample_match,
        sample_invoice,
    ):
        """Test explain_match raises NotFoundError when transaction doesn't exist"""
        mock_match_repo.get_by_id.return_value = sample_match
        mock_invoice_repo.get_by_id.return_value = sample_invoice
        mock_transaction_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await reconciliation_service.explain_match(1, 1)

    @pytest.mark.asyncio
    async def test_explain_match_context_structure(
        self,
        reconciliation_service,
        mock_match_repo,
        mock_invoice_repo,
        mock_transaction_repo,
        mock_ai_service,
        sample_match,
        sample_invoice,
        sample_transaction,
    ):
        """Test explain_match passes correct context structure to AI service"""
        mock_match_repo.get_by_id.return_value = sample_match
        mock_invoice_repo.get_by_id.return_value = sample_invoice
        mock_transaction_repo.get_by_id.return_value = sample_transaction
        mock_ai_service.generate_explanation.return_value = {
            "explanation": "Match explanation",
            "confidence": 90,
        }

        await reconciliation_service.explain_match(1, 1)

        call_args = mock_ai_service.generate_explanation.call_args
        context = call_args[0][0] if call_args[0] else call_args.kwargs.get("context")

        assert "invoice" in context
        assert context["invoice"]["id"] == 10
        assert context["invoice"]["amount"] == 1500.0
        assert context["invoice"]["vendor_id"] == 100

        assert "transaction" in context
        assert context["transaction"]["id"] == 20
        assert context["transaction"]["amount"] == 1500.0

        assert "match" in context
        assert context["match"]["score"] == 92.5
        assert context["match"]["reason"] == "Amount matches, date within 2 days"


class TestExplainEndpoint:
    """Tests for explain_match REST endpoint - requires full app integration tests"""
    pass
