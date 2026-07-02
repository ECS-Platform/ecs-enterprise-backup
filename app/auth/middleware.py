"""Central authentication middleware.

Responsibilities (authentication only — NO authorization decisions):
  * On each request, determine whether the path is public.
  * For protected paths, authenticate via the configured provider, build the
    user context, and attach it to request.state.principal.
  * Reject anonymous/invalid requests with proper HTTP status codes.
  * Emit authentication audit events (success / failure).

Secure-by-default: when auth.enabled is true and no dev bypass is configured,
every non-public route requires a valid identity. When auth.enabled is false,
the middleware is a transparent pass-through (legacy behaviour) so existing ECS
functionality is preserved exactly until an operator turns auth on.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import events
from app.auth.context import AuthenticatedUser
from app.auth.demo import auth_bypassed, demo_mode
from app.auth.errors import AuthenticationError


def _load_auth_cfg() -> dict[str, Any]:
    try:
        from ecs_platform.config import load_auth_config

        return load_auth_config().get("auth", {}) or {}
    except Exception:  # noqa: BLE001 - missing/!invalid config -> auth disabled, fail safe to legacy
        return {}


def _public_paths(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("public_paths", "")
    if isinstance(raw, (list, tuple)):
        items = [str(p).strip() for p in raw]
    else:
        items = [p.strip() for p in str(raw).split(",")]
    return [p for p in items if p]


def _is_public(path: str, public: list[str]) -> bool:
    for p in public:
        if path == p:
            return True
        # Prefix match for directories like /static, /static/ecs.
        if p != "/" and path.startswith(p.rstrip("/") + "/"):
            return True
    return False


def _demo_principal_from_request(request: Request) -> AuthenticatedUser | None:
    """Build a lightweight demo principal from the ?role=&user= query params.

    LOCAL/DEMO ONLY — used exclusively by the ECS_LOCAL_AUTH_BYPASS branch so the
    identity chosen at /login (which redirects with role/user query params) is
    reflected downstream instead of an anonymous request. Never validates a token
    and never runs in production (the caller is gated on the bypass flags).
    Returns None when no role/user is present so behaviour matches the anonymous
    demo pass-through for token-less API calls.
    """
    try:
        role = (request.query_params.get("role") or "").strip()
        user = (request.query_params.get("user") or "").strip()
    except Exception:  # noqa: BLE001 - never let identity synthesis break a demo request
        return None
    if not role and not user:
        return None
    username = user or role or "demo"
    return AuthenticatedUser(
        user_id=f"local::{username}",
        username=username,
        display_name=user or role.replace("_", " ").title() or "Demo User",
        email=f"{username}@local.demo",
        roles=(role,) if role else (),
        groups=(),
        auth_source="local_bypass",
    )


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._cfg = _load_auth_cfg()
        self._enabled = bool(self._cfg.get("enabled", True)) if self._cfg else False
        self._public = _public_paths(self._cfg)
        self._dev_mode = bool((self._cfg.get("dev_mode", {}) or {}).get("enabled", False))
        # Build the provider once; defer hard failures to request time so a
        # misconfigured IdP never prevents the app from booting.
        self._provider = None
        if self._enabled:
            try:
                from app.auth.providers import build_provider

                self._provider = build_provider(self._cfg)
            except Exception:  # noqa: BLE001
                self._provider = None

    async def dispatch(self, request: Request, call_next):
        # LOCAL/DEMO AUTH BYPASS (default OFF): when DEMO_MODE or
        # ECS_LOCAL_AUTH_BYPASS is on, authentication is bypassed for every route
        # so the app is reachable through a browser without a live IdP minting
        # Bearer tokens (the /login flow only redirects; it does not set a
        # token/cookie). Checked first and read per-request so it works
        # regardless of config loading / startup order. NON-PRODUCTION ONLY —
        # with both flags off this branch is skipped and production auth is
        # enforced exactly as before.
        if auth_bypassed():
            # DEMO_MODE keeps the original anonymous pass-through (principal=None)
            # for full backward compatibility. ECS_LOCAL_AUTH_BYPASS additionally
            # synthesises a principal from the ?role=&user= query so the chosen
            # login identity flows to downstream code that reads the principal.
            request.state.principal = (
                None if demo_mode() else _demo_principal_from_request(request)
            )
            return await call_next(request)

        # Pass-through when auth is disabled — preserves legacy behaviour exactly.
        if not self._enabled:
            request.state.principal = None
            return await call_next(request)

        path = request.url.path
        if _is_public(path, self._public):
            request.state.principal = None
            return await call_next(request)

        if self._provider is None:
            events.token_validation_failure("provider_unavailable", path)
            return self._reject(AuthenticationError(
                "provider_unavailable", "Authentication provider is not available."))

        try:
            principal: AuthenticatedUser = self._provider.authenticate(request)
        except AuthenticationError as exc:
            events.token_validation_failure(exc.reason, path)
            events.login_failure(exc.reason, source=getattr(self._provider, "name", ""))
            return self._reject(exc)
        except Exception as exc:  # noqa: BLE001 - never leak internals; treat as auth failure
            events.token_validation_failure("internal_error", path)
            return self._reject(AuthenticationError("internal_error", "Authentication error."))

        request.state.principal = principal
        # Successful identity established (dev-mode logs at debug volume to avoid noise).
        if self._dev_mode:
            events._emit("debug", f"Dev-mode principal: {principal.username or principal.user_id}")
        else:
            events.login_success(principal.user_id, principal.username, principal.auth_source)
        return await call_next(request)

    @staticmethod
    def _reject(exc: AuthenticationError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.http_status == 401 else {}
        return JSONResponse(
            {"error": "unauthorized", "reason": exc.reason, "detail": exc.detail},
            status_code=exc.http_status,
            headers=headers,
        )


def register_authentication(app: FastAPI) -> None:
    """Install the authentication middleware on the FastAPI app.

    Safe to call unconditionally: if auth is disabled in config the middleware
    becomes a transparent pass-through.
    """
    app.add_middleware(AuthenticationMiddleware)
