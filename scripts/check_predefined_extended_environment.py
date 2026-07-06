#!/usr/bin/env python3
"""ECS extended-technology environment diagnostic.

Covers the extended predefined-query targets and enterprise integration
skeletons added on top of the base set:
  * Redis        (container redis)
  * Apache HTTPD (container apache-demo)
  * Tomcat       (container tomcat-demo)
  * MongoDB      (container mongodb-demo / URI)
  * SQL Server   (optional endpoint; container sqlserver-demo)
  * kubectl availability (Kubernetes)
  * oc availability      (OpenShift)
  * ServiceNow CMDB config presence
  * Archer config presence

Safety:
  * Never prints passwords / tokens / URIs — secrets show as SET / MISSING only.
  * Works even when Docker is not running (container status = UNKNOWN).
  * --json for machine-readable output; --no-docker-check for no-docker mode.

Exit code 0 unless a REQUIRED check fails. By default nothing here is "required"
(these targets are opt-in), so the script reports status and exits 0; pass
--strict to fail when an expected container is not running.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from shutil import which
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
        name = parts[0].strip() if len(parts) > 0 else ""
        service = parts[1].strip() if len(parts) > 1 else ""
        project = parts[2].strip() if len(parts) > 2 else ""
        if name:
            containers.append({"name": name, "service": service, "project": project})
    return containers


def _container_name_matches(target: str, container_name: str) -> bool:
    """True if a running container *name* plausibly belongs to ``target``.

    Resilient to the Compose project prefix. Matches:
      * exact name                         redis            == redis
      * project-prefixed compose name      ecs-redis-1      -> ...-redis-<n>
      * prefix (startswith)                ecs-redis...     / redis-demo
    """
    if not target:
        return False
    if container_name == target:  # exact container name
        return True
    if container_name.startswith(target):  # e.g. redis-demo, ecs-redis (startswith target)
        return True
    if container_name.endswith(f"-{target}"):  # project-prefixed, no index suffix
        return True
    if f"-{target}-" in container_name:  # <project>-<service>-<index>, e.g. ecs-redis-1
        return True
    # startswith("ecs-<target>") style: a leading "<prefix>-<target>" segment.
    if container_name.startswith(f"ecs-{target}"):
        return True
    return False


def find_running_container(
    target: str, running: list[dict[str, str]] | None
) -> str | None:
    """Return the matched running container name for ``target``, else ``None``.

    ``target`` is the Compose service name / configured container short-name.
    Matching order (most authoritative first):
      1. exact Compose *service* label  (ecs-redis-1 has service=redis)
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

    Kept for backward compatibility (and unit tests). Delegates to the resilient
    matcher so exact names, Compose service labels, and project-prefixed names
    (e.g. ``ecs-redis-1`` for service ``redis``) are all detected.
    """
    running = list_running_containers()
    if running is None:
        return None
    return find_running_container(name, running) is not None


def _mask(value: Any) -> str:
    return "SET" if value not in (None, "") else "MISSING"


def build_report(args) -> dict[str, Any]:
    from modules.operations.engines.linux_connector import get_apache_config, get_tomcat_config
    from modules.operations.engines.redis_connector import get_redis_config
    from modules.operations.engines.mongodb_connector import get_mongodb_config
    from modules.operations.engines.sqlserver_connector import get_sqlserver_config
    from modules.operations.engines.kubernetes_connector import (
        get_kubernetes_config,
        get_openshift_config,
    )
    from modules.operations.integrations.servicenow_cmdb import config_status as snow_status
    from modules.operations.integrations.archer import config_status as archer_status

    env_status = load_env()
    do_docker = not args.no_docker_check
    docker_ok = docker_available() if do_docker else None

    # List running containers ONCE (project-prefix agnostic) and reuse for every
    # technology, so detection does not depend on the Compose project name.
    running = list_running_containers() if do_docker else None

    def container_check(name: str) -> tuple[str | None, str | None]:
        """Return (status, matched_container_name)."""
        if not do_docker:
            return None, None
        if running is None:
            return "UNKNOWN", None
        matched = find_running_container(name, running)
        return ("RUNNING" if matched else "NOT RUNNING"), matched

    redis = get_redis_config()
    apache = get_apache_config()
    tomcat = get_tomcat_config()
    mongo = get_mongodb_config()
    mssql = get_sqlserver_config()
    k8s = get_kubernetes_config()
    ocp = get_openshift_config()

    def _container_entry(technology: str, container: str, profile: str, **extra: Any) -> dict[str, Any]:
        status, matched = container_check(container)
        entry: dict[str, Any] = {
            "technology": technology,
            "kind": extra.pop("kind", "container"),
            "container": container,
            "profile": profile,
            "status": status,
            "matched_container": matched,
        }
        entry.update(extra)
        return entry

    checks: list[dict[str, Any]] = [
        _container_entry("Redis", redis["container"], "reuse existing redis",
                         password=_mask(redis["password"])),
        _container_entry("Apache HTTPD", apache["container"], "apache-demo / infra-demo-extended"),
        _container_entry("Tomcat", tomcat["container"], "tomcat-demo / infra-demo-extended"),
        _container_entry("MongoDB", mongo["container"], "mongodb-demo / db-demo-extended",
                         database=mongo["database"], uri=_mask(mongo["uri"])),
        _container_entry("SQL Server", "sqlserver-demo", "sqlserver-demo (optional/heavy)",
                         kind="database", host=mssql["host"], port=mssql["port"],
                         database=mssql["database"], user=mssql["user"],
                         password=_mask(mssql["password"])),
        {"technology": "Kubernetes", "kind": "cli", "binary": k8s["binary"],
         "kubeconfig": _mask(k8s["kubeconfig"]),
         "cli_available": which(k8s["binary"]) is not None},
        {"technology": "OpenShift", "kind": "cli", "binary": ocp["binary"],
         "kubeconfig": _mask(ocp["kubeconfig"]),
         "cli_available": which(ocp["binary"]) is not None},
        {"technology": "ServiceNow CMDB", "kind": "integration", **snow_status()},
        {"technology": "Archer", "kind": "integration", **archer_status()},
    ]

    ok = True
    if args.strict:
        for c in checks:
            if c.get("kind") in ("container", "database") and c.get("status") not in (None, "RUNNING"):
                ok = False

    return {
        "repository": str(ROOT),
        "python": platform.python_version(),
        "env_status": env_status,
        "docker_available": docker_ok,
        "strict": bool(args.strict),
        "checks": checks,
        "ok": ok,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ECS Extended Technology Environment Diagnostic",
        "=============================================",
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
        if c["kind"] in ("container", "database"):
            lines.append(f"  Container/profile: {c['container']}  ({c['profile']})")
            for key in ("host", "port", "database", "user"):
                if key in c:
                    lines.append(f"  {key.capitalize()}: {c[key]}")
            for secret in ("password", "uri"):
                if secret in c:
                    lines.append(f"  {secret.capitalize()}: {c[secret]}")
            if c.get("status") is not None:
                matched = c.get("matched_container")
                if matched and matched != c.get("container"):
                    lines.append(f"  Status: {c['status']} (matched container: {matched})")
                else:
                    lines.append(f"  Status: {c['status']}")
        elif c["kind"] == "cli":
            lines.append(f"  Binary: {c['binary']}  Available: {'YES' if c['cli_available'] else 'NO'}")
            lines.append(f"  Kubeconfig: {c['kubeconfig']}")
        elif c["kind"] == "integration":
            lines.append(f"  Base URL configured: {c.get('base_url_configured')}")
            for k in ("client_id", "client_secret", "api_token"):
                if k in c:
                    lines.append(f"  {k}: {c[k]}")
            lines.append(f"  Ready: {c.get('ready')}")
        lines.append("")
    lines.append("=============================================")
    lines.append(f"Overall: {'PASS' if report['ok'] else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ECS extended-technology environment diagnostic (never prints secrets).",
    )
    parser.add_argument("--strict", action="store_true",
                        help="Fail if an expected demo container is not running.")
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
