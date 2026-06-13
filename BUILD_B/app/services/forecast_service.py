import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, extract

from app.models.models import Token, Counter

logger = logging.getLogger(__name__)

class ForecastService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def forecast_peak_hours(self, organization_id: int) -> Dict[str, Any]:
        """
        Analyze last 30 days of ticket distribution by hour of day.
        Returns:
            peak_hours: list of string representations
            traffic_distribution: raw map
            quiet_hours: list of string representations
        """
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)
        
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

        forecast = {h: 0 for h in range(24)}
        for row in raw_forecast:
            forecast[int(row.hour)] = int(row.count)

        avg_traffic = sum(forecast.values()) / 24.0 if sum(forecast.values()) > 0 else 0
        peak_threshold = avg_traffic * 1.5 if avg_traffic > 0 else 0
        quiet_threshold = avg_traffic * 0.5 if avg_traffic > 0 else float('inf')

        peak_hours = []
        quiet_hours = []

        for h, c in forecast.items():
            hour_str = f"{h%12 or 12}{'AM' if h < 12 else 'PM'}-{((h+1)%12) or 12}{'AM' if (h+1)%24 < 12 else 'PM'}"
            if c > peak_threshold and c > 0:
                peak_hours.append(hour_str)
            elif c <= quiet_threshold:
                quiet_hours.append(hour_str)

        return {
            "peak_hours": peak_hours,
            "quiet_hours": quiet_hours,
            "traffic_distribution": forecast
        }
