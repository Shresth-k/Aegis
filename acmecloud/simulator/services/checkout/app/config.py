"""Runtime configuration for the AcmeCloud checkout service.

Short overview:
- Loads service and database settings from environment variables.
- Keeps service metadata independent from database configuration.
- Supports the Phase 1 DB_CONNECTION_POOL deployment setting.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Service metadata that is safe to load during application import."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
    )

    service_version: str = "2.4.0"


class Settings(ServiceSettings):
    """Full runtime configuration required by the checkout service."""

    database_url: str
    db_pool_size: int = Field(
        default=50,
        gt=0,
        validation_alias=AliasChoices(
            "DB_CONNECTION_POOL",
            "DB_POOL_SIZE",
        ),
    )
    db_pool_timeout: float = Field(default=5.0, gt=0)
    db_operation_delay_ms: int = Field(default=0, ge=0)


@lru_cache
def get_service_settings() -> ServiceSettings:
    """Return cached service metadata without requiring database settings."""
    return ServiceSettings()


@lru_cache
def get_settings() -> Settings:
    """Return cached full application configuration."""
    return Settings()
