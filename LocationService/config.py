"""
Centralized configuration management for LocationService
Using pydantic-settings for environment variable validation
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    service_name: str = "locationservice"
    service_version: str = "1.0.0"

    # Database (Redis)
    redis_host: str
    redis_port: int = 6380  # Azure Redis default port
    redis_password: str = ""  # Optional for local dev
    redis_ssl: bool = True  # Azure Redis requires SSL

    # Server config
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Logging
    log_level: str = "INFO"

    # Location settings
    driver_location_ttl: int = 300  # 5 minutes
    default_search_radius_km: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        protocol = "rediss" if self.redis_ssl else "redis"
        if self.redis_password:
            return f"{protocol}://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"{protocol}://{self.redis_host}:{self.redis_port}"

    def validate_required_settings(self) -> None:
        """Validate that all critical settings are present"""
        if not self.redis_host:
            raise ValueError("REDIS_HOST must be set")


# Global settings instance
settings = Settings()

# Validate on import
settings.validate_required_settings()
