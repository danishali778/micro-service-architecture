from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "development", "staging", "production"]
InternalAuthMode = Literal["local_header", "deferred"]
RedAgentAdapterName = Literal["local_fake", "deferred"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    service_name: str = Field(
        default="red-agent-service",
        validation_alias="SERVICE_NAME",
    )
    environment: Environment = Field(
        default="local",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    internal_api_prefix: str = Field(
        default="/internal/v1",
        validation_alias="INTERNAL_API_PREFIX",
    )

    database_url: str = Field(
        default="postgresql+psycopg://red_agent:red_agent@127.0.0.1:5432/red_agent",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        validation_alias="DATABASE_MAX_OVERFLOW",
    )
    database_pool_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        validation_alias="DATABASE_POOL_TIMEOUT_SECONDS",
    )
    require_current_migration: bool = Field(
        default=True,
        validation_alias="REQUIRE_CURRENT_MIGRATION",
    )

    internal_auth_mode: InternalAuthMode = Field(
        default="local_header",
        validation_alias="INTERNAL_AUTH_MODE",
    )
    red_agent_adapter: RedAgentAdapterName = Field(
        default="local_fake",
        validation_alias="RED_AGENT_ADAPTER",
    )
    default_agent_profile_ref: str = Field(
        default="red-agent-local-fake@1",
        min_length=1,
        max_length=160,
        validation_alias="DEFAULT_AGENT_PROFILE_REF",
    )
    agent_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=120,
        validation_alias="AGENT_TIMEOUT_SECONDS",
    )
    idempotency_retention_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        validation_alias="IDEMPOTENCY_RETENTION_HOURS",
    )

    @model_validator(mode="after")
    def validate_environment_safety(self) -> "Settings":
        if self.internal_auth_mode == "local_header" and self.environment not in {
            "local",
            "test",
        }:
            raise ValueError("local_header internal authentication is limited to local and test")
        if self.red_agent_adapter == "local_fake" and self.environment not in {"local", "test"}:
            raise ValueError("local_fake red agent adapter is limited to local and test")
        if not self.internal_api_prefix.startswith("/"):
            raise ValueError("INTERNAL_API_PREFIX must start with '/'")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
