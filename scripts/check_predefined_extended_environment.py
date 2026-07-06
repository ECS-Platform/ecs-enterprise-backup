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


def container_running(name: str) -> bool | None:
    try:
        r = subprocess.run(
            ["docker", "ps", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode != 0:
            return None
        return name in {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}
    except Exception:  # noqa: BLE001
        return None


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

    def container_check(name: str) -> str | None:
        if not do_docker:
            return None
        r = container_running(name)
        return "RUNNING" if r else ("NOT RUNNING" if r is False else "UNKNOWN")

    redis = get_redis_config()
    apache = get_apache_config()
    tomcat = get_tomcat_config()
    mongo = get_mongodb_config()
    mssql = get_sqlserver_config()
    k8s = get_kubernetes_config()
    ocp = get_openshift_config()

    checks: list[dict[str, Any]] = [
        {"technology": "Redis", "kind": "container", "container": redis["container"],
         "profile": "reuse existing redis", "password": _mask(redis["password"]),
         "status": container_check(redis["container"])},
        {"technology": "Apache HTTPD", "kind": "container", "container": apache["container"],
         "profile": "apache-demo / infra-demo-extended", "status": container_check(apache["container"])},
        {"technology": "Tomcat", "kind": "container", "container": tomcat["container"],
         "profile": "tomcat-demo / infra-demo-extended", "status": container_check(tomcat["container"])},
        {"technology": "MongoDB", "kind": "container", "container": mongo["container"],
         "profile": "mongodb-demo / db-demo-extended", "database": mongo["database"],
         "uri": _mask(mongo["uri"]), "status": container_check(mongo["container"])},
        {"technology": "SQL Server", "kind": "database", "container": "sqlserver-demo",
         "profile": "sqlserver-demo (optional/heavy)", "host": mssql["host"], "port": mssql["port"],
         "database": mssql["database"], "user": mssql["user"], "password": _mask(mssql["password"]),
         "status": container_check("sqlserver-demo")},
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
