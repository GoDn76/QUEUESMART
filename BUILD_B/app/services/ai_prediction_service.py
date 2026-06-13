import logging
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.models import Token, ServiceType
from app.repositories.redis_repo import RedisRepository

logger = logging.getLogger(__name__)

class AIPredictionService:
    def __init__(self, db: AsyncSession, redis_repo: RedisRepository) -> None:
        self.db = db
        self.redis_repo = redis_repo

    async def estimate_wait_time(self, counter_id: int, service_type_id: int, active_counter_count: int = 1) -> int:
        """
        Estimate wait time in minutes using formula:
        (avg_service_duration * people_ahead) / active_counter_count
        """
        # 1. Check Redis wait-time cache
        if self.redis_repo.is_available:
            cached_wait = await self.redis_repo.get_cached_wait_time(counter_id)
            if cached_wait is not None:
                return cached_wait

        # 2. Get queue length
        waiting_count = 0
        if self.redis_repo.is_available:
            try:
                active_tokens = await self.redis_repo.get_queue_tokens(counter_id)
                waiting_count = len(active_tokens)
            except Exception as e:
                logger.warning(f"Failed to fetch queue list from Redis: {e}")

        if waiting_count == 0:
            count_stmt = select(func.count(Token.id)).where(
                Token.counter_id == counter_id,
                Token.status == "WAITING"
            )
            waiting_count = (await self.db.execute(count_stmt)).scalar() or 0

        if waiting_count == 0:
            return 0

        # 3. Calculate avg duration
        duration_stmt = select(Token.called_at, Token.created_at).where(
            Token.counter_id == counter_id,
            Token.called_at.is_not(None),
            Token.created_at >= (datetime.now(timezone.utc) - timedelta(days=1)).replace(tzinfo=None)
        )
        durations = (await self.db.execute(duration_stmt)).all()

        avg_duration_minutes = 0.0
        if durations:
            total_seconds = sum((called_at - created_at).total_seconds() for called_at, created_at in durations)
            avg_duration_minutes = (total_seconds / len(durations)) / 60.0

        if avg_duration_minutes <= 0.1:
            service_stmt = select(ServiceType).where(ServiceType.id == service_type_id)
            service = (await self.db.execute(service_stmt)).scalars().first()
            avg_duration_minutes = float(service.estimated_duration_minutes) if service else 15.0

        # Formula: (avg_duration * people_ahead) / active_counter_count
        estimated_wait = int((avg_duration_minutes * waiting_count) / max(1, active_counter_count))
        if estimated_wait < 1:
            estimated_wait = 1

        if self.redis_repo.is_available:
            await self.redis_repo.cache_wait_time(counter_id, estimated_wait)

        return estimated_wait

    async def get_gemini_migration_suggestion(self, from_counter_data: dict, to_counter_data: dict) -> Optional[dict]:
        """
        Uses Google GenAI (Gemini) to suggest if a migration makes sense.
        Optional integration; falls back gracefully.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return self._heuristic_migration_suggestion(from_counter_data, to_counter_data)

        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Analyze these two queues and suggest if moving 1 token from Counter A to Counter B is optimal.
            Counter A: {from_counter_data['waiting']} waiting, avg wait: {from_counter_data['avg_wait']} mins.
            Counter B: {to_counter_data['waiting']} waiting, avg wait: {to_counter_data['avg_wait']} mins.
            Return ONLY a valid JSON object with:
            {{"recommend_migration": boolean, "predicted_time_saved_minutes": int, "reason": "short text"}}
            """
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini API error during migration suggestion: {e}")
            return self._heuristic_migration_suggestion(from_counter_data, to_counter_data)

    def _heuristic_migration_suggestion(self, from_data: dict, to_data: dict) -> dict:
        wait_a = from_data.get('avg_wait', 15) * from_data.get('waiting', 0)
        wait_b = to_data.get('avg_wait', 15) * to_data.get('waiting', 0)
        
        if wait_a > (wait_b + 15):
            return {
                "recommend_migration": True,
                "predicted_time_saved_minutes": int(wait_a - wait_b - 15),
                "reason": "Counter B has significantly less traffic, offering a faster wait time."
            }
        return {
            "recommend_migration": False,
            "predicted_time_saved_minutes": 0,
            "reason": "Traffic is balanced or Counter A is faster."
        }
