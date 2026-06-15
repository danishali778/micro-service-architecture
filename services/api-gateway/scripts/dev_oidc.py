import os
import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from pydantic import BaseModel

ISSUER = os.getenv("DEV_OIDC_ISSUER", "http://127.0.0.1:9000").rstrip("/")
KEY_ID = "local-development-key"
AUDIENCE = "api-gateway"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
PUBLIC_JWK: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(
    PRIVATE_KEY.public_key(), as_dict=True
)
PUBLIC_JWK.update({"kid": KEY_ID, "alg": "RS256", "use": "sig"})

app = FastAPI(title="Local OIDC Stub")


class TokenRequest(BaseModel):
    subject: str = "local-user"
    tenant_id: str = "local-tenant"
    scope: str = "scenarios:read"
    expires_in_seconds: int = 3_600


@app.get("/.well-known/openid-configuration")
async def discovery() -> dict[str, Any]:
    return {
        "issuer": ISSUER,
        "jwks_uri": f"{ISSUER}/jwks",
        "id_token_signing_alg_values_supported": ["RS256"],
    }


@app.get("/jwks")
async def jwks() -> dict[str, Any]:
    return {"keys": [PUBLIC_JWK]}


@app.post("/token")
async def issue_token(request: TokenRequest) -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": request.subject,
            "tenant_id": request.tenant_id,
            "scope": request.scope,
            "iat": now,
            "nbf": now,
            "exp": now + request.expires_in_seconds,
        },
        PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )
    return {"access_token": token, "token_type": "Bearer"}
