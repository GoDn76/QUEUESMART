import abc

class NotificationProvider(abc.ABC):
    @abc.abstractmethod
    async def send_message(self, phone: str, message: str) -> bool:
        """Sends a message to the provided phone number."""
        pass
