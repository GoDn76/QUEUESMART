from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_redis_repo, get_current_organization
from app.models.models import Organization
from app.schemas.schemas import AnalyticsSummaryOut
from app.services.analytics import AnalyticsService
from app.repositories.redis_repo import RedisRepository

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryOut)
async def get_analytics_summary(
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Retrieve administrative metrics, wait times, service durations, and drop-off rate summaries."""
    analytics_service = AnalyticsService(db=db, redis_repo=redis_repo)
    return await analytics_service.get_summary(organization_id=org.id)

@router.get("/forecast/rush-hours")
async def get_rush_hours(
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    from app.services.forecast_service import ForecastService
    service = ForecastService(db)
    return await service.forecast_peak_hours(organization_id=org.id)
