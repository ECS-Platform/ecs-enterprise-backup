"""Authentication audit events (Phase 1 scope only).

Captures authentication-specific signals — login success, login failure, and
token-validation failure. This is intentionally NOT the full ECS audit-logging
framework (deferred to a later phase); it reuses the existing ecs_logging
channel so events surface in the standard log stream. Never logs token contents.
"""

from __future__ import annotations


def _emit(level: str, message: str) -> None:
    try:
        from modules.shared.services import ecs_logging

        getattr(ecs_logging, level, ecs_logging.info)("Auth", message)
    except Exception:  # noqa: BLE001 - auth audit must never break a request
        pass


def login_success(user_id: str, username: str, source: str) -> None:
    who = username or user_id or "unknown"
    _emit("info", f"Login success: {who} via {source}")


def login_failure(reason: str, source: str = "", detail: str = "") -> None:
    extra = f" ({detail})" if detail else ""
    src = f" via {source}" if source else ""
    _emit("warning", f"Login failure: {reason}{src}{extra}")


def token_validation_failure(reason: str, path: str = "") -> None:
    where = f" on {path}" if path else ""
    _emit("warning", f"Token validation failure: {reason}{where}")
