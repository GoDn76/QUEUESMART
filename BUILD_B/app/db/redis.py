import logging
from typing import Optional
from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self) -> None:
        self.client: Optional[Redis] = None

    async def connect(self) -> None:
        """Establish Redis connection pool."""
        if not self.client:
            logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
            try:
                self.client = from_url(settings.REDIS_URL, decode_responses=True)
                await self.client.ping()
                logger.info("Connected to Redis successfully.")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Redis operations will run in degraded PostgreSQL fallback mode.")
                self.client = None

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.error(f"Error during Redis disconnect: {e}")
            finally:
                self.client = None
                logger.info("Disconnected from Redis.")


redis_manager = RedisManager()


async def get_redis() -> Optional[Redis]:
    """Dependency generator to retrieve the active Redis client."""
    return redis_manager.client
