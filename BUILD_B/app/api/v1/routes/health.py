import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.v1.deps import get_db, get_redis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Verify PostgreSQL and Redis connection integrity."""
    postgres_status = "DOWN"
    redis_status = "DOWN"
    overall_status = "healthy"

    # 1. Test PostgreSQL connection
    try:
        await db.execute(text("SELECT 1"))
        postgres_status = "UP"
    except Exception as e:
        logger.error(f"Health check PostgreSQL connection failed: {e}")
        overall_status = "unhealthy"

    # 2. Test Redis connection
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = "UP"
        except Exception as e:
            logger.error(f"Health check Redis connection failed: {e}")
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        # Redis client unavailable (degraded mode)
        if overall_status == "healthy":
            overall_status = "degraded"

    # 3. Check Twilio configuration (no network request, just config check)
    from app.core.config import settings
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER:
        twilio_status = "CONFIGURED"
    else:
        twilio_status = "NOT_CONFIGURED"

    response_payload = {
        "status": overall_status,
        "postgres": postgres_status,
        "redis": redis_status,
        "twilio": twilio_status,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if overall_status in ["healthy", "degraded"]:
        return response_payload
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_payload
        )
