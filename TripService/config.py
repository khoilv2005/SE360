"""
Centralized configuration management for TripService
Using pydantic-settings for environment variable validation
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    service_name: str = "tripservice"
    service_version: str = "1.0.0"

    # Database (CosmosDB / MongoDB)
    cosmos_connection_string: str
    cosmos_db_name: str = "trips_db"

    # External Services
    mapbox_access_token: str
    user_service_base_url: str = "http://userservice:8000"
    driver_service_base_url: str = "http://driverservice:8000"
    payment_service_base_url: str = "http://paymentservice:8000"
    location_service_base_url: str = "http://locationservice:8000"

    # Service-to-service authentication
    tripsvc_client_id: Optional[str] = None
    tripsvc_client_secret: Optional[str] = None

    # Server config
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Logging
    log_level: str = "INFO"

    # Timeouts (seconds)
    external_service_timeout: int = 20
    mapbox_timeout: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def validate_required_settings(self) -> None:
        """Validate that all critical settings are present"""
        if not self.cosmos_connection_string:
            raise ValueError("COSMOS_CONNECTION_STRING must be set")
        if not self.mapbox_access_token:
            raise ValueError("MAPBOX_ACCESS_TOKEN must be set")


# Global settings instance
settings = Settings()

# Validate on import
settings.validate_required_settings()
