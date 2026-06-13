import pytest
from app.services.notification_providers.base_provider import NotificationProvider
from app.services.notification_providers.noop_provider import NoOpProvider
from app.services.notification_providers.whatsapp_web_provider import WhatsAppWebProvider
from app.services.notification_providers.meta_whatsapp_provider import MetaCloudWhatsAppProvider
from app.services.notification_providers.twilio_whatsapp_provider import TwilioWhatsAppProvider

def check_implements_interface(provider_cls):
    """Verify that a provider class implements NotificationProvider interface correctly."""
    assert issubclass(provider_cls, NotificationProvider)
    # Check that it has an async send_message method
    import inspect
    assert hasattr(provider_cls, 'send_message')
    assert inspect.iscoroutinefunction(provider_cls.send_message)

def test_noop_provider_interface():
    check_implements_interface(NoOpProvider)

def test_whatsapp_web_provider_interface():
    check_implements_interface(WhatsAppWebProvider)

def test_meta_whatsapp_provider_interface():
    check_implements_interface(MetaCloudWhatsAppProvider)

def test_twilio_whatsapp_provider_interface():
    check_implements_interface(TwilioWhatsAppProvider)

@pytest.mark.asyncio
async def test_noop_provider_returns_true():
    provider = NoOpProvider()
    result = await provider.send_message("+1234567890", "Test")
    assert result is True

@pytest.mark.asyncio
async def test_whatsapp_web_handles_failure(mocker):
    # Mock httpx to throw an exception and verify it returns False, not raising it
    provider = WhatsAppWebProvider()
    mocker.patch('httpx.AsyncClient.post', side_effect=Exception("Connection refused"))
    
    result = await provider.send_message("+1234567890", "Test")
    assert result is False
