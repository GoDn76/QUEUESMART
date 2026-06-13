import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case

from app.models.models import Token, Counter, ServiceType
from app.repositories.redis_repo import RedisRepository
from app.schemas.schemas import AnalyticsSummaryOut, MetricBreakdown

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Computes operations metrics, wait times, service speeds and drop-off rates."""

    def __init__(self, db: AsyncSession, redis_repo: RedisRepository) -> None:
        self.db = db
        self.redis_repo = redis_repo

    async def get_summary(self, organization_id: int) -> AnalyticsSummaryOut:
        """Retrieve real-time metrics and historical analytical breakdowns for an organization."""
        # 1. Fetch real-time operational counters
        active_tokens = 0
        completed_today = 0
        waiting_count = 0

        if self.redis_repo.is_available:
            try:
                active_tokens = await self.redis_repo.get_metric(organization_id, "active_tokens")
                completed_today = await self.redis_repo.get_metric(organization_id, "completed_today")
                waiting_count = await self.redis_repo.get_metric(organization_id, "waiting_count")
            except Exception as e:
                logger.warning(f"Failed to fetch metrics from Redis: {e}")

        # Fallback to PostgreSQL if Redis is offline or counters are empty
        if active_tokens == 0 and completed_today == 0 and waiting_count == 0:
            logger.info("Operational metrics missing in Redis; querying PostgreSQL database.")
            active_tokens = await self._get_db_token_count(organization_id, ["WAITING", "IN_PROGRESS"])
            waiting_count = await self._get_db_token_count(organization_id, ["WAITING"])
            completed_today = await self._get_db_token_count(
                organization_id, ["COMPLETED"], today_only=True
            )

        # 2. Compute historical aggregates
        overall_breakdown = await self._compute_metrics(organization_id)
        
        # 3. Compute breakdowns grouped by counter
        by_counter = await self._compute_breakdown_by_counter(organization_id)

        # 4. Compute breakdowns grouped by service type
        by_service_type = await self._compute_breakdown_by_service_type(organization_id)

        # 5. Compute drop-off rate
        total = overall_breakdown.total_tokens
        dropped = overall_breakdown.dropped_tokens
        drop_off_rate = (dropped / total) if total > 0 else 0.0

        return AnalyticsSummaryOut(
            active_tokens=active_tokens,
            completed_today=completed_today,
            waiting_count=waiting_count,
            drop_off_rate=drop_off_rate,
            overall=overall_breakdown,
            by_counter=by_counter,
            by_service_type=by_service_type
        )

    # --- Private Database Fetch Helpers ---

    async def _get_db_token_count(
        self, organization_id: int, statuses: List[str], today_only: bool = False
    ) -> int:
        """Count tokens matching given criteria in PostgreSQL."""
        stmt = select(func.count(Token.id)).join(Counter).where(
            Counter.organization_id == organization_id,
            Token.status.in_(statuses)
        )
        if today_only:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            stmt = stmt.where(Token.created_at >= today_start)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_wait_time_metrics(self, tokens: List[Token]) -> Dict[str, float]:
        """Compute average wait time from token history."""
        wait_times_sec = []
        for t in tokens:
            if t.called_at and t.created_at:
                wait_times_sec.append((t.called_at - t.created_at).total_seconds())
        avg_wait = (sum(wait_times_sec) / len(wait_times_sec) / 60.0) if wait_times_sec else 0.0
        return {"average_wait_minutes": round(avg_wait, 2)}

    async def get_utilization_metrics(self, tokens: List[Token]) -> Dict[str, float]:
        """Compute average serving time from token history."""
        service_durations_sec = []
        for t in tokens:
            if t.completed_at and t.called_at and t.status == "COMPLETED":
                service_durations_sec.append((t.completed_at - t.called_at).total_seconds())
        avg_service = (sum(service_durations_sec) / len(service_durations_sec) / 60.0) if service_durations_sec else 0.0
        return {"average_service_minutes": round(avg_service, 2)}

    async def get_dropoff_metrics(self, tokens: List[Token]) -> Dict[str, Any]:
        """Compute drop-off volume and rates."""
        total = len(tokens)
        dropped = sum(1 for t in tokens if t.status in ["SKIPPED", "ABANDONED"])
        drop_rate = (dropped / total) if total > 0 else 0.0
        return {
            "total_tokens": total,
            "dropped_tokens": dropped,
            "drop_off_rate": round(drop_rate, 4)
        }

    async def _compute_metrics(
        self, organization_id: int, counter_id: Optional[int] = None, service_type_id: Optional[int] = None
    ) -> MetricBreakdown:
        """Calculate combined metrics breakdown for a set of filters."""
        stmt = select(Token).join(Counter).where(Counter.organization_id == organization_id)
        if counter_id is not None:
            stmt = stmt.where(Token.counter_id == counter_id)
        if service_type_id is not None:
            stmt = stmt.where(Token.service_type_id == service_type_id)

        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        wait_metrics = await self.get_wait_time_metrics(tokens)
        utilization_metrics = await self.get_utilization_metrics(tokens)
        dropoff_metrics = await self.get_dropoff_metrics(tokens)

        return MetricBreakdown(
            average_wait_minutes=wait_metrics["average_wait_minutes"],
            average_service_minutes=utilization_metrics["average_service_minutes"],
            total_tokens=dropoff_metrics["total_tokens"],
            dropped_tokens=dropoff_metrics["dropped_tokens"],
            drop_off_rate=dropoff_metrics["drop_off_rate"]
        )

    async def _compute_breakdown_by_counter(self, organization_id: int) -> Dict[str, MetricBreakdown]:
        """Generate metric summaries for all counters owned by the organization."""
        stmt = select(Counter).where(Counter.organization_id == organization_id)
        counters = (await self.db.execute(stmt)).scalars().all()
        
        breakdown = {}
        for c in counters:
            breakdown[c.name] = await self._compute_metrics(organization_id, counter_id=c.id)
        return breakdown

    async def _compute_breakdown_by_service_type(self, organization_id: int) -> Dict[str, MetricBreakdown]:
        """Generate metric summaries for all service types offered by the organization."""
        stmt = select(ServiceType).where(ServiceType.organization_id == organization_id)
        services = (await self.db.execute(stmt)).scalars().all()
        
        breakdown = {}
        for s in services:
            breakdown[s.name] = await self._compute_metrics(organization_id, service_type_id=s.id)
        return breakdown
