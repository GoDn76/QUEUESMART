from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "QueueMind"
    
    # Database Configuration
    # Fallback to local sqlite or default docker postgres string for local testing if not set
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/queuemind"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security Configurations
    SECRET_KEY: str = "38b97dc3f8c5c7774e1d70d24f0c7de7649d012463e26c62489c628ebfe6a655"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Application Config
    QUEUE_NEAR_THRESHOLD: int = 2
    
    # Twilio Notification Config
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    
    # Notification Providers
    NOTIFICATION_PROVIDER: str = "whatsapp_web"
    WHATSAPP_WEB_URL: str = "http://localhost:3001"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        # Automatically rewrite host-published port 5433 to internal container port 5432 inside docker network
        if "@db:5433" in self.DATABASE_URL:
            self.DATABASE_URL = self.DATABASE_URL.replace("@db:5433", "@db:5432")


settings = Settings()
