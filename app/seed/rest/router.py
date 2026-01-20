"""
FastAPI endpoints for destructive seeding utilities.
Protected by ENABLE_SEED_ENDPOINTS feature flag to avoid accidental use.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.config.exceptions import ForbiddenError
from app.database.session import get_db
from app.seed.repository import SeedRepository
from app.seed.service import SeedService
from app.seed.rest.schemas import SeedResponse, CleanupResponse, SeedStatusResponse

router = APIRouter(prefix="/api/v1/seed", tags=["seed"])


def require_seed_enabled(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.enable_seed_endpoints:
        raise ForbiddenError(
            detail="Seed endpoints are disabled. Set ENABLE_SEED_ENDPOINTS=true to enable."
        )
    return settings


def get_seed_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(require_seed_enabled),
) -> SeedService:
    repository = SeedRepository(db)
    return SeedService(session=db, repository=repository)


@router.post(
    "",
    response_model=SeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Run destructive seed",
    description="Deletes all tenant-scoped data, reseeds curated fixtures, and returns a summary.",
)
async def run_seed(service: SeedService = Depends(get_seed_service)) -> SeedResponse:
    return await service.seed()


@router.post(
    "/cleanup",
    response_model=CleanupResponse,
    status_code=status.HTTP_200_OK,
    summary="Cleanup seeded data",
    description="Deletes all tenant-scoped data without inserting replacements.",
)
async def cleanup_seed(service: SeedService = Depends(get_seed_service)) -> CleanupResponse:
    return await service.cleanup()


@router.get(
    "/status",
    response_model=SeedStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect current dataset",
    description="Returns counts and date ranges without mutating data.",
)
async def seed_status(service: SeedService = Depends(get_seed_service)) -> SeedStatusResponse:
    return await service.status()
