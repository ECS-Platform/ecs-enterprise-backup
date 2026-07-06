#!/usr/bin/env python3
"""ECS predefined-database environment diagnostic (safe, onboarding).

Helps a new developer quickly identify environment / configuration / database
connectivity issues BEFORE running predefined queries. It reuses the exact same
config loaders and connectors the predefined-query module uses, so a green result
here means the real queries should run.

Safety:
  * Never prints passwords — only SET / MISSING.
  * Read-only: the only SQL issued is ``SELECT 1``.
  * Degrades gracefully when Docker / drivers / .env are absent.

Usage:
    python scripts/check_predefined_db_environment.py
    python scripts/check_predefined_db_environment.py --json
    python scripts/check_predefined_db_environment.py --skip-mysql --no-docker-check

Flags:
    --skip-postgres     Skip the PostgreSQL checks.
    --skip-yugabyte     Skip the YugabyteDB checks.
    --skip-mysql        Skip the Aurora MySQL / MySQL checks.
    --no-docker-check   Do not query Docker for container status.
    --json              Emit a machine-readable JSON report instead of text.

Exit code 0 when all (non-skipped) required DB checks pass; 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- #
# .env loading (optional)
# --------------------------------------------------------------------------- #
def load_env() -> str:
    """Load .env into os.environ if python-dotenv is available. Returns status."""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return "no .env file found (using process env / defaults)"
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path, override=False)
        return f"loaded {env_path}"
    except Exception:  # noqa: BLE001 - python-dotenv missing or unreadable; not fatal
        return f"found {env_path} but python-dotenv is not installed (skipped)"


# --------------------------------------------------------------------------- #
# Password masking helpers
# --------------------------------------------------------------------------- #
def _mask(value: Any) -> str:
    """Return SET / MISSING for a secret — never the value itself."""
    return "SET" if value not in (None, "") else "MISSING"


# --------------------------------------------------------------------------- #
# Docker helpers
# --------------------------------------------------------------------------- #
def docker_available() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=8
        )
        return r.returncode == 0
    except Exception:  # noqa: BLE001 - docker not installed / not running
        return False


def container_running(name: str) -> bool | None:
    """True/False if the named container is running; None if Docker unavailable."""
    try:
        r = subprocess.run(
            ["docker", "ps", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode != 0:
            return None
        return name in {line.strip() for line in r.stdout.splitlines() if line.strip()}
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# TCP + login checks
# --------------------------------------------------------------------------- #
def tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:  # noqa: BLE001 - unreachable host/port
        return False


def _login_postgres(cfg: dict[str, Any]) -> tuple[bool, str]:
    try:
        import psycopg2
    except ImportError:
        return False, "psycopg2 not installed (pip install -r requirements.txt)"
    conn = None
    try:
        kwargs = dict(
            host=cfg["host"], port=cfg["port"], dbname=cfg["database"],
            user=cfg["user"], password=cfg["password"],
            connect_timeout=min(int(cfg.get("timeout_sec", 5)), 5),
        )
        if cfg.get("sslmode"):
            kwargs["sslmode"] = cfg["sslmode"]
        conn = psycopg2.connect(**kwargs)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True, "SELECT 1 succeeded"
    except Exception as exc:  # noqa: BLE001
        return False, _classify_error(str(exc))
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


def _login_mysql(cfg: dict[str, Any]) -> tuple[bool, str]:
    try:
        import pymysql
    except ImportError:
        return False, "PyMySQL not installed (pip install -r requirements.txt)"
    conn = None
    try:
        kwargs: dict[str, Any] = dict(
            host=cfg["host"], port=cfg["port"], database=cfg["database"],
            user=cfg["user"], password=cfg["password"],
            connect_timeout=min(int(cfg.get("timeout_sec", 5)), 5),
        )
        if cfg.get("ssl"):
            kwargs["ssl"] = {"ssl": {}}
        conn = pymysql.connect(**kwargs)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True, "SELECT 1 succeeded"
    except Exception as exc:  # noqa: BLE001
        return False, _classify_error(str(exc))
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


def _classify_error(message: str) -> str:
    """Return a short, safe reason (never echoes credentials)."""
    lower = message.lower()
    if "access denied" in lower or "authentication failed" in lower or "password authentication failed" in lower:
        return "Authentication failed."
    if "unknown database" in lower or "does not exist" in lower:
        return "Database not found."
    if "timed out" in lower or "timeout" in lower:
        return "Connection timed out."
    if "refused" in lower or "could not connect" in lower or "can't connect" in lower or "no route" in lower:
        return "Connection refused / host unreachable."
    # Keep it short and non-sensitive.
    return "Connection/login failed."


# --------------------------------------------------------------------------- #
# Per-database check
# --------------------------------------------------------------------------- #
def _recommended_action(technology: str, tcp_ok: bool, login_ok: bool, reason: str) -> str:
    if login_ok:
        return ""
    if not tcp_ok:
        return (f"{technology}: target not reachable. Start the container "
                f"(docker compose --profile db-targets up -d) or check host/port, "
                f"VPN, and security group.")
    if reason == "Authentication failed.":
        if technology == "Aurora MySQL":
            return ("Check docker-compose.yml MYSQL_ROOT_PASSWORD / MYSQL_USER / "
                    "MYSQL_PASSWORD. Align .env ECS_MYSQL_USER / ECS_MYSQL_PASSWORD / "
                    "ECS_MYSQL_DATABASE with the target DB credentials.")
        env_prefix = "ECS_PG" if technology == "PostgreSQL" else "ECS_YB"
        return (f"Align .env {env_prefix}_USER / {env_prefix}_PASSWORD / "
                f"{env_prefix}_DATABASE with the target DB credentials.")
    if reason == "Database not found.":
        return f"{technology}: create the database or fix the *_DATABASE value in .env."
    return f"{technology}: verify host/port/credentials in .env and that the DB is healthy."


def check_database(
    technology: str,
    cfg: dict[str, Any],
    container: str,
    do_docker: bool,
    ssl_field: str,
    login_fn,
) -> dict[str, Any]:
    ssl_display = cfg.get(ssl_field, "")
    result: dict[str, Any] = {
        "technology": technology,
        "config": {
            "host": cfg.get("host"),
            "port": cfg.get("port"),
            "database": cfg.get("database"),
            "user": cfg.get("user"),
            "password": _mask(cfg.get("password")),
            ssl_field: ssl_display,
        },
        "container": container,
        "container_status": None,
        "tcp": None,
        "login": None,
        "reason": "",
        "recommended_action": "",
    }

    if do_docker:
        running = container_running(container)
        result["container_status"] = (
            "RUNNING" if running else ("NOT RUNNING" if running is False else "UNKNOWN")
        )

    tcp_ok = tcp_check(str(cfg.get("host")), int(cfg.get("port")))
    result["tcp"] = "PASS" if tcp_ok else "FAIL"

    if tcp_ok:
        login_ok, reason = login_fn(cfg)
    else:
        login_ok, reason = False, "Connection refused / host unreachable."
    result["login"] = "PASS" if login_ok else "FAIL"
    if not login_ok:
        result["reason"] = reason
        result["recommended_action"] = _recommended_action(technology, tcp_ok, login_ok, reason)

    result["ok"] = tcp_ok and login_ok
    return result


# --------------------------------------------------------------------------- #
# Text rendering
# --------------------------------------------------------------------------- #
def _render_block(res: dict[str, Any]) -> str:
    cfg = res["config"]
    ssl_key = [k for k in cfg if k in ("sslmode", "ssl")][0]
    lines = [
        res["technology"],
        "-" * len(res["technology"]),
        "Config:",
        f"  Host: {cfg['host']}",
        f"  Port: {cfg['port']}",
        f"  Database: {cfg['database']}",
        f"  User: {cfg['user']}",
        f"  Password: {cfg['password']}",
        f"  {'SSL mode' if ssl_key == 'sslmode' else 'SSL'}: {cfg[ssl_key]}",
        "",
    ]
    if res["container_status"] is not None:
        lines += ["Docker:", f"  Container {res['container']}: {res['container_status']}", ""]
    lines.append(f"TCP connectivity: {res['tcp']}")
    lines.append(f"Login check: {res['login']}")
    if res["login"] == "FAIL":
        lines.append(f"Reason: {res['reason']}")
        if res["recommended_action"]:
            lines.append("Recommended action:")
            for part in _wrap(res["recommended_action"]):
                lines.append(f"  {part}")
    return "\n".join(lines)


def _wrap(text: str, width: int = 76) -> list[str]:
    words = text.split()
    out, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_report(args) -> dict[str, Any]:
    env_status = load_env()

    # Import config loaders lazily so --skip-* still works if a module is missing.
    checks: list[dict[str, Any]] = []
    do_docker = not args.no_docker_check
    docker_ok = docker_available() if do_docker else None

    if not args.skip_postgres:
        from modules.operations.engines.postgresql_connector import get_postgresql_config

        checks.append(check_database(
            "PostgreSQL", get_postgresql_config(), "postgres-demo",
            do_docker, "sslmode", _login_postgres,
        ))

    if not args.skip_yugabyte:
        from modules.operations.engines.yugabyte_connector import get_yugabyte_config

        checks.append(check_database(
            "YugabyteDB", get_yugabyte_config(), "yugabyte",
            do_docker, "sslmode", _login_postgres,  # YSQL is PG-wire
        ))

    if not args.skip_mysql:
        from modules.operations.engines.mysql_connector import get_mysql_config

        checks.append(check_database(
            "Aurora MySQL / MySQL-compatible", get_mysql_config(), "mysql-demo",
            do_docker, "ssl", _login_mysql,
        ))

    all_ok = all(c["ok"] for c in checks) if checks else True
    return {
        "repository": str(ROOT),
        "python": platform.python_version(),
        "env_status": env_status,
        "docker_available": docker_ok,
        "checks": checks,
        "ok": all_ok,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ECS Predefined Database Environment Diagnostic",
        "=============================================",
        "",
        f"Repository: {report['repository']}",
        f"Python: {report['python']}",
        f"Environment: {report['env_status']}",
    ]
    if report["docker_available"] is not None:
        lines.append(f"Docker available: {'YES' if report['docker_available'] else 'NO'}")
    lines.append("")
    for res in report["checks"]:
        lines.append(_render_block(res))
        lines.append("")
    lines.append("=============================================")
    lines.append(f"Overall: {'PASS' if report['ok'] else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ECS predefined-database environment diagnostic (safe; never prints passwords).",
    )
    parser.add_argument("--skip-postgres", action="store_true", help="Skip PostgreSQL checks.")
    parser.add_argument("--skip-yugabyte", action="store_true", help="Skip YugabyteDB checks.")
    parser.add_argument("--skip-mysql", action="store_true", help="Skip Aurora MySQL / MySQL checks.")
    parser.add_argument("--no-docker-check", action="store_true", help="Do not query Docker.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
