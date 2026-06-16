import time
from typing import Any, cast

import httpx
import jwt
import pytest
from app.core.exceptions import UnauthorizedError
from app.domain.value_objects.tenant_context import Principal
from app.infrastructure.oidc.token_validator import SupabaseJwtTokenValidator
from conftest import make_test_settings
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://issuer.test/auth/v1"
AUDIENCE = "authenticated"
KEY_ID = "test-key"


def public_jwk(private_key: rsa.RSAPrivateKey, key_id: str = KEY_ID) -> dict[str, Any]:
    jwk = cast(
        dict[str, Any],
        jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True),
    )
    jwk.update({"kid": key_id, "alg": "RS256", "use": "sig"})
    return jwk


def token(
    private_key: rsa.RSAPrivateKey,
    *,
    key_id: str = KEY_ID,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    claims: dict[str, Any] | None = None,
    removed_claims: frozenset[str] = frozenset(),
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": "subject-1",
        "session_id": "session-1",
        "role": "authenticated",
        "iat": now,
        "exp": now + 300,
    }
    if claims:
        payload.update(claims)
    for claim in removed_claims:
        payload.pop(claim, None)
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": key_id},
    )


def jwks_transport(key: rsa.RSAPrivateKey) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/v1/.well-known/jwks.json":
            return httpx.Response(200, json={"keys": [public_jwk(key)]})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


class FakeIdentityClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def resolve_session_context(
        self,
        *,
        subject_id: str,
        session_id: str,
        correlation_id: str,
    ) -> Principal:
        self.calls.append((subject_id, session_id, correlation_id))
        return Principal(
            subject_id="user-1",
            tenant_id="tenant-1",
            scopes=frozenset({"scenarios:read", "matches:read"}),
        )


@pytest.mark.anyio
async def test_validates_rs256_token_and_canonical_claims() -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    identity_client = FakeIdentityClient()
    async with httpx.AsyncClient(transport=jwks_transport(key)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=identity_client,
        )
        await validator.initialize()
        principal = await validator.validate(token(key), correlation_id="correlation-1")

    assert validator.is_ready
    assert principal.subject_id == "user-1"
    assert principal.tenant_id == "tenant-1"
    assert principal.scopes == frozenset({"scenarios:read", "matches:read"})
    assert identity_client.calls == [("subject-1", "session-1", "correlation-1")]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"sub": ""},
        {"session_id": ""},
        {"role": "anon"},
    ],
)
async def test_rejects_invalid_or_missing_canonical_claims(claims: dict[str, Any]) -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    async with httpx.AsyncClient(transport=jwks_transport(key)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        with pytest.raises(UnauthorizedError):
            await validator.validate(token(key, claims=claims), correlation_id="correlation-1")


@pytest.mark.anyio
@pytest.mark.parametrize("claim", ["exp", "iat", "sub", "session_id", "role"])
async def test_rejects_missing_required_claim(claim: str) -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    async with httpx.AsyncClient(transport=jwks_transport(key)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        with pytest.raises(UnauthorizedError):
            await validator.validate(
                token(key, removed_claims=frozenset({claim})),
                correlation_id="correlation-1",
            )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("issuer", "audience"),
    [
        ("https://wrong-issuer.test", AUDIENCE),
        (ISSUER, "wrong-audience"),
    ],
)
async def test_rejects_wrong_issuer_or_audience(issuer: str, audience: str) -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    async with httpx.AsyncClient(transport=jwks_transport(key)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        with pytest.raises(UnauthorizedError):
            await validator.validate(
                token(key, issuer=issuer, audience=audience),
                correlation_id="correlation-1",
            )


@pytest.mark.anyio
async def test_rejects_forged_signature() -> None:
    trusted_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    forged_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    async with httpx.AsyncClient(transport=jwks_transport(trusted_key)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        with pytest.raises(UnauthorizedError):
            await validator.validate(token(forged_key), correlation_id="correlation-1")


@pytest.mark.anyio
async def test_refreshes_jwks_when_token_uses_unknown_key_id() -> None:
    original_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    rotated_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    jwks_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal jwks_requests
        jwks_requests += 1
        keys = (
            [public_jwk(original_key)]
            if jwks_requests == 1
            else [public_jwk(original_key), public_jwk(rotated_key, "rotated-key")]
        )
        return httpx.Response(200, json={"keys": keys})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        principal = await validator.validate(
            token(rotated_key, key_id="rotated-key"),
            correlation_id="correlation-1",
        )

    assert principal.subject_id == "user-1"
    assert jwks_requests == 2


@pytest.mark.anyio
async def test_rate_limits_forced_refreshes_for_unknown_key_ids() -> None:
    trusted_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    unknown_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    jwks_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal jwks_requests
        jwks_requests += 1
        return httpx.Response(200, json={"keys": [public_jwk(trusted_key)]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()

        for key_id in ("unknown-1", "unknown-2", "unknown-3"):
            with pytest.raises(UnauthorizedError):
                await validator.validate(
                    token(unknown_key, key_id=key_id),
                    correlation_id="correlation-1",
                )

    assert jwks_requests == 2


@pytest.mark.anyio
async def test_ensure_ready_refreshes_expired_metadata() -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    discovery_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal discovery_requests
        discovery_requests += 1
        return httpx.Response(200, json={"keys": [public_jwk(key)]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        validator._expires_at = 0.0
        validator._next_refresh_allowed_at = 0.0

        assert await validator.ensure_ready()

    assert discovery_requests == 2


@pytest.mark.anyio
async def test_rejects_hs256_token_before_signature_validation() -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    hs_token = jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "subject-1",
            "session_id": "session-1",
            "role": "authenticated",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        "shared-secret",
        algorithm="HS256",
        headers={"kid": KEY_ID},
    )
    async with httpx.AsyncClient(transport=jwks_transport(key)) as http_client:
        validator = SupabaseJwtTokenValidator(
            settings=make_test_settings(),
            http_client=http_client,
            identity_client=FakeIdentityClient(),
        )
        await validator.initialize()
        with pytest.raises(UnauthorizedError):
            await validator.validate(hs_token, correlation_id="correlation-1")
