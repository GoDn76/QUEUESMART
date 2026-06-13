import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.models import Token, Counter, Organization
from app.repositories.redis_repo import RedisRepository
from app.services.queue_engine import QueueEngine

logger = logging.getLogger(__name__)

class RedisRecoveryService:
    """Service to rebuild Redis operational state from PostgreSQL on application startup."""
    
    def __init__(self, db: AsyncSession, redis_repo: RedisRepository):
        self.db = db
        self.redis_repo = redis_repo
        self.queue_engine = QueueEngine(db, redis_repo, None)

    async def rebuild_cache(self) -> None:
        """
        Rebuilds Redis operational state from PostgreSQL truth on startup.
        - Rebuild WAITING queues.
        - Rebuild IN_PROGRESS current_token caches.
        - Rebuild organization metrics.
        - Logs warnings on inconsistencies.
        """
        if not self.redis_repo.is_available:
            logger.warning("Redis is unavailable; skipping cache rebuild.")
            return

        logger.info("Starting Redis cache recovery from PostgreSQL...")

        counters_result = await self.db.execute(select(Counter))
        counters = counters_result.scalars().all()
        
        for counter in counters:
            # 1. Clear existing Redis queues to prevent stale data
            if self.redis_repo.redis:
                await self.redis_repo.redis.delete(f"queue:{counter.id}")
                await self.redis_repo.clear_current_token(counter.id)

            # 2. Rebuild WAITING queue using sorted score calculation
            tokens_result = await self.db.execute(
                select(Token).where(Token.counter_id == counter.id, Token.status == "WAITING")
            )
            waiting_tokens = tokens_result.scalars().all()
            for token in waiting_tokens:
                score = self.queue_engine.calculate_score(counter.queue_type, token.priority_score, token.created_at)
                await self.redis_repo.push_to_queue(counter.id, token.id, score)
                
            # 3. Rebuild IN_PROGRESS current token cache
            in_prog_result = await self.db.execute(
                select(Token)
                .where(Token.counter_id == counter.id, Token.status == "IN_PROGRESS")
                .order_by(Token.called_at.desc())
            )
            in_progress_tokens = in_prog_result.scalars().all()
            
            if in_progress_tokens:
                current_token = in_progress_tokens[0]
                if len(in_progress_tokens) > 1:
                    logger.warning(
                        f"Multiple IN_PROGRESS tokens found for counter {counter.id}. "
                        f"Using token {current_token.id} (called at {current_token.called_at}) as authoritative."
                    )
                
                await self.redis_repo.set_current_token(counter.id, {
                    "token_id": current_token.id,
                    "token_number": current_token.token_number,
                    "status": "IN_PROGRESS",
                    "customer_name": current_token.customer_name,
                    "called_at": current_token.called_at.isoformat() if current_token.called_at else ""
                })

        # 4. Rebuild organization metrics
        orgs_result = await self.db.execute(select(Organization))
        orgs = orgs_result.scalars().all()
        
        for org in orgs:
            # waiting_count
            wait_count = await self.db.execute(
                select(func.count(Token.id)).join(Counter).where(
                    Counter.organization_id == org.id,
                    Token.status == "WAITING"
                )
            )
            await self.redis_repo.set_metric(org.id, "waiting_count", wait_count.scalar() or 0)
            
            # active_tokens (WAITING + IN_PROGRESS)
            active_count = await self.db.execute(
                select(func.count(Token.id)).join(Counter).where(
                    Counter.organization_id == org.id,
                    Token.status.in_(["WAITING", "IN_PROGRESS"])
                )
            )
            await self.redis_repo.set_metric(org.id, "active_tokens", active_count.scalar() or 0)
            
            # completed_today
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            completed_count = await self.db.execute(
                select(func.count(Token.id)).join(Counter).where(
                    Counter.organization_id == org.id,
                    Token.status == "COMPLETED",
                    Token.completed_at >= today
                )
            )
            await self.redis_repo.set_metric(org.id, "completed_today", completed_count.scalar() or 0)

        logger.info("Redis cache recovery completed successfully.")
