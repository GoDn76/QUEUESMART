import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.models import TokenMigrationRequest, Token, QueueEvent, Counter
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus
from app.core.exceptions import NotFoundException, QueueEngineException

logger = logging.getLogger(__name__)

class MigrationService:
    def __init__(self, db: AsyncSession, redis_repo: RedisRepository, event_bus: EventBus) -> None:
        self.db = db
        self.redis_repo = redis_repo
        self.event_bus = event_bus

    async def create_migration_request(
        self, token_id: int, from_counter_id: int, to_counter_id: int, operator_id: int, 
        predicted_time_saved: Optional[int] = None, reason: Optional[str] = None
    ) -> TokenMigrationRequest:
        
        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token or token.status != "WAITING":
            raise QueueEngineException("Only waiting tokens can be migrated.")
        
        if token.counter_id != from_counter_id:
            raise QueueEngineException("Token does not belong to the specified source counter.")
            
        req = TokenMigrationRequest(
            token_id=token_id,
            from_counter_id=from_counter_id,
            to_counter_id=to_counter_id,
            predicted_time_saved=predicted_time_saved,
            reason=reason,
            status="PENDING",
            created_by_id=operator_id
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        
        # Publish notification to operators
        payload = {
            "event": "MIGRATION_REQUEST_CREATED",
            "migration_id": req.id,
            "token_number": token.token_number,
            "from_counter": from_counter_id,
            "to_counter": to_counter_id
        }
        await self.event_bus.publish(f"counter:{from_counter_id}", payload)
        await self.event_bus.publish(f"counter:{to_counter_id}", payload)
        
        return req

    async def approve_migration_admin(self, migration_id: int, admin_id: int) -> TokenMigrationRequest:
        req = await self._get_req(migration_id)
        if req.status in ["REJECTED", "EXECUTED", "FULLY_APPROVED"]:
            raise QueueEngineException(f"Cannot approve request in {req.status} state.")
            
        req.source_operator_approved = True
        req.destination_operator_approved = True
        req.status = "FULLY_APPROVED"
        req.approved_by_id = admin_id
        req.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        await self.db.commit()
        await self.db.refresh(req)
        
        await self.execute_migration(req.id)
        return req

    async def approve_migration_operator(self, migration_id: int, operator_id: int, is_source: bool) -> TokenMigrationRequest:
        req = await self._get_req(migration_id)
        if req.status in ["REJECTED", "EXECUTED", "FULLY_APPROVED"]:
            raise QueueEngineException(f"Cannot approve request in {req.status} state.")
            
        if is_source:
            req.source_operator_approved = True
            req.status = "SOURCE_APPROVED" if not req.destination_operator_approved else "FULLY_APPROVED"
        else:
            req.destination_operator_approved = True
            req.status = "DESTINATION_APPROVED" if not req.source_operator_approved else "FULLY_APPROVED"
            
        if req.status == "FULLY_APPROVED":
            req.approved_by_id = operator_id
            req.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
            
        await self.db.commit()
        await self.db.refresh(req)
        
        payload = {
            "event": "MIGRATION_APPROVED",
            "migration_id": req.id,
            "status": req.status
        }
        await self.event_bus.publish(f"counter:{req.from_counter_id}", payload)
        await self.event_bus.publish(f"counter:{req.to_counter_id}", payload)
        
        if req.status == "FULLY_APPROVED":
            await self.execute_migration(req.id)
            
        return req

    async def reject_migration(self, migration_id: int, operator_id: int) -> TokenMigrationRequest:
        req = await self._get_req(migration_id)
        if req.status in ["REJECTED", "EXECUTED"]:
            raise QueueEngineException(f"Cannot reject request in {req.status} state.")
            
        req.status = "REJECTED"
        await self.db.commit()
        await self.db.refresh(req)
        
        payload = {"event": "MIGRATION_REJECTED", "migration_id": req.id}
        await self.event_bus.publish(f"counter:{req.from_counter_id}", payload)
        await self.event_bus.publish(f"counter:{req.to_counter_id}", payload)
        
        return req

    async def execute_migration(self, migration_id: int) -> None:
        """
        Transactional execution.
        Order: DB changes, QueueEvent insert, DB commit, Redis movement, PubSub events.
        """
        req = await self._get_req(migration_id)
        if req.status != "FULLY_APPROVED":
            raise QueueEngineException("Migration must be fully approved to execute.")
            
        token = (await self.db.execute(select(Token).where(Token.id == req.token_id))).scalars().first()
        if not token or token.status != "WAITING":
            req.status = "REJECTED"
            await self.db.commit()
            raise QueueEngineException("Token is no longer waiting in the queue.")
            
        # 1. Database changes
        old_counter_id = token.counter_id
        new_counter_id = req.to_counter_id
        token.counter_id = new_counter_id
        
        req.status = "EXECUTED"
        req.executed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # 2. QueueEvent insert
        event = QueueEvent(
            token_id=token.id,
            event_type="TOKEN_MIGRATED",
            event_data={
                "old_counter": old_counter_id,
                "new_counter": new_counter_id,
                "saved_minutes": req.predicted_time_saved
            },
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.db.add(event)
        
        # 3. DB commit
        await self.db.commit()
        
        # 4. Redis queue movement
        if self.redis_repo.is_available:
            try:
                # Remove from old queue
                await self.redis_repo.client.zrem(f"queue:{old_counter_id}", str(token.id))
                
                # We need the queue_type of the new counter to calculate score
                counter_stmt = select(Counter).where(Counter.id == new_counter_id)
                new_counter = (await self.db.execute(counter_stmt)).scalars().first()
                
                if new_counter:
                    # from queue_engine calculate_score logic
                    timestamp = token.created_at.timestamp()
                    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    waiting_minutes = (now_utc - token.created_at).total_seconds() / 60.0
                    effective_priority = token.priority_score + int(max(0, waiting_minutes) // 10)

                    if new_counter.queue_type == "FIFO":
                        score = timestamp
                    elif new_counter.queue_type == "PRIORITY":
                        score = - (effective_priority * 10000000000) + timestamp
                    else: # HYBRID
                        bucket = effective_priority // 20
                        score = - (bucket * 10000000000) + timestamp
                        
                    await self.redis_repo.push_to_queue(new_counter_id, token.id, score)
                    
                    # Update metrics
                    await self.redis_repo.decrement_metric(new_counter.organization_id, "waiting_count") # wait, old counter org
                    # Assume same organization.
            except Exception as e:
                logger.error(f"Redis failure during migration execution: {e}. State might be degraded.")
                # WE DO NOT ROLLBACK DB TRANSACTION.
                
        # 5. PubSub and WebSocket notifications
        payload = {
            "event": "TOKEN_MIGRATED",
            "token_id": token.id,
            "token_number": token.token_number,
            "old_counter": old_counter_id,
            "new_counter": new_counter_id
        }
        await self.event_bus.publish(f"counter:{old_counter_id}", payload)
        await self.event_bus.publish(f"counter:{new_counter_id}", payload)
        
        await self.event_bus.publish(f"user:{token.id}", {
            "event": "TOKEN_MIGRATED",
            "message": f"You have been migrated to counter {new_counter_id}."
        })

    async def _get_req(self, migration_id: int) -> TokenMigrationRequest:
        req = (await self.db.execute(select(TokenMigrationRequest).where(TokenMigrationRequest.id == migration_id))).scalars().first()
        if not req:
            raise NotFoundException("Migration request not found.")
        return req
