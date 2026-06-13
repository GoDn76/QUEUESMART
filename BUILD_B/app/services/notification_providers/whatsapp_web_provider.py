import logging
import httpx
from app.services.notification_providers.base_provider import NotificationProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppWebProvider(NotificationProvider):
    async def send_message(self, phone: str, message: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.WHATSAPP_WEB_URL}/send",
                    json={"phone": phone, "message": message},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("success", False)
        except httpx.HTTPError as e:
            logger.warning("NOTIFICATION_SEND_FAILED", extra={"provider": "whatsapp_web", "phone": phone, "error": str(e)})
            return False
        except Exception as e:
            logger.warning("NOTIFICATION_SEND_FAILED", extra={"provider": "whatsapp_web", "phone": phone, "error": str(e)})
            return False
