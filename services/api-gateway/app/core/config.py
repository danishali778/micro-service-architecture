from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, model_validator
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

    service_name: str = Field(default="api-gateway", validation_alias="SERVICE_NAME")
    environment: Environment = Field(default="local", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    public_api_prefix: str = Field(default="/api/v1", validation_alias="PUBLIC_API_PREFIX")

    supabase_jwt_issuer: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9999/auth/v1"),
        validation_alias=AliasChoices("SUPABASE_JWT_ISSUER", "OIDC_ISSUER"),
    )
    supabase_jwt_audience: str = Field(
        default="authenticated",
        validation_alias=AliasChoices("SUPABASE_JWT_AUDIENCE", "OIDC_AUDIENCE"),
    )
    supabase_jwks_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9999/auth/v1/.well-known/jwks.json"),
        validation_alias=AliasChoices("SUPABASE_JWKS_URL", "OIDC_JWKS_URL"),
    )
    supabase_jwt_algorithms: str = Field(
        default="RS256,ES256",
        validation_alias="SUPABASE_JWT_ALGORITHMS",
    )
    oidc_jwks_cache_ttl_seconds: int = Field(
        default=300, ge=30, le=86_400, validation_alias="OIDC_JWKS_CACHE_TTL_SECONDS"
    )
    oidc_refresh_cooldown_seconds: int = Field(
        default=30, ge=1, le=300, validation_alias="OIDC_REFRESH_COOLDOWN_SECONDS"
    )

    scenario_service_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9100"),
        validation_alias="SCENARIO_SERVICE_URL",
    )
    match_orchestrator_service_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9300"),
        validation_alias="MATCH_ORCHESTRATOR_SERVICE_URL",
    )
    identity_service_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://127.0.0.1:9200"),
        validation_alias="IDENTITY_SERVICE_URL",
    )
    downstream_connect_timeout_ms: int = Field(
        default=500, ge=50, le=30_000, validation_alias="DOWNSTREAM_CONNECT_TIMEOUT_MS"
    )
    downstream_request_timeout_ms: int = Field(
        default=3_000, ge=100, le=60_000, validation_alias="DOWNSTREAM_REQUEST_TIMEOUT_MS"
    )
    internal_auth_mode: InternalAuthMode = Field(
        default="local_header", validation_alias="INTERNAL_AUTH_MODE"
    )
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="CORS_ALLOWED_ORIGINS",
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
        if self.environment == "production" and "*" in self.cors_allowed_origins:
            raise ValueError("production cannot use a wildcard CORS origin")
        if not self.public_api_prefix.startswith("/"):
            raise ValueError("PUBLIC_API_PREFIX must start with '/'")
        if "HS256" in self.allowed_jwt_algorithms:
            raise ValueError("Supabase shared-secret JWT validation is not supported")
        if self.environment not in {"local", "test"} and str(self.supabase_jwks_url).startswith(
            "http://"
        ):
            raise ValueError("Supabase JWKS URL must use HTTPS outside local and test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
