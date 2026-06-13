from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.v1.deps import get_db, get_current_operator, get_queue_engine, get_redis_repo, get_active_operator_session, get_event_bus
from app.models.models import Operator, Token, Counter
from app.schemas.schemas import TokenOut, OperatorAddTokenRequest, EscalateTokenRequest, TokenMigrationRequestOut
from app.services.queue_engine import QueueEngine
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus

router = APIRouter()


@router.post("/call-next", response_model=TokenOut)
async def call_next_customer(
    operator: Operator = Depends(get_active_operator_session),
    queue_engine: QueueEngine = Depends(get_queue_engine)
):
    """Call the next customer in the queue for the operator's assigned counter."""
    if not operator.counter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator is not assigned to any counter."
        )
    return await queue_engine.call_next(counter_id=operator.counter_id, operator_id=operator.id)


@router.post("/complete/{token_id}", response_model=TokenOut)
async def complete_serving(
    token_id: int,
    operator: Operator = Depends(get_active_operator_session),
    queue_engine: QueueEngine = Depends(get_queue_engine)
):
    """Mark the currently serving token as completed."""
    # Safety check: ensure operator is assigned to a counter
    if not operator.counter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator is not assigned to any counter."
        )
    return await queue_engine.complete_token(token_id=token_id, operator_id=operator.id)


@router.post("/skip/{token_id}", response_model=TokenOut)
async def skip_serving(
    token_id: int,
    operator: Operator = Depends(get_active_operator_session),
    queue_engine: QueueEngine = Depends(get_queue_engine)
):
    """Mark the currently serving token as skipped."""
    if not operator.counter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator is not assigned to any counter."
        )
    return await queue_engine.skip_token(token_id=token_id, operator_id=operator.id)


@router.get("/current-queue", response_model=List[TokenOut])
async def list_current_queue(
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Retrieve all waiting customers in the operator's queue, sorted according to queue rules."""
    if not operator.counter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator is not assigned to any counter."
        )

    counter_id = operator.counter_id
    token_ids = []

    # 1. Fetch from Redis Sorted Set
    if redis_repo.is_available:
        try:
            token_ids = await redis_repo.get_queue_tokens(counter_id)
        except Exception:
            token_ids = []

    # 2. Fallback to Database sorting if Redis is empty / down
    if not token_ids:
        counter_result = await db.execute(select(Counter).where(Counter.id == counter_id))
        counter = counter_result.scalars().first()
        if not counter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")

        query = select(Token).where(Token.counter_id == counter_id, Token.status == "WAITING")
        if counter.queue_type == "FIFO":
            query = query.order_by(Token.created_at.asc())
        elif counter.queue_type == "PRIORITY":
            query = query.order_by(Token.priority_score.desc(), Token.created_at.asc())
        elif counter.queue_type == "HYBRID":
            # Bucket priority first (priority // 20) desc, then created_at asc
            from sqlalchemy import desc
            query = query.order_by(desc(Token.priority_score / 20), Token.created_at.asc())
        else:
            query = query.order_by(Token.created_at.asc())

        result = await db.execute(query)
        return result.scalars().all()

    # 3. Resolve token structures preserving active Redis Sorted Set order
    result = await db.execute(select(Token).where(Token.id.in_(token_ids)))
    tokens_map = {t.id: t for t in result.scalars().all()}
    
    return [tokens_map[tid] for tid in token_ids if tid in tokens_map]


@router.post("/add-token", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def operator_add_token(
    request_in: OperatorAddTokenRequest,
    operator: Operator = Depends(get_active_operator_session),
    db: AsyncSession = Depends(get_db),
    queue_engine: QueueEngine = Depends(get_queue_engine)
):
    """Enables an operator to join a customer to the queue on their behalf."""
    # Verify counter exists and belongs to the operator's organization
    counter_result = await db.execute(
        select(Counter).where(Counter.id == request_in.counter_id, Counter.organization_id == operator.organization_id)
    )
    counter = counter_result.scalars().first()
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found or doesn't belong to your organization."
        )

    # Operator-assisted registration delegates directly to queue engine join_queue
    return await queue_engine.join_queue(
        qr_slug=counter.qr_slug,
        customer_name=request_in.customer_name,
        customer_phone=request_in.customer_phone,
        service_type_id=request_in.service_type_id,
        operator_id=operator.id
    )


@router.post("/escalate-token/{token_id}", response_model=TokenOut)
async def operator_escalate_token(
    token_id: int,
    request_in: EscalateTokenRequest,
    operator: Operator = Depends(get_active_operator_session),
    db: AsyncSession = Depends(get_db),
    queue_engine: QueueEngine = Depends(get_queue_engine)
):
    """Enables an operator/admin to escalate a token's priority, re-sorting the active queue."""
    # Verify token exists and belongs to operator's organization
    token_result = await db.execute(select(Token).where(Token.id == token_id))
    token = token_result.scalars().first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")

    # Verify counter belongs to operator's organization
    counter_result = await db.execute(
        select(Counter).where(Counter.id == token.counter_id, Counter.organization_id == operator.organization_id)
    )
    if not counter_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to escalate tokens for this counter."
        )

    return await queue_engine.escalate_token(
        token_id=token_id,
        new_priority_weight=request_in.new_priority_weight,
        reason=request_in.reason,
        operator_id=operator.id
    )


@router.get("/current-serving", response_model=Optional[TokenOut])
async def get_current_serving_token(
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Fetch the ticket currently being served at the operator's active counter."""
    if not operator.counter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator is not assigned to any counter."
        )

    counter_id = operator.counter_id
    current_token_data = None

    if redis_repo.is_available:
        try:
            current_token_data = await redis_repo.get_current_token(counter_id)
        except Exception:
            pass

    if current_token_data:
        token_id = current_token_data.get("token_id")
        return await db.get(Token, token_id)

    # Fallback DB query
    stmt = (
        select(Token)
        .where(Token.counter_id == counter_id, Token.status == "IN_PROGRESS")
        .order_by(Token.called_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


@router.post("/heartbeat", status_code=status.HTTP_200_OK)
async def operator_heartbeat(
    operator: Operator = Depends(get_current_operator),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Keep the operator session alive and refresh the Redis lock."""
    if not operator.counter_id:
        raise HTTPException(status_code=400, detail="Operator not assigned to any counter.")
    
    if not redis_repo.is_available:
        raise HTTPException(status_code=503, detail="Operator session validation temporarily unavailable.")
        
    session_id = getattr(operator, "_current_session_id", "")
    refreshed = await redis_repo.refresh_counter_lock(operator.counter_id, session_id)
    if not refreshed:
        raise HTTPException(status_code=403, detail="Session expired or lock lost.")
        
    return {"status": "ok", "message": "Heartbeat refreshed"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def operator_logout(
    operator: Operator = Depends(get_current_operator),
    redis_repo: RedisRepository = Depends(get_redis_repo),
    event_bus: EventBus = Depends(get_event_bus)
):
    """Release the counter lock and log the operator out."""
    if operator.counter_id and redis_repo.is_available:
        session_id = getattr(operator, "_current_session_id", "")
        await redis_repo.release_counter_lock(operator.counter_id, session_id)
        
        # Publish event
        from datetime import datetime, timezone
        payload = {
            "event": "OPERATOR_LOGOUT",
            "organization_id": operator.organization_id,
            "counter_id": operator.counter_id,
            "operator_id": operator.id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await event_bus.publish(f"org:{operator.organization_id}", payload)
        
    return {"status": "ok", "message": "Logged out successfully"}

@router.get("/migrations", response_model=List[TokenMigrationRequestOut])
async def list_operator_migrations(
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db)
):
    from app.models.models import TokenMigrationRequest
    from sqlalchemy import or_
    if not operator.counter_id:
        return []
    stmt = select(TokenMigrationRequest).where(
        or_(TokenMigrationRequest.from_counter_id == operator.counter_id, TokenMigrationRequest.to_counter_id == operator.counter_id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/migrations/{migration_id}/approve")
async def operator_approve_migration(
    migration_id: int,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    if not operator.counter_id:
        raise HTTPException(status_code=400, detail="Operator not assigned to any counter.")
    
    from app.services.migration_service import MigrationService
    from app.models.models import TokenMigrationRequest
    
    req = (await db.execute(select(TokenMigrationRequest).where(TokenMigrationRequest.id == migration_id))).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Migration request not found.")
        
    is_source = (req.from_counter_id == operator.counter_id)
    if not is_source and req.to_counter_id != operator.counter_id:
        raise HTTPException(status_code=403, detail="You are not authorized to approve this migration.")
        
    service = MigrationService(db, redis_repo, event_bus)
    from app.core.exceptions import QueueEngineException
    try:
        return await service.approve_migration_operator(migration_id, operator.id, is_source)
    except QueueEngineException as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/migrations/{migration_id}/reject")
async def operator_reject_migration(
    migration_id: int,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    if not operator.counter_id:
        raise HTTPException(status_code=400, detail="Operator not assigned to any counter.")
        
    from app.services.migration_service import MigrationService
    from app.models.models import TokenMigrationRequest
    
    req = (await db.execute(select(TokenMigrationRequest).where(TokenMigrationRequest.id == migration_id))).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Migration request not found.")
        
    if req.from_counter_id != operator.counter_id and req.to_counter_id != operator.counter_id:
        raise HTTPException(status_code=403, detail="You are not authorized to reject this migration.")
        
    service = MigrationService(db, redis_repo, event_bus)
    from app.core.exceptions import QueueEngineException
    try:
        return await service.reject_migration(migration_id, operator.id)
    except QueueEngineException as e:
        raise HTTPException(status_code=400, detail=str(e))
