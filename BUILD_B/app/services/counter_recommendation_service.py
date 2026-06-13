import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.models import Counter, Operator, Token
from app.repositories.redis_repo import RedisRepository
from app.services.ai_prediction_service import AIPredictionService

logger = logging.getLogger(__name__)

class CounterRecommendationService:
    def __init__(self, db: AsyncSession, redis_repo: RedisRepository) -> None:
        self.db = db
        self.redis_repo = redis_repo
        self.prediction_service = AIPredictionService(db, redis_repo)

    async def get_counter_recommendation(self, service_type_id: int, organization_id: int) -> Optional[Dict[str, Any]]:
        """
        Recommends the best counter based on queue length, active operators, avg duration, predicted wait.
        """
        # 1. Fetch all active counters for the organization that have operators assigned
        # (Assuming operators map 1:1 or N:1 to counters)
        counters_stmt = select(Counter).where(
            Counter.organization_id == organization_id,
            Counter.active == True
        )
        counters_result = await self.db.execute(counters_stmt)
        counters = counters_result.scalars().all()

        if not counters:
            return None

        counter_stats = []

        for counter in counters:
            # Active operators count
            op_stmt = select(func.count(Operator.id)).where(
                Operator.counter_id == counter.id,
                Operator.active == True
            )
            active_operators = (await self.db.execute(op_stmt)).scalar() or 0

            # Estimate wait time
            estimated_wait = await self.prediction_service.estimate_wait_time(
                counter_id=counter.id, 
                service_type_id=service_type_id,
                active_counter_count=active_operators
            )

            # Get waiting count
            waiting_count = 0
            if self.redis_repo.is_available:
                try:
                    active_tokens = await self.redis_repo.get_queue_tokens(counter.id)
                    waiting_count = len(active_tokens)
                except Exception as e:
                    logger.warning(f"Failed to fetch queue list from Redis: {e}")

            if waiting_count == 0:
                count_stmt = select(func.count(Token.id)).where(
                    Token.counter_id == counter.id,
                    Token.status == "WAITING"
                )
                waiting_count = (await self.db.execute(count_stmt)).scalar() or 0

            counter_stats.append({
                "counter_id": counter.id,
                "counter_name": counter.name,
                "active_operators": active_operators,
                "waiting_count": waiting_count,
                "estimated_wait": estimated_wait
            })

        # Rank counters: Primarily by lowest estimated_wait, then by active_operators (more is better), then waiting count
        counter_stats.sort(key=lambda x: (
            x["estimated_wait"], 
            -x["active_operators"], 
            x["waiting_count"]
        ))

        best_counter = counter_stats[0]
        
        # Build reason string
        if len(counter_stats) > 1:
            second_best = counter_stats[1]
            if best_counter["estimated_wait"] < second_best["estimated_wait"]:
                saving = second_best["estimated_wait"] - best_counter["estimated_wait"]
                reason = f"Counter {best_counter['counter_id']} offers a {saving} minute faster wait time."
            elif best_counter["active_operators"] > second_best["active_operators"]:
                reason = f"Counter {best_counter['counter_id']} has more active operators handling the load."
            else:
                reason = f"Counter {best_counter['counter_id']} has the optimal balance of wait time and capacity."
        else:
            reason = "This is the only active counter."

        return {
            "recommended_counter": best_counter["counter_id"],
            "counter_name": best_counter["counter_name"],
            "estimated_wait": best_counter["estimated_wait"],
            "reason": reason,
            "stats": counter_stats
        }
