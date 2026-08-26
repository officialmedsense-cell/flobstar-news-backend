"""
Application configuration using Pydantic Settings
Environment-based configuration for different environments
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Flobstar News Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Supabase (Database)
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_DB_HOST: Optional[str] = None
    SUPABASE_DB_PORT: Optional[int] = 5432
    SUPABASE_DB_NAME: Optional[str] = "postgres"
    SUPABASE_DB_USER: Optional[str] = "postgres"
    SUPABASE_DB_PASSWORD: Optional[str] = None
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = "FJovoIU58hXLNnW4zJUz1a0HqUnUegnc"
    MISTRAL_API_KEY_FALLBACK: Optional[str] = "llZIFBtjBsgeIHliEygwbOOCUVKqXVO7"
    AI_MODEL: str = "gpt-4-turbo-preview"
    
    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    RESEND_SENDER_EMAIL: str = "onboarding@resend.dev"
    RESEND_SENDER_NAME: str = "Flobstar News"
    
    # Telegram (optional)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Slack (optional)
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Processing settings
    RSS_POLLING_INTERVAL_MINUTES: int = 15
    MAX_CONCURRENT_SOURCE_CHECKS: int = 10
    STORY_PROCESSING_TIMEOUT_SECONDS: int = 300
    
    # Frontend URL (for CORS and callbacks)
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def database_url(self) -> Optional[str]:
        """Construct async PostgreSQL database URL if direct credentials exist"""
        if self.SUPABASE_DB_PASSWORD and self.SUPABASE_DB_HOST:
            return f"postgresql+asyncpg://{self.SUPABASE_DB_USER}:{self.SUPABASE_DB_PASSWORD}@{self.SUPABASE_DB_HOST}:{self.SUPABASE_DB_PORT}/{self.SUPABASE_DB_NAME}"
        return None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
