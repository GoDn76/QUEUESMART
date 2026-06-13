import abc
import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional, Any
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class EventBus(abc.ABC):
    """Abstract EventBus interface for decoupled messaging."""

    @abc.abstractmethod
    async def publish(self, channel: str, message: dict) -> None:
        """Publish a message to a channel."""
        pass

    @abc.abstractmethod
    async def subscribe(self, channel_pattern: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        """Subscribe to a channel pattern and handle incoming events."""
        pass


class RedisEventBus(EventBus):
    """EventBus implementation backed by Redis Pub/Sub."""

    def __init__(self, redis_client: Optional[Redis]) -> None:
        self.redis = redis_client

    async def publish(self, channel: str, message: dict) -> None:
        if not self.redis:
            logger.warning(f"Redis is unavailable; event '{message.get('event')}' not published to channel '{channel}'")
            return
        try:
            await self.redis.publish(channel, json.dumps(message))
            logger.debug(f"Event published to Redis channel '{channel}': {message}")
        except Exception as e:
            logger.error(f"Error publishing event to Redis channel '{channel}': {e}")

    async def subscribe(self, channel_pattern: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        if not self.redis:
            logger.warning(f"Redis is unavailable; cannot subscribe to pattern '{channel_pattern}'")
            return

        async def _listener() -> None:
            logger.info(f"Starting Redis Pub/Sub listener for pattern: {channel_pattern}")
            import redis.exceptions
            
            while True:
                pubsub = self.redis.pubsub()
                try:
                    # Use psubscribe to support patterns (e.g. 'counter:*' or 'organization:*')
                    await pubsub.psubscribe(channel_pattern)
                    while True:
                        try:
                            async for message in pubsub.listen():
                                if message and message["type"] == "pmessage":
                                    try:
                                        data = json.loads(message["data"])
                                        await handler(data)
                                    except json.JSONDecodeError:
                                        logger.error(f"Failed to decode message data: {message['data']}")
                                    except Exception as e:
                                        logger.error(f"Error inside event handler for '{channel_pattern}': {e}")
                        except redis.exceptions.TimeoutError:
                            # Socket timeout, just ignore and resume listening
                            continue
                        except redis.exceptions.ConnectionError as e:
                            logger.error(f"ConnectionError in Redis Pub/Sub listener for '{channel_pattern}': {e}. Reconnecting...")
                            break  # Break inner loop to recreate pubsub and resubscribe
                except asyncio.CancelledError:
                    logger.info(f"Listener for pattern '{channel_pattern}' was cancelled.")
                    break
                except Exception as e:
                    logger.error(f"Exception in Redis Pub/Sub listener loop: {e}")
                    await asyncio.sleep(5)  # Back off before reconnecting
                finally:
                    try:
                        await pubsub.punsubscribe(channel_pattern)
                        await pubsub.close()
                    except Exception:
                        pass

        # Run listener loop in background task
        asyncio.create_task(_listener())
