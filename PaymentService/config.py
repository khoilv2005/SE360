"""
Centralized configuration management for PaymentService
Using pydantic-settings for environment variable validation
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    service_name: str = "paymentservice"
    service_version: str = "1.0.0"

    # Database (CosmosDB / MongoDB)
    cosmos_connection_string: str
    cosmos_db_name: str = "payments_db"

    # VNPay configuration
    vnp_tmn_code: str
    vnp_hash_secret: str
    vnp_url: str
    vnp_return_url: str = "http://localhost:3000/payment/return"

    # Server config
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Logging
    log_level: str = "INFO"

    # Payment settings
    default_currency: str = "VND"
    min_wallet_balance: int = 0

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
        if not self.vnp_tmn_code:
            raise ValueError("VNP_TMN_CODE must be set")
        if not self.vnp_hash_secret:
            raise ValueError("VNP_HASH_SECRET must be set")
        if not self.vnp_url:
            raise ValueError("VNP_URL must be set")


# Global settings instance
settings = Settings()

# Validate on import
settings.validate_required_settings()
