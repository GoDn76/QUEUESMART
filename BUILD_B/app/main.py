import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.init_db import init_db
from app.db.redis import redis_manager, get_redis
from app.core.event_bus import RedisEventBus
from app.core.websocket_manager import websocket_manager
from app.core.exceptions import QueueMindException, QueueException

# API Routers
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.counters import router as counters_router
from app.api.v1.routes.services import router as services_router
from app.api.v1.routes.operator import router as operator_router
from app.api.v1.routes.display import router as display_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.public import router as public_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.migrations import router as migrations_router
from app.api.v1.routes.predictions import router as predictions_router

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for setup and cleanup hooks."""
    # 1. Initialize PostgreSQL tables and seed sample data
    try:
        await init_db()
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
        raise e

    # 2. Setup Redis Connection
    await redis_manager.connect()

    # 3. Initialize Redis EventBus and bind WS broadcast listener
    redis_client = await get_redis()
    if redis_client:
        event_bus = RedisEventBus(redis_client=redis_client)
        # Binds background listeners for pattern matching routes
        await websocket_manager.start_event_bus_subscriptions(event_bus)
    else:
        logger.warning("Redis client is not available. Real-time WebSocket subscriptions will run in process-local room mode only.")

    # 4. Run Redis Recovery Service
    from app.services.redis_recovery import RedisRecoveryService
    from app.db.session import async_session_maker
    from app.repositories.redis_repo import RedisRepository
    async with async_session_maker() as db_session:
        redis_repo = RedisRepository(redis_client=redis_client)
        recovery_service = RedisRecoveryService(db=db_session, redis_repo=redis_repo)
        await recovery_service.rebuild_cache()

    yield

    # 4. Cleanup Redis Pool
    await redis_manager.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QueueMind Production-Grade QR-based Smart Queue Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development and API integration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers for custom exceptions
@app.exception_handler(QueueMindException)
@app.exception_handler(QueueException)
async def queue_exception_handler(request, exc: Exception):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=getattr(exc, "status_code", 400),
        content={"error": exc.__class__.__name__, "message": getattr(exc, "message", str(exc))}
    )

# REST API Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin Operations"])
app.include_router(counters_router, prefix="/api/v1/counters", tags=["Counters"])
app.include_router(services_router, prefix="/api/v1/services", tags=["Service Types"])
app.include_router(operator_router, prefix="/api/v1/operator", tags=["Operator Dashboard"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics Summary"])
app.include_router(display_router, prefix="/api/v1/display", tags=["Display Boards"])
app.include_router(health_router, prefix="/health", tags=["Health Check"])
app.include_router(public_router, prefix="/q", tags=["Public Queue Flow"])
app.include_router(migrations_router, prefix="/api/v1/migrations", tags=["Migrations"])
app.include_router(predictions_router, prefix="/api/v1/predictions", tags=["Predictions"])


@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "documentation": "/docs"
    }


# --- WebSocket Room Endpoints ---

@app.websocket("/ws/counter/{counter_id}")
async def websocket_counter(websocket: WebSocket, counter_id: int):
    """WebSocket room for operator dash status messages."""
    await websocket_manager.connect_counter(counter_id, websocket)
    try:
        while True:
            # Keep connection open and listen for any messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect_counter(counter_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error on counter room {counter_id}: {e}")
        websocket_manager.disconnect_counter(counter_id, websocket)


@app.websocket("/ws/display/{counter_id}")
async def websocket_display(websocket: WebSocket, counter_id: int):
    """WebSocket room for public display boards updates."""
    await websocket_manager.connect_display(counter_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect_display(counter_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error on display room {counter_id}: {e}")
        websocket_manager.disconnect_display(counter_id, websocket)


@app.websocket("/ws/organization/{organization_id}")
async def websocket_organization(websocket: WebSocket, organization_id: int):
    """WebSocket room for organization live metrics dashboard updates."""
    await websocket_manager.connect_organization(organization_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect_organization(organization_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error on organization room {organization_id}: {e}")
        websocket_manager.disconnect_organization(organization_id, websocket)


@app.websocket("/ws/user/{token_id}")
async def websocket_user(websocket: WebSocket, token_id: int):
    """WebSocket room for targeted user notifications (e.g. YOUR_TURN, queue position shifts)."""
    await websocket_manager.connect_user(token_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect_user(token_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error on user room {token_id}: {e}")
        websocket_manager.disconnect_user(token_id, websocket)
