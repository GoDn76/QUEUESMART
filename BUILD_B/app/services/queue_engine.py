import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.orm import selectinload

from app.models.models import Token, QueueEvent, Counter, ServiceType
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus
from app.core.exceptions import NotFoundException, QueueEngineException, RateLimitException, IdempotencyException

logger = logging.getLogger(__name__)


class QueueEngine:
    """Core Queue logic orchestrating database persistence, Redis state, events and WebSockets."""

    def __init__(self, db: AsyncSession, redis_repo: RedisRepository, event_bus: EventBus) -> None:
        self.db = db
        self.redis_repo = redis_repo
        self.event_bus = event_bus

    def calculate_score(self, queue_type: str, priority_score: int, created_at: datetime) -> float:
        """
        Calculate composite score for Redis Sorted Set.
        Redis pops smallest score first (using ZPOPMIN).
        
        Dynamic Priority Aging:
        effective_priority = base_priority + (waiting_minutes // 10)
        
        - FIFO: Score is created_timestamp
        - PRIORITY: Score = - (effective_priority * 10^10) + created_timestamp
        - HYBRID: Score = - ((effective_priority // 20) * 10^10) + created_timestamp
        """
        timestamp = created_at.timestamp()
        
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        waiting_minutes = (now_utc - created_at).total_seconds() / 60.0
        effective_priority = priority_score + int(max(0, waiting_minutes) // 10)

        if queue_type == "FIFO":
            return timestamp
        elif queue_type == "PRIORITY":
            return - (effective_priority * 10000000000) + timestamp
        elif queue_type == "HYBRID":
            bucket = effective_priority // 20  # Buckets 0 to 5
            return - (bucket * 10000000000) + timestamp
        else:
            return timestamp

    async def join_queue(
        self, qr_slug: str, customer_name: str, customer_phone: str, service_type_id: int, operator_id: Optional[int] = None
    ) -> Token:
        """Allow a public customer or operator to join a queue."""
        # 1. Fetch counter
        counter_result = await self.db.execute(select(Counter).where(Counter.qr_slug == qr_slug, Counter.active == True))
        counter = counter_result.scalars().first()
        if not counter:
            raise NotFoundException(f"Active queue not found for QR slug: {qr_slug}")

        # 2. Fetch service type
        service_result = await self.db.execute(
            select(ServiceType).where(
                ServiceType.id == service_type_id,
                ServiceType.organization_id == counter.organization_id
            )
        )
        service_type = service_result.scalars().first()
        if not service_type:
            raise NotFoundException(f"Service type {service_type_id} not found under counter's organization")

        # 3. Check Redis Rate Limiter
        if self.redis_repo.is_available:
            is_limited = await self.redis_repo.check_rate_limit(customer_phone)
            if is_limited:
                raise RateLimitException("Maximum of 3 queue joins within 5 minutes per phone number.")

        # 4. Set priority score (initially equals service weight)
        priority_score = service_type.priority_weight

        # 5. Pre-allocate database-native sequence value to avoid extra updates
        bind = self.db.bind
        dialect_name = bind.dialect.name if bind else "postgresql"
        if dialect_name == "sqlite":
            from sqlalchemy import text
            res = await self.db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM tokens"))
            seq_val = res.scalar() or 1
        else:
            from sqlalchemy import text
            try:
                res = await self.db.execute(text("SELECT nextval('tokens_sequence_number_seq')"))
                seq_val = res.scalar()
            except Exception:
                res = await self.db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM tokens"))
                seq_val = res.scalar() or 1

        # 6. Persist token in database (single-write insert)
        token = Token(
            counter_id=counter.id,
            service_type_id=service_type.id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            status="WAITING",
            priority_score=priority_score,
            sequence_number=seq_val,
            token_number=f"T-{seq_val:03d}",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        # 7. Update Redis operational state
        if self.redis_repo.is_available:
            score = self.calculate_score(counter.queue_type, token.priority_score, token.created_at)
            try:
                await self.redis_repo.push_to_queue(counter.id, token.id, score)
                await self.redis_repo.increment_metric(counter.organization_id, "waiting_count")
                await self.redis_repo.increment_metric(counter.organization_id, "active_tokens")
            except Exception as e:
                logger.warning(f"Failed to write to Redis during join: {e}. Running in degraded mode.")

        # 8. Record QueueEvent history
        queue_event = QueueEvent(
            token_id=token.id,
            operator_id=operator_id,
            event_type="JOINED" if not operator_id else "ADD_WALKIN",
            event_data={"customer_name": customer_name, "counter_name": counter.name},
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(queue_event)
        await self.db.commit()

        # 9. Publish event on EventBus
        event_payload = {
            "event": "TOKEN_JOINED",
            "organization_id": counter.organization_id,
            "counter_id": counter.id,
            "token_id": token.id,
            "token_number": token.token_number,
            "payload": {
                "customer_name": customer_name
            },
            "timestamp": token.created_at.isoformat()
        }
        await self.event_bus.publish(f"counter:{counter.id}", event_payload)
        await self.event_bus.publish(f"organization:{counter.organization_id}", event_payload)

        logger.info(f"Token {token.id} joined", extra={
            "organization_id": counter.organization_id, 
            "counter_id": counter.id, 
            "token_id": token.id, 
            "event_type": "TOKEN_JOINED"
        })

        # Notify top users of new join position context
        await self.notify_top_users_near(counter.id)

        return token

    async def call_next(self, counter_id: int, operator_id: int) -> Token:
        """Call the next customer from the queue."""
        # 1. Fetch counter
        counter_result = await self.db.execute(select(Counter).where(Counter.id == counter_id))
        counter = counter_result.scalars().first()
        if not counter:
            raise NotFoundException(f"Counter with ID {counter_id} not found")

        # Idempotency Guard: Ensure no token is currently IN_PROGRESS
        existing_result = await self.db.execute(
            select(Token).where(Token.counter_id == counter_id, Token.status == "IN_PROGRESS")
        )
        if existing_result.scalars().first():
            raise IdempotencyException("A token is already in progress. Complete or skip it before calling the next token.")

        next_token_id: Optional[int] = None

        # 2. Try fetching from Redis first
        if self.redis_repo.is_available:
            try:
                next_token_id = await self.redis_repo.pop_next_from_queue(counter.id)
            except Exception as e:
                logger.warning(f"Failed to pop from Redis: {e}. Falling back to PostgreSQL.")
                next_token_id = None

        # 3. Fallback to PostgreSQL if Redis is unavailable or empty
        if not next_token_id:
            db_token = await self._get_next_token_from_db(counter.id, counter.queue_type)
            if not db_token:
                raise NotFoundException("No customers currently waiting in the queue.")
            next_token_id = db_token.id
            logger.info(f"Retrieved token {next_token_id} from PostgreSQL (degraded fallback).")

        # 4. Fetch the token from DB and update state
        token_result = await self.db.execute(select(Token).where(Token.id == next_token_id))
        token = token_result.scalars().first()
        if not token or token.status != "WAITING":
            # If state inconsistency occurs, recurse or raise
            raise QueueEngineException("Selected token is no longer available.")

        token.status = "IN_PROGRESS"
        token.called_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.db.commit()
        await self.db.refresh(token)

        # 5. Update Redis serving state and metrics
        if self.redis_repo.is_available:
            try:
                await self.redis_repo.set_current_token(counter.id, {
                    "token_id": token.id,
                    "token_number": token.token_number,
                    "status": "IN_PROGRESS",
                    "customer_name": token.customer_name,
                    "called_at": token.called_at.isoformat()
                })
                await self.redis_repo.decrement_metric(counter.organization_id, "waiting_count")
            except Exception as e:
                logger.warning(f"Failed to update Redis serving token: {e}")

        # 6. Record QueueEvent
        queue_event = QueueEvent(
            token_id=token.id,
            operator_id=operator_id,
            event_type="CALLED_NEXT",
            event_data={"called_at": token.called_at.isoformat()},
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(queue_event)
        await self.db.commit()

        # 7. Publish O(1) Queue Advanced Broadcast to EventBus
        event_payload = {
            "event": "QUEUE_ADVANCED",
            "organization_id": counter.organization_id,
            "counter_id": counter.id,
            "token_id": token.id,
            "token_number": token.token_number,
            "payload": {
                "current_serving_sequence": token.sequence_number
            },
            "timestamp": token.called_at.isoformat()
        }
        await self.event_bus.publish(f"counter:{counter.id}", event_payload)
        await self.event_bus.publish(f"organization:{counter.organization_id}", event_payload)

        logger.info(f"Queue advanced for counter {counter.id}", extra={
            "organization_id": counter.organization_id, 
            "counter_id": counter.id, 
            "token_id": token.id, 
            "event_type": "QUEUE_ADVANCED"
        })

        # 8. Notify called user in room
        await self.event_bus.publish(f"user:{token.id}", {
            "event": "YOUR_TURN",
            "token_id": token.id,
            "token_number": token.token_number,
            "message": "It is your turn! Please proceed to the counter."
        })
        
        # Trigger external notification (SMS/WhatsApp)
        from app.services.notification_service import NotificationService
        ns = NotificationService(self.db, self.redis_repo)
        await ns.notify_your_turn(token.id, counter.name)

        # 9. Notify top 3 users of sequence approach (TOKEN_NEAR)
        await self.notify_top_users_near(counter.id)

        return token

    async def complete_token(self, token_id: int, operator_id: int) -> Token:
        """Mark token as completed."""
        token_result = await self.db.execute(
            select(Token).where(Token.id == token_id).options(selectinload(Token.counter))
        )
        token = token_result.scalars().first()
        if not token:
            raise NotFoundException(f"Token with ID {token_id} not found")
        if token.status != "IN_PROGRESS":
            raise IdempotencyException("Token must be currently in progress to mark as completed. It may have already been processed.")

        token.status = "COMPLETED"
        token.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.db.commit()

        # Update Redis serving state and metrics
        if self.redis_repo.is_available:
            try:
                await self.redis_repo.clear_current_token(token.counter_id)
                await self.redis_repo.decrement_metric(token.counter.organization_id, "active_tokens")
                await self.redis_repo.increment_metric(token.counter.organization_id, "completed_today")
            except Exception as e:
                logger.warning(f"Failed to clear current token or metrics in Redis: {e}")

        # Record QueueEvent
        queue_event = QueueEvent(
            token_id=token.id,
            operator_id=operator_id,
            event_type="COMPLETED_TOKEN",
            event_data={"completed_at": token.completed_at.isoformat()},
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(queue_event)
        await self.db.commit()

        # Publish to EventBus
        event_payload = {
            "event": "TOKEN_COMPLETED",
            "organization_id": token.counter.organization_id,
            "counter_id": token.counter_id,
            "token_id": token.id,
            "token_number": token.token_number,
            "payload": {},
            "timestamp": token.completed_at.isoformat()
        }
        await self.event_bus.publish(f"counter:{token.counter_id}", event_payload)
        await self.event_bus.publish(f"organization:{token.counter.organization_id}", event_payload)

        return token

    async def skip_token(self, token_id: int, operator_id: int) -> Token:
        """Skip the current token."""
        token_result = await self.db.execute(
            select(Token).where(Token.id == token_id).options(selectinload(Token.counter))
        )
        token = token_result.scalars().first()
        if not token:
            raise NotFoundException(f"Token with ID {token_id} not found")
        if token.status != "IN_PROGRESS":
            raise IdempotencyException("Token must be currently in progress to skip. It may have already been processed.")

        token.status = "SKIPPED"
        token.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.db.commit()

        # Update Redis serving state and metrics
        if self.redis_repo.is_available:
            try:
                await self.redis_repo.clear_current_token(token.counter_id)
                await self.redis_repo.decrement_metric(token.counter.organization_id, "active_tokens")
            except Exception as e:
                logger.warning(f"Failed to clear current token or metrics in Redis: {e}")

        # Record QueueEvent
        queue_event = QueueEvent(
            token_id=token.id,
            operator_id=operator_id,
            event_type="SKIPPED_TOKEN",
            event_data={"skipped_at": token.completed_at.isoformat()},
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(queue_event)
        await self.db.commit()

        # Publish to EventBus
        event_payload = {
            "event": "TOKEN_SKIPPED",
            "organization_id": token.counter.organization_id,
            "counter_id": token.counter_id,
            "token_id": token.id,
            "token_number": token.token_number,
            "payload": {},
            "timestamp": token.completed_at.isoformat()
        }
        await self.event_bus.publish(f"counter:{token.counter_id}", event_payload)
        await self.event_bus.publish(f"organization:{token.counter.organization_id}", event_payload)

        return token



    async def escalate_token(self, token_id: int, new_priority_weight: int, reason: str, operator_id: int) -> Token:
        """Escalate an existing token's priority, re-sorting it in Redis and notifying rooms."""
        token_result = await self.db.execute(
            select(Token).where(Token.id == token_id).options(selectinload(Token.counter))
        )
        token = token_result.scalars().first()
        if not token:
            raise NotFoundException(f"Token with ID {token_id} not found")

        old_priority = token.priority_score
        token.priority_score = new_priority_weight
        await self.db.commit()
        await self.db.refresh(token)

        # 1. Re-sort in Redis if the token is waiting
        if token.status == "WAITING" and self.redis_repo.is_available:
            try:
                score = self.calculate_score(token.counter.queue_type, token.priority_score, token.created_at)
                await self.redis_repo.push_to_queue(token.counter_id, token.id, score)
            except Exception as e:
                logger.warning(f"Failed to update Redis Sorted Set score for token {token_id}: {e}")

        # 2. Record QueueEvent audit trail
        queue_event = QueueEvent(
            token_id=token.id,
            operator_id=operator_id,
            event_type="ESCALATED_TOKEN",
            event_data={
                "old_priority": old_priority,
                "new_priority": new_priority_weight,
                "reason": reason
            },
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(queue_event)
        await self.db.commit()

        # 3. Publish event to EventBus
        event_payload = {
            "event": "TOKEN_ESCALATED",
            "organization_id": token.counter.organization_id,
            "counter_id": token.counter_id,
            "token_id": token.id,
            "token_number": token.token_number,
            "payload": {
                "old_priority": old_priority,
                "new_priority": new_priority_weight,
                "reason": reason
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
        await self.event_bus.publish(f"counter:{token.counter_id}", event_payload)
        await self.event_bus.publish(f"organization:{token.counter.organization_id}", event_payload)

        # 4. Notify affected user directly
        await self.event_bus.publish(f"user:{token.id}", {
            "event": "TOKEN_ESCALATED",
            "token_id": token.id,
            "token_number": token.token_number,
            "new_priority": new_priority_weight,
            "message": f"Your ticket priority has been escalated to {new_priority_weight}."
        })

        # 5. Notify top users near of potential position shifts
        await self.notify_top_users_near(token.counter_id)

        return token

    # --- Private Helpers ---

    async def _get_next_token_from_db(self, counter_id: int, queue_type: str) -> Optional[Token]:
        """SQL query fallback logic mimicking Redis Sorted Set rules."""
        tokens = await self._get_waiting_tokens_from_db(counter_id, queue_type, limit=1)
        return tokens[0] if tokens else None

    async def _get_waiting_tokens_from_db(self, counter_id: int, queue_type: str, limit: int = 3) -> List[Token]:
        """Query waitlist directly from database and sort with dynamic priority aging."""
        query = select(Token).where(Token.counter_id == counter_id, Token.status == "WAITING")
        result = await self.db.execute(query)
        tokens = list(result.scalars().all())

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        def _sort_key(t: Token) -> float:
            waiting_minutes = (now_utc - t.created_at).total_seconds() / 60.0
            effective_priority = t.priority_score + int(max(0, waiting_minutes) // 10)
            timestamp = t.created_at.timestamp()
            if queue_type == "FIFO":
                return timestamp
            elif queue_type == "PRIORITY":
                return - (effective_priority * 10000000000) + timestamp
            elif queue_type == "HYBRID":
                bucket = effective_priority // 20
                return - (bucket * 10000000000) + timestamp
            else:
                return timestamp

        tokens.sort(key=_sort_key)
        return tokens[:limit]

    async def notify_top_users_near(self, counter_id: int) -> None:
        """Broadcast TOKEN_NEAR directly to top 3 waiting users in O(1)."""
        waiting_token_ids: List[int] = []

        if self.redis_repo.is_available:
            try:
                waiting_token_ids = await self.redis_repo.get_queue_tokens(counter_id)
                waiting_token_ids = waiting_token_ids[:3]
            except Exception as e:
                logger.warning(f"Failed to fetch queue token list from Redis: {e}")

        # Fallback to DB query if Redis failed or returned empty
        if not waiting_token_ids:
            counter_result = await self.db.execute(select(Counter).where(Counter.id == counter_id))
            counter = counter_result.scalars().first()
            if counter:
                db_tokens = await self._get_waiting_tokens_from_db(counter_id, counter.queue_type, limit=3)
                waiting_token_ids = [t.id for t in db_tokens]

        # Notify only top 3 users near
        from app.services.notification_service import NotificationService
        ns = NotificationService(self.db, self.redis_repo)
        
        for index, token_id in enumerate(waiting_token_ids):
            await self.event_bus.publish(
                f"user:{token_id}",
                {
                    "event": "TOKEN_NEAR",
                    "token_id": token_id,
                    "people_ahead": index,
                    "message": "Your turn is coming up soon! Please remain nearby."
                }
            )
            
            # People ahead = index (since 0 means they are next, 1 means 1 person ahead, 2 means 2 people ahead).
            if index == 2:
                await ns.notify_token_near(token_id, counter_id)
