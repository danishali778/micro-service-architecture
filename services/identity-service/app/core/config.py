from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "development", "staging", "production"]
InternalAuthMode = Literal["local_header", "deferred"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    service_name: str = Field(default="identity-service", validation_alias="SERVICE_NAME")
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
        default="postgresql+psycopg://identity_service:identity_service@127.0.0.1:5432/identity_service",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias="DATABASE_POOL_SIZE",
    )
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

    supabase_auth_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9999/auth/v1"),
        validation_alias="SUPABASE_AUTH_URL",
    )
    supabase_anon_key: SecretStr = Field(
        default=SecretStr("local-anon-key"),
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY"),
    )
    supabase_service_role_key: SecretStr | None = Field(
        default=SecretStr("local-service-role-key"),
        validation_alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    supabase_jwt_issuer: str = Field(
        default="http://127.0.0.1:9999/auth/v1",
        validation_alias="SUPABASE_JWT_ISSUER",
    )
    supabase_jwks_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9999/auth/v1/.well-known/jwks.json"),
        validation_alias="SUPABASE_JWKS_URL",
    )
    supabase_jwt_audience: str = Field(
        default="authenticated",
        validation_alias="SUPABASE_JWT_AUDIENCE",
    )
    supabase_jwt_algorithms: str = Field(
        default="RS256,ES256",
        validation_alias="SUPABASE_JWT_ALGORITHMS",
    )
    supabase_request_timeout_ms: int = Field(
        default=5_000,
        ge=100,
        le=60_000,
        validation_alias="SUPABASE_REQUEST_TIMEOUT_MS",
    )

    internal_auth_mode: InternalAuthMode = Field(
        default="local_header",
        validation_alias="INTERNAL_AUTH_MODE",
    )

    @property
    def allowed_jwt_algorithms(self) -> tuple[str, ...]:
        return tuple(
            item.strip() for item in self.supabase_jwt_algorithms.split(",") if item.strip()
        )

    @model_validator(mode="after")
    def validate_environment_safety(self) -> "Settings":
        if self.internal_auth_mode == "local_header" and self.environment not in {"local", "test"}:
            raise ValueError("local_header internal authentication is limited to local and test")
        if not self.internal_api_prefix.startswith("/"):
            raise ValueError("INTERNAL_API_PREFIX must start with '/'")
        if "HS256" in self.allowed_jwt_algorithms:
            raise ValueError("Supabase shared-secret JWT validation is not supported")
        if self.environment == "production" and str(self.supabase_jwks_url).startswith("http://"):
            raise ValueError("production Supabase JWKS URL must use HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
