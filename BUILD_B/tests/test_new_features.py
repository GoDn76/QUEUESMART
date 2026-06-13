import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
import uuid
import secrets

from app.models.models import Token, Counter, DisplayBoard, Operator, Organization
from app.services.queue_engine import QueueEngine
from app.core.exceptions import IdempotencyException
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_health_endpoint_response(client: AsyncClient):
    """Test health endpoint returns timestamp and overall status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "timestamp" in data
    assert "version" in data

@pytest.mark.asyncio
async def test_display_board_state_validation(client: AsyncClient, db_session, test_organization, test_counter):
    """Test that GET /display/{id}/state enforces token matching."""
    board_uuid = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    board = DisplayBoard(
        uuid_id=board_uuid,
        organization_id=test_organization.id,
        counter_id=test_counter.id,
        name="Test Board",
        board_type="COUNTER",
        access_token=token
    )
    db_session.add(board)
    await db_session.commit()

    # Request without token
    resp = await client.get(f"/api/v1/display/{board_uuid}/state")
    assert resp.status_code == 401

    # Request with invalid token
    resp = await client.get(f"/api/v1/display/{board_uuid}/state?access_token=invalid")
    assert resp.status_code == 401

    # Request with valid token
    resp = await client.get(f"/api/v1/display/{board_uuid}/state?access_token={token}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Board"

@pytest.mark.asyncio
async def test_idempotency_call_next(db_session, mock_redis_repo, mock_event_bus, test_counter, test_service_type):
    """Test that double-calling call_next raises IdempotencyException."""
    engine = QueueEngine(db_session, mock_redis_repo, mock_event_bus)

    # Join queue twice
    t1 = await engine.join_queue(test_counter.qr_slug, "Bob", "123", test_service_type.id)
    t2 = await engine.join_queue(test_counter.qr_slug, "Alice", "456", test_service_type.id)

    # Call first
    called_t1 = await engine.call_next(test_counter.id, 1)
    assert called_t1.status == "IN_PROGRESS"

    # Call second without completing first should raise error
    with pytest.raises(IdempotencyException, match="already in progress"):
        await engine.call_next(test_counter.id, 1)
        
    # Complete first
    await engine.complete_token(called_t1.id, 1)
    
    # Call second succeeds
    called_t2 = await engine.call_next(test_counter.id, 1)
    assert called_t2.status == "IN_PROGRESS"

@pytest.mark.asyncio
async def test_idempotency_complete_token(db_session, mock_redis_repo, mock_event_bus, test_counter, test_service_type):
    """Test that double-completing raises IdempotencyException."""
    engine = QueueEngine(db_session, mock_redis_repo, mock_event_bus)

    t1 = await engine.join_queue(test_counter.qr_slug, "Charlie", "789", test_service_type.id)
    called = await engine.call_next(test_counter.id, 1)
    
    await engine.complete_token(called.id, 1)
    
    # Complete again should raise error
    with pytest.raises(IdempotencyException, match="currently in progress to mark as completed"):
        await engine.complete_token(called.id, 1)


@pytest.mark.asyncio
async def test_automated_qr_slug_generation(client, test_organization):
    """Test that creating a counter without a qr_slug generates a conforming unique slug, and returns it."""
    # 1. Login organization to get authorization headers
    admin_token = create_access_token(subject=f"org:{test_organization.id}")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create counter without qr_slug
    resp1 = await client.post(
        "/api/v1/counters/",
        headers=headers,
        json={"name": "Auto Slug Counter 1", "queue_type": "FIFO"}
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert "qr_slug" in data1
    slug1 = data1["qr_slug"]
    
    # Verify xxxx-yyyy pattern
    import re
    assert re.match(r"^[a-zA-Z]{4}-\d{4}$", slug1) is not None

    # 3. Create another counter to verify uniqueness and pattern conformity
    resp2 = await client.post(
        "/api/v1/counters/",
        headers=headers,
        json={"name": "Auto Slug Counter 2", "queue_type": "FIFO"}
    )
    assert resp2.status_code == 201
    data2 = resp2.json()
    slug2 = data2["qr_slug"]
    assert re.match(r"^[a-zA-Z]{4}-\d{4}$", slug2) is not None
    assert slug1 != slug2

    # 4. Attempt to create a counter with a duplicate slug (should fail)
    resp3 = await client.post(
        "/api/v1/counters/",
        headers=headers,
        json={"name": "Auto Slug Counter 3", "queue_type": "FIFO", "qr_slug": slug1}
    )
    assert resp3.status_code == 400


@pytest.mark.asyncio
async def test_display_board_alternative_auth(client, db_session, test_organization, test_counter):
    """Test that display board state endpoint accepts board access_token, admin JWT, and operator JWT from the same organization."""
    # 1. Setup Display Board
    board_uuid = str(uuid.uuid4())
    board_token = secrets.token_urlsafe(32)
    board = DisplayBoard(
        uuid_id=board_uuid,
        organization_id=test_organization.id,
        counter_id=test_counter.id,
        name="Auth Test Board",
        board_type="COUNTER",
        access_token=board_token
    )
    db_session.add(board)
    
    # 2. Setup an Operator in the same organization
    operator = Operator(
        organization_id=test_organization.id,
        counter_id=test_counter.id,
        name="Display Operator",
        email="display_op@hospital.com",
        hashed_password="hashed_password",
        active=True
    )
    db_session.add(operator)
    await db_session.commit()
    await db_session.refresh(operator)

    # 3. Create tokens for testing
    board_access_header = {"Authorization": f"Bearer {board_token}"}
    
    admin_token = create_access_token(subject=f"org:{test_organization.id}")
    admin_header = {"Authorization": f"Bearer {admin_token}"}
    
    op_token = create_access_token(
        subject=f"operator:{operator.id}",
        custom_claims={"session_version": operator.session_version, "session_id": "some_session"}
    )
    op_header = {"Authorization": f"Bearer {op_token}"}

    # 4. Verify access with Display Board access_token
    resp = await client.get(f"/api/v1/display/{board_uuid}/state", headers=board_access_header)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Auth Test Board"

    # 5. Verify access with Admin Bearer token
    resp = await client.get(f"/api/v1/display/{board_uuid}/state", headers=admin_header)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Auth Test Board"

    # 6. Verify access with Operator Bearer token
    resp = await client.get(f"/api/v1/display/{board_uuid}/state", headers=op_header)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Auth Test Board"

    # 7. Verify access with different organization's Admin token (should fail)
    other_org = Organization(name="Other Hospital", email="other_admin@hospital.com", hashed_password="hashed")
    db_session.add(other_org)
    await db_session.commit()
    await db_session.refresh(other_org)
    
    other_admin_token = create_access_token(subject=f"org:{other_org.id}")
    other_admin_header = {"Authorization": f"Bearer {other_admin_token}"}
    
    resp = await client.get(f"/api/v1/display/{board_uuid}/state", headers=other_admin_header)
    assert resp.status_code == 401
