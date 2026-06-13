import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import Organization, Operator
from app.schemas.schemas import OrganizationCreate, UserLogin
from app.core.security import get_password_hash, verify_password, create_access_token
from app.repositories.redis_repo import RedisRepository
from app.core.exceptions import AuthenticationException, QueueEngineException

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    async def register_organization(db: AsyncSession, org_in: OrganizationCreate) -> Organization:
        """Register a new organization."""
        # Check if email exists
        result = await db.execute(select(Organization).where(Organization.email == org_in.email))
        if result.scalars().first():
            raise QueueEngineException("Organization with this email already exists.")

        # Also check if operator exists with this email to avoid collision
        op_result = await db.execute(select(Operator).where(Operator.email == org_in.email))
        if op_result.scalars().first():
            raise QueueEngineException("Email is already registered as an operator.")

        org = Organization(
            name=org_in.name,
            email=org_in.email,
            hashed_password=get_password_hash(org_in.password)
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        logger.info(f"Registered new organization: {org.name} ({org.email})")
        return org

    @staticmethod
    async def authenticate_organization(db: AsyncSession, credentials: UserLogin) -> str:
        """Authenticate an organization and return a JWT access token."""
        result = await db.execute(select(Organization).where(Organization.email == credentials.email))
        org = result.scalars().first()
        if not org or not verify_password(credentials.password, org.hashed_password):
            raise AuthenticationException("Incorrect email or password.")

        # Create access token with role prefix/payload
        token = create_access_token(subject=f"org:{org.id}")
        logger.info(f"Organization authenticated: {org.email}")
        return token

    @staticmethod
    async def authenticate_operator(db: AsyncSession, credentials: UserLogin, redis_repo: RedisRepository) -> dict:
        """Authenticate an operator and return a JWT access token along with session."""
        import uuid
        from datetime import datetime, timezone

        result = await db.execute(select(Operator).where(Operator.email == credentials.email))
        operator = result.scalars().first()
        if not operator:
            raise AuthenticationException("Incorrect email or password.")
            
        if not operator.active:
            raise AuthenticationException("Operator account is disabled.")

        # Rate Limiting
        if redis_repo.is_available:
            failed_count = await redis_repo.record_failed_login(operator.id)
            if failed_count > 5:
                raise AuthenticationException("Too many failed login attempts. Try again later.")
        else:
            if operator.failed_login_attempts >= 5:
                raise AuthenticationException("Too many failed login attempts. Try again later.")

        if not verify_password(credentials.password, operator.hashed_password):
            operator.failed_login_attempts += 1
            await db.commit()
            raise AuthenticationException("Incorrect email or password.")

        # Login successful
        operator.failed_login_attempts = 0
        operator.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        if redis_repo.is_available:
            await redis_repo.clear_failed_logins(operator.id)

        session_id = str(uuid.uuid4())
        
        # Acquire Lock
        if operator.counter_id:
            if not redis_repo.is_available:
                raise QueueEngineException("Operator session validation temporarily unavailable.")
            
            acquired = await redis_repo.acquire_counter_lock(
                counter_id=operator.counter_id,
                operator_id=operator.id,
                session_id=session_id
            )
            if not acquired:
                raise QueueEngineException("Counter already controlled by another active operator.")

        # Create token
        token = create_access_token(
            subject=f"operator:{operator.id}",
            custom_claims={
                "session_version": operator.session_version,
                "session_id": session_id
            }
        )
        logger.info(f"Operator authenticated: {operator.email}")
        return {"access_token": token, "session_id": session_id, "counter_id": operator.counter_id}
