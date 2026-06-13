import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import Token, QueueEvent
from app.services.notification_providers.base_provider import NotificationProvider
from app.services.notification_providers.noop_provider import NoOpProvider
from app.services.notification_providers.twilio_sms_provider import TwilioSMSProvider
from app.services.notification_providers.twilio_whatsapp_provider import TwilioWhatsAppProvider
from app.services.notification_providers.whatsapp_web_provider import WhatsAppWebProvider
from app.services.notification_providers.meta_whatsapp_provider import MetaCloudWhatsAppProvider
from app.repositories.redis_repo import RedisRepository
from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, db: AsyncSession, redis_repo: RedisRepository):
        self.db = db
        self.redis_repo = redis_repo
        self.provider = self._get_provider()

    def _get_provider(self) -> NotificationProvider:
        provider_name = settings.NOTIFICATION_PROVIDER.lower()
        if provider_name == "whatsapp_web":
            return WhatsAppWebProvider()
        elif provider_name == "twilio":
            return TwilioWhatsAppProvider()  # Or whatever Twilio wrapper they want
        elif provider_name == "meta":
            return MetaCloudWhatsAppProvider()
        else:
            return NoOpProvider()

    async def send(self, phone: str, message: str) -> bool:
        """Generic send method for testing and ad-hoc messages."""
        try:
            return await self.provider.send_message(phone, message)
        except Exception as e:
            logger.warning(
                "NOTIFICATION_SEND_FAILED",
                extra={
                    "provider": settings.NOTIFICATION_PROVIDER,
                    "phone": phone,
                    "error": str(e)
                }
            )
            return False

    async def notify_token_near(self, token_id: int, counter_id: int) -> None:
        """Sends TOKEN_NEAR notification exactly once."""
        if self.redis_repo.is_available:
            redis_client = self.redis_repo.redis
            already_sent = await redis_client.setnx(f"near_notification_sent:{token_id}", "1")
            if not already_sent:
                return
            await redis_client.expire(f"near_notification_sent:{token_id}", 86400)

        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token:
            return

        message = f"QueueMind Alert\n\nToken {token.token_number} is only 2 positions away.\n\nPlease proceed towards the counter."
        
        try:
            sent = await self.provider.send_message(token.customer_phone, message)
            if sent:
                logger.info(json.dumps({"event_type": "NOTIFICATION_SENT", "token_id": token.id, "phone": token.customer_phone, "provider": settings.NOTIFICATION_PROVIDER}))
            else:
                logger.warning(json.dumps({"event_type": "NOTIFICATION_FAILED", "token_id": token.id, "provider": settings.NOTIFICATION_PROVIDER}))
        except Exception as e:
            logger.warning(json.dumps({"event_type": "NOTIFICATION_FAILED", "token_id": token.id, "error": str(e), "provider": settings.NOTIFICATION_PROVIDER}))
            sent = False
            
        if sent:
            event = QueueEvent(
                token_id=token.id,
                event_type="NOTIFICATION_SENT",
                event_data={"type": "TOKEN_NEAR", "provider": settings.NOTIFICATION_PROVIDER}
            )
            self.db.add(event)
            await self.db.commit()

    async def notify_your_turn(self, token_id: int, counter_name: str) -> None:
        """Sends YOUR_TURN notification exactly once."""
        if self.redis_repo.is_available:
            redis_client = self.redis_repo.redis
            already_sent = await redis_client.setnx(f"your_turn_notification_sent:{token_id}", "1")
            if not already_sent:
                return
            await redis_client.expire(f"your_turn_notification_sent:{token_id}", 86400)

        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token:
            return

        message = f"QueueMind Alert\n\nToken {token.token_number} is now being served.\n\nPlease proceed immediately to Counter {counter_name}."
        
        try:
            sent = await self.provider.send_message(token.customer_phone, message)
            if sent:
                logger.info(json.dumps({"event_type": "NOTIFICATION_SENT", "token_id": token.id, "phone": token.customer_phone, "provider": settings.NOTIFICATION_PROVIDER}))
            else:
                logger.warning(json.dumps({"event_type": "NOTIFICATION_FAILED", "token_id": token.id, "provider": settings.NOTIFICATION_PROVIDER}))
        except Exception as e:
            logger.warning(json.dumps({"event_type": "NOTIFICATION_FAILED", "token_id": token.id, "error": str(e), "provider": settings.NOTIFICATION_PROVIDER}))
            sent = False

        if sent:
            event = QueueEvent(
                token_id=token.id,
                event_type="NOTIFICATION_SENT",
                event_data={"type": "YOUR_TURN", "provider": settings.NOTIFICATION_PROVIDER}
            )
            self.db.add(event)
            await self.db.commit()

    async def notify_token_escalated(self, token_id: int) -> None:
        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token: return
        message = f"QueueMind Alert\n\nYour token {token.token_number} has been escalated."
        await self.send(token.customer_phone, message)

    async def notify_counter_migration_approved(self, token_id: int, counter_name: str) -> None:
        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token: return
        message = f"QueueMind Alert\n\nYour token {token.token_number} was migrated to Counter {counter_name}."
        await self.send(token.customer_phone, message)

    async def notify_queue_paused(self, token_id: int) -> None:
        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token: return
        message = f"QueueMind Alert\n\nThe queue is temporarily paused."
        await self.send(token.customer_phone, message)

    async def notify_queue_resumed(self, token_id: int) -> None:
        token = (await self.db.execute(select(Token).where(Token.id == token_id))).scalars().first()
        if not token: return
        message = f"QueueMind Alert\n\nThe queue has resumed."
        await self.send(token.customer_phone, message)
