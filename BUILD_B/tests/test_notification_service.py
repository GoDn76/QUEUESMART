import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.notification_service import NotificationService
from app.models.models import Token

@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Setup mock execute to return a mock token
    mock_result = MagicMock()
    mock_token = Token(
        id=1,
        token_number="T-001",
        customer_phone="+1234567890",
    )
    mock_result.scalars.return_value.first.return_value = mock_token
    db.execute.return_value = mock_result
    return db

@pytest.fixture
def mock_redis():
    repo = MagicMock()
    repo.is_available = True
    repo.redis = AsyncMock()
    repo.redis.setnx.return_value = True # Default to allow sending
    return repo

@pytest.mark.asyncio
async def test_notify_token_near_deduplication(mock_db, mock_redis):
    # Setup redis to reject (already sent)
    mock_redis.redis.setnx.return_value = False
    
    service = NotificationService(mock_db, mock_redis)
    service.sms_provider.send_message = AsyncMock()
    service.whatsapp_provider.send_message = AsyncMock()
    
    await service.notify_token_near(1, 1)
    
    mock_redis.redis.setnx.assert_called_once_with("near_notification_sent:1", "1")
    service.sms_provider.send_message.assert_not_called()
    service.whatsapp_provider.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_notify_token_near_sends_messages(mock_db, mock_redis):
    service = NotificationService(mock_db, mock_redis)
    service.sms_provider.send_message = AsyncMock(return_value=True)
    service.whatsapp_provider.send_message = AsyncMock(return_value=True)
    
    await service.notify_token_near(1, 1)
    
    service.sms_provider.send_message.assert_called_once()
    service.whatsapp_provider.send_message.assert_called_once()
    mock_db.add.assert_called_once() # QueueEvent
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_notify_token_near_exception_handling(mock_db, mock_redis):
    """Test that provider failures don't propagate to the caller."""
    service = NotificationService(mock_db, mock_redis)
    service.sms_provider.send_message = AsyncMock(side_effect=Exception("Twilio is down"))
    service.whatsapp_provider.send_message = AsyncMock(side_effect=Exception("Twilio is down"))
    
    # Should not raise exception
    await service.notify_token_near(1, 1)
    
    # DB add/commit should NOT be called since both failed
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_notify_your_turn_exception_handling(mock_db, mock_redis):
    """Test that provider failures don't propagate to the caller."""
    service = NotificationService(mock_db, mock_redis)
    service.sms_provider.send_message = AsyncMock(side_effect=Exception("Twilio is down"))
    service.whatsapp_provider.send_message = AsyncMock(side_effect=Exception("Twilio is down"))
    
    # Should not raise exception
    await service.notify_your_turn(1, "Counter 1")
    
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
