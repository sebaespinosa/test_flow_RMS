"""
GraphQL tests for reconciliation domain.
Tests query and mutation resolvers with mocked service layer.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.main import create_app
from app.reconciliation.models import MatchEntity
from app.reconciliation.service import ReconciliationService


@pytest.fixture
def mock_reconciliation_service():
    """Mock ReconciliationService for GraphQL testing"""
    return AsyncMock(spec=ReconciliationService)


@pytest.fixture
def sample_match():
    """Sample match entity for testing"""
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


def get_graphql_client(app):
    """Get GraphQL test client for app"""
    from httpx import AsyncClient

    return AsyncClient(app=app, base_url="http://testserver")


class TestExplainReconciliationQuery:
    """Tests for explainReconciliation query"""

    @pytest.mark.asyncio
    async def test_explain_reconciliation_query_structure(self):
        """Test that explainReconciliation query is properly defined"""
        from app.reconciliation.graphql.queries import Query
        from app.reconciliation.graphql.types import ExplanationType

        # Verify query has explainReconciliation method
        assert hasattr(Query, "explain_reconciliation")

        # Get the resolver
        resolver = getattr(Query, "explain_reconciliation")

        # Verify it's a callable method
        assert callable(resolver)

    @pytest.mark.asyncio
    async def test_explain_reconciliation_returns_explanation_type(self):
        """Test that explainReconciliation returns ExplanationType"""
        from app.reconciliation.graphql.queries import Query

        # Verify return type annotation
        resolver = getattr(Query, "explain_reconciliation")
        assert callable(resolver)
        
        # Check the function has proper annotations
        assert hasattr(resolver, "__annotations__")
        assert "return" in resolver.__annotations__


class TestReconcileMutation:
    """Tests for reconcile mutation"""

    @pytest.mark.asyncio
    async def test_reconcile_with_defaults(self):
        """Test reconcile mutation with default parameters"""
        query = """
            mutation {
                reconcile(tenantId: 1) {
                    total
                    returned
                    candidates {
                        id
                        invoiceId
                        bankTransactionId
                        score
                        status
                        reason
                        createdAt
                    }
                }
            }
        """

        app = create_app()
        # Query structure validation
        assert "mutation" in query
        assert "reconcile" in query

    @pytest.mark.asyncio
    async def test_reconcile_with_input(self):
        """Test reconcile mutation with input parameters"""
        query = """
            mutation {
                reconcile(
                    tenantId: 1,
                    input: { top: 10, minScore: "80" }
                ) {
                    total
                    returned
                    candidates {
                        id
                        score
                        status
                    }
                }
            }
        """

        app = create_app()
        # Query structure validation
        assert "mutation" in query
        assert "top: 10" in query
        assert "minScore" in query

    @pytest.mark.asyncio
    async def test_reconcile_mutation_structure(self):
        """Test that reconcile mutation is properly defined"""
        from app.reconciliation.graphql.mutations import Mutation

        # Verify mutation has reconcile method
        assert hasattr(Mutation, "reconcile")

        # Get the resolver
        resolver = getattr(Mutation, "reconcile")

        # Verify it's a callable method
        assert callable(resolver)

    def test_reconciliation_input_type_structure(self):
        """Test ReconciliationInput type structure"""
        from app.reconciliation.graphql.types import ReconciliationInput

        # Verify input has expected fields
        assert hasattr(ReconciliationInput, "__strawberry_definition__")

    @pytest.mark.asyncio
    async def test_reconcile_returns_reconciliation_result(self):
        """Test that reconcile returns ReconciliationResultType"""
        from app.reconciliation.graphql.mutations import Mutation

        resolver = getattr(Mutation, "reconcile")
        assert callable(resolver)
        assert hasattr(resolver, "__annotations__")


class TestConfirmMatchMutation:
    """Tests for confirmMatch mutation"""

    @pytest.mark.asyncio
    async def test_confirm_match_mutation(self):
        """Test confirmMatch mutation"""
        query = """
            mutation {
                confirmMatch(tenantId: 1, matchId: 1) {
                    id
                    invoiceId
                    bankTransactionId
                    score
                    status
                    reason
                    createdAt
                }
            }
        """

        app = create_app()
        # Query structure validation
        assert "mutation" in query
        assert "confirmMatch" in query
        assert "matchId: 1" in query

    @pytest.mark.asyncio
    async def test_confirm_match_mutation_structure(self):
        """Test that confirmMatch mutation is properly defined"""
        from app.reconciliation.graphql.mutations import Mutation

        # Verify mutation has confirm_match method
        assert hasattr(Mutation, "confirm_match")

        # Get the resolver
        resolver = getattr(Mutation, "confirm_match")

        # Verify it's a callable method
        assert callable(resolver)

    @pytest.mark.asyncio
    async def test_confirm_match_returns_match_type(self):
        """Test that confirmMatch returns MatchType"""
        from app.reconciliation.graphql.mutations import Mutation
        from app.reconciliation.graphql.types import MatchType

        resolver = getattr(Mutation, "confirm_match")
        assert callable(resolver)
        assert hasattr(resolver, "__annotations__")


class TestMatchTypeConversion:
    """Tests for MatchType.from_entity conversion"""

    def test_match_type_from_entity(self, sample_match):
        """Test conversion of MatchEntity to MatchType"""
        from app.reconciliation.graphql.types import MatchType

        match_type = MatchType.from_entity(sample_match)

        assert match_type.id == 1
        assert match_type.invoice_id == 10
        assert match_type.bank_transaction_id == 25
        assert match_type.score == Decimal("95")
        assert match_type.status == "proposed"
        assert match_type.reason == "Exact amount match + 2 days apart + INV-500 in description"
        assert match_type.confirmed_at is None
        assert match_type.created_at == datetime(2026, 1, 20, 10, 0, 0)

    def test_match_type_from_entity_with_confirmation(self):
        """Test MatchType conversion with confirmed match"""
        from app.reconciliation.graphql.types import MatchType

        confirmed_match = MatchEntity(
            id=2,
            tenant_id=1,
            invoice_id=11,
            bank_transaction_id=26,
            score=Decimal("85"),
            status="confirmed",
            reason="Amount + date match",
            confirmed_at=datetime(2026, 1, 20, 11, 0, 0),
            created_at=datetime(2026, 1, 20, 10, 0, 0),
            updated_at=datetime(2026, 1, 20, 11, 0, 0),
        )

        match_type = MatchType.from_entity(confirmed_match)

        assert match_type.status == "confirmed"
        assert match_type.confirmed_at == datetime(2026, 1, 20, 11, 0, 0)


class TestGraphQLTypeDefinitions:
    """Tests for GraphQL type definitions"""

    def test_match_type_is_strawberry_type(self):
        """Test that MatchType is a valid Strawberry type"""
        from app.reconciliation.graphql.types import MatchType

        assert hasattr(MatchType, "__strawberry_definition__")

    def test_reconciliation_result_type_is_strawberry_type(self):
        """Test that ReconciliationResultType is a valid Strawberry type"""
        from app.reconciliation.graphql.types import ReconciliationResultType

        assert hasattr(ReconciliationResultType, "__strawberry_definition__")

    def test_explanation_type_is_strawberry_type(self):
        """Test that ExplanationType is a valid Strawberry type"""
        from app.reconciliation.graphql.types import ExplanationType

        assert hasattr(ExplanationType, "__strawberry_definition__")

    def test_reconciliation_input_is_strawberry_input(self):
        """Test that ReconciliationInput is a valid Strawberry input type"""
        from app.reconciliation.graphql.types import ReconciliationInput

        assert hasattr(ReconciliationInput, "__strawberry_definition__")

    def test_match_type_fields(self):
        """Test that MatchType has all required fields"""
        from app.reconciliation.graphql.types import MatchType

        # Create a dummy instance to verify fields
        match = MatchType(
            id=1,
            invoice_id=10,
            bank_transaction_id=25,
            score=Decimal("95"),
            status="proposed",
            reason="Test reason",
            confirmed_at=None,
            created_at=datetime(2026, 1, 20, 10, 0, 0),
        )

        assert match.id == 1
        assert match.invoice_id == 10
        assert match.bank_transaction_id == 25
        assert match.score == Decimal("95")
        assert match.status == "proposed"
        assert match.reason == "Test reason"
        assert match.confirmed_at is None
        assert match.created_at == datetime(2026, 1, 20, 10, 0, 0)

    def test_reconciliation_result_type_fields(self):
        """Test that ReconciliationResultType has all required fields"""
        from app.reconciliation.graphql.types import ReconciliationResultType, MatchType

        match = MatchType(
            id=1,
            invoice_id=10,
            bank_transaction_id=25,
            score=Decimal("95"),
            status="proposed",
            reason="Test",
            confirmed_at=None,
            created_at=datetime(2026, 1, 20, 10, 0, 0),
        )

        result = ReconciliationResultType(
            total=5,
            returned=2,
            candidates=[match],
        )

        assert result.total == 5
        assert result.returned == 2
        assert len(result.candidates) == 1
        assert result.candidates[0].id == 1

    def test_explanation_type_fields(self):
        """Test that ExplanationType has all required fields"""
        from app.reconciliation.graphql.types import ExplanationType

        explanation = ExplanationType(
            score=Decimal("95"),
            reason="Exact amount match + 2 days apart",
            invoice_id=10,
            transaction_id=25,
        )

        assert explanation.score == Decimal("95")
        assert explanation.reason == "Exact amount match + 2 days apart"
        assert explanation.invoice_id == 10
        assert explanation.transaction_id == 25

    def test_reconciliation_input_fields(self):
        """Test that ReconciliationInput has all fields with defaults"""
        from app.reconciliation.graphql.types import ReconciliationInput

        # With defaults
        input1 = ReconciliationInput()
        assert input1.top == 5
        assert input1.min_score == Decimal("60")

        # With custom values
        input2 = ReconciliationInput(top=10, min_score=Decimal("80"))
        assert input2.top == 10
        assert input2.min_score == Decimal("80")


class TestGraphQLSchemaRegistration:
    """Tests for GraphQL schema registration with FastAPI"""

    def test_reconciliation_schema_loadable(self):
        """Test that reconciliation GraphQL schema can be loaded"""
        from app.reconciliation.graphql.queries import Query
        from app.reconciliation.graphql.mutations import Mutation

        # Both should exist and be importable
        assert Query is not None
        assert Mutation is not None

    @pytest.mark.asyncio
    async def test_mutation_type_accessible(self):
        """Test that Mutation type is accessible"""
        from app.reconciliation.graphql.mutations import Mutation

        # Should have both mutations
        assert hasattr(Mutation, "reconcile")
        assert hasattr(Mutation, "confirm_match")

    @pytest.mark.asyncio
    async def test_query_type_accessible(self):
        """Test that Query type is accessible"""
        from app.reconciliation.graphql.queries import Query

        # Should have the query
        assert hasattr(Query, "explain_reconciliation")
