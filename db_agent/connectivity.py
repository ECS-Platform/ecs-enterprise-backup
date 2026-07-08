"""DB Agent connectivity checks (prototype).

Reuses ECS's existing database connector (``PostgreSQLConnector``) for DB checks
and a dependency-light TCP reachability probe for SSH hosts. Every check is
read-only, bounded, and NEVER raises — an unreachable/unconfigured target
returns a structured failure result instead of blocking the agent.

No enterprise security is required for any check.
"""

from __future__ import annotations

import socket
import time
from typing import Any

from db_agent.config import AgentConfig, DbTarget, SshTarget


def _result(ok: bool, target: str, detail: str, *, latency_ms: int = 0,
            configured: bool = True, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok,
        "target": target,
        "configured": configured,
        "status": "ok" if ok else ("not_configured" if not configured else "error"),
        "detail": detail,
        "latency_ms": latency_ms,
    }
    out.update(extra)
    return out


def check_tcp(host: str, port: int, timeout_sec: int) -> tuple[bool, str, int]:
    """Lightweight TCP connect probe. Never raises; returns (ok, detail, ms)."""
    started = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=max(1, int(timeout_sec))):
            ms = int((time.perf_counter() - started) * 1000)
            return True, f"TCP connect to {host}:{port} succeeded", ms
    except Exception as exc:  # noqa: BLE001 - report, never raise
        ms = int((time.perf_counter() - started) * 1000)
        return False, f"TCP connect to {host}:{port} failed: {type(exc).__name__}", ms


def check_db(db: DbTarget) -> dict[str, Any]:
    """Check database connectivity by reusing ECS's PostgreSQLConnector.

    Returns a structured result. If the target is unconfigured, reports
    ``not_configured`` (never an error). If ``psycopg2`` or the connector is
    unavailable, degrades to a TCP reachability probe. Never raises.
    """
    if not db.configured:
        return _result(False, "database", "DB target not configured "
                       "(set DB_HOST/DB_NAME/DB_USERNAME)", configured=False)
    # Preferred: real driver connect via the existing ECS connector.
    started = time.perf_counter()
    try:
        from modules.operations.engines.postgresql_connector import PostgreSQLConnector

        conn = PostgreSQLConnector(
            host=db.host, port=db.port, database=db.name, user=db.username,
            password=db.password, sslmode=db.sslmode, timeout_sec=db.timeout_sec,
        )
        ok = conn.connect()
        if ok:
            probe = conn.execute("SELECT 1")
            conn.disconnect()
            ms = int((time.perf_counter() - started) * 1000)
            return _result(bool(probe.success), "database",
                           "DB connect + SELECT 1 succeeded" if probe.success
                           else (probe.error_message or "probe query failed"),
                           latency_ms=ms, engine="postgresql")
        conn.disconnect()
        ms = int((time.perf_counter() - started) * 1000)
        return _result(False, "database", conn._last_error or "DB connect failed",
                       latency_ms=ms, engine="postgresql")
    except Exception:  # noqa: BLE001 - driver unavailable -> TCP fallback
        ok, detail, ms = check_tcp(db.host, db.port, db.timeout_sec)
        return _result(ok, "database", f"driver unavailable; {detail}",
                       latency_ms=ms, engine="tcp_fallback")


def check_ssh(ssh: SshTarget) -> dict[str, Any]:
    """Check host reachability for the SSH target (prototype = TCP probe).

    A full SSH handshake needs an SSH client library; the prototype keeps
    dependencies light and does a TCP reachability probe to the SSH port, which
    is enough to validate jump-server -> host network reachability during UAT.

    TODO(prod): when a real SSH session is needed, add an optional paramiko-based
    handshake here (guarded so its absence never blocks the agent).
    """
    if not ssh.configured:
        return _result(False, "ssh", "SSH target not configured "
                       "(set SSH_HOST/SSH_USERNAME)", configured=False)
    ok, detail, ms = check_tcp(ssh.host, ssh.port, ssh.timeout_sec)
    return _result(ok, "ssh", detail, latency_ms=ms, mode="tcp_probe")


def check_all(cfg: AgentConfig) -> dict[str, Any]:
    """Run DB + SSH checks and summarize. Never raises."""
    db = check_db(cfg.db)
    ssh = check_ssh(cfg.ssh)
    checks = [db, ssh]
    configured = [c for c in checks if c.get("configured")]
    healthy = all(c["ok"] for c in configured) if configured else False
    return {
        "ok": healthy,
        "summary": {
            "targets_configured": len(configured),
            "targets_total": len(checks),
            "all_configured_healthy": healthy,
        },
        "database": db,
        "ssh": ssh,
    }
