import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Operator, Counter, Organization
from app.core.security import get_password_hash, create_access_token

# Note: Tests assume an isolated testing environment with mocked Redis and DB fixtures.

@pytest.fixture
def admin_token(sample_org):
    return create_access_token(subject=f"org:{sample_org.id}")

@pytest.fixture
async def sample_org(db_session: AsyncSession):
    org = Organization(name="Test Org", email="admin@test.com", hashed_password="hashed")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org

@pytest.fixture
async def sample_counter(db_session: AsyncSession, sample_org):
    counter = Counter(organization_id=sample_org.id, name="Test Counter", queue_type="FIFO", qr_slug="test-counter")
    db_session.add(counter)
    await db_session.commit()
    await db_session.refresh(counter)
    return counter

@pytest.fixture
async def sample_operator(db_session: AsyncSession, sample_org, sample_counter):
    op = Operator(
        organization_id=sample_org.id,
        counter_id=sample_counter.id,
        name="Test Op",
        email="op@test.com",
        hashed_password=get_password_hash("password123"),
        active=True
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)
    return op

@pytest.mark.asyncio
async def test_failed_login_lockout(async_client: AsyncClient, sample_operator, db_session: AsyncSession):
    # Attempt 6 failed logins
    for _ in range(6):
        response = await async_client.post(
            "/api/v1/auth/operator/login",
            json={"email": "op@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    # 7th attempt with correct password should be rejected due to lockout
    response = await async_client.post(
        "/api/v1/auth/operator/login",
        json={"email": "op@test.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert "Too many failed login attempts" in response.json()["message"]

@pytest.mark.asyncio
async def test_disabled_operator_rejection(async_client: AsyncClient, sample_operator, db_session: AsyncSession):
    sample_operator.active = False
    await db_session.commit()
    
    response = await async_client.post(
        "/api/v1/auth/operator/login",
        json={"email": "op@test.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert "disabled" in response.json()["message"]

@pytest.mark.asyncio
async def test_session_version_invalidation(async_client: AsyncClient, sample_operator, db_session: AsyncSession):
    # Login to get token
    response = await async_client.post(
        "/api/v1/auth/operator/login",
        json={"email": "op@test.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Increment session version (simulate admin reset)
    sample_operator.session_version += 1
    await db_session.commit()
    
    # Attempt to use token for heartbeat
    response = await async_client.post(
        "/api/v1/operator/heartbeat",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert "Session expired" in response.json()["detail"]

@pytest.mark.asyncio
async def test_force_takeover_behavior(async_client: AsyncClient, sample_operator, db_session: AsyncSession, admin_token: str):
    # Operator logs in and gets session lock
    response = await async_client.post(
        "/api/v1/auth/operator/login",
        json={"email": "op@test.com", "password": "password123"}
    )
    op_token = response.json()["access_token"]
    
    # Admin forces takeover
    res = await async_client.post(
        f"/api/v1/admin/counters/{sample_operator.counter_id}/force-takeover",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    
    # Operator attempts heartbeat (should fail because lock is gone)
    res_hb = await async_client.post(
        "/api/v1/operator/heartbeat",
        headers={"Authorization": f"Bearer {op_token}"}
    )
    assert res_hb.status_code == 403
    assert "Session expired or lock lost" in res_hb.json()["detail"]
