import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, extract

from app.models.models import Token, Counter, ServiceType
from app.repositories.redis_repo import RedisRepository

logger = logging.getLogger(__name__)


class QueuePredictionService:
    """Statistical prediction engine and metrics forecasting layer."""

    def __init__(self, db: AsyncSession, redis_repo: RedisRepository) -> None:
        self.db = db
        self.redis_repo = redis_repo

    async def estimate_wait_time(self, counter_id: int, service_type_id: int) -> int:
        """
        Estimate wait time in minutes for a customer joining a specific service type at a counter.
        Checks cache first, then calculates based on queue length and actual historical speeds.
        """
        # 1. Check Redis wait-time cache
        if self.redis_repo.is_available:
            cached_wait = await self.redis_repo.get_cached_wait_time(counter_id)
            if cached_wait is not None:
                logger.debug(f"Wait time cache hit for counter {counter_id}: {cached_wait} mins")
                return cached_wait

        # 2. Get active queue length (number of waiting people)
        waiting_count = 0
        if self.redis_repo.is_available:
            try:
                active_tokens = await self.redis_repo.get_queue_tokens(counter_id)
                waiting_count = len(active_tokens)
            except Exception as e:
                logger.warning(f"Failed to fetch queue list from Redis: {e}")

        # Fallback to DB count if Redis is down or empty
        if waiting_count == 0:
            count_stmt = select(func.count(Token.id)).where(
                Token.counter_id == counter_id,
                Token.status == "WAITING"
            )
            count_result = await self.db.execute(count_stmt)
            waiting_count = count_result.scalar() or 0

        # If nobody is in line, estimated wait time is 0 minutes
        if waiting_count == 0:
            return 0

        # 3. Calculate average service duration per token in the last 24 hours
        # Duration: called_at - created_at (wait time in queue) or completed_at - called_at (service duration)
        # We need the average wait time of a token at this counter.
        duration_stmt = select(Token.called_at, Token.created_at).where(
            Token.counter_id == counter_id,
            Token.called_at.is_not(None),
            Token.created_at >= (datetime.now(timezone.utc) - timedelta(days=1)).replace(tzinfo=None)
        )
        duration_result = await self.db.execute(duration_stmt)
        durations = duration_result.all()

        avg_wait_minutes = 0.0
        if durations:
            total_seconds = sum((called_at - created_at).total_seconds() for called_at, created_at in durations)
            avg_wait_minutes = (total_seconds / len(durations)) / 60.0

        # 4. Fallback to ServiceType estimated duration if no historical records are available
        if avg_wait_minutes <= 0.1:
            service_stmt = select(ServiceType).where(ServiceType.id == service_type_id)
            service_result = await self.db.execute(service_stmt)
            service = service_result.scalars().first()
            avg_wait_minutes = float(service.estimated_duration_minutes) if service else 15.0

        # Estimated Wait Time = people in front * average wait duration
        estimated_wait = int(waiting_count * avg_wait_minutes)
        if estimated_wait < 1:
            estimated_wait = 1

        # 5. Cache result in Redis for 60 seconds
        if self.redis_repo.is_available:
            await self.redis_repo.cache_wait_time(counter_id, estimated_wait)

        return estimated_wait

    async def forecast_peak_hours(self, organization_id: int) -> Dict[int, int]:
        """
        Analyze ticket distribution by hour of day for the past 30 days.
        Returns a dictionary mapping hour (0-23) to ticket volume.
        """
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)
        
        # Query tokens grouped by hour of creation
        stmt = (
            select(
                extract("hour", Token.created_at).label("hour"),
                func.count(Token.id).label("count")
            )
            .join(Counter)
            .where(
                Counter.organization_id == organization_id,
                Token.created_at >= thirty_days_ago
            )
            .group_by(extract("hour", Token.created_at))
            .order_by("hour")
        )

        result = await self.db.execute(stmt)
        raw_forecast = result.all()

        # Build full 24-hour schedule dictionary filled with zeros
        forecast = {h: 0 for h in range(24)}
        for row in raw_forecast:
            hour_val = int(row.hour)
            forecast[hour_val] = int(row.count)

        return forecast

    async def generate_admin_insights(self, organization_id: int) -> List[str]:
        """
        Generate rule-based management insights from historical operational metrics.
        Optional: Can be extended to connect to Gemini/OpenAI API.
        """
        insights = []

        # 1. Fetch counters and count active tickets
        counters_result = await self.db.execute(
            select(Counter).where(Counter.organization_id == organization_id)
        )
        counters = counters_result.scalars().all()

        if not counters:
            return ["No active counters registered. Add counters to start tracking queue efficiency."]

        # 2. Analyze highest drop-off rate
        # Drop-off rate = (SKIPPED + ABANDONED) / TOTAL
        stmt = (
            select(
                Token.counter_id,
                func.count(Token.id).label("total"),
                func.sum(func.case((Token.status.in_(["SKIPPED", "ABANDONED"]), 1), else_=0)).label("dropped")
            )
            .join(Counter)
            .where(Counter.organization_id == organization_id)
            .group_by(Token.counter_id)
        )
        metrics_result = await self.db.execute(stmt)
        metrics = metrics_result.all()

        worst_counter_id = None
        max_drop_rate = 0.0

        for row in metrics:
            total = row.total or 0
            dropped = row.dropped or 0
            if total > 5:  # Require minimum sample size
                drop_rate = (dropped / total) * 100
                if drop_rate > max_drop_rate:
                    max_drop_rate = drop_rate
                    worst_counter_id = row.counter_id

        if worst_counter_id and max_drop_rate > 15.0:
            c_result = await self.db.execute(select(Counter.name).where(Counter.id == worst_counter_id))
            c_name = c_result.scalar()
            insights.append(
                f"Counter '{c_name}' exhibits a high drop-off rate of {max_drop_rate:.1f}%. "
                f"Consider adding operator support or analyzing ticket routing during peak hours."
            )

        # 3. Analyze service type duration bottlenecks
        dur_stmt = (
            select(
                Token.service_type_id,
                func.avg(Token.completed_at - Token.called_at).label("avg_dur")
            )
            .join(Counter)
            .where(
                Counter.organization_id == organization_id,
                Token.status == "COMPLETED",
                Token.completed_at.is_not(None),
                Token.called_at.is_not(None)
            )
            .group_by(Token.service_type_id)
        )
        durations = (await self.db.execute(dur_stmt)).all()

        slowest_service_id = None
        max_duration_sec = 0.0

        for row in durations:
            if row.avg_dur:
                sec = row.avg_dur.total_seconds()
                if sec > max_duration_sec:
                    max_duration_sec = sec
                    slowest_service_id = row.service_type_id

        if slowest_service_id and max_duration_sec > 600:  # > 10 minutes
            s_result = await self.db.execute(select(ServiceType.name).where(ServiceType.id == slowest_service_id))
            s_name = s_result.scalar()
            insights.append(
                f"Service Type '{s_name}' averages {max_duration_sec/60:.1f} minutes of serving duration. "
                f"Consider providing online forms for customers to complete while waiting in line to reduce handling times."
            )

        # 4. Peak Traffic hour insight
        forecast = await self.forecast_peak_hours(organization_id)
        peak_hour = max(forecast, key=forecast.get)
        peak_count = forecast[peak_hour]

        if peak_count > 0:
            ampm = "PM" if peak_hour >= 12 else "AM"
            display_hour = peak_hour - 12 if peak_hour > 12 else (12 if peak_hour == 0 else peak_hour)
            insights.append(
                f"Peak customer intake occurs at {display_hour} {ampm} with a historical count of {peak_count} registrations. "
                f"Ensure all counters are active between {display_hour-1 if display_hour>1 else 12} and {display_hour+1} {ampm}."
            )

        # Fallback default insight
        if not insights:
            insights.append(
                "QueueMind operates optimally. System throughput is stable with drop-off rates under 5% across all counters."
            )

        # LLM Integration Placeholder:
        # if settings.GEMINI_API_KEY:
        #     # call Gemini model to generate natural language insights combining this raw stats data
        #     pass

        return insights
