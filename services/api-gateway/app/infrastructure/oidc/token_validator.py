import asyncio
import time
from typing import Any, cast

import httpx
import jwt

from app.application.ports.identity_client import IdentityClient
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError
from app.domain.value_objects.tenant_context import Principal


class SupabaseJwtTokenValidator:
    def __init__(
        self,
        *,
        settings: Settings,
        http_client: httpx.AsyncClient,
        identity_client: IdentityClient,
    ) -> None:
        self._settings = settings
        self._http_client = http_client
        self._identity_client = identity_client
        self._keys: dict[str, dict[str, Any]] = {}
        self._expires_at = 0.0
        self._next_refresh_allowed_at = 0.0
        self._next_forced_refresh_allowed_at = 0.0
        self._unknown_key_ids: dict[str, float] = {}
        self._refresh_lock = asyncio.Lock()

    @property
    def is_ready(self) -> bool:
        return bool(self._keys) and time.monotonic() < self._expires_at

    async def initialize(self) -> None:
        await self._refresh()

    async def ensure_ready(self) -> bool:
        if self.is_ready:
            return True
        try:
            await self._refresh()
        except (httpx.HTTPError, ValueError, KeyError):
            return False
        return self.is_ready

    async def validate(self, token: str, *, correlation_id: str) -> Principal:
        if not await self.ensure_ready():
            raise ServiceUnavailableError("Authentication metadata is unavailable.")

        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if (
                not isinstance(algorithm, str)
                or algorithm not in self._settings.allowed_jwt_algorithms
            ):
                raise UnauthorizedError()
            key_id = header.get("kid")
            if not isinstance(key_id, str):
                raise UnauthorizedError()
            if key_id not in self._keys and not self._is_unknown_key_cached(key_id):
                try:
                    await self._refresh(force=True)
                except (httpx.HTTPError, ValueError, KeyError):
                    pass
            if not isinstance(key_id, str) or key_id not in self._keys:
                self._unknown_key_ids[key_id] = (
                    time.monotonic() + self._settings.oidc_refresh_cooldown_seconds
                )
                raise UnauthorizedError()

            signing_key = jwt.PyJWK.from_dict(self._keys[key_id], algorithm=algorithm).key
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key,
                algorithms=list(self._settings.allowed_jwt_algorithms),
                audience=self._settings.supabase_jwt_audience,
                issuer=str(self._settings.supabase_jwt_issuer).rstrip("/"),
                options={"require": ["exp", "iat", "sub", "session_id", "role"]},
            )
        except UnauthorizedError:
            raise
        except jwt.InvalidTokenError as error:
            raise UnauthorizedError() from error

        subject = claims.get("sub")
        session_id = claims.get("session_id")
        role = claims.get("role")
        if not isinstance(subject, str) or not subject:
            raise UnauthorizedError()
        if not isinstance(session_id, str) or not session_id:
            raise UnauthorizedError()
        if role != "authenticated":
            raise UnauthorizedError()

        return await self._identity_client.resolve_session_context(
            subject_id=subject,
            session_id=session_id,
            correlation_id=correlation_id,
        )

    async def _refresh(self, *, force: bool = False) -> None:
        async with self._refresh_lock:
            if self.is_ready and not force:
                return
            now = time.monotonic()
            if force:
                if now < self._next_forced_refresh_allowed_at:
                    return
                self._next_forced_refresh_allowed_at = (
                    now + self._settings.oidc_refresh_cooldown_seconds
                )
            else:
                if now < self._next_refresh_allowed_at:
                    return
                self._next_refresh_allowed_at = now + self._settings.oidc_refresh_cooldown_seconds

            jwks_response = await self._http_client.get(str(self._settings.supabase_jwks_url))
            jwks_response.raise_for_status()
            jwks = cast(dict[str, Any], jwks_response.json())
            keys = jwks.get("keys")
            if not isinstance(keys, list):
                raise ValueError("OIDC JWKS has no keys list")

            parsed_keys: dict[str, dict[str, Any]] = {}
            for key in keys:
                if isinstance(key, dict) and isinstance(key.get("kid"), str):
                    parsed_keys[key["kid"]] = cast(dict[str, Any], key)
            if not parsed_keys:
                raise ValueError("OIDC JWKS has no usable signing keys")

            self._keys = parsed_keys
            self._expires_at = time.monotonic() + self._settings.oidc_jwks_cache_ttl_seconds
            self._unknown_key_ids.clear()

    def _is_unknown_key_cached(self, key_id: str) -> bool:
        expires_at = self._unknown_key_ids.get(key_id, 0.0)
        if time.monotonic() < expires_at:
            return True
        self._unknown_key_ids.pop(key_id, None)
        return False


OidcTokenValidator = SupabaseJwtTokenValidator
