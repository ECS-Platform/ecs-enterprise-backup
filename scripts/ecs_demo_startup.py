#!/usr/bin/env python3
"""ECS demo startup + health validation (idempotent).

Starts existing docker-compose services with their declared profiles, waits for
real readiness, validates connector runtime configuration, and prints a status
table. Reuses docker helpers from check_predefined_db_environment.py.

Exit code 1 only for required *core* failures (Docker down, ECS port conflict,
core backing services not ready, ECS app not reachable). Optional / heavy /
external targets are reported without blocking core startup.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.check_predefined_db_environment import (  # noqa: E402
    _mask,
    docker_available,
    find_running_container,
    list_running_containers,
    load_env,
    tcp_check,
)

COMPOSE_FILE = ROOT / "docker-compose.yml"
ECS_PORT = 8000
HEAVY_SERVICES = frozenset({"yugabyte", "oracle-demo", "sqlserver-demo", "sonarqube-demo", "aerospike"})
CORE_SERVICES = ("postgres-demo", "postgres", "pgvector", "redis", "minio")
ECS_SERVICE = "ecs"

# Optional demo targets keyed by compose service -> profiles (from docker-compose.yml).
OPTIONAL_SERVICE_PROFILES: dict[str, tuple[str, ...]] = {
    "ubuntu-demo": ("demo-connectors",),
    "sonarqube-demo": ("demo-connectors",),
    "mysql-demo": ("db-targets",),
    "yugabyte": ("db-targets",),
    "nginx-demo": ("nginx-demo", "infra-demo"),
    "rhel8-demo": ("rhel-demo", "infra-demo"),
    "rhel9-demo": ("rhel-demo", "infra-demo"),
    "apache-demo": ("apache-demo", "infra-demo-extended"),
    "tomcat-demo": ("tomcat-demo", "infra-demo-extended"),
    "mongodb-demo": ("mongodb-demo", "db-demo-extended"),
    "oracle-demo": ("oracle-demo",),
    "sqlserver-demo": ("sqlserver-demo",),
    "aerospike": ("aerospike", "demo"),
}

STATUS_PASS = "PASS"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"
STATUS_SKIPPED = "SKIPPED"
STATUS_EXTERNAL = "EXTERNAL"


@dataclass(frozen=True)
class TechSpec:
    technology: str
    service: str
    profiles: tuple[str, ...] = ()
    container: str = ""
    dns: str = ""
    heavy: bool = False
    external: bool = False
    unsupported: bool = False
    host_port: int | None = None
    host_port_env: str = ""
    readiness: str = "tcp"
    config_fn: str = ""
    password_env: str = ""
    user_field: str = "user"
    probe_control: str = ""


TECHNOLOGY_SPECS: tuple[TechSpec, ...] = (
    TechSpec("PostgreSQL", "postgres-demo", container="postgres-demo", dns="postgres-demo",
             host_port=5432, readiness="postgres", config_fn="postgresql", password_env="ECS_PG_PASSWORD",
             probe_control="PGX-001"),
    TechSpec("YugabyteDB", "yugabyte", profiles=("db-targets",), container="yugabyte", dns="yugabyte",
             heavy=True, host_port=15433, readiness="ysql", config_fn="yugabyte", password_env="ECS_YB_PASSWORD",
             probe_control="YBX-001"),
    TechSpec("Aurora MySQL", "mysql-demo", profiles=("db-targets",), container="mysql-demo", dns="mysql-demo",
             host_port=3306, readiness="mysql", config_fn="mysql", password_env="ECS_MYSQL_PASSWORD",
             probe_control="MYX-002"),
    TechSpec("Oracle", "oracle-demo", profiles=("oracle-demo",), container="oracle-demo", dns="oracle-demo",
             heavy=True, host_port=1521, readiness="oracle", config_fn="oracle", password_env="ECS_ORACLE_PASSWORD"),
    TechSpec("SQL Server", "sqlserver-demo", profiles=("sqlserver-demo",), container="sqlserver-demo",
             dns="sqlserver-demo", heavy=True, host_port=1433, readiness="mssql",
             config_fn="sqlserver", password_env="ECS_SQLSERVER_PASSWORD"),
    TechSpec("MongoDB", "mongodb-demo", profiles=("mongodb-demo", "db-demo-extended"), container="mongodb-demo",
             dns="mongodb-demo", host_port=27017, readiness="mongo", config_fn="mongodb", password_env=""),
    TechSpec("Redis", "redis", container="redis", dns="redis", host_port=6379, readiness="redis",
             config_fn="redis", password_env="ECS_REDIS_PASSWORD"),
    TechSpec("SonarQube", "sonarqube-demo", profiles=("demo-connectors",), container="sonarqube-demo",
             dns="sonarqube-demo", heavy=True, host_port=9000, readiness="sonarqube",
             config_fn="sonarqube", password_env="ECS_SONAR_PASSWORD", probe_control="APP-001"),
    TechSpec("Linux", "ubuntu-demo", profiles=("demo-connectors",), container="ubuntu-demo", dns="ubuntu-demo",
             readiness="container", config_fn="linux"),
    TechSpec("NGINX", "nginx-demo", profiles=("nginx-demo", "infra-demo"), container="nginx-demo", dns="nginx-demo",
             host_port=8081, readiness="http", config_fn="nginx"),
    TechSpec("RHEL 8.x", "rhel8-demo", profiles=("rhel-demo", "infra-demo"), container="rhel8-demo", dns="rhel8-demo",
             readiness="container", config_fn="rhel8"),
    TechSpec("RHEL 9.x", "rhel9-demo", profiles=("rhel-demo", "infra-demo"), container="rhel9-demo", dns="rhel9-demo",
             readiness="container", config_fn="rhel9"),
    TechSpec("Apache HTTPD", "apache-demo", profiles=("apache-demo", "infra-demo-extended"), container="apache-demo",
             dns="apache-demo", host_port=8082, readiness="http", config_fn="apache"),
    TechSpec("Tomcat", "tomcat-demo", profiles=("tomcat-demo", "infra-demo-extended"), container="tomcat-demo",
             dns="tomcat-demo", host_port=8083, readiness="http", config_fn="tomcat"),
    TechSpec("Aerospike", "aerospike", profiles=("aerospike", "demo"), container="ecs-aerospike", dns="ecs-aerospike",
             heavy=True, host_port=13000, host_port_env="AEROSPIKE_HOST_PORT", readiness="asinfo",
             config_fn="aerospike", password_env="AEROSPIKE_PASSWORD", probe_control="ASX-001"),
    TechSpec("GitLeaks", "", readiness="gitleaks", config_fn="gitleaks"),
    TechSpec("Trivy", "", readiness="trivy", config_fn="trivy"),
    TechSpec("Kubernetes", "", external=True, readiness="k8s", config_fn="kubernetes"),
    TechSpec("OpenShift", "", external=True, readiness="openshift", config_fn="openshift"),
    TechSpec("Windows", "", unsupported=True),
)

TECH_BY_NAME = {t.technology.lower(): t for t in TECHNOLOGY_SPECS}


def load_compose_services() -> dict[str, dict[str, Any]]:
    """Parse service names and profiles from docker-compose.yml."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    if not COMPOSE_FILE.is_file():
        return {}
    data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8")) or {}
    services = data.get("services") or {}
    out: dict[str, dict[str, Any]] = {}
    for name, block in services.items():
        if not isinstance(block, dict):
            continue
        profiles = tuple(block.get("profiles") or ())
        ports = block.get("ports") or []
        host_ports: list[int] = []
        for p in ports:
            parsed = _parse_compose_host_port(p)
            if parsed is not None:
                host_ports.append(parsed)
        out[name] = {"profiles": profiles, "host_ports": host_ports, "container_name": block.get("container_name", "")}
    return out


def _parse_compose_host_port(port_mapping: Any) -> int | None:
    if not isinstance(port_mapping, str) or ":" not in port_mapping:
        return None
    m = re.match(r"^\$\{[^}]+:-(\d+)\}:\d+$", port_mapping)
    if m:
        return int(m.group(1))
    host = port_mapping.rsplit(":", 1)[0]
    if host.isdigit():
        return int(host)
    m2 = re.search(r":-(\d+)\}?$", host)
    if m2:
        return int(m2.group(1))
    return None


def resolve_host_port(spec: TechSpec, compose: dict[str, dict[str, Any]]) -> int | None:
    if spec.host_port_env:
        raw = os.environ.get(spec.host_port_env, "").strip()
        if raw.isdigit():
            return int(raw)
    if spec.host_port is not None:
        return spec.host_port
    meta = compose.get(spec.service) or {}
    ports = meta.get("host_ports") or []
    return int(ports[0]) if ports else None


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def detect_port_conflicts(specs: list[TechSpec], compose: dict[str, dict[str, Any]]) -> list[str]:
    conflicts: list[str] = []
    seen: dict[int, str] = {}
    for spec in specs:
        port = resolve_host_port(spec, compose)
        if port is None:
            continue
        if port in seen and seen[port] != spec.technology:
            conflicts.append(f"host port {port} shared by {seen[port]} and {spec.technology}")
        seen[port] = spec.technology
        if port_in_use(port) and not find_running_container(spec.container or spec.service, list_running_containers()):
            conflicts.append(
                f"host port {port} ({spec.technology}) in use but {spec.service or 'target'} container not running"
            )
    return conflicts


def _pid_command(pid: int) -> str:
    try:
        r = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, timeout=3)
        return (r.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def stop_conflicting_ecs_python(port: int = ECS_PORT) -> list[str]:
    """Stop only host Python/uvicorn processes bound to the ECS port."""
    stopped: list[str] = []
    try:
        r = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                           capture_output=True, text=True, timeout=5)
    except Exception:  # noqa: BLE001
        return stopped
    if r.returncode != 0 or not r.stdout.strip():
        return stopped
    for raw in r.stdout.splitlines():
        pid_s = raw.strip()
        if not pid_s.isdigit():
            continue
        pid = int(pid_s)
        cmd = _pid_command(pid).lower()
        if "uvicorn" not in cmd and "app.main" not in cmd:
            continue
        if "docker" in cmd:
            continue
        try:
            subprocess.run(["kill", str(pid)], check=False, timeout=3)
            stopped.append(f"pid {pid}")
        except Exception:  # noqa: BLE001
            pass
    return stopped


def compose_config_valid() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
            capture_output=True, text=True, timeout=30, cwd=ROOT,
        )
        if r.returncode == 0:
            return True, "valid"
        return False, (r.stderr or r.stdout or "compose config failed").strip()[:200]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def resolve_credential(spec: TechSpec, cfg: dict[str, Any]) -> str:
    """Env var wins over connector default (never returns the raw secret)."""
    if not spec.password_env and _secret_not_required(spec):
        return "N/A"
    if spec.password_env:
        return _mask(os.environ.get(spec.password_env) or cfg.get("password") or cfg.get("token"))
    return _mask(cfg.get("password") or cfg.get("token"))


def _secret_not_required(spec: TechSpec) -> bool:
    """True when the technology has no expected password/token for demo health."""
    if spec.password_env:
        return False
    return spec.readiness in (
        "container", "http", "gitleaks", "trivy", "k8s", "openshift", "mongo", "asinfo",
    ) or spec.unsupported or spec.external


def _probe_password(spec: TechSpec, cfg: dict[str, Any]) -> str:
    """Password for in-container probes only — never logged or printed."""
    if spec.password_env:
        return str(os.environ.get(spec.password_env) or cfg.get("password") or cfg.get("token") or "")
    return str(cfg.get("password") or cfg.get("token") or "")


def _container_inspect_state(container: str) -> dict[str, Any]:
    """Return status, restarting flag, and restart count for diagnostics."""
    name = find_running_container(container, list_running_containers())
    if not name:
        return {"name": "", "status": "not_found", "restarting": False, "restart_count": 0}
    try:
        r = subprocess.run(
            [
                "docker", "inspect", name,
                "--format", "{{.State.Status}} {{.State.Restarting}} {{.RestartCount}}",
            ],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode != 0:
            return {"name": name, "status": "unknown", "restarting": False, "restart_count": 0}
        parts = (r.stdout or "").strip().split()
        status = parts[0] if parts else "unknown"
        restarting = len(parts) > 1 and parts[1].lower() == "true"
        restart_count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        return {"name": name, "status": status, "restarting": restarting, "restart_count": restart_count}
    except Exception:  # noqa: BLE001
        return {"name": name, "status": "unknown", "restarting": False, "restart_count": 0}


def _restart_diagnostic(container: str) -> str:
    state = _container_inspect_state(container)
    if not state.get("restarting") and state.get("status") not in ("restarting", "dead", "exited"):
        return ""
    name = state.get("name") or container
    return (
        f"restarting (count={state.get('restart_count', 0)}, state={state.get('status')}); "
        f"inspect: docker logs {name}"
    )


def ecs_runtime() -> str:
    """Classify ECS on :8000 as docker, host-python, or none."""
    running = list_running_containers() or []
    if find_running_container(ECS_SERVICE, running):
        return "docker"
    if not port_in_use(ECS_PORT):
        return "none"
    try:
        r = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{ECS_PORT}", "-sTCP:LISTEN", "-t"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:  # noqa: BLE001
        return "none"
    for raw in (r.stdout or "").splitlines():
        if not raw.strip().isdigit():
            continue
        cmd = _pid_command(int(raw.strip())).lower()
        if "uvicorn" in cmd and "app.main" in cmd and "docker" not in cmd:
            return "host-python"
    return "none"


def _container_networks(container_name: str) -> set[str]:
    try:
        r = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode != 0:
            return set()
        return {n for n in r.stdout.split() if n}
    except Exception:  # noqa: BLE001
        return set()


def dns_from_container(source_container: str, hostname: str) -> tuple[bool, str]:
    ok, msg = _docker_exec(source_container, ["getent", "hosts", hostname], timeout=8)
    if ok and msg:
        return True, msg.split()[0]
    return False, f"{hostname} unresolved"


def ecs_needs_recreate() -> tuple[bool, str]:
    runtime = ecs_runtime()
    if runtime == "host-python":
        return True, "host-python ECS on :8000 (use Docker ECS)"
    ecs_name = find_running_container(ECS_SERVICE, list_running_containers() or [])
    if not ecs_name:
        return True, "ecs container missing"
    if not ecs_app_ready():
        return True, "ecs /healthz unhealthy"
    pg_name = find_running_container("postgres-demo", list_running_containers() or [])
    if pg_name:
        if not _container_networks(ecs_name) & _container_networks(pg_name):
            return True, "ecs not on compose network with postgres-demo"
        ok, detail = dns_from_container(ecs_name, "postgres-demo")
        if not ok:
            return True, detail
    return False, ""


def _sql_creds(config_fn: str) -> dict[str, Any]:
    return load_connector_config(config_fn)


def _select_one_via_exec(container: str, shell_cmd: list[str]) -> tuple[bool, str]:
    return _docker_exec(container, shell_cmd, timeout=20)


def _add_service(services: set[str], profiles: set[str], svc: str) -> None:
    services.add(svc)
    profiles.update(OPTIONAL_SERVICE_PROFILES.get(svc, ()))


def services_for_mode(args: argparse.Namespace) -> tuple[set[str], set[str]]:
    """Return (services, profiles) to start."""
    services: set[str] = set()
    profiles: set[str] = set()

    if args.technology:
        spec = TECH_BY_NAME.get(args.technology.lower())
        if not spec:
            raise SystemExit(f"Unknown technology: {args.technology}")
        services.update(CORE_SERVICES)
        if spec.service:
            _add_service(services, profiles, spec.service)
        if not args.status_only:
            services.add(ECS_SERVICE)
        return services, profiles

    services.update(CORE_SERVICES)

    if args.core:
        if not args.status_only:
            services.add(ECS_SERVICE)
        return services, profiles

    if args.all:
        for svc, profs in OPTIONAL_SERVICE_PROFILES.items():
            if args.skip_heavy and svc in HEAVY_SERVICES:
                continue
            _add_service(services, profiles, svc)

    if not args.status_only:
        services.add(ECS_SERVICE)
    return services, profiles


def compose_up(
    services: set[str],
    profiles: set[str],
    *,
    dry_run: bool = False,
    force_recreate: set[str] | None = None,
) -> None:
    if not services:
        return
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    for profile in sorted(profiles):
        cmd.extend(["--profile", profile])
    cmd.append("up")
    cmd.append("-d")
    if force_recreate:
        cmd.append("--force-recreate")
        cmd.extend(sorted(force_recreate))
    else:
        cmd.append("--no-recreate")
        cmd.extend(sorted(services))
    if dry_run:
        print("[dry-run]", " ".join(cmd))
        return
    subprocess.run(cmd, cwd=ROOT, check=False, timeout=600)


def technology_matrix(compose: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Technology-to-service/profile matrix for reporting and tests."""
    compose = compose or load_compose_services()
    rows: list[dict[str, Any]] = []
    for spec in TECHNOLOGY_SPECS:
        meta = compose.get(spec.service, {}) if spec.service else {}
        rows.append({
            "technology": spec.technology,
            "service": spec.service or "-",
            "profiles": list(spec.profiles or meta.get("profiles") or ()),
            "heavy": spec.heavy,
            "external": spec.external,
            "unsupported": spec.unsupported,
        })
    return rows


def _docker_exec(container: str, cmd: list[str], timeout: float = 15.0) -> tuple[bool, str]:
    running = list_running_containers()
    name = find_running_container(container, running)
    if not name:
        return False, "container not running"
    try:
        r = subprocess.run(["docker", "exec", name, *cmd], capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or r.stderr or "").strip()[:200]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def wait_ready(spec: TechSpec, timeout: float = 120.0) -> tuple[bool, str]:
    deadline = time.time() + timeout
    host_port = resolve_host_port(spec, load_compose_services())
    while time.time() < deadline:
        ok, detail = _probe_once(spec, host_port)
        if ok:
            return True, detail
        time.sleep(2.0)
    return False, detail


def _probe_once(spec: TechSpec, host_port: int | None) -> tuple[bool, str]:
    kind = spec.readiness
    if spec.unsupported:
        return False, "unsupported"
    if kind == "container":
        running = find_running_container(spec.container or spec.service, list_running_containers())
        return bool(running), running or "not running"
    if kind == "tcp":
        if host_port and tcp_check("127.0.0.1", host_port):
            return True, f"tcp:{host_port}"
        return False, "tcp closed"
    if kind == "postgres":
        cfg = _sql_creds("postgresql")
        user = cfg.get("user") or "ecs_user"
        db = cfg.get("database") or "ecs_demo"
        return _select_one_via_exec(
            spec.container,
            ["psql", "-U", user, "-d", db, "-tAc", "SELECT 1"],
        )
    if kind == "ysql":
        restart_msg = _restart_diagnostic(spec.container)
        if restart_msg:
            return False, restart_msg
        cfg = _sql_creds("yugabyte")
        user = cfg.get("user") or "yugabyte"
        db = cfg.get("database") or "yugabyte"
        pw = _probe_password(spec, cfg)
        if pw:
            ok, msg = _select_one_via_exec(
                spec.container,
                ["bin/ysqlsh", "-h", "127.0.0.1", "-U", user, "-d", db, "-c", "SELECT 1;"],
            )
        else:
            ok, msg = _docker_exec(
                spec.container,
                ["sh", "-c", 'bin/ysqlsh -h 127.0.0.1 -U "${ECS_YB_USER:-yugabyte}" -d yugabyte -c "SELECT 1;"'],
            )
        if ok:
            return True, "SELECT 1"
        port = host_port or 15433
        if tcp_check("127.0.0.1", port):
            return False, f"ysql tcp:{port} (query failed)"
        return False, msg or "ysql closed"
    if kind == "mysql":
        cfg = _sql_creds("mysql")
        user = cfg.get("user") or "ecs_user"
        pw = _probe_password(spec, cfg)
        if pw:
            ok, msg = _docker_exec(
                spec.container,
                ["mysql", f"-u{user}", f"-p{pw}", "-e", "SELECT 1"],
            )
        else:
            # Demo container injects MYSQL_* from compose when host env is unset.
            ok, msg = _docker_exec(
                spec.container,
                ["sh", "-c", 'mysql -u"${MYSQL_USER:-ecs_user}" -p"${MYSQL_PASSWORD}" -e "SELECT 1"'],
            )
        return ok, "SELECT 1" if ok else msg
    if kind == "mongo":
        ok, msg = _docker_exec(spec.container, ["mongosh", "--quiet", "--eval", "db.adminCommand('ping')"])
        return ok, msg
    if kind == "oracle":
        cfg = _sql_creds("oracle")
        user = cfg.get("user") or "ecs_user"
        pw = cfg.get("password") or ""
        svc = cfg.get("service_name") or "FREEPDB1"
        ok, msg = _docker_exec(
            spec.container,
            ["bash", "-lc", f"echo 'SELECT 1 FROM DUAL;' | sqlplus -s {user}/{pw}@//localhost:1521/{svc}"],
            timeout=45,
        )
        if ok and "1" in msg:
            return True, "SELECT 1"
        if host_port and tcp_check("127.0.0.1", host_port):
            return False, "listener up, auth/query failed"
        return False, msg or "listener closed"
    if kind == "mssql":
        cfg = _sql_creds("sqlserver")
        user = cfg.get("user") or "sa"
        pw = cfg.get("password") or ""
        for sqlcmd in (
            "/opt/mssql-tools18/bin/sqlcmd",
            "/opt/mssql-tools/bin/sqlcmd",
        ):
            ok, msg = _docker_exec(
                spec.container,
                [sqlcmd, "-S", "localhost", "-U", user, "-P", pw, "-C", "-Q", "SELECT 1", "-h", "-1"],
                timeout=30,
            )
            if ok and "1" in msg:
                return True, "SELECT 1"
        if host_port and tcp_check("127.0.0.1", host_port):
            return False, "tcp open, SELECT 1 failed"
        return False, "tcp closed"
    if kind == "redis":
        ok, msg = _docker_exec(spec.container, ["redis-cli", "ping"])
        return ok, msg
    if kind == "sonarqube":
        url = f"http://127.0.0.1:{host_port or 9000}/api/system/status"
        try:
            with urllib.request.urlopen(url, timeout=4) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            if '"UP"' in body or '"status":"UP"' in body.replace(" ", ""):
                return True, "status UP"
            return False, body[:120]
        except urllib.error.URLError as exc:
            return False, str(exc.reason)
    if kind == "asinfo":
        ok, msg = _docker_exec(spec.container, ["asinfo", "-v", "build"])
        return ok, msg
    if kind == "http":
        port = host_port or 80
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=4) as resp:
                return resp.status < 500, f"http {resp.status}"
        except urllib.error.HTTPError as exc:
            return exc.code < 500, f"http {exc.code}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
    if kind == "gitleaks":
        cfg = load_connector_config("gitleaks")
        path = str(cfg.get("scan_path") or ROOT / "demo-data" / "gitleaks-sample")
        return Path(path).is_dir(), f"path:{path}"
    if kind == "trivy":
        try:
            r = subprocess.run(["docker", "image", "inspect", "aquasec/trivy"], capture_output=True, timeout=10)
            if r.returncode == 0:
                return True, "aquasec/trivy"
            return False, "aquasec/trivy image missing (docker pull aquasec/trivy)"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
    if kind == "k8s":
        binary = os.environ.get("ECS_KUBECTL_PATH", "kubectl")
        kube = os.environ.get("ECS_KUBECONFIG", "")
        if not kube and not shutil_which(binary):
            return False, "kubectl/kubeconfig missing"
        return bool(kube or shutil_which(binary)), "external cluster"
    if kind == "openshift":
        binary = os.environ.get("ECS_OC_PATH", "oc")
        kube = os.environ.get("ECS_OPENSHIFT_KUBECONFIG", "") or os.environ.get("ECS_KUBECONFIG", "")
        if not kube and not shutil_which(binary):
            return False, "oc/kubeconfig missing"
        return bool(kube or shutil_which(binary)), "external cluster"
    return False, "unknown probe"


def shutil_which(cmd: str) -> str | None:
    from shutil import which
    return which(cmd)


def load_connector_config(name: str) -> dict[str, Any]:
    loaders: dict[str, Callable[[], dict[str, Any]]] = {
        "postgresql": lambda: __import__("modules.operations.engines.postgresql_connector", fromlist=["get_postgresql_config"]).get_postgresql_config(),
        "yugabyte": lambda: __import__("modules.operations.engines.yugabyte_connector", fromlist=["get_yugabyte_config"]).get_yugabyte_config(),
        "mysql": lambda: __import__("modules.operations.engines.mysql_connector", fromlist=["get_mysql_config"]).get_mysql_config(),
        "oracle": lambda: __import__("modules.operations.engines.oracle_connector", fromlist=["get_oracle_config"]).get_oracle_config(),
        "sqlserver": lambda: __import__("modules.operations.engines.sqlserver_connector", fromlist=["get_sqlserver_config"]).get_sqlserver_config(),
        "mongodb": lambda: __import__("modules.operations.engines.mongodb_connector", fromlist=["get_mongodb_config"]).get_mongodb_config(),
        "redis": lambda: __import__("modules.operations.engines.redis_connector", fromlist=["get_redis_config"]).get_redis_config(),
        "sonarqube": lambda: __import__("modules.operations.engines.sonarqube_connector", fromlist=["get_sonarqube_config"]).get_sonarqube_config(),
        "linux": lambda: __import__("modules.operations.engines.linux_connector", fromlist=["get_linux_config"]).get_linux_config(),
        "nginx": lambda: __import__("modules.operations.engines.linux_connector", fromlist=["get_nginx_config"]).get_nginx_config(),
        "rhel8": lambda: __import__("modules.operations.engines.linux_connector", fromlist=["get_rhel_config"]).get_rhel_config(8),
        "rhel9": lambda: __import__("modules.operations.engines.linux_connector", fromlist=["get_rhel_config"]).get_rhel_config(9),
        "apache": lambda: __import__("modules.operations.engines.linux_connector", fromlist=["get_apache_config"]).get_apache_config(),
        "tomcat": lambda: __import__("modules.operations.engines.linux_connector", fromlist=["get_tomcat_config"]).get_tomcat_config(),
        "aerospike": lambda: __import__("modules.operations.engines.aerospike_connector", fromlist=["get_aerospike_config"]).get_aerospike_config(),
        "gitleaks": lambda: __import__("modules.operations.engines.gitleaks_connector", fromlist=["get_gitleaks_config"]).get_gitleaks_config(),
        "trivy": lambda: __import__("modules.operations.engines.trivy_connector", fromlist=["get_trivy_config"]).get_trivy_config(),
        "kubernetes": lambda: __import__("modules.operations.engines.kubernetes_connector", fromlist=["get_kubernetes_config"]).get_kubernetes_config(),
        "openshift": lambda: __import__("modules.operations.engines.kubernetes_connector", fromlist=["get_openshift_config"]).get_openshift_config(),
    }
    fn = loaders.get(name)
    if not fn:
        return {}
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}


def connector_summary(spec: TechSpec, cfg: dict[str, Any]) -> str:
    if not cfg:
        return "n/a"
    if cfg.get("_error"):
        return "load error"
    parts: list[str] = []
    for key in ("host", "port", "database", "container", "base_url", "scan_path", "image", "binary", "kubeconfig"):
        if key in cfg and cfg.get(key) not in (None, ""):
            parts.append(f"{key}={cfg[key]}")
    user = cfg.get("user") or cfg.get("username")
    if user:
        parts.append(f"user={user}")
    pw = cfg.get("password") or cfg.get("token") or ""
    secret = resolve_credential(spec, cfg)
    parts.append(f"secret={secret}")
    return ", ".join(parts) if parts else "configured"


def classify_status(
    spec: TechSpec,
    *,
    running: bool,
    ready: bool,
    connector_ok: bool,
    selected: bool,
    cfg: dict[str, Any],
    port_warn: bool = False,
    dns_ok: bool = True,
) -> str:
    if spec.unsupported:
        return STATUS_EXTERNAL
    if spec.external:
        return STATUS_EXTERNAL if not cfg.get("kubeconfig") else (STATUS_PASS if ready else STATUS_WARN)
    if not selected:
        return STATUS_SKIPPED
    if not spec.service and spec.readiness in ("gitleaks", "trivy"):
        return STATUS_PASS if ready else STATUS_WARN
    if not spec.service:
        return STATUS_SKIPPED
    if port_warn:
        return STATUS_WARN
    if not running:
        return STATUS_FAIL
    if not dns_ok:
        return STATUS_WARN
    if not ready:
        return STATUS_FAIL
    if cfg.get("_error"):
        return STATUS_FAIL
    cred = resolve_credential(spec, cfg)
    if cred == "MISSING" and spec.password_env:
        return STATUS_WARN
    return STATUS_PASS


def _run_probe_in_docker(control_id: str) -> bool:
    """Execute a predefined-query smoke probe INSIDE the detected ECS container.

    Reuses the existing ECS container detection (find_running_container) and the
    same engine entrypoint (run_predefined_query) — no execution logic is
    duplicated; it is simply invoked in the correct (Docker) runtime where the
    engine's drivers and compose-network DNS are available. Returns True only
    when the in-container run reports ok=True.
    """
    ecs_name = find_running_container(ECS_SERVICE, list_running_containers() or [])
    if not ecs_name:
        return False
    code = (
        "import json;"
        "from modules.operations.engines import predefined_queries_engine as e;"
        "e.load_predefined_queries(force=True);"
        f"print(json.dumps(e.run_predefined_query({control_id!r}, 'ecs-demo-startup')))"
    )
    try:
        r = subprocess.run(
            ["docker", "exec", ecs_name, "python", "-c", code],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:  # noqa: BLE001
        return False
    if r.returncode != 0 or not (r.stdout or "").strip():
        return False
    # The engine may print log lines before the JSON; parse the last JSON object.
    for line in reversed((r.stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return bool(json.loads(line).get("ok"))
            except Exception:  # noqa: BLE001
                return False
    return False


def _run_probe_on_host(control_id: str) -> bool:
    from modules.operations.engines import predefined_queries_engine as engine
    engine.load_predefined_queries(force=True)
    out = engine.run_predefined_query(control_id, "ecs-demo-startup")
    return bool(out.get("ok"))


def probe_connector(spec: TechSpec, runtime: str = "host-python") -> bool:
    """Run a control smoke probe in the interpreter matching the ECS runtime.

    * runtime == "docker"      -> execute via `docker exec` inside the ECS
      container (where the engine's drivers + compose-network DNS live).
    * runtime == "host-python" -> execute in this (host) interpreter.
    * runtime == "none"        -> ECS is not running; skip the probe (report True
      so a non-running ECS never manufactures a false connector failure).
    """
    if not spec.probe_control:
        if spec.config_fn in ("kubernetes", "openshift", "gitleaks", "trivy"):
            return True
        if spec.readiness == "container":
            return True
        return False
    if runtime == "none":
        return True
    try:
        if runtime == "docker":
            return _run_probe_in_docker(spec.probe_control)
        return _run_probe_on_host(spec.probe_control)
    except Exception:  # noqa: BLE001
        return False


def wait_core_backing(timeout: float) -> list[str]:
    """Wait for core backing services with real query/readiness probes."""
    failures: list[str] = []
    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        (
            "postgres-demo",
            lambda: _select_one_via_exec(
                "postgres-demo",
                ["psql", "-U", os.environ.get("ECS_PG_USER", "ecs_user"),
                 "-d", os.environ.get("ECS_PG_DATABASE", "ecs_demo"), "-tAc", "SELECT 1"],
            ),
        ),
        (
            "postgres",
            lambda: _select_one_via_exec(
                "postgres",
                ["psql", "-U", "ecs_user", "-d", "ecs_repository", "-tAc", "SELECT 1"],
            ),
        ),
        (
            "pgvector",
            lambda: _select_one_via_exec(
                "pgvector",
                ["psql", "-U", "ecs_user", "-d", "ecs_vectors", "-tAc", "SELECT 1"],
            ),
        ),
        ("redis", lambda: _docker_exec("redis", ["redis-cli", "PING"])),
    ]
    for name, probe in checks:
        deadline = time.time() + timeout
        ok, detail = False, "timeout"
        while time.time() < deadline:
            ok, detail = probe()
            if ok:
                break
            time.sleep(2.0)
        if not ok:
            failures.append(f"{name}: {detail}")
    if not tcp_check("127.0.0.1", 9002):
        failures.append("minio: tcp:9002 closed")
    return failures


def ecs_port_blocked() -> bool:
    if not port_in_use(ECS_PORT):
        return False
    running = list_running_containers() or []
    for c in running:
        if c.get("service") == ECS_SERVICE or (c.get("name") or "").endswith("-ecs-1"):
            return False
    return True


def build_rows(
    selected_services: set[str],
    wait: bool,
    probe_connectors: bool,
    port_conflicts: list[str] | None = None,
) -> list[dict[str, str]]:
    running_list = list_running_containers() or []
    compose = load_compose_services()
    ecs_name = find_running_container(ECS_SERVICE, running_list) or ""
    # Detect the ECS runtime once so smoke probes execute in the matching
    # interpreter (docker exec vs host python) rather than always on the host.
    runtime = ecs_runtime()
    rows: list[dict[str, str]] = []
    conflict_ports = {line for line in (port_conflicts or [])}
    for spec in TECHNOLOGY_SPECS:
        if not spec.service:
            selected = True
        elif spec.service in CORE_SERVICES:
            selected = True
        else:
            selected = spec.service in selected_services
        if spec.service:
            container = find_running_container(spec.container or spec.service, running_list) or ""
            running = bool(container)
        else:
            container = ""
            running = True
        ready = False
        ready_detail = ""
        if running or spec.external or spec.unsupported or not spec.service:
            if wait and selected and spec.service and running:
                ready, ready_detail = wait_ready(spec, timeout=30.0)
            else:
                ready, ready_detail = _probe_once(spec, resolve_host_port(spec, compose))
        cfg = load_connector_config(spec.config_fn) if spec.config_fn else {}
        conn_text = connector_summary(spec, cfg)
        dns_ok = True
        dns_detail = "-"
        if spec.dns and ecs_name and running:
            dns_ok, dns_detail = dns_from_container(ecs_name, spec.dns)
        port_warn = any(
            str(resolve_host_port(spec, compose) or "") in msg for msg in conflict_ports
        )
        conn_ok = (
            probe_connector(spec, runtime)
            if probe_connectors and spec.probe_control and ready and ecs_app_ready()
            else True
        )
        status = classify_status(
            spec, running=running, ready=ready, connector_ok=conn_ok,
            selected=selected, cfg=cfg, port_warn=port_warn, dns_ok=dns_ok,
        )
        check = ready_detail or "-"
        if dns_detail != "-":
            check = f"{check}; dns={dns_detail}" if check != "-" else f"dns={dns_detail}"
        rows.append({
            "technology": spec.technology,
            "target": spec.service or spec.readiness,
            "container": container or "-",
            "dns": spec.dns or "-",
            "check": check,
            "connector": conn_text[:80],
            "status": status,
        })
    return rows


def print_table(rows: list[dict[str, str]]) -> None:
    headers = ("Technology", "Service/Target", "Container", "DNS", "TCP/API", "Connector", "Status")
    widths = [len(h) for h in headers]
    for row in rows:
        vals = (row["technology"], row["target"], row["container"], row["dns"], row["check"], row["connector"], row["status"])
        widths = [max(w, len(v)) for w, v in zip(widths, vals)]
    fmt = "  ".join(f"{{:{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(row["technology"], row["target"], row["container"], row["dns"], row["check"], row["connector"], row["status"]))


def ecs_app_ready() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{ECS_PORT}/healthz", timeout=4) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start ECS demo stack and validate technology health.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--core", action="store_true", help="Start core backing services + ECS only.")
    mode.add_argument("--all", action="store_true", help="Start core + demo targets (+ heavy unless --skip-heavy).")
    mode.add_argument("--status-only", action="store_true", help="Report status; do not start services.")
    p.add_argument("--technology", metavar="NAME", help="Start/check one technology (e.g. 'SonarQube').")
    p.add_argument("--skip-heavy", action="store_true", help="Skip Oracle, YugabyteDB, SQL Server, SonarQube, Aerospike.")
    p.add_argument("--json", action="store_true", help="Emit JSON report.")
    p.add_argument("--wait-timeout", type=float, default=120.0, help="Seconds to wait for core dependencies.")
    p.add_argument("--probe-connectors", action="store_true", help="Run predefined control probes when ECS is up.")
    args = p.parse_args(argv)
    if not (args.core or args.all or args.status_only or args.technology):
        args.core = True
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env_note = load_env()
    report: dict[str, Any] = {
        "ok": True,
        "env": env_note,
        "ecs_runtime": ecs_runtime(),
        "compose_valid": False,
        "core_failures": [],
        "stopped_pids": [],
        "port_conflicts": [],
        "matrix": technology_matrix(),
    }

    if not docker_available():
        print("ERROR: Docker Desktop/daemon is not available. Start Docker and retry.", file=sys.stderr)
        return 1

    compose_ok, compose_msg = compose_config_valid()
    report["compose_valid"] = compose_ok
    if not compose_ok:
        report["core_failures"].append(f"compose: {compose_msg}")
        print(f"ERROR: docker compose config invalid: {compose_msg}", file=sys.stderr)
        return 1

    runtime = ecs_runtime()
    report["ecs_runtime"] = runtime
    if runtime == "host-python" and not args.status_only:
        stopped = stop_conflicting_ecs_python(ECS_PORT)
        report["stopped_pids"] = stopped
        runtime = ecs_runtime()
        report["ecs_runtime"] = runtime
    else:
        stopped = stop_conflicting_ecs_python(ECS_PORT) if runtime != "docker" else []
        report["stopped_pids"] = stopped
    if ecs_port_blocked():
        report["core_failures"].append(
            f"port {ECS_PORT} is in use by a non-ECS process; free it or stop the conflicting service"
        )

    try:
        services, profiles = services_for_mode(args)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1

    conflicts = detect_port_conflicts(list(TECHNOLOGY_SPECS), load_compose_services())
    report["port_conflicts"] = conflicts
    for msg in conflicts:
        print(f"WARNING: port conflict: {msg}")

    if not args.status_only and not report["core_failures"]:
        backing = set(CORE_SERVICES)
        optional = services - backing - {ECS_SERVICE}
        compose_up(backing | optional, profiles)
        if ECS_SERVICE in services:
            report["core_failures"].extend(wait_core_backing(args.wait_timeout))
            if not report["core_failures"]:
                recreate, reason = ecs_needs_recreate()
                if recreate:
                    print(f"Recreating ECS: {reason}")
                    compose_up({ECS_SERVICE}, set(), force_recreate={ECS_SERVICE})
                else:
                    compose_up({ECS_SERVICE}, set())
                deadline = time.time() + args.wait_timeout
                while time.time() < deadline and not ecs_app_ready():
                    time.sleep(2.0)
                if not ecs_app_ready():
                    report["core_failures"].append("ecs: /healthz not ready")

    probe = args.probe_connectors or (args.all and not args.status_only)
    rows = build_rows(services, wait=not args.status_only, probe_connectors=probe, port_conflicts=conflicts)
    report["rows"] = rows
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if stopped:
            print(f"Stopped host uvicorn on :{ECS_PORT}: {', '.join(stopped)}")
        print(f"ECS runtime: {report['ecs_runtime']}")
        print_table(rows)

    if report["core_failures"]:
        report["ok"] = False
        for item in report["core_failures"]:
            print(f"CORE FAILURE: {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
