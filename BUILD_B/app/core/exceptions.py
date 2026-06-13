from fastapi import HTTPException, status


class QueueMindException(Exception):
    """Base exception for all QueueMind application errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundException(QueueMindException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class QueueEngineException(QueueMindException):
    """Exception raised during queue engine operations."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class AuthenticationException(QueueMindException):
    """Exception raised for authentication or authorization failures."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class RateLimitException(QueueMindException):
    """Exception raised when a user exceeds the allowed API requests/join limit."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class QueueException(QueueMindException):
    """Base exception for all queue-specific operational errors."""
    pass


class TokenNotFoundException(QueueException):
    def __init__(self, message: str = "Token not found."):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class CounterNotFoundException(QueueException):
    def __init__(self, message: str = "Counter not found."):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class DisplayBoardNotFoundException(QueueException):
    def __init__(self, message: str = "Display board not found."):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class InvalidEscalationException(QueueException):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class IdempotencyException(QueueException):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)
