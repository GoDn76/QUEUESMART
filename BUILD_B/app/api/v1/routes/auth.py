from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_redis_repo
from app.repositories.redis_repo import RedisRepository
from app.schemas.schemas import OrganizationCreate, OrganizationOut, UserLogin, TokenResponse, SessionLoginResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def register_org(org_in: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    """Register a new organization."""
    return await AuthService.register_organization(db=db, org_in=org_in)


@router.post("/login", response_model=TokenResponse)
async def login_org(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Log in as an organization admin."""
    token = await AuthService.authenticate_organization(db=db, credentials=credentials)
    return TokenResponse(access_token=token)


@router.post("/operator/login", response_model=SessionLoginResponse)
async def login_operator(
    credentials: UserLogin, 
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Log in as a counter operator."""
    result = await AuthService.authenticate_operator(db=db, credentials=credentials, redis_repo=redis_repo)
    return SessionLoginResponse(access_token=result["access_token"], session_id=result["session_id"])
