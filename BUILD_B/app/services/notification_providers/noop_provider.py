import logging
from .base_provider import NotificationProvider

logger = logging.getLogger(__name__)

class NoOpProvider(NotificationProvider):
    async def send_message(self, phone: str, message: str) -> bool:
        logger.info(f"NoOpProvider [Mock sending] to {phone}: {message}")
        return True
