import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import get_db
from app.db.redis import get_redis
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus, RedisEventBus
from app.services.queue_engine import QueueEngine
from app.models.models import Organization, Operator
from app.core.exceptions import AuthenticationException, NotFoundException

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_redis_repo(redis_client=Depends(get_redis)) -> RedisRepository:
    """Dependency injecting Redis repository."""
    return RedisRepository(redis_client=redis_client)


async def get_event_bus(redis_client=Depends(get_redis)) -> EventBus:
    """Dependency injecting Redis EventBus."""
    return RedisEventBus(redis_client=redis_client)


async def get_queue_engine(
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo),
    event_bus: EventBus = Depends(get_event_bus)
) -> QueueEngine:
    """Dependency injecting core QueueEngine."""
    return QueueEngine(db=db, redis_repo=redis_repo, event_bus=event_bus)


async def get_current_user_subject(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """Extract and validate credentials subject from OAuth token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject: str = payload.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials token payload.",
            )
        return subject
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials token.",
        )


async def get_current_organization(
    db: AsyncSession = Depends(get_db),
    subject: str = Depends(get_current_user_subject)
) -> Organization:
    """Ensure the authenticated user is an Organization and return its model."""
    if not subject.startswith("org:"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin role has access to this resource.",
        )
    
    org_id = int(subject.split(":")[1])
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    return org


async def get_current_operator(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Operator:
    """Ensure the authenticated user is an Operator and return its model."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication credentials.")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject: str = payload.get("sub")
        session_version: int = payload.get("session_version", 1)
        session_id: str = payload.get("session_id", "")
        if not subject or not subject.startswith("operator:"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only counter operator role has access to this resource.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials token.")
    
    operator_id = int(subject.split(":")[1])
    result = await db.execute(select(Operator).where(Operator.id == operator_id))
    operator = result.scalars().first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator credentials not found.")
        
    if not operator.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator account is disabled.")
        
    if operator.session_version != session_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired due to credential reset.")
        
    # Store session id for the lock validation dependency
    operator._current_session_id = session_id
    
    return operator


async def get_active_operator_session(
    operator: Operator = Depends(get_current_operator),
    redis_repo: RedisRepository = Depends(get_redis_repo)
) -> Operator:
    """Validate that the operator holds the active session lock for their counter."""
    if not operator.counter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator is not assigned to any counter."
        )
        
    if not redis_repo.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operator session validation temporarily unavailable."
        )
        
    lock_status = await redis_repo.get_counter_lock_status(operator.counter_id)
    if not lock_status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active session found for this counter. Please log in again."
        )
        
    if lock_status.get("session_id") != getattr(operator, "_current_session_id", ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Counter already controlled by another active operator."
        )
        
    return operator


async def get_current_staff_org_id(
    db: AsyncSession = Depends(get_db),
    subject: str = Depends(get_current_user_subject)
) -> int:
    """Validate subject and return organization ID for either organization admin or operator."""
    if subject.startswith("org:"):
        return int(subject.split(":")[1])
    elif subject.startswith("operator:"):
        operator_id = int(subject.split(":")[1])
        result = await db.execute(select(Operator).where(Operator.id == operator_id))
        operator = result.scalars().first()
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Operator account not found.",
            )
        return operator.organization_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff credentials required to access this resource.",
        )

