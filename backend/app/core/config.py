"""
Application configuration management using Pydantic settings.
"""
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "AI Business Copilot"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False

    # Anthropic Claude
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    MAX_TOKENS: int = 4096

    # Microsoft Entra ID
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_TENANT_ID: str
    AZURE_REDIRECT_URI: str

    # Dropbox
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    DROPBOX_REFRESH_TOKEN: str

    # Xero
    XERO_CLIENT_ID: str
    XERO_CLIENT_SECRET: str
    XERO_TENANT_ID: str
    XERO_REFRESH_TOKEN: str

    # Unleashed
    UNLEASHED_API_ID: str
    UNLEASHED_API_KEY: str

    # HubSpot
    HUBSPOT_ACCESS_TOKEN: str
    HUBSPOT_PORTAL_ID: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    CORS_ORIGINS: str = "http://localhost:3000"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Indexing
    INDEX_BATCH_SIZE: int = 100
    INDEX_SCHEDULE_CRON: str = "0 2 * * 0"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in v.split(",")]

    @property
    def database_url_async(self) -> str:
        """Convert sync postgresql URL to async postgresql+asyncpg."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


# Global settings instance
settings = Settings()
