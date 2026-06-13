import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

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

    # 3. Check Notification Provider
    from app.core.config import settings
    notification_provider = settings.NOTIFICATION_PROVIDER
    provider_status = "UP"

    if notification_provider == "whatsapp_web":
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{settings.WHATSAPP_WEB_URL}/health")
                if res.status_code == 200 and res.json().get("status") == "UP":
                    provider_status = "UP"
                else:
                    provider_status = "DOWN"
        except Exception:
            provider_status = "DOWN"
    elif notification_provider == "noop":
        provider_status = "UP"
    # For twilio/meta, you could do a basic config check or API ping, 
    # but for now we'll just check if it's set.
    elif notification_provider == "twilio":
        if settings.TWILIO_ACCOUNT_SID: provider_status = "UP"
        else: provider_status = "DOWN"

    response_payload = {
        "status": overall_status,
        "postgres": postgres_status,
        "redis": redis_status,
        "notification_provider": notification_provider,
        "provider_status": provider_status,
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
