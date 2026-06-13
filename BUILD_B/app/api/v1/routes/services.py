from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.v1.deps import get_db, get_current_organization
from app.models.models import Organization, ServiceType
from app.schemas.schemas import ServiceTypeCreate, ServiceTypeOut

router = APIRouter()


@router.post("/", response_model=ServiceTypeOut, status_code=status.HTTP_201_CREATED)
async def create_service_type(
    service_in: ServiceTypeCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization)
):
    """Create a new service type for the organization."""
    service_type = ServiceType(
        organization_id=org.id,
        name=service_in.name,
        estimated_duration_minutes=service_in.estimated_duration_minutes,
        priority_weight=service_in.priority_weight
    )
    db.add(service_type)
    await db.commit()
    await db.refresh(service_type)
    return service_type


@router.get("/", response_model=List[ServiceTypeOut])
async def list_service_types(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization)
):
    """Retrieve all service types registered by the organization."""
    result = await db.execute(select(ServiceType).where(ServiceType.organization_id == org.id))
    return result.scalars().all()
