import asyncio
from datetime import datetime, timezone
import pytest
import httpx
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.db.redis import get_redis
from app.repositories.redis_repo import RedisRepository
from app.core.event_bus import EventBus
from app.models.models import Organization, Counter, ServiceType, Operator, Token

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
                # Filter values
                if key in self.mock_redis.store:
                    now = float(max_val) if max_val != "inf" else datetime.now(timezone.utc).timestamp()
                    # SQLite rate limit filter mock: remove items older than 300
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
        # mapping is a dict: {element: score}
        self.store.setdefault(key, {})
        for elem, score in mapping.items():
            self.store[key][elem] = float(score)
        return len(mapping)

    async def zpopmin(self, key, count=1):
        if key not in self.store or not self.store[key]:
            return []
        # Sort elements by score ascending
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
        # Return elements only
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


# --- SQLite Testing DB setup ---

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

mock_redis_client = MockRedis()


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def override_get_redis():
    return mock_redis_client


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis


@pytest.fixture(autouse=True, scope="module")
def setup_test_db():
    """Create sqlite tables before running tests."""
    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())



def test_full_integration_workflow():
    client = TestClient(app)

    # 1. Register organization
    reg_response = client.post(
        "/api/v1/auth/register",
        json={"name": "Test Clinic", "email": "admin@testclinic.com", "password": "securepassword"}
    )
    assert reg_response.status_code == status.HTTP_201_CREATED
    assert reg_response.json()["name"] == "Test Clinic"

    # 2. Login organization
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@testclinic.com", "password": "securepassword"}
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create service type
    service_response = client.post(
        "/api/v1/services/",
        headers=headers,
        json={"name": "Standard Checkup", "estimated_duration_minutes": 15, "priority_weight": 20}
    )
    assert service_response.status_code == status.HTTP_201_CREATED
    service_id = service_response.json()["id"]

    # 4. Create counter (without qr_slug to test automated generation)
    counter_response = client.post(
        "/api/v1/counters/",
        headers=headers,
        json={"name": "General Counter A", "queue_type": "HYBRID"}
    )
    assert counter_response.status_code == status.HTTP_201_CREATED
    counter_data = counter_response.json()
    counter_id = counter_data["id"]
    qr_slug = counter_data["qr_slug"]
    
    # Assert pattern of generated qr_slug (4 letters, hyphen, 4 digits)
    import re
    assert re.match(r"^[a-zA-Z]{4}-\d{4}$", qr_slug) is not None

    # 5. Create operator
    operator_response = client.post(
        f"/api/v1/counters/{counter_id}/operators",
        headers=headers,
        json={"name": "Operator Jane", "email": "jane@testclinic.com", "password": "janepassword"}
    )
    assert operator_response.status_code == status.HTTP_201_CREATED
    assert operator_response.json()["name"] == "Operator Jane"

    # 6. Login operator
    op_login_response = client.post(
        "/api/v1/auth/operator/login",
        json={"email": "jane@testclinic.com", "password": "janepassword"}
    )
    assert op_login_response.status_code == status.HTTP_200_OK
    op_token = op_login_response.json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # 7. Customer scans QR code & gets public status
    status_response = client.get(f"/q/{qr_slug}")
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["counter_name"] == "General Counter A"

    # 8. Customer joins queue (checks concurrency-safe token generation format T-001)
    join_response1 = client.post(
        f"/q/{qr_slug}/join",
        json={"customer_name": "Alice Smith", "customer_phone": "+15550199", "service_type_id": service_id}
    )
    assert join_response1.status_code == status.HTTP_201_CREATED
    token_1 = join_response1.json()
    assert token_1["token_number"] == "T-001"
    assert token_1["status"] == "WAITING"

    # Join second customer (T-002)
    join_response2 = client.post(
        f"/q/{qr_slug}/join",
        json={"customer_name": "Bob Jones", "customer_phone": "+15550188", "service_type_id": service_id}
    )
    assert join_response2.status_code == status.HTTP_201_CREATED
    token_2 = join_response2.json()
    assert token_2["token_number"] == "T-002"

    # 9. Operator inspects queue
    queue_response = client.get("/api/v1/operator/current-queue", headers=op_headers)
    assert queue_response.status_code == status.HTTP_200_OK
    assert len(queue_response.json()) == 2
    assert queue_response.json()[0]["token_number"] == "T-001"

    # 10. Operator calls next customer
    call_response = client.post("/api/v1/operator/call-next", headers=op_headers)
    assert call_response.status_code == status.HTTP_200_OK
    assert call_response.json()["token_number"] == "T-001"
    assert call_response.json()["status"] == "IN_PROGRESS"

    # 11. Public page status check
    status_response = client.get(f"/q/{qr_slug}")
    assert status_response.json()["current_token"]["token_number"] == "T-001"
    assert status_response.json()["people_ahead"] == 1  # Bob is still waiting

    # 12. Operator completes Alice
    complete_response = client.post(f"/api/v1/operator/complete/{token_1['id']}", headers=op_headers)
    assert complete_response.status_code == status.HTTP_200_OK
    assert complete_response.json()["status"] == "COMPLETED"

    # 13. Operator calls next (Bob)
    call_response2 = client.post("/api/v1/operator/call-next", headers=op_headers)
    assert call_response2.json()["token_number"] == "T-002"

    # 14. Operator skips Bob
    skip_response = client.post(f"/api/v1/operator/skip/{token_2['id']}", headers=op_headers)
    assert skip_response.status_code == status.HTTP_200_OK
    assert skip_response.json()["status"] == "SKIPPED"

    # 15. Admin reads analytics summary
    analytics_response = client.get("/api/v1/analytics/summary", headers=headers)
    assert analytics_response.status_code == status.HTTP_200_OK
    analytics_data = analytics_response.json()
    # Check drop-off rate tracking: skipped/total = 1/2 = 50%
    assert analytics_data["drop_off_rate"] == 0.5
    assert analytics_data["overall"]["dropped_tokens"] == 1
    assert analytics_data["overall"]["total_tokens"] == 2
