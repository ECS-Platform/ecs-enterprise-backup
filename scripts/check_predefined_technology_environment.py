#!/usr/bin/env python3
"""ECS predefined-technology environment diagnostic (infrastructure targets).

Complements scripts/check_predefined_db_environment.py (databases) by checking the
Docker demo targets for the INFRASTRUCTURE technologies:
  * NGINX          (nginx-demo)
  * Linux          (ubuntu-demo)
  * RHEL 8.x       (rhel8-demo)
  * RHEL 9.x       (rhel9-demo)
  * Oracle         (oracle-demo — heavy; only when the oracle-demo profile is used)

For each it reports Docker availability, the configured container/host, and
whether that container is running. Never prints passwords. Read-only.

Usage:
    python scripts/check_predefined_technology_environment.py
    python scripts/check_predefined_technology_environment.py --json
    python scripts/check_predefined_technology_environment.py --expect-oracle
    python scripts/check_predefined_technology_environment.py --no-docker-check

Exit code 0 when all expected containers are running (or Docker checks skipped);
1 when an expected container is not running.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_env() -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return "no .env file found (using process env / defaults)"
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path, override=False)
        return f"loaded {env_path}"
    except Exception:  # noqa: BLE001
        return f"found {env_path} but python-dotenv is not installed (skipped)"


def docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=8)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def list_running_containers() -> list[dict[str, str]] | None:
    """All running containers with their Compose service/project labels.

    Returns a list of ``{"name", "service", "project"}`` dicts, or ``None`` when
    Docker is unavailable. We deliberately do NOT filter by name here so detection
    is independent of the Compose project prefix (``<project>-<service>-<index>``).
    """
    fmt = '{{.Names}}\t{{.Label "com.docker.compose.service"}}\t{{.Label "com.docker.compose.project"}}'
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", fmt],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode != 0:
            return None
    except Exception:  # noqa: BLE001
        return None
    containers: list[dict[str, str]] = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        cname = parts[0].strip() if len(parts) > 0 else ""
        service = parts[1].strip() if len(parts) > 1 else ""
        project = parts[2].strip() if len(parts) > 2 else ""
        if cname:
            containers.append({"name": cname, "service": service, "project": project})
    return containers


def _container_name_matches(target: str, container_name: str) -> bool:
    """True if a running container *name* plausibly belongs to ``target``.

    Resilient to the Compose project prefix. Matches:
      * exact name                         nginx-demo == nginx-demo
      * project-prefixed compose name      ecs-nginx-demo-1 -> ...-nginx-demo-<n>
      * prefix (startswith)                nginx-demo... / ecs-nginx-demo
    """
    if not target:
        return False
    if container_name == target:  # exact container name
        return True
    if container_name.startswith(target):  # e.g. nginx-demo-x, ecs-... (startswith target)
        return True
    if container_name.endswith(f"-{target}"):  # project-prefixed, no index suffix
        return True
    if f"-{target}-" in container_name:  # <project>-<service>-<index>, e.g. ecs-nginx-demo-1
        return True
    if container_name.startswith(f"ecs-{target}"):  # startswith("ecs-<target>") style
        return True
    return False


def find_running_container(
    target: str, running: list[dict[str, str]] | None
) -> str | None:
    """Return the matched running container name for ``target``, else ``None``.

    ``target`` is the Compose service name / configured container short-name.
    Matching order (most authoritative first):
      1. exact Compose *service* label
      2. exact container name
      3. name heuristics (project prefix / startswith) via _container_name_matches
    """
    if not target or not running:
        return None
    for c in running:  # 1. authoritative: compose service label
        if c.get("service") == target:
            return c["name"]
    for c in running:  # 2. exact container name
        if c.get("name") == target:
            return c["name"]
    for c in running:  # 3. project-prefix / startswith heuristics
        if _container_name_matches(target, c.get("name", "")):
            return c["name"]
    return None


def container_running(name: str) -> bool | None:
    """True/False if a container for ``name`` is running; None if Docker is down.

    Resilient to the Compose project prefix: matches by exact container name,
    Compose service label, and project-prefixed names. Diagnostics-only — does
    not affect connectors.
    """
    running = list_running_containers()
    if running is None:
        return None
    return find_running_container(name, running) is not None


def _mask(value: Any) -> str:
    return "SET" if value not in (None, "") else "MISSING"


def _targets() -> list[dict[str, Any]]:
    """Resolve each infra technology's container via the connector config layer."""
    from modules.operations.engines.linux_connector import (
        get_linux_config,
        get_nginx_config,
        get_rhel_config,
    )
    from modules.operations.engines.oracle_connector import get_oracle_config

    nginx = get_nginx_config()
    linux = get_linux_config()
    rh8 = get_rhel_config(8)
    rh9 = get_rhel_config(9)
    oracle = get_oracle_config()
    return [
        {"technology": "NGINX", "container": nginx["container"], "profile": "nginx-demo / infra-demo",
         "timeout_sec": nginx["timeout_sec"], "kind": "container"},
        {"technology": "Linux", "container": linux["container"], "profile": "demo-connectors",
         "timeout_sec": linux["timeout_sec"], "kind": "container"},
        {"technology": "Red Hat Enterprise Linux 8.x", "container": rh8["container"],
         "profile": "rhel-demo / infra-demo", "timeout_sec": rh8["timeout_sec"], "kind": "container"},
        {"technology": "Red Hat Enterprise Linux 9.x", "container": rh9["container"],
         "profile": "rhel-demo / infra-demo", "timeout_sec": rh9["timeout_sec"], "kind": "container"},
        {"technology": "Oracle", "container": "oracle-demo", "profile": "oracle-demo (heavy)",
         "host": oracle["host"], "port": oracle["port"], "service_name": oracle["service_name"],
         "user": oracle["user"], "password": _mask(oracle["password"]),
         "timeout_sec": oracle["timeout_sec"], "kind": "database"},
    ]


def build_report(args) -> dict[str, Any]:
    env_status = load_env()
    do_docker = not args.no_docker_check
    docker_ok = docker_available() if do_docker else None

    # List running containers ONCE (project-prefix agnostic) and reuse per target,
    # so detection does not depend on the Compose project name.
    running = list_running_containers() if do_docker else None

    checks: list[dict[str, Any]] = []
    for t in _targets():
        rec = dict(t)
        # Oracle only counts toward failure when explicitly expected (heavy/optional).
        expected = True
        if t["technology"] == "Oracle":
            expected = bool(args.expect_oracle)
        rec["expected"] = expected
        if not do_docker:
            rec["container_status"] = None
            rec["matched_container"] = None
            rec["ok"] = True
        elif running is None:
            rec["container_status"] = "UNKNOWN"
            rec["matched_container"] = None
            rec["ok"] = True  # cannot prove failure when Docker is unavailable
        else:
            matched = find_running_container(t["container"], running)
            rec["matched_container"] = matched
            rec["container_status"] = "RUNNING" if matched else "NOT RUNNING"
            rec["ok"] = (matched is not None) if expected else True
        checks.append(rec)

    all_ok = all(c["ok"] for c in checks)
    return {
        "repository": str(ROOT),
        "python": platform.python_version(),
        "env_status": env_status,
        "docker_available": docker_ok,
        "expect_oracle": bool(args.expect_oracle),
        "checks": checks,
        "ok": all_ok,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ECS Predefined Technology (Infrastructure) Environment Diagnostic",
        "================================================================",
        "",
        f"Repository: {report['repository']}",
        f"Python: {report['python']}",
        f"Environment: {report['env_status']}",
    ]
    if report["docker_available"] is not None:
        lines.append(f"Docker available: {'YES' if report['docker_available'] else 'NO'}")
    lines.append("")
    for c in report["checks"]:
        lines.append(c["technology"])
        lines.append("-" * len(c["technology"]))
        lines.append(f"  Container/profile: {c['container']}  ({c['profile']})")
        if c["kind"] == "database":
            lines.append(f"  Host: {c.get('host')}  Port: {c.get('port')}  Service: {c.get('service_name')}")
            lines.append(f"  User: {c.get('user')}  Password: {c.get('password')}")
        if c.get("container_status") is not None:
            note = "" if c["expected"] else "  (optional; not expected unless --expect-oracle)"
            matched = c.get("matched_container")
            match_txt = f" (matched: {matched})" if matched and matched != c["container"] else ""
            lines.append(f"  Status: {c['container_status']}{match_txt}{note}")
        lines.append("")
    lines.append("================================================================")
    lines.append(f"Overall: {'PASS' if report['ok'] else 'FAIL'}")
    lines.append("")
    lines.append("Start lightweight infra:  docker compose --profile infra-demo up -d "
                 "nginx-demo rhel8-demo rhel9-demo")
    lines.append("Start Oracle (heavy):     docker compose --profile oracle-demo up -d oracle-demo")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ECS predefined-technology (infra) environment diagnostic (never prints passwords).",
    )
    parser.add_argument("--expect-oracle", action="store_true",
                        help="Treat the heavy oracle-demo container as required.")
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
