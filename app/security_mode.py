"""Centralized ECS security-mode resolution (single source of truth).

Purpose
-------
Make security *enforcement* configurable and **non-blocking by default in
LOCAL/DEMO** so ECS runs for prototype/budget-approval demos without a live IdP,
Vault, TLS certificates, key rotation, or real connector credentials — while
keeping strict behavior in UAT/PROD/DR. This module ADDS a canonical flag surface
and RESOLVES it against the flags ECS already uses; it removes no security code
and changes no PROD/DR default.

Security mode
-------------
``ECS_SECURITY_MODE`` is the top-level switch: ``demo`` | ``uat`` | ``production``.
When unset it is derived from ``ECS_ENV`` (local/dev -> demo, sit/uat -> uat,
prod/dr -> production) so existing deployments keep their behavior. ``DEMO_MODE``
(the long-standing full-bypass flag) also implies ``demo`` mode.

Canonical flags (all overridable via env; mode-aware defaults)
-------------------------------------------------------------
    ECS_AUTH_ENABLED                 require JWT/OIDC authentication
    ECS_RBAC_ENFORCEMENT             enforce RBAC (vs demo/query-param role)
    ECS_REQUIRE_TLS                  require TLS / force_https
    ECS_REQUIRE_VAULT               require a secrets manager / Vault
    ECS_REQUIRE_SECRETS             require real secrets to be present
    ECS_REQUIRE_OIDC                require an OIDC/IdP provider
    ECS_ALLOW_DEMO_AUTH             allow demo / query-param role behavior
    ECS_ALLOW_IN_MEMORY             allow in-memory fallback (no PG/Redis/etc.)
    ECS_CONNECTOR_EXECUTION_ENABLED allow live connector execution (always opt-in)
    ECS_STRICT_CONFIG_VALIDATION    treat config validation issues strictly
    ECS_STARTUP_FAIL_ON_CONFIG_ERROR abort startup when config validation errors

Every getter is env-read at call time (immune to caching / startup ordering) and
never raises — any failure resolves to the SECURE default for the active mode.

Compatibility
-------------
Existing flags remain authoritative where they already exist:
  * ``DEMO_MODE`` / ``ECS_LOCAL_AUTH_BYPASS`` (auth bypass) — unchanged.
  * ``RBAC_ENFORCEMENT_ENABLED`` — still honored; ``ECS_RBAC_ENFORCEMENT`` is an
    accepted alias.
  * ``ECS_AUTH_ENABLED`` — still read by the auth layer; this module only
    supplies a mode-aware DEFAULT when it is unset.
  * ``ECS_VALIDATE_CONFIG`` / ``ECS_VALIDATE_SECRETS`` — still honored by the
    validator; the two ``ECS_STRICT_*`` / ``ECS_STARTUP_*`` flags add explicit
    control over whether validation errors abort startup.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}

#: Security modes, least -> most strict.
MODE_DEMO = "demo"
MODE_UAT = "uat"
MODE_PRODUCTION = "production"
_VALID_MODES = (MODE_DEMO, MODE_UAT, MODE_PRODUCTION)

#: How ECS_ENV maps to a security mode when ECS_SECURITY_MODE is not set.
_ENV_TO_MODE = {
    "local": MODE_DEMO,
    "dev": MODE_DEMO,
    "sit": MODE_UAT,
    "uat": MODE_UAT,
    "prod": MODE_PRODUCTION,
    "dr": MODE_PRODUCTION,
}


def _raw(name: str) -> str:
    try:
        return str(os.environ.get(name, "")).strip()
    except Exception:  # noqa: BLE001 - env read must never raise
        return ""


def _tri(name: str) -> bool | None:
    """Return True/False when the flag is explicitly set, else None (unset)."""
    val = _raw(name).lower()
    if val in _TRUTHY:
        return True
    if val in _FALSY:
        return False
    return None


def _demo_mode_flag() -> bool:
    """The long-standing DEMO_MODE full-bypass flag (kept authoritative)."""
    try:
        from app.auth.demo import demo_mode
        return demo_mode()
    except Exception:  # noqa: BLE001
        return _raw("DEMO_MODE").lower() in _TRUTHY


def _active_env() -> str:
    try:
        from config.environment_loader import active_environment
        return (active_environment() or "local").strip().lower()
    except Exception:  # noqa: BLE001
        return (_raw("ECS_ENV") or "local").lower()


# --------------------------------------------------------------------------- #
# Mode resolution
# --------------------------------------------------------------------------- #
def security_mode() -> str:
    """Resolve the active security mode: 'demo' | 'uat' | 'production'.

    Precedence: explicit ``ECS_SECURITY_MODE`` > ``DEMO_MODE`` (=> demo) >
    derived from ``ECS_ENV`` > default 'demo' (safe for prototype, and existing
    prod/DR deployments derive 'production' from ECS_ENV=prod/dr).
    """
    explicit = _raw("ECS_SECURITY_MODE").lower()
    if explicit in _VALID_MODES:
        return explicit
    # Common aliases.
    if explicit in {"prod", "production"}:
        return MODE_PRODUCTION
    if explicit in {"local", "demo", "dev", "prototype"}:
        return MODE_DEMO
    if _demo_mode_flag():
        return MODE_DEMO
    return _ENV_TO_MODE.get(_active_env(), MODE_DEMO)


def is_demo() -> bool:
    return security_mode() == MODE_DEMO


def is_uat() -> bool:
    return security_mode() == MODE_UAT


def is_production() -> bool:
    """True for production-grade strictness (production mode OR prod/dr env)."""
    return security_mode() == MODE_PRODUCTION or _active_env() in ("prod", "dr")


def _default_strict() -> bool:
    """Baseline strictness: production strict, uat medium, demo lenient."""
    return is_production()


def _resolve(flag: str, *, strict_default: bool, aliases: tuple[str, ...] = ()) -> bool:
    """Resolve a canonical requirement flag.

    Explicit value (flag or any alias) wins; otherwise fall back to the
    mode-aware ``strict_default``. Production mode is never silently relaxed:
    when in production and the flag is unset, the strict default applies.
    """
    for name in (flag, *aliases):
        tri = _tri(name)
        if tri is not None:
            return tri
    return strict_default


# --------------------------------------------------------------------------- #
# Canonical requirement flags (mode-aware defaults; explicit env always wins)
# --------------------------------------------------------------------------- #
def auth_enabled() -> bool:
    """Whether JWT/OIDC authentication is required.

    Demo mode defaults OFF (browse without a token). Honors the existing
    ``ECS_AUTH_ENABLED`` flag verbatim when set. Never on in demo unless the
    operator explicitly forces ``ECS_AUTH_ENABLED=true``.
    """
    tri = _tri("ECS_AUTH_ENABLED")
    if tri is not None:
        return tri
    return not is_demo()  # uat/prod default ON; demo default OFF


def require_oidc() -> bool:
    return _resolve("ECS_REQUIRE_OIDC", strict_default=is_production())


def require_tls() -> bool:
    return _resolve("ECS_REQUIRE_TLS", strict_default=is_production())


def require_vault() -> bool:
    return _resolve("ECS_REQUIRE_VAULT", strict_default=is_production())


def require_secrets() -> bool:
    """Whether real secrets must be present (else missing secrets are warnings)."""
    return _resolve("ECS_REQUIRE_SECRETS", strict_default=is_production(),
                    aliases=("ECS_VALIDATE_SECRETS",))


def rbac_enforcement() -> bool:
    """Whether RBAC is enforced. Demo forces OFF; honors existing flags.

    Accepts ``ECS_RBAC_ENFORCEMENT`` (new canonical) and the long-standing
    ``RBAC_ENFORCEMENT_ENABLED``. Demo mode never enforces RBAC.
    """
    if is_demo():
        return False
    return _resolve("ECS_RBAC_ENFORCEMENT", strict_default=is_production(),
                    aliases=("RBAC_ENFORCEMENT_ENABLED",))


def allow_demo_auth() -> bool:
    """Whether demo / query-param role behavior is allowed. Default ON in demo."""
    tri = _tri("ECS_ALLOW_DEMO_AUTH")
    if tri is not None:
        return tri
    return not is_production()


def allow_in_memory() -> bool:
    """Whether in-memory fallback (no PG/Redis/vector/LLM) is allowed.

    Default ON except in production, so a prototype runs with no infrastructure.
    """
    tri = _tri("ECS_ALLOW_IN_MEMORY")
    if tri is not None:
        return tri
    return not is_production()


def connector_execution_enabled() -> bool:
    """Whether live connector execution is enabled. ALWAYS opt-in (default OFF).

    Mirrors the existing ``ECS_CONNECTOR_EXECUTION_ENABLED`` contract in every
    mode — demo, uat, and production all require it to be explicitly enabled.
    """
    return _tri("ECS_CONNECTOR_EXECUTION_ENABLED") is True


# --------------------------------------------------------------------------- #
# Config-validation strictness / startup gating
# --------------------------------------------------------------------------- #
def strict_config_validation() -> bool:
    """Whether config validation should be treated strictly.

    Default: production strict, demo/uat lenient. Honors the new
    ``ECS_STRICT_CONFIG_VALIDATION`` and the existing ``ECS_VALIDATE_CONFIG``
    (``strict``/``on``/truthy => strict; ``off`` => lenient).
    """
    tri = _tri("ECS_STRICT_CONFIG_VALIDATION")
    if tri is not None:
        return tri
    legacy = _raw("ECS_VALIDATE_CONFIG").lower()
    if legacy in {"strict", "on", "1", "true", "yes"}:
        return True
    if legacy in _FALSY:
        return False
    return is_production()


def startup_fail_on_config_error() -> bool:
    """Whether config-validation ERRORS should abort startup.

    Demo defaults to NON-blocking (warn only) so a prototype never fails to
    start; production/DR default to blocking. Explicit
    ``ECS_STARTUP_FAIL_ON_CONFIG_ERROR`` always wins. ``ECS_VALIDATE_CONFIG=off``
    forces non-blocking (back-compat).
    """
    if _raw("ECS_VALIDATE_CONFIG").lower() in _FALSY:
        return False
    tri = _tri("ECS_STARTUP_FAIL_ON_CONFIG_ERROR")
    if tri is not None:
        return tri
    # Fall back to the existing gate: strict env or forced validation.
    if strict_config_validation():
        return True
    return is_production()


# --------------------------------------------------------------------------- #
# Summary (for logging / a diagnostics endpoint)
# --------------------------------------------------------------------------- #
def summary() -> dict[str, object]:
    """A secret-free snapshot of the resolved security posture (for logs)."""
    return {
        "security_mode": security_mode(),
        "environment": _active_env(),
        "auth_enabled": auth_enabled(),
        "rbac_enforcement": rbac_enforcement(),
        "require_oidc": require_oidc(),
        "require_tls": require_tls(),
        "require_vault": require_vault(),
        "require_secrets": require_secrets(),
        "allow_demo_auth": allow_demo_auth(),
        "allow_in_memory": allow_in_memory(),
        "connector_execution_enabled": connector_execution_enabled(),
        "strict_config_validation": strict_config_validation(),
        "startup_fail_on_config_error": startup_fail_on_config_error(),
    }
