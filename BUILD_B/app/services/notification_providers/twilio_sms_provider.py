import os
import logging
import aiohttp
from .base_provider import NotificationProvider

logger = logging.getLogger(__name__)

class TwilioSMSProvider(NotificationProvider):
    def __init__(self):
        from app.core.config import settings
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER

    async def send_message(self, phone: str, message: str) -> bool:
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio SMS credentials missing. Skipping SMS.")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
        data = {
            "To": phone,
            "From": self.from_number,
            "Body": message
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, auth=auth, data=data) as response:
                    if response.status in (200, 201):
                        logger.info(f"Twilio SMS sent to {phone}")
                        return True
                    else:
                        resp_text = await response.text()
                        logger.error(f"Failed to send Twilio SMS to {phone}. Status: {response.status}, Error: {resp_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {e}")
            return False
