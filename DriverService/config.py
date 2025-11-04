"""
Centralized configuration management for DriverService
Using pydantic-settings for environment variable validation
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    service_name: str = "driverservice"
    service_version: str = "1.0.0"

    # Security
    secret_key: str
    algorithm: str = "HS256"

    # Database (CosmosDB / MongoDB)
    cosmos_connection_string: str
    cosmos_db_name: str = "drivers_db"

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

    def validate_required_settings(self) -> None:
        """Validate that all critical settings are present"""
        if not self.secret_key:
            raise ValueError("SECRET_KEY must be set")
        if not self.cosmos_connection_string:
            raise ValueError("COSMOS_CONNECTION_STRING must be set")


# Global settings instance
settings = Settings()

# Validate on import
settings.validate_required_settings()
