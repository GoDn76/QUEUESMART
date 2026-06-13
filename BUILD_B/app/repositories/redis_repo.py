import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisRepository:
    """Repository handling all Redis operational read/write actions."""

    def __init__(self, redis_client: Optional[Redis]) -> None:
        self.redis = redis_client

    @property
    def is_available(self) -> bool:
        return self.redis is not None

    # --- Active Queue Management (Sorted Sets) ---

    async def push_to_queue(self, counter_id: int, token_id: int, score: float) -> None:
        """Add a token to the counter's active queue using Sorted Sets."""
        if not self.redis:
            return
        key = f"queue:{counter_id}"
        try:
            await self.redis.zadd(key, {str(token_id): score})
            logger.debug(f"Pushed token {token_id} to Redis queue {key} with score {score}")
        except Exception as e:
            logger.error(f"Redis error in push_to_queue for counter {counter_id}: {e}")
            raise

    async def pop_next_from_queue(self, counter_id: int) -> Optional[int]:
        """Retrieve and remove the token with the lowest score (highest priority / first arrival) from queue."""
        if not self.redis:
            return None
        key = f"queue:{counter_id}"
        try:
            # zpopmin pops elements with the lowest score first
            result = await self.redis.zpopmin(key, count=1)
            if result:
                token_id, score = result[0]
                logger.debug(f"Popped token {token_id} from Redis queue {key} (score: {score})")
                return int(token_id)
            return None
        except Exception as e:
            logger.error(f"Redis error in pop_next_from_queue for counter {counter_id}: {e}")
            raise

    async def remove_from_queue(self, counter_id: int, token_id: int) -> None:
        """Remove a specific token from the active queue."""
        if not self.redis:
            return
        key = f"queue:{counter_id}"
        try:
            await self.redis.zrem(key, str(token_id))
            logger.debug(f"Removed token {token_id} from Redis queue {key}")
        except Exception as e:
            logger.error(f"Redis error in remove_from_queue for counter {counter_id}: {e}")
            raise

    async def get_queue_tokens(self, counter_id: int) -> List[int]:
        """Get list of token IDs currently in the active queue, ordered by score."""
        if not self.redis:
            return []
        key = f"queue:{counter_id}"
        try:
            # zrange fetches ascending order by score
            token_ids = await self.redis.zrange(key, 0, -1)
            return [int(tid) for tid in token_ids]
        except Exception as e:
            logger.error(f"Redis error in get_queue_tokens for counter {counter_id}: {e}")
            return []

    # --- Current Serving Token ---

    async def set_current_token(self, counter_id: int, token_data: Dict[str, Any]) -> None:
        """Store the details of the token currently being served at the counter."""
        if not self.redis:
            return
        key = f"current_token:{counter_id}"
        try:
            await self.redis.set(key, json.dumps(token_data))
            logger.debug(f"Set current token for counter {counter_id}: {token_data}")
        except Exception as e:
            logger.error(f"Redis error in set_current_token for counter {counter_id}: {e}")
            raise

    async def get_current_token(self, counter_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve details of the token currently being served."""
        if not self.redis:
            return None
        key = f"current_token:{counter_id}"
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis error in get_current_token for counter {counter_id}: {e}")
            return None

    async def clear_current_token(self, counter_id: int) -> None:
        """Clear the current serving token for the counter."""
        if not self.redis:
            return
        key = f"current_token:{counter_id}"
        try:
            await self.redis.delete(key)
            logger.debug(f"Cleared current token for counter {counter_id}")
        except Exception as e:
            logger.error(f"Redis error in clear_current_token for counter {counter_id}: {e}")
            raise

    # --- Live Dashboard Metrics ---

    async def increment_metric(self, org_id: int, metric_name: str, amount: int = 1) -> None:
        """Increment live metrics counter for an organization."""
        if not self.redis:
            return
        key = f"metrics:org:{org_id}:{metric_name}"
        try:
            await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis error incrementing metric {metric_name} for org {org_id}: {e}")

    async def decrement_metric(self, org_id: int, metric_name: str, amount: int = 1) -> None:
        """Decrement live metrics counter for an organization."""
        if not self.redis:
            return
        key = f"metrics:org:{org_id}:{metric_name}"
        try:
            await self.redis.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis error decrementing metric {metric_name} for org {org_id}: {e}")

    async def get_metric(self, org_id: int, metric_name: str) -> int:
        """Get current value of a specific organization metric."""
        if not self.redis:
            return 0
        key = f"metrics:org:{org_id}:{metric_name}"
        try:
            val = await self.redis.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"Redis error getting metric {metric_name} for org {org_id}: {e}")
            return 0

    async def set_metric(self, org_id: int, metric_name: str, value: int) -> None:
        """Set a metric directly."""
        if not self.redis:
            return
        key = f"metrics:org:{org_id}:{metric_name}"
        try:
            await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis error setting metric {metric_name} for org {org_id}: {e}")

    # --- Wait Time Caching ---

    async def cache_wait_time(self, counter_id: int, wait_time: int) -> None:
        """Cache computed wait time for a counter with 60-second TTL."""
        if not self.redis:
            return
        key = f"prediction:counter:{counter_id}"
        try:
            payload = {
                "estimated_wait": wait_time,
                "updated_at": time.time()
            }
            await self.redis.setex(key, 60, json.dumps(payload))
        except Exception as e:
            logger.error(f"Redis error caching wait time for counter {counter_id}: {e}")

    async def get_cached_wait_time(self, counter_id: int) -> Optional[int]:
        """Fetch cached wait time for a counter if valid."""
        if not self.redis:
            return None
        key = f"prediction:counter:{counter_id}"
        try:
            data = await self.redis.get(key)
            if data:
                payload = json.loads(data)
                return payload.get("estimated_wait")
            return None
        except Exception as e:
            logger.error(f"Redis error reading wait time cache for counter {counter_id}: {e}")
            return None

    # --- Sliding Window Rate Limiting ---

    async def check_rate_limit(self, phone_number: str) -> bool:
        """
        Check rate limit: max 3 queue joins per 5 minutes per phone number.
        Returns True if rate limited, False if allowed.
        """
        if not self.redis:
            # Fail-open if Redis is down, to maintain operations
            return False
        key = f"rate_limit:{phone_number}"
        now = time.time()
        window = 300  # 5 minutes in seconds
        try:
            # Start Redis transaction via pipeline
            async with self.redis.pipeline(transaction=True) as pipe:
                # Remove timestamps older than the 5-minute sliding window
                pipe.zremrangebyscore(key, "-inf", str(now - window))
                # Count current elements in window
                pipe.zcard(key)
                # Execute transaction
                _, count = await pipe.execute()

                if count >= 3:
                    logger.warning(f"Rate limit hit for phone number: {phone_number}")
                    return True

                # If limit not hit, record this attempt
                async with self.redis.pipeline(transaction=True) as pipe2:
                    pipe2.zadd(key, {f"{now}-{count}": now})
                    pipe2.expire(key, window)
                    await pipe2.execute()
                
                return False
        except Exception as e:
            logger.error(f"Redis error during rate limit check for {phone_number}: {e}")
            return False

    # --- Operator Session Locks ---

    async def acquire_counter_lock(self, counter_id: int, operator_id: int, session_id: str, ttl: int = 90) -> bool:
        """Attempt to acquire session lock for a counter. Returns True if acquired, False otherwise."""
        if not self.redis:
            return False  # Fail-closed for locks if Redis is down
        key = f"counter_active:{counter_id}"
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps({
            "operator_id": operator_id,
            "session_id": session_id,
            "last_seen": now
        })
        try:
            # set nx=True means 'set if not exists'
            acquired = await self.redis.set(key, payload, ex=ttl, nx=True)
            if acquired:
                logger.info(f"Operator {operator_id} acquired lock on counter {counter_id} (session {session_id})")
                return True
            return False
        except Exception as e:
            logger.error(f"Redis error in acquire_counter_lock for counter {counter_id}: {e}")
            return False

    async def refresh_counter_lock(self, counter_id: int, session_id: str, ttl: int = 90) -> bool:
        """Refresh lock TTL if the session_id matches."""
        if not self.redis:
            return False
        key = f"counter_active:{counter_id}"
        try:
            data = await self.redis.get(key)
            if not data:
                return False
            payload = json.loads(data)
            if payload.get("session_id") != session_id:
                return False
            
            payload["last_seen"] = datetime.now(timezone.utc).isoformat()
            await self.redis.set(key, json.dumps(payload), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis error in refresh_counter_lock for counter {counter_id}: {e}")
            return False

    async def release_counter_lock(self, counter_id: int, session_id: str) -> None:
        """Release lock only if the session_id matches."""
        if not self.redis:
            return
        key = f"counter_active:{counter_id}"
        try:
            data = await self.redis.get(key)
            if not data:
                return
            payload = json.loads(data)
            if payload.get("session_id") == session_id:
                await self.redis.delete(key)
                logger.info(f"Released lock on counter {counter_id} (session {session_id})")
        except Exception as e:
            logger.error(f"Redis error in release_counter_lock for counter {counter_id}: {e}")

    async def force_release_counter_lock(self, counter_id: int) -> None:
        """Admin override to release counter lock immediately."""
        if not self.redis:
            return
        key = f"counter_active:{counter_id}"
        try:
            await self.redis.delete(key)
            logger.warning(f"Admin force-released lock on counter {counter_id}")
        except Exception as e:
            logger.error(f"Redis error in force_release_counter_lock for counter {counter_id}: {e}")

    async def get_counter_lock_status(self, counter_id: int) -> Optional[Dict[str, Any]]:
        """Fetch the current lock details for a counter."""
        if not self.redis:
            return None
        key = f"counter_active:{counter_id}"
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis error in get_counter_lock_status for counter {counter_id}: {e}")
            return None

    # --- Login Rate Limiting ---

    async def record_failed_login(self, operator_id: int) -> int:
        """Record a failed login attempt for an operator and return the count in the 15m window."""
        if not self.redis:
            return 0
        key = f"failed_logins:operator:{operator_id}"
        window = 900  # 15 minutes
        now = time.time()
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, "-inf", str(now - window))
                pipe.zadd(key, {f"{now}": now})
                pipe.zcard(key)
                pipe.expire(key, window)
                results = await pipe.execute()
                count = results[2]
                return count
        except Exception as e:
            logger.error(f"Redis error in record_failed_login for operator {operator_id}: {e}")
            return 0

    async def clear_failed_logins(self, operator_id: int) -> None:
        """Clear failed login attempts for an operator."""
        if not self.redis:
            return
        key = f"failed_logins:operator:{operator_id}"
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis error in clear_failed_logins for operator {operator_id}: {e}")
