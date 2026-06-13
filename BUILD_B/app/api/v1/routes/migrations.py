from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.v1.deps import get_db, get_current_organization, get_redis_repo, get_event_bus
from app.schemas.schemas import TokenMigrationRequestOut, TokenMigrationRequestCreate, TokenMigrationApproval
from app.models.models import TokenMigrationRequest, Organization
from app.services.migration_service import MigrationService
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus
from app.core.exceptions import QueueEngineException

router = APIRouter()

def get_migration_service(db: AsyncSession = Depends(get_db), redis_repo: RedisRepository = Depends(get_redis_repo), event_bus: EventBus = Depends(get_event_bus)):
    return MigrationService(db, redis_repo, event_bus)

@router.get("/pending", response_model=List[TokenMigrationRequestOut])
async def list_pending_migrations(
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    # Depending on your access patterns, an admin is an Organization.
    # org.id is the current admin's ID
    stmt = select(TokenMigrationRequest).where(TokenMigrationRequest.status.in_(["PENDING", "SOURCE_APPROVED", "DESTINATION_APPROVED"]))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{migration_id}/approve", response_model=TokenMigrationRequestOut)
async def admin_approve_migration(
    migration_id: int,
    org: Organization = Depends(get_current_organization),
    service: MigrationService = Depends(get_migration_service)
):
    try:
        return await service.approve_migration_admin(migration_id, org.id)
    except QueueEngineException as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{migration_id}/reject", response_model=TokenMigrationRequestOut)
async def admin_reject_migration(
    migration_id: int,
    org: Organization = Depends(get_current_organization),
    service: MigrationService = Depends(get_migration_service)
):
    try:
        return await service.reject_migration(migration_id, org.id)
    except QueueEngineException as e:
        raise HTTPException(status_code=400, detail=str(e))
