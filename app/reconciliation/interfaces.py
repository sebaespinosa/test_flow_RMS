"""
Repository interfaces (ABCs) for match operations.
Defines contracts for data access layer.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from app.reconciliation.models import MatchEntity


class IMatchRepository(ABC):
    """Abstract repository for match operations"""

    @abstractmethod
    async def create(self, match: MatchEntity) -> MatchEntity:
        """Create a new match record"""
        pass

    @abstractmethod
    async def get_by_id(self, match_id: int, tenant_id: int) -> Optional[MatchEntity]:
        """Get match by ID with tenant isolation"""
        pass

    @abstractmethod
    async def get_by_invoice(
        self,
        invoice_id: int,
        tenant_id: int,
        status: Optional[str] = None,
    ) -> List[MatchEntity]:
        """Get all matches for an invoice, optionally filtered by status"""
        pass

    @abstractmethod
    async def get_proposed_candidates(
        self,
        tenant_id: int,
        top: int = 5,
        min_score: Decimal = Decimal("60"),
    ) -> tuple[List[MatchEntity], int]:
        """
        Get proposed match candidates sorted by score descending.
        
        Returns:
            Tuple of (candidates list, total count of all proposed matches)
        """
        pass

    @abstractmethod
    async def update_status(
        self,
        match_id: int,
        tenant_id: int,
        status: str,
        confirmed_at: Optional[object] = None,
    ) -> MatchEntity:
        """Update match status (proposed, confirmed, rejected)"""
        pass

    @abstractmethod
    async def get_confirmed_for_invoice(
        self,
        invoice_id: int,
        tenant_id: int,
    ) -> Optional[MatchEntity]:
        """Get confirmed match for an invoice (if exists)"""
        pass
