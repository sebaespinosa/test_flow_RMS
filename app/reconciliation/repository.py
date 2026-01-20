"""
Repository implementation for match data access.
Handles all database operations for matches with tenant isolation.
"""

from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.reconciliation.models import MatchEntity
from app.reconciliation.interfaces import IMatchRepository


class MatchRepository(IMatchRepository):
    """Concrete repository for match operations"""

    def __init__(self, session: AsyncSession):
        """Initialize with database session"""
        self.session = session

    async def create(self, match: MatchEntity) -> MatchEntity:
        """Create a new match record"""
        self.session.add(match)
        await self.session.flush()
        return match

    async def get_by_id(self, match_id: int, tenant_id: int) -> Optional[MatchEntity]:
        """Get match by ID with tenant isolation"""
        stmt = select(MatchEntity).where(
            and_(
                MatchEntity.id == match_id,
                MatchEntity.tenant_id == tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_invoice(
        self,
        invoice_id: int,
        tenant_id: int,
        status: Optional[str] = None,
    ) -> List[MatchEntity]:
        """Get all matches for an invoice, optionally filtered by status"""
        filters = [
            MatchEntity.tenant_id == tenant_id,
            MatchEntity.invoice_id == invoice_id,
        ]
        if status:
            filters.append(MatchEntity.status == status)

        stmt = select(MatchEntity).where(and_(*filters))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_proposed_candidates(
        self,
        tenant_id: int,
        top: int = 5,
        min_score: Decimal = Decimal("60"),
    ) -> tuple[List[MatchEntity], int]:
        """
        Get proposed match candidates sorted by score descending.
        
        Returns:
            Tuple of (candidates list, total count of all proposed matches for tenant)
        """
        # Get total count of proposed matches
        count_stmt = select(MatchEntity).where(
            and_(
                MatchEntity.tenant_id == tenant_id,
                MatchEntity.status == "proposed",
            )
        )
        count_result = await self.session.execute(count_stmt)
        total_count = len(count_result.scalars().all())

        # Get top candidates with filters
        stmt = (
            select(MatchEntity)
            .where(
                and_(
                    MatchEntity.tenant_id == tenant_id,
                    MatchEntity.status == "proposed",
                    MatchEntity.score >= min_score,
                )
            )
            .order_by(MatchEntity.score.desc())
            .limit(top)
        )
        result = await self.session.execute(stmt)
        candidates = result.scalars().all()

        return candidates, total_count

    async def update_status(
        self,
        match_id: int,
        tenant_id: int,
        status: str,
        confirmed_at: Optional[object] = None,
    ) -> MatchEntity:
        """Update match status (proposed, confirmed, rejected)"""
        match = await self.get_by_id(match_id, tenant_id)
        if not match:
            raise ValueError(f"Match {match_id} not found for tenant {tenant_id}")

        match.status = status
        if confirmed_at:
            match.confirmed_at = confirmed_at

        await self.session.flush()
        return match

    async def get_confirmed_for_invoice(
        self,
        invoice_id: int,
        tenant_id: int,
    ) -> Optional[MatchEntity]:
        """Get confirmed match for an invoice (if exists)"""
        stmt = select(MatchEntity).where(
            and_(
                MatchEntity.tenant_id == tenant_id,
                MatchEntity.invoice_id == invoice_id,
                MatchEntity.status == "confirmed",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
