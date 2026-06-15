import asyncio
import time
from typing import Any, cast
from urllib.parse import urlparse

import httpx
import jwt

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError
from app.domain.value_objects.tenant_context import Principal


class OidcTokenValidator:
    def __init__(self, *, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client
        self._keys: dict[str, dict[str, Any]] = {}
        self._expires_at = 0.0
        self._refresh_lock = asyncio.Lock()

    @property
    def is_ready(self) -> bool:
        return bool(self._keys) and time.monotonic() < self._expires_at

    async def initialize(self) -> None:
        await self._refresh()

    async def validate(self, token: str) -> Principal:
        if not self.is_ready:
            try:
                await self._refresh()
            except (httpx.HTTPError, ValueError, KeyError) as error:
                raise ServiceUnavailableError("Authentication metadata is unavailable.") from error

        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                raise UnauthorizedError()
            key_id = header.get("kid")
            if not isinstance(key_id, str) or key_id not in self._keys:
                await self._refresh(force=True)
            if not isinstance(key_id, str) or key_id not in self._keys:
                raise UnauthorizedError()

            signing_key = jwt.PyJWK.from_dict(self._keys[key_id], algorithm="RS256").key
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self._settings.oidc_audience,
                issuer=str(self._settings.oidc_issuer).rstrip("/"),
                options={"require": ["exp", "sub", "tenant_id", "scope"]},
            )
        except UnauthorizedError:
            raise
        except jwt.InvalidTokenError as error:
            raise UnauthorizedError() from error

        subject = claims.get("sub")
        tenant_id = claims.get("tenant_id")
        scope = claims.get("scope")
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(tenant_id, str)
            or not tenant_id
            or not isinstance(scope, str)
        ):
            raise UnauthorizedError()

        return Principal(
            subject_id=subject,
            tenant_id=tenant_id,
            scopes=frozenset(scope.split()),
        )

    async def _refresh(self, *, force: bool = False) -> None:
        async with self._refresh_lock:
            if self.is_ready and not force:
                return

            discovery_response = await self._http_client.get(str(self._settings.oidc_discovery_url))
            discovery_response.raise_for_status()
            metadata = cast(dict[str, Any], discovery_response.json())

            expected_issuer = str(self._settings.oidc_issuer).rstrip("/")
            if metadata.get("issuer") != expected_issuer:
                raise ValueError("OIDC discovery issuer does not match configured issuer")

            jwks_uri = metadata.get("jwks_uri")
            if not isinstance(jwks_uri, str):
                raise ValueError("OIDC discovery metadata has no valid jwks_uri")
            self._validate_jwks_uri(jwks_uri)

            jwks_response = await self._http_client.get(jwks_uri)
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

    def _validate_jwks_uri(self, jwks_uri: str) -> None:
        parsed = urlparse(jwks_uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OIDC jwks_uri must be an absolute HTTP URL")
        if self._settings.environment not in {"local", "test"} and parsed.scheme != "https":
            raise ValueError("OIDC jwks_uri must use HTTPS outside local and test")
