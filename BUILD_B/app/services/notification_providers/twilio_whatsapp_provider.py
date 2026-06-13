import logging
import aiohttp
from app.services.notification_providers.base_provider import NotificationProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class TwilioWhatsAppProvider(NotificationProvider):
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM

    async def send_message(self, phone: str, message: str) -> bool:
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio WhatsApp credentials missing. Skipping WhatsApp.")
            return False

        # Twilio WhatsApp numbers must start with "whatsapp:"
        to_phone = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
        data = {
            "To": to_phone,
            "From": self.from_number,
            "Body": message
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, auth=auth, data=data) as response:
                    if response.status in (200, 201):
                        logger.info(f"Twilio WhatsApp sent to {phone}")
                        return True
                    else:
                        resp_text = await response.text()
                        logger.error(f"Failed to send Twilio WhatsApp to {phone}. Status: {response.status}, Error: {resp_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending Twilio WhatsApp: {e}")
            return False
