"""
Centralized configuration management for UserService
Using pydantic-settings for environment variable validation
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    service_name: str = "userservice"
    service_version: str = "1.0.0"

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    # Database (PostgreSQL)
    postgres_host: str
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: str
    postgres_db: str = "uitgo_users"

    # Service credentials (for service-to-service auth)
    tripsvc_client_id: Optional[str] = None
    tripsvc_client_secret: Optional[str] = None

    # Server config
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def validate_required_settings(self) -> None:
        """Validate that all critical settings are present"""
        if not self.secret_key:
            raise ValueError("SECRET_KEY must be set")
        if not self.postgres_host:
            raise ValueError("POSTGRES_HOST must be set")
        if not self.postgres_user:
            raise ValueError("POSTGRES_USER must be set")
        if not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD (DB_PASSWORD) must be set")


# Global settings instance
settings = Settings()

# Validate on import
settings.validate_required_settings()
