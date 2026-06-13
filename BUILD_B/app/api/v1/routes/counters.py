from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.v1.deps import get_db, get_current_organization, get_redis_repo
from app.models.models import Organization, Counter, Operator
from app.repositories.redis_repo import RedisRepository
from app.schemas.schemas import CounterCreate, CounterOut, OperatorCreate, OperatorOut
from app.core.security import get_password_hash
from app.core.exceptions import QueueEngineException, NotFoundException

router = APIRouter()


import random
import string

def generate_qr_slug() -> str:
    """Generate a random slug in pattern xxxx-yyyy where x is a-zA-Z and y is 0-9."""
    letters = ''.join(random.choices(string.ascii_letters, k=4))
    digits = ''.join(random.choices(string.digits, k=4))
    return f"{letters}-{digits}"


async def generate_unique_qr_slug(db: AsyncSession) -> str:
    """Generate a unique QR slug by checking database existence."""
    while True:
        slug = generate_qr_slug()
        slug_result = await db.execute(select(Counter).where(Counter.qr_slug == slug))
        if not slug_result.scalars().first():
            return slug


@router.post("/", response_model=CounterOut, status_code=status.HTTP_201_CREATED)
async def create_counter(
    counter_in: CounterCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization)
):
    """Create a new counter for the authenticated organization."""
    if not counter_in.qr_slug:
        qr_slug = await generate_unique_qr_slug(db)
    else:
        qr_slug = counter_in.qr_slug
        # Check if qr_slug is unique
        slug_result = await db.execute(select(Counter).where(Counter.qr_slug == qr_slug))
        if slug_result.scalars().first():
            raise QueueEngineException(f"QR slug '{qr_slug}' is already taken.")

    counter = Counter(
        organization_id=org.id,
        name=counter_in.name,
        queue_type=counter_in.queue_type,
        qr_slug=qr_slug,
        active=True
    )
    db.add(counter)
    await db.commit()
    await db.refresh(counter)
    return counter


@router.get("/", response_model=List[CounterOut])
async def list_counters(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization)
):
    """Retrieve all counters registered under the organization."""
    result = await db.execute(select(Counter).where(Counter.organization_id == org.id))
    return result.scalars().all()


@router.post("/{counter_id}/operators", response_model=OperatorOut, status_code=status.HTTP_201_CREATED)
async def create_counter_operator(
    counter_id: int,
    operator_in: OperatorCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization)
):
    """Provision a new Operator and assign them to the specified Counter."""
    # Verify counter exists and belongs to this organization
    counter_result = await db.execute(
        select(Counter).where(Counter.id == counter_id, Counter.organization_id == org.id)
    )
    counter = counter_result.scalars().first()
    if not counter:
        raise NotFoundException(f"Counter {counter_id} not found in your organization.")

    # Check if operator email is already registered
    email_result = await db.execute(select(Operator).where(Operator.email == operator_in.email))
    if email_result.scalars().first():
        raise QueueEngineException(f"An operator with email '{operator_in.email}' already exists.")

    # Also check organization email to avoid collision
    org_result = await db.execute(select(Organization).where(Organization.email == operator_in.email))
    if org_result.scalars().first():
        raise QueueEngineException("Email is registered as an organization administrator.")

    operator = Operator(
        organization_id=org.id,
        name=operator_in.name,
        email=operator_in.email,
        hashed_password=get_password_hash(operator_in.password),
        counter_id=counter.id
    )
    db.add(operator)
    await db.commit()
    await db.refresh(operator)
    return operator


@router.get("/{counter_id}/operators", response_model=List[OperatorOut])
async def list_counter_operators(
    counter_id: int,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization)
):
    """Get all operators assigned to the specified Counter."""
    # Verify counter exists and belongs to this organization
    counter_result = await db.execute(
        select(Counter).where(Counter.id == counter_id, Counter.organization_id == org.id)
    )
    if not counter_result.scalars().first():
        raise NotFoundException(f"Counter {counter_id} not found in your organization.")

    result = await db.execute(select(Operator).where(Operator.counter_id == counter_id))
    return result.scalars().all()

@router.get("/recommendations")
async def get_counter_recommendations(
    service_type_id: int,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    from app.services.counter_recommendation_service import CounterRecommendationService
    service = CounterRecommendationService(db, redis_repo)
    res = await service.get_counter_recommendation(service_type_id, org.id)
    if not res:
        raise NotFoundException("No active counters found for recommendation.")
    return res
