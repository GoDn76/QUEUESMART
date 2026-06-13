from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_redis_repo
from app.services.ai_prediction_service import AIPredictionService
from app.repositories.redis_repo import RedisRepository

router = APIRouter()

def get_prediction_service(db=Depends(get_db), redis_repo=Depends(get_redis_repo)):
    return AIPredictionService(db, redis_repo)

@router.get("/wait-time/{counter_id}")
async def get_wait_time_prediction(
    counter_id: int,
    service_type_id: int = Query(..., description="The ID of the service type the customer wants"),
    service: AIPredictionService = Depends(get_prediction_service)
):
    estimated_wait = await service.estimate_wait_time(counter_id, service_type_id)
    return {
        "counter_id": counter_id,
        "estimated_wait": estimated_wait
    }
