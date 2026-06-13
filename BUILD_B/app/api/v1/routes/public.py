import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.v1.deps import get_db, get_redis_repo, get_queue_engine
from app.models.models import Counter, Token, ServiceType
from app.schemas.schemas import PublicQueueStatusOut, TokenCreate, TokenOut
from app.services.queue_engine import QueueEngine
from app.repositories.redis_repo import RedisRepository
from app.services.prediction import QueuePredictionService

logger = logging.getLogger(__name__)
router = APIRouter()


def _format_hour(h: int) -> str:
    """Format hour (0-23) to AM/PM string representation."""
    if h == 0 or h == 24:
        return "12 AM"
    elif h == 12:
        return "12 PM"
    elif h > 12:
        return f"{h - 12} PM"
    else:
        return f"{h} AM"


async def _get_suggested_window(organization_id: int, prediction_service: QueuePredictionService) -> str:
    """Determine a low-traffic 2-hour window based on peak hours forecast."""
    try:
        forecast = await prediction_service.forecast_peak_hours(organization_id)
        # Target standard operational hours (9 AM to 5 PM)
        working_hours = {h: count for h, count in forecast.items() if 9 <= h <= 17}
        if working_hours:
            best_hour = min(working_hours, key=working_hours.get)
            end_hour = best_hour + 2 if best_hour + 2 <= 18 else 18
            return f"{_format_hour(best_hour)} - {_format_hour(end_hour)}"
    except Exception as e:
        logger.error(f"Error forecasting peak hours for suggested window: {e}")
    return "2 PM - 4 PM"  # Default fallback


@router.get("/{qr_slug}", response_model=PublicQueueStatusOut)
async def get_public_queue_status(
    qr_slug: str,
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Fetch the general status of a queue page for end-users scanning a QR code."""
    # 1. Fetch counter
    counter_result = await db.execute(select(Counter).where(Counter.qr_slug == qr_slug, Counter.active == True))
    counter = counter_result.scalars().first()
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue not found or inactive")

    # 2. Get currently serving token
    current_token_data = None
    if redis_repo.is_available:
        try:
            current_token_data = await redis_repo.get_current_token(counter.id)
        except Exception:
            current_token_data = None

    current_token = None
    if current_token_data:
        token_id = current_token_data.get("token_id")
        token_result = await db.execute(select(Token).where(Token.id == token_id))
        current_token = token_result.scalars().first()
    
    if not current_token:
        # Fallback to query database for the active IN_PROGRESS token
        stmt = (
            select(Token)
            .where(Token.counter_id == counter.id, Token.status == "IN_PROGRESS")
            .order_by(Token.called_at.desc())
            .limit(1)
        )
        current_token = (await db.execute(stmt)).scalars().first()

    # 3. Retrieve active queue length
    waiting_count = 0
    token_ids = []
    if redis_repo.is_available:
        try:
            token_ids = await redis_repo.get_queue_tokens(counter.id)
            waiting_count = len(token_ids)
        except Exception:
            waiting_count = 0

    if waiting_count == 0 and not token_ids:
        # DB fallback count
        count_stmt = select(func.count(Token.id)).where(
            Token.counter_id == counter.id,
            Token.status == "WAITING"
        )
        count_result = await db.execute(count_stmt)
        waiting_count = count_result.scalar() or 0

    # 4. Fetch available service types
    services_result = await db.execute(
        select(ServiceType).where(ServiceType.organization_id == counter.organization_id)
    )
    service_types = list(services_result.scalars().all())

    # 5. Calculate wait-time estimation & low traffic hours
    prediction_service = QueuePredictionService(db, redis_repo)
    service_type_id = service_types[0].id if service_types else 1
    
    estimated_wait = 0
    if waiting_count > 0:
        estimated_wait = await prediction_service.estimate_wait_time(counter.id, service_type_id)
        
    suggested_window = await _get_suggested_window(counter.organization_id, prediction_service)

    return PublicQueueStatusOut(
        counter_id=counter.id,
        counter_name=counter.name,
        queue_type=counter.queue_type,
        current_token=current_token,
        people_ahead=waiting_count,
        estimated_wait_minutes=estimated_wait,
        suggested_low_traffic_window=suggested_window,
        service_types=service_types
    )


@router.post("/{qr_slug}/join", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def join_queue(
    qr_slug: str,
    token_in: TokenCreate,
    queue_engine: QueueEngine = Depends(get_queue_engine)
):
    """Enables a customer to join a queue instantly with minimal details."""
    try:
        return await queue_engine.join_queue(
            qr_slug=qr_slug,
            customer_name=token_in.customer_name,
            customer_phone=token_in.customer_phone,
            service_type_id=token_in.service_type_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{qr_slug}/status/{token_number}", response_model=TokenOut)
async def get_token_status(
    qr_slug: str,
    token_number: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve status, queue position, and estimated wait for a specific ticket number."""
    # Find counter first
    counter_result = await db.execute(select(Counter).where(Counter.qr_slug == qr_slug))
    counter = counter_result.scalars().first()
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue not found")

    # Find token
    token_result = await db.execute(
        select(Token).where(
            Token.counter_id == counter.id,
            Token.token_number == token_number
        )
    )
    token = token_result.scalars().first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Token '{token_number}' not found")

    return token
