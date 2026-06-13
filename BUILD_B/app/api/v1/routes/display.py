import logging
import uuid
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.v1.deps import get_db, get_redis_repo, get_current_staff_org_id
from app.models.models import Counter, Token, ServiceType, DisplayBoard, Organization
from app.schemas.schemas import (
    DisplayBoardOut,
    TokenOut,
    DisplayBoardCreate,
    DisplayBoardCreateResponse,
    CounterDisplayState,
    DisplayBoardDetailsResponse,
)
from app.repositories.redis_repo import RedisRepository
from app.services.prediction import QueuePredictionService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create", response_model=DisplayBoardCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_display_board(
    board_in: DisplayBoardCreate,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_staff_org_id)
):
    """Register a new Display Board under the staff's organization."""
    # If counter-specific, verify counter exists and belongs to organization
    if board_in.board_type == "COUNTER":
        if not board_in.counter_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="counter_id is required for COUNTER type display boards."
            )
        counter_res = await db.execute(
            select(Counter).where(Counter.id == board_in.counter_id, Counter.organization_id == org_id)
        )
        if not counter_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Counter {board_in.counter_id} not found in your organization."
            )

    display_uuid = str(uuid.uuid4())
    access_token = secrets.token_urlsafe(32)

    display_board = DisplayBoard(
        uuid_id=display_uuid,
        organization_id=org_id,
        counter_id=board_in.counter_id,
        name=board_in.name,
        board_type=board_in.board_type,
        access_token=access_token
    )
    db.add(display_board)
    await db.commit()

    # Frontend will use the display_id (uuid) to open the dashboard URL
    display_url = f"https://queuemind.app/display/{display_uuid}"

    return DisplayBoardCreateResponse(
        display_id=display_uuid,
        display_token=access_token,
        display_url=display_url
    )


@router.delete("/{display_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_display_board(
    display_id: str,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_staff_org_id)
):
    """Delete a Display Board matching the specified display UUID."""
    res = await db.execute(
        select(DisplayBoard).where(DisplayBoard.uuid_id == display_id, DisplayBoard.organization_id == org_id)
    )
    board = res.scalars().first()
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Display board not found or not in your organization."
        )

    await db.delete(board)
    await db.commit()

@router.get("/", response_model=List[DisplayBoardDetailsResponse])
async def list_display_boards(
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_staff_org_id),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """List all display boards in the organization."""
    res = await db.execute(select(DisplayBoard).where(DisplayBoard.organization_id == org_id))
    boards = res.scalars().all()
    
    results = []
    for board in boards:
        # Simplified response just for listing
        results.append(DisplayBoardDetailsResponse(
            display_id=board.uuid_id,
            name=board.name,
            board_type=board.board_type,
            organization_id=board.organization_id,
            organization_name="",  # Not strictly needed for list view
            counter_id=board.counter_id,
            overall_waiting_count=0,
            overall_completed_today=0
        ))
    return results


async def _get_counter_state(
    counter: Counter, db: AsyncSession, redis_repo: RedisRepository
) -> CounterDisplayState:
    """Helper to load real-time serving states, waitlist, and wait prediction for a counter."""
    counter_id = counter.id

    # 1. Get current token
    current_token_data = None
    if redis_repo.is_available:
        try:
            current_token_data = await redis_repo.get_current_token(counter_id)
        except Exception:
            current_token_data = None

    current_token = None
    if current_token_data:
        token_id = current_token_data.get("token_id")
        current_token = await db.get(Token, token_id)

    if not current_token:
        stmt = (
            select(Token)
            .where(Token.counter_id == counter_id, Token.status == "IN_PROGRESS")
            .order_by(Token.called_at.desc())
            .limit(1)
        )
        current_token = (await db.execute(stmt)).scalars().first()

    # 2. Get upcoming queue list
    token_ids = []
    if redis_repo.is_available:
        try:
            token_ids = await redis_repo.get_queue_tokens(counter_id)
        except Exception:
            token_ids = []

    upcoming_tokens = []
    if token_ids:
        tokens_result = await db.execute(select(Token).where(Token.id.in_(token_ids)))
        tokens_map = {t.id: t for t in tokens_result.scalars().all()}
        upcoming_tokens = [tokens_map[tid] for tid in token_ids if tid in tokens_map]
    else:
        query = select(Token).where(Token.counter_id == counter_id, Token.status == "WAITING")
        if counter.queue_type == "FIFO":
            query = query.order_by(Token.created_at.asc())
        elif counter.queue_type == "PRIORITY":
            query = query.order_by(Token.priority_score.desc(), Token.created_at.asc())
        elif counter.queue_type == "HYBRID":
            from sqlalchemy import desc
            query = query.order_by(desc(Token.priority_score / 20), Token.created_at.asc())
        else:
            query = query.order_by(Token.created_at.asc())
        upcoming_tokens = list((await db.execute(query)).scalars().all())

    # 3. Wait prediction
    pred_service = QueuePredictionService(db, redis_repo)
    service_type_id = 1
    if upcoming_tokens:
        service_type_id = upcoming_tokens[0].service_type_id
    else:
        service_stmt = select(ServiceType.id).where(ServiceType.organization_id == counter.organization_id).limit(1)
        val = (await db.execute(service_stmt)).scalar()
        if val:
            service_type_id = val

    estimated_wait = await pred_service.estimate_wait_time(counter_id, service_type_id)

    return CounterDisplayState(
        counter_id=counter.id,
        counter_name=counter.name,
        queue_type=counter.queue_type,
        active=counter.active,
        current_token=current_token,
        upcoming_tokens=upcoming_tokens,
        queue_length=len(upcoming_tokens),
        estimated_wait_minutes=estimated_wait
    )


@router.get("/{display_id}/state", response_model=DisplayBoardDetailsResponse)
async def get_display_board_state(
    display_id: str,
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Securely retrieve detailed metadata and state metrics for a Display Board."""
    token_val = access_token
    if authorization and authorization.startswith("Bearer "):
        token_val = authorization.replace("Bearer ", "")
        
    if not token_val:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token.")

    res = await db.execute(select(DisplayBoard).where(DisplayBoard.uuid_id == display_id))
    board = res.scalars().first()
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Display board not found."
        )
        
    authenticated = False
    if secrets.compare_digest(board.access_token, token_val):
        authenticated = True
    else:
        try:
            from jose import jwt, JWTError
            from app.core.config import settings
            from app.models.models import Operator
            
            payload = jwt.decode(token_val, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            subject: str = payload.get("sub", "")
            
            if subject.startswith("org:"):
                org_id = int(subject.split(":")[1])
                if org_id == board.organization_id:
                    authenticated = True
            elif subject.startswith("operator:"):
                operator_id = int(subject.split(":")[1])
                operator = await db.get(Operator, operator_id)
                if operator and operator.active and operator.organization_id == board.organization_id:
                    session_version = payload.get("session_version", 1)
                    if operator.session_version == session_version:
                        authenticated = True
        except (JWTError, ValueError, AttributeError):
            pass

    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.")

    # Fetch Organization Details
    org = await db.get(Organization, board.organization_id)
    org_name = org.name if org else "Unknown Organization"

    counter_state = None
    all_counters_state = None

    if board.board_type == "COUNTER":
        counter_result = await db.execute(select(Counter).where(Counter.id == board.counter_id))
        counter = counter_result.scalars().first()
        if counter:
            counter_state = await _get_counter_state(counter, db, redis_repo)
    else:
        # ORGANIZATION level display board: load states for all active counters
        counters_res = await db.execute(
            select(Counter).where(Counter.organization_id == board.organization_id, Counter.active == True)
        )
        counters = counters_res.scalars().all()
        all_counters_state = []
        for c in counters:
            all_counters_state.append(await _get_counter_state(c, db, redis_repo))

    # Fetch organization overall stats
    overall_waiting_count = 0
    overall_completed_today = 0
    if redis_repo.is_available:
        try:
            overall_waiting_count = await redis_repo.get_metric(board.organization_id, "waiting_count")
            overall_completed_today = await redis_repo.get_metric(board.organization_id, "completed_today")
        except Exception:
            pass

    if overall_waiting_count == 0 and overall_completed_today == 0:
        waiting_stmt = select(func.count(Token.id)).join(Counter).where(
            Counter.organization_id == board.organization_id, Token.status == "WAITING"
        )
        overall_waiting_count = (await db.execute(waiting_stmt)).scalar() or 0

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        completed_stmt = select(func.count(Token.id)).join(Counter).where(
            Counter.organization_id == board.organization_id,
            Token.status == "COMPLETED",
            Token.completed_at >= today_start
        )
        overall_completed_today = (await db.execute(completed_stmt)).scalar() or 0

    return DisplayBoardDetailsResponse(
        display_id=board.uuid_id,
        name=board.name,
        board_type=board.board_type,
        organization_id=board.organization_id,
        organization_name=org_name,
        counter_id=board.counter_id,
        counter_state=counter_state,
        all_counters_state=all_counters_state,
        overall_waiting_count=overall_waiting_count,
        overall_completed_today=overall_completed_today
    )


@router.get("/{counter_id:int}", response_model=DisplayBoardOut)
async def get_counter_display_board(
    counter_id: int,
    db: AsyncSession = Depends(get_db),
    redis_repo: RedisRepository = Depends(get_redis_repo)
):
    """Legacy public API returning display metadata for a specific counter integer ID (for backwards compatibility)."""
    counter_result = await db.execute(select(Counter).where(Counter.id == counter_id))
    counter = counter_result.scalars().first()
    if not counter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")

    state = await _get_counter_state(counter, db, redis_repo)

    return DisplayBoardOut(
        counter_id=state.counter_id,
        counter_name=state.counter_name,
        queue_type=state.queue_type,
        current_token=state.current_token,
        upcoming_tokens=state.upcoming_tokens,
        queue_length=state.queue_length,
        estimated_wait_minutes=state.estimated_wait_minutes
    )
