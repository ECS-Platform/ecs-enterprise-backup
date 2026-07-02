"""JWT validation with JWKS retrieval and caching.

Validates RS256 (Azure AD / OIDC) tokens against the IdP's published signing
keys (JWKS). Keys are fetched lazily and cached; on a key-id miss the cache is
refreshed once (handles IdP key rotation).

Dependency note: requires PyJWT + cryptography. Import is lazy so the rest of
ECS still boots (e.g. in dev-mode) when those libraries are absent — a clear
AuthenticationError is raised only if real JWT validation is actually attempted.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any

from app.auth.errors import AuthenticationError

_JWKS_TTL_SECONDS = 3600
_JWKS_HTTP_TIMEOUT = 5


class _JwksCache:
    """Thread-safe JWKS cache keyed by JWKS URI."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    def get(self, uri: str, *, force: bool = False) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            cached = self._store.get(uri)
            if cached and not force and (now - cached[0]) < _JWKS_TTL_SECONDS:
                return cached[1]
        jwks = _fetch_json(uri)
        with self._lock:
            self._store[uri] = (now, jwks)
        return jwks


_jwks_cache = _JwksCache()


def _fetch_json(uri: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(uri, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_JWKS_HTTP_TIMEOUT) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError("jwks_unavailable", f"Unable to fetch signing keys: {exc}") from exc


def _require_pyjwt():
    try:
        import jwt  # PyJWT
        from jwt import PyJWKClient  # noqa: F401  (presence check)

        return jwt
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError(
            "jwt_lib_missing",
            "JWT validation requires PyJWT and cryptography (pip install 'pyjwt[crypto]').",
        ) from exc


def _signing_key(jwt_mod, token: str, jwks: dict[str, Any]):
    """Find the RSA signing key in the JWKS matching the token's `kid`."""
    try:
        header = jwt_mod.get_unverified_header(token)
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError("malformed_token", "Token header could not be parsed.") from exc
    kid = header.get("kid")
    from jwt.algorithms import RSAAlgorithm

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(key))
    return None


def validate_token(token: str, *, jwks_uri: str, issuer: str,
                   audiences: list[str], leeway: int = 60) -> dict[str, Any]:
    """Validate a JWT and return its claims, or raise AuthenticationError.

    Verifies signature (RS256 via JWKS), issuer, audience, and exp/nbf with the
    configured clock-skew leeway. Refreshes JWKS once on a key-id miss to handle
    IdP key rotation.
    """
    jwt_mod = _require_pyjwt()
    if not jwks_uri or not issuer:
        raise AuthenticationError("provider_unconfigured", "Identity provider is not configured.")

    jwks = _jwks_cache.get(jwks_uri)
    key = _signing_key(jwt_mod, token, jwks)
    if key is None:
        # Possible key rotation — force-refresh JWKS and retry once.
        jwks = _jwks_cache.get(jwks_uri, force=True)
        key = _signing_key(jwt_mod, token, jwks)
    if key is None:
        raise AuthenticationError("unknown_kid", "Token signing key not recognised.")

    options = {"require": ["exp", "iss"]}
    decode_kwargs: dict[str, Any] = {
        "algorithms": ["RS256"],
        "issuer": issuer,
        "leeway": leeway,
        "options": options,
    }
    if audiences:
        decode_kwargs["audience"] = audiences
    else:
        options["verify_aud"] = False

    try:
        return jwt_mod.decode(token, key=key, **decode_kwargs)
    except jwt_mod.ExpiredSignatureError as exc:
        raise AuthenticationError("expired", "Token has expired.") from exc
    except jwt_mod.InvalidAudienceError as exc:
        raise AuthenticationError("audience_mismatch", "Token audience is not allowed.") from exc
    except jwt_mod.InvalidIssuerError as exc:
        raise AuthenticationError("issuer_mismatch", "Token issuer is not trusted.") from exc
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError("invalid_token", "Token validation failed.") from exc
