import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone
import json
import time

from app.main import app
from app.db.session import Base, get_db
from app.db.redis import get_redis
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus
from app.models.models import Organization, Counter, ServiceType, Operator, DisplayBoard
from app.core.security import create_access_token, get_password_hash

# --- Mock Redis Implementation for Testing ---

class MockRedisPipeline:
    def __init__(self, mock_redis):
        self.mock_redis = mock_redis
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def zremrangebyscore(self, key, min_val, max_val):
        self.commands.append(("zremrange", key, min_val, max_val))
        return self

    def zcard(self, key):
        self.commands.append(("zcard", key))
        return self

    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))
        return self

    def expire(self, key, time_val):
        self.commands.append(("expire", key, time_val))
        return self

    async def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == "zremrange":
                key, min_val, max_val = cmd[1], cmd[2], cmd[3]
                if key in self.mock_redis.store:
                    now = float(max_val) if max_val != "inf" else datetime.now(timezone.utc).timestamp()
                    self.mock_redis.store[key] = {k: v for k, v in self.mock_redis.store[key].items() if v >= now}
                results.append(0)
            elif cmd[0] == "zcard":
                key = cmd[1]
                count = len(self.mock_redis.store.get(key, {}))
                results.append(count)
            elif cmd[0] == "zadd":
                key, mapping = cmd[1], cmd[2]
                self.mock_redis.store.setdefault(key, {}).update(mapping)
                results.append(len(mapping))
            elif cmd[0] == "expire":
                results.append(True)
        return results


class MockRedis:
    def __init__(self):
        self.store = {}
        self.pubsub_messages = []

    async def ping(self):
        return True

    async def zadd(self, key, mapping):
        self.store.setdefault(key, {})
        for elem, score in mapping.items():
            self.store[key][elem] = float(score)
        return len(mapping)

    async def zpopmin(self, key, count=1):
        if key not in self.store or not self.store[key]:
            return []
        sorted_items = sorted(self.store[key].items(), key=lambda x: x[1])
        popped = sorted_items[:count]
        for elem, _ in popped:
            del self.store[key][elem]
        return popped

    async def zrem(self, key, member):
        if key in self.store and member in self.store[key]:
            del self.store[key][member]
            return 1
        return 0

    async def zrange(self, key, start, stop):
        if key not in self.store or not self.store[key]:
            return []
        sorted_items = sorted(self.store[key].items(), key=lambda x: x[1])
        elems = [item[0] for item in sorted_items]
        if stop == -1:
            return elems[start:]
        return elems[start:stop + 1]

    async def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        if nx and key in self.store:
            return None
        if xx and key not in self.store:
            return None
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    async def incrby(self, key, amount):
        val = int(self.store.get(key, 0))
        val += amount
        self.store[key] = str(val)
        return val

    async def decrby(self, key, amount):
        val = int(self.store.get(key, 0))
        val -= amount
        self.store[key] = str(val)
        return val

    async def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    async def publish(self, channel, message):
        self.pubsub_messages.append((channel, message))
        return 1

    def pipeline(self, transaction=True):
        return MockRedisPipeline(self)

    async def close(self):
        pass


class MockEventBus(EventBus):
    async def publish(self, channel: str, message: dict) -> None:
        pass

    async def subscribe(self, channel_pattern: str, handler) -> None:
        pass


# --- Pytest fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def db_engine():
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine

@pytest.fixture(autouse=True)
def setup_db_tables(db_engine):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def create_tables():
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables():
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    loop.run_until_complete(create_tables())
    yield
    loop.run_until_complete(drop_tables())

@pytest.fixture
async def db_session(db_engine):
    TestingSessionLocal = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@pytest.fixture
def mock_redis_client():
    return MockRedis()

@pytest.fixture
def mock_redis_repo(mock_redis_client):
    return RedisRepository(redis_client=mock_redis_client)

@pytest.fixture
def mock_event_bus():
    return MockEventBus()

@pytest.fixture
async def client(db_session, mock_redis_client):
    """Async Client fixture for test endpoints."""
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return mock_redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(client):
    """Alias for client to match test_operator_auth requirements."""
    yield client

@pytest.fixture
async def test_organization(db_session: AsyncSession):
    org = Organization(
        name="Test Hospital",
        email="test_admin@hospital.com",
        hashed_password=get_password_hash("password123")
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org

@pytest.fixture
async def test_counter(db_session: AsyncSession, test_organization):
    counter = Counter(
        organization_id=test_organization.id,
        name="Test counter",
        queue_type="FIFO",
        qr_slug="test-counter-slug",
        active=True
    )
    db_session.add(counter)
    await db_session.commit()
    await db_session.refresh(counter)
    return counter

@pytest.fixture
async def test_service_type(db_session: AsyncSession, test_organization):
    service = ServiceType(
        organization_id=test_organization.id,
        name="Consultation",
        estimated_duration_minutes=15,
        priority_weight=20
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service

@pytest.fixture
def admin_token(test_organization):
    return create_access_token(subject=f"org:{test_organization.id}")
