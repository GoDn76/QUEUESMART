from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.v1.deps import get_db, get_current_organization, get_redis_repo
from app.models.models import Organization, Operator, Counter, QueueEvent
from app.schemas.schemas import OperatorCreate, OperatorAdminOut, OperatorResetPassword, AdminCounterStatusResponse
from app.core.security import get_password_hash
from app.repositories.redis_repo import RedisRepository
from datetime import datetime, timezone

router = APIRouter()

@router.post("/operators/create", response_model=OperatorAdminOut)
async def create_operator(
    operator_in: OperatorCreate,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Create a new operator."""
    result = await db.execute(select(Operator).where(Operator.email == operator_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Operator email already exists.")
        
    operator = Operator(
        organization_id=org.id,
        name=operator_in.name,
        email=operator_in.email,
        hashed_password=get_password_hash(operator_in.password),
        counter_id=operator_in.counter_id
    )
    db.add(operator)
    await db.commit()
    await db.refresh(operator)
    return operator

@router.post("/operators/reset-password/{operator_id}", response_model=OperatorAdminOut)
async def reset_operator_password(
    operator_id: int,
    reset_in: OperatorResetPassword,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Admin resets an operator password, incrementing their session version to invalidate active sessions."""
    operator = await db.get(Operator, operator_id)
    if not operator or operator.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Operator not found.")
        
    operator.hashed_password = get_password_hash(reset_in.new_password)
    operator.session_version += 1
    operator.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    audit = QueueEvent(
        operator_id=operator.id,
        event_type="PASSWORD_RESET",
        event_data={"admin_id": org.id}
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(operator)
    return operator

@router.post("/operators/disable/{operator_id}", response_model=OperatorAdminOut)
async def disable_operator(
    operator_id: int,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Disable an operator, incrementing session version."""
    operator = await db.get(Operator, operator_id)
    if not operator or operator.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Operator not found.")
        
    operator.active = False
    operator.session_version += 1
    
    audit = QueueEvent(
        operator_id=operator.id,
        event_type="OPERATOR_DISABLED"
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(operator)
    return operator

@router.post("/operators/enable/{operator_id}", response_model=OperatorAdminOut)
async def enable_operator(
    operator_id: int,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Enable a disabled operator."""
    operator = await db.get(Operator, operator_id)
    if not operator or operator.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Operator not found.")
        
    operator.active = True
    
    audit = QueueEvent(
        operator_id=operator.id,
        event_type="OPERATOR_ENABLED"
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(operator)
    return operator

@router.get("/operators", response_model=list[OperatorAdminOut])
async def list_operators(
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """List all operators in the organization."""
    result = await db.execute(select(Operator).where(Operator.organization_id == org.id))
    return result.scalars().all()

@router.delete("/operators/{operator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operator(
    operator_id: int,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Delete an operator permanently."""
    operator = await db.get(Operator, operator_id)
    if not operator or operator.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Operator not found.")
        
    await db.delete(operator)
    await db.commit()
    return None

@router.get("/counters", response_model=list[AdminCounterStatusResponse])
async def list_counters_status(
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """List all counters with their current session lock status."""
    result = await db.execute(select(Counter).where(Counter.organization_id == org.id))
    counters = result.scalars().all()
    
    responses = []
    for c in counters:
        status_resp = AdminCounterStatusResponse(
            counter_id=c.id,
            counter_name=c.name,
            session_active=False,
            queue_length=0
        )
        
        # operator info
        op_res = await db.execute(select(Operator).where(Operator.counter_id == c.id, Operator.active == True))
        op = op_res.scalars().first()
        if op:
            status_resp.operator = op.name
            
        # queue length & session info
        if redis_repo.is_available:
            q_tokens = await redis_repo.get_queue_tokens(c.id)
            status_resp.queue_length = len(q_tokens)
            
            lock = await redis_repo.get_counter_lock_status(c.id)
            if lock:
                status_resp.session_active = True
                status_resp.last_seen = lock.get("last_seen")
                
        responses.append(status_resp)
        
    return responses

@router.post("/counters/{counter_id}/force-takeover", status_code=status.HTTP_200_OK)
async def force_counter_takeover(
    counter_id: int,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Admin forces release of a counter session lock."""
    counter = await db.get(Counter, counter_id)
    if not counter or counter.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Counter not found.")
        
    if not redis_repo.is_available:
        raise HTTPException(status_code=503, detail="Redis unavailable.")
        
    await redis_repo.force_release_counter_lock(counter_id)
    
    audit = QueueEvent(
        event_type="COUNTER_FORCE_TAKEOVER",
        event_data={"counter_id": counter_id, "admin_org_id": org.id}
    )
    db.add(audit)
    await db.commit()
    
    return {"status": "ok", "message": f"Lock released for counter {counter_id}"}

from pydantic import BaseModel
class TestNotificationRequest(BaseModel):
    phone: str

@router.post("/test-notification")
async def test_notification(
    request: TestNotificationRequest,
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    from app.services.notification_service import NotificationService
    service = NotificationService(db, redis_repo)
    message = "QueueMind Test Notification: If you see this, your provider is working!"
    success = await service.send(request.phone, message)
    return {"success": success}
