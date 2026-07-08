"""DB Agent FastAPI micro-service (PROTOTYPE).

>>> THIS IS A PROTOTYPE. THIS IS NOT PRODUCTION SECURE. <<<

Runs on a jump server inside a secured internal bank network during prototype /
UAT. It starts using ONLY configuration values and has NO dependency on
enterprise security infrastructure (mTLS/JWT/OIDC/OAuth/Vault/PKI/SSO/Azure AD/
Keycloak/HSM). Missing security infra NEVER prevents startup.

Endpoints:
  GET /            — service banner + prototype warning
  GET /healthz     — liveness (always 200; no I/O)
  GET /readyz      — readiness (200 when configured targets reachable, else 503;
                     NEVER blocks startup — 503 is an informational signal)
  GET /config      — resolved config, secrets masked (SET/MISSING only)
  GET /security    — prototype security posture + optional feature flags
  GET /connectivity            — DB + SSH connectivity summary
  GET /connectivity/database   — DB connectivity check (reuses ECS connector)
  GET /connectivity/ssh        — SSH host reachability check

Run:
    python -m db_agent            # uses DB_AGENT_HOST / DB_AGENT_PORT
    uvicorn db_agent.app:app --host 0.0.0.0 --port 8099
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from db_agent import __version__
from db_agent import connectivity, security
from db_agent.config import load_config

app = FastAPI(title="ECS DB Agent (Prototype)", version=__version__)

_PROTOTYPE_BANNER = (
    "PROTOTYPE — NOT PRODUCTION SECURE. No enterprise security is enforced. "
    "See db_agent/README.md for the production hardening checklist."
)


@app.middleware("http")
async def _optional_auth(request: Request, call_next):
    """Prototype auth hook — DISABLED by default (allows every request).

    Provides the single, explicit place where future JWT/OIDC enforcement is
    switched on via ENABLE_JWT / ENABLE_OIDC without changing routes. While
    disabled it is a transparent pass-through, so the agent runs with no tokens.
    """
    ok, _reason = security.authenticate_request(dict(request.headers))
    if not ok:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    response = await call_next(request)
    # Advertise prototype status on every response (never leaks internals).
    response.headers["X-DB-Agent-Mode"] = "prototype"
    return response


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "ecs-db-agent",
        "version": __version__,
        "prototype": True,
        "production_secure": False,
        "warning": _PROTOTYPE_BANNER,
    }


@app.get("/healthz")
def healthz() -> JSONResponse:
    """Liveness — the process is up. Does no I/O; always 200."""
    return JSONResponse({"status": "ok", "prototype": True})


@app.get("/readyz")
def readyz() -> JSONResponse:
    """Readiness — degraded (503) is informational and never blocks startup.

    Returns 200 when every *configured* target is reachable. When no target is
    configured yet (fresh prototype), reports 'degraded' with 503 but the agent
    keeps serving — readiness is a signal, not a gate.
    """
    cfg = load_config()
    checks = connectivity.check_all(cfg)
    configured = checks["summary"]["targets_configured"]
    ready = bool(configured) and checks["ok"]
    body = {
        "status": "ready" if ready else "degraded",
        "prototype": True,
        "targets_configured": configured,
        "database_ok": checks["database"]["ok"],
        "ssh_ok": checks["ssh"]["ok"],
    }
    return JSONResponse(body, status_code=200 if ready else 503)


@app.get("/config")
def config() -> dict[str, Any]:
    """Resolved configuration with secrets masked (never returns a secret)."""
    return load_config().masked()


@app.get("/security")
def security_posture() -> dict[str, Any]:
    """Prototype security posture + optional ENABLE_* feature flags (all off)."""
    return security.posture()


@app.get("/connectivity")
def connectivity_all() -> dict[str, Any]:
    """DB + SSH connectivity summary (read-only; never raises)."""
    return connectivity.check_all(load_config())


@app.get("/connectivity/database")
def connectivity_db() -> dict[str, Any]:
    """Database connectivity check — reuses ECS's PostgreSQLConnector."""
    return connectivity.check_db(load_config().db)


@app.get("/connectivity/ssh")
def connectivity_ssh() -> dict[str, Any]:
    """SSH host reachability check (prototype = TCP probe)."""
    return connectivity.check_ssh(load_config().ssh)


def main() -> None:
    """Console entrypoint: serve using DB_AGENT_HOST / DB_AGENT_PORT from config."""
    import uvicorn

    cfg = load_config()
    # Plain HTTP by default; tls_context() returns None unless mTLS is enabled
    # (see db_agent.security) — so the agent starts with no certificates.
    ssl_ctx = security.tls_context()  # noqa: F841 - reserved for future mTLS wiring
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
