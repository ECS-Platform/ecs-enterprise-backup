"""Authentication readiness validation (Phase 5.3).

Validates ONBOARDING CONFIGURATION readiness only — it never performs real
authentication or any network call. It checks that the configuration fields
required for the chosen authentication type are present (non-empty), where
"present" means either a literal value is supplied or the named environment
variable resolves to a non-empty value.
"""

from __future__ import annotations

import os
from typing import Mapping

from app.connectivity.models import AuthenticationReadiness, AuthType, Outcome

# Required config fields per auth type (overridable via config policy).
DEFAULT_AUTH_REQUIREMENTS: dict[str, list[str]] = {
    "oauth": ["client_id_env", "client_secret_env", "tenant_id_env"],
    "oauth2": ["client_id_env", "client_secret_env"],
    "oauth2_client_credentials": ["client_id_env", "client_secret_env", "tenant_id_env"],
    "pat": ["token_env"],
    "token": ["token_env"],
    "service_account": ["username_env", "password_env"],
    "basic": ["username_env", "password_env"],
    "ldap": ["username_env", "password_env"],
    "kerberos": ["username_env"],
    "saml": ["client_id_env"],
    "jwt": ["token_env"],
    "prisma_credentials": ["access_key_env", "secret_key_env"],
}

# Map the onboarding AuthType enum to a config requirement key.
_AUTHTYPE_TO_KEY = {
    AuthType.OAUTH: "oauth",
    AuthType.PAT: "pat",
    AuthType.SERVICE_ACCOUNT: "service_account",
    AuthType.LDAP: "ldap",
    AuthType.KERBEROS: "kerberos",
    AuthType.SAML: "saml",
    AuthType.JWT: "jwt",
}


def _normalize_auth_type(auth_type) -> str:
    if isinstance(auth_type, AuthType):
        return _AUTHTYPE_TO_KEY.get(auth_type, auth_type.value.lower())
    return str(auth_type or "").strip().lower().replace(" ", "_")


def _field_present(field_name: str, auth_config: Mapping[str, str],
                   *, env: Mapping[str, str] | None = None) -> bool:
    """A field is present if a literal value is set, or its *_env var resolves."""
    env = env if env is not None else os.environ
    raw = auth_config.get(field_name)
    if isinstance(raw, str) and raw.strip():
        # If it names an env var (key ends with _env), resolve it; else literal value.
        if field_name.endswith("_env"):
            return bool(str(env.get(raw, "")).strip())
        return True
    # Also accept a value stored under the non-_env alias (e.g. "token").
    alias = field_name[:-4] if field_name.endswith("_env") else field_name
    alt = auth_config.get(alias)
    return isinstance(alt, str) and alt.strip() != ""


def assess_authentication(auth_type, auth_config: Mapping[str, str] | None = None, *,
                          requirements: Mapping[str, list[str]] | None = None,
                          env: Mapping[str, str] | None = None
                          ) -> AuthenticationReadiness:
    """Assess authentication configuration readiness. Never raises, never authenticates."""
    auth_config = dict(auth_config or {})
    reqs = dict(DEFAULT_AUTH_REQUIREMENTS)
    if requirements:
        reqs.update({k: list(v) for k, v in requirements.items()})

    key = _normalize_auth_type(auth_type)
    required = reqs.get(key)
    label = auth_type.value if isinstance(auth_type, AuthType) else str(auth_type)

    if required is None:
        return AuthenticationReadiness(
            auth_type=label, outcome=Outcome.WARNING, required_fields=[],
            present_fields=[], missing_fields=[], score=50.0,
            detail=f"unknown auth type '{label}' -> cannot validate requirements")

    present = [f for f in required if _field_present(f, auth_config, env=env)]
    missing = [f for f in required if f not in present]
    total = len(required) or 1
    score = round(100.0 * len(present) / total, 1)

    if not missing:
        outcome = Outcome.PASS
        detail = "all required authentication fields present"
    elif present:
        outcome = Outcome.WARNING
        detail = "some authentication fields missing: " + ", ".join(missing)
    else:
        outcome = Outcome.FAIL
        detail = "no required authentication fields present"

    return AuthenticationReadiness(
        auth_type=label, outcome=outcome, required_fields=list(required),
        present_fields=present, missing_fields=missing, score=score, detail=detail)
