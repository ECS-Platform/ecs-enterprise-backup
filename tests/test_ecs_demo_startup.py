"""Focused tests for scripts/ecs_demo_startup.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent

import scripts.ecs_demo_startup as startup  # noqa: E402


COMPOSE_SNIPPET = """
services:
  postgres-demo:
    container_name: postgres-demo
    ports: ["5432:5432"]
  mysql-demo:
    profiles: ["db-targets"]
    container_name: mysql-demo
    ports: ["3306:3306"]
  sonarqube-demo:
    profiles: ["demo-connectors"]
    container_name: sonarqube-demo
    ports: ["9000:9000"]
  aerospike:
    profiles: ["aerospike", "demo"]
    container_name: ecs-aerospike
    ports: ["${AEROSPIKE_HOST_PORT:-13000}:3000"]
  oracle-demo:
    profiles: ["oracle-demo"]
    container_name: oracle-demo
    ports: ["1521:1521"]
"""


def test_load_compose_services_discovers_profiles(tmp_path, monkeypatch):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(COMPOSE_SNIPPET, encoding="utf-8")
    monkeypatch.setattr(startup, "COMPOSE_FILE", compose)
    services = startup.load_compose_services()
    assert services["mysql-demo"]["profiles"] == ("db-targets",)
    assert services["aerospike"]["host_ports"] == [13000]
    assert services["postgres-demo"]["profiles"] == ()


def test_parse_args_required_flags():
    assert startup.parse_args(["--core"]).core is True
    assert startup.parse_args(["--all"]).all is True
    assert startup.parse_args(["--status-only"]).status_only is True
    assert startup.parse_args(["--technology", "Redis"]).technology == "Redis"
    assert startup.parse_args(["--skip-heavy"]).skip_heavy is True
    with pytest.raises(SystemExit):
        startup.parse_args(["--help"])


def test_services_for_mode_core_vs_all():
    core_args = startup.parse_args(["--core"])
    core_svcs, core_profiles = startup.services_for_mode(core_args)
    assert "postgres-demo" in core_svcs
    assert "ecs" in core_svcs
    assert "mysql-demo" not in core_svcs
    assert core_profiles == set()

    all_args = startup.parse_args(["--all", "--skip-heavy"])
    all_svcs, all_profiles = startup.services_for_mode(all_args)
    assert "mysql-demo" in all_svcs
    assert "sonarqube-demo" not in all_svcs
    assert "db-targets" in all_profiles


def test_services_for_mode_technology_includes_core():
    args = startup.parse_args(["--technology", "SonarQube"])
    svcs, profiles = startup.services_for_mode(args)
    assert "sonarqube-demo" in svcs
    assert "postgres-demo" in svcs
    assert "demo-connectors" in profiles


def test_mysql_probe_uses_container_password_when_host_env_empty(monkeypatch):
    spec = startup.TECH_BY_NAME["aurora mysql"]
    captured: list[list[str]] = []

    def fake_exec(container, cmd, timeout=15.0):
        captured.append(cmd)
        return True, "1"

    monkeypatch.setattr(startup, "_sql_creds", lambda _n: {"user": "ecs_user", "password": ""})
    monkeypatch.setattr(startup, "_docker_exec", fake_exec)
    ok, detail = startup._probe_once(spec, 3306)
    assert ok is True
    assert detail == "SELECT 1"
    assert captured[0] == ["sh", "-c", 'mysql -u"${MYSQL_USER:-ecs_user}" -p"${MYSQL_PASSWORD}" -e "SELECT 1"']


def test_mysql_probe_uses_resolved_password_when_env_set(monkeypatch):
    spec = startup.TECH_BY_NAME["aurora mysql"]
    captured: list[list[str]] = []

    def fake_exec(container, cmd, timeout=15.0):
        captured.append(cmd)
        return True, "1"

    monkeypatch.setenv("ECS_MYSQL_PASSWORD", "ecs_password")
    monkeypatch.setattr(startup, "_sql_creds", lambda _n: {"user": "ecs_user", "password": ""})
    monkeypatch.setattr(startup, "_docker_exec", fake_exec)
    ok, _ = startup._probe_once(spec, 3306)
    assert ok is True
    assert captured[0] == ["mysql", "-uecs_user", "-pecs_password", "-e", "SELECT 1"]


def test_postgresql_pass_when_auth_probe_succeeds_but_connector_probe_fails():
    spec = startup.TECH_BY_NAME["postgresql"]
    status = startup.classify_status(
        spec,
        running=True,
        ready=True,
        connector_ok=False,
        selected=True,
        cfg={"host": "postgres-demo", "password": "ecs_password"},
    )
    assert status == startup.STATUS_PASS


def test_postgresql_warn_when_auth_probe_fails():
    spec = startup.TECH_BY_NAME["postgresql"]
    status = startup.classify_status(
        spec,
        running=True,
        ready=False,
        connector_ok=False,
        selected=True,
        cfg={"host": "postgres-demo"},
    )
    assert status == startup.STATUS_FAIL


def test_secret_na_for_linux_and_gitleaks():
    linux = startup.TECH_BY_NAME["linux"]
    gitleaks = startup.TECH_BY_NAME["gitleaks"]
    assert startup.resolve_credential(linux, {}) == "N/A"
    assert startup.resolve_credential(gitleaks, {}) == "N/A"
    assert "secret=N/A" in startup.connector_summary(linux, {"container": "ubuntu-demo"})
    assert "secret=N/A" in startup.connector_summary(gitleaks, {"scan_path": "/tmp"})


def test_yugabyte_restart_diagnostics(monkeypatch):
    spec = startup.TECH_BY_NAME["yugabytedb"]
    monkeypatch.setattr(
        startup,
        "_container_inspect_state",
        lambda _c: {"name": "yugabyte", "status": "restarting", "restarting": True, "restart_count": 3},
    )
    ok, detail = startup._probe_once(spec, 15433)
    assert ok is False
    assert "restart_count=3" in detail or "count=3" in detail
    assert "docker logs yugabyte" in detail


def test_classify_status_external():
    spec = startup.TECH_BY_NAME["kubernetes"]
    assert startup.classify_status(
        spec, running=False, ready=False, connector_ok=True, selected=True, cfg={"kubeconfig": ""},
    ) == startup.STATUS_EXTERNAL


def test_classify_status_skipped_optional():
    spec = startup.TECH_BY_NAME["oracle"]
    assert startup.classify_status(
        spec, running=False, ready=False, connector_ok=True, selected=False, cfg={},
    ) == startup.STATUS_SKIPPED


def test_classify_status_pass_when_ready(monkeypatch):
    monkeypatch.setenv("ECS_REDIS_PASSWORD", "set")
    spec = startup.TECH_BY_NAME["redis"]
    assert startup.classify_status(
        spec, running=True, ready=True, connector_ok=True, selected=True, cfg={"host": "redis"},
    ) == startup.STATUS_PASS


def test_detect_port_conflict_when_port_busy_without_container(monkeypatch):
    spec = startup.TECH_BY_NAME["postgresql"]
    compose = {"postgres-demo": {"host_ports": [5432], "profiles": ()}}
    monkeypatch.setattr(startup, "port_in_use", lambda _port, host="127.0.0.1": True)
    monkeypatch.setattr(startup, "find_running_container", lambda *_a, **_k: None)
    conflicts = startup.detect_port_conflicts([spec], compose)
    assert any("5432" in c for c in conflicts)


def test_resolve_credential_env_precedence(monkeypatch):
    monkeypatch.setenv("ECS_PG_PASSWORD", "from-env")
    spec = startup.TECH_BY_NAME["postgresql"]
    assert startup.resolve_credential(spec, {"password": "from-config"}) == "SET"
    monkeypatch.delenv("ECS_PG_PASSWORD", raising=False)
    assert startup.resolve_credential(spec, {"password": "from-config"}) == "SET"


def test_resolve_credential_na_not_missing():
    spec = startup.TECH_BY_NAME["linux"]
    assert startup.resolve_credential(spec, {}) == "N/A"
    assert startup.resolve_credential(spec, {}) != "MISSING"


def test_connector_summary_masks_secrets(monkeypatch):
    monkeypatch.setenv("ECS_PG_PASSWORD", "super-secret")
    spec = startup.TECH_BY_NAME["postgresql"]
    text = startup.connector_summary(spec, {"host": "postgres-demo", "port": 5432, "user": "ecs_user"})
    assert "super-secret" not in text
    assert "secret=SET" in text


def test_compose_up_uses_no_recreate_by_default(monkeypatch):
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    startup.compose_up({"redis"}, set())
    assert "--no-recreate" in captured[0]
    assert "--force-recreate" not in captured[0]


def test_compose_up_force_recreate_only_ecs(monkeypatch):
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    startup.compose_up({startup.ECS_SERVICE}, set(), force_recreate={startup.ECS_SERVICE})
    assert "--force-recreate" in captured[0]
    assert captured[0][-1] == startup.ECS_SERVICE


def test_status_only_skips_compose_up(monkeypatch):
    calls: list[tuple[set[str], set[str]]] = []

    def _record(services, profiles, **kwargs):
        calls.append((services, profiles))

    monkeypatch.setattr(startup, "docker_available", lambda: True)
    monkeypatch.setattr(startup, "compose_config_valid", lambda: (True, "valid"))
    monkeypatch.setattr(startup, "ecs_runtime", lambda: "none")
    monkeypatch.setattr(startup, "stop_conflicting_ecs_python", lambda *_: [])
    monkeypatch.setattr(startup, "ecs_port_blocked", lambda: False)
    monkeypatch.setattr(startup, "compose_up", _record)
    monkeypatch.setattr(startup, "build_rows", lambda *_a, **_k: [])
    monkeypatch.setattr(startup, "load_env", lambda: "loaded .env (read-only)")
    monkeypatch.setattr(startup, "detect_port_conflicts", lambda *_a, **_k: [])

    rc = startup.main(["--status-only"])
    assert rc == 0
    assert calls == []


def test_ecs_runtime_distinguishes_host_python(monkeypatch):
    monkeypatch.setattr(startup, "find_running_container", lambda *_a, **_k: None)
    monkeypatch.setattr(startup, "port_in_use", lambda *_a, **kwargs: True)
    monkeypatch.setattr(startup, "_pid_command", lambda _pid: "uvicorn app.main:app --port 8000")
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "999\n", ""),
    )
    assert startup.ecs_runtime() == "host-python"


def test_ecs_runtime_distinguishes_docker(monkeypatch):
    monkeypatch.setattr(startup, "find_running_container", lambda *_a, **_k: "ecs-ecs-1")
    assert startup.ecs_runtime() == "docker"


def test_stop_conflicting_ecs_python_only_uvicorn(monkeypatch):
    monkeypatch.setattr(
        startup,
        "_pid_command",
        lambda pid: "uvicorn app.main:app --port 8000" if pid == 42 else "python unrelated.py",
    )
    killed: list[str] = []

    def fake_run(cmd, **kwargs):
        if cmd and cmd[0] == "lsof":
            return subprocess.CompletedProcess(cmd, 0, "42\n99\n", "")
        if cmd and cmd[0] == "kill":
            killed.append(cmd[1])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    stopped = startup.stop_conflicting_ecs_python(8000)
    assert stopped == ["pid 42"]
    assert killed == ["42"]


def test_wait_ready_retries_until_success(monkeypatch):
    spec = startup.TECH_BY_NAME["redis"]
    attempts = {"n": 0}

    def flaky(_spec, _port):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return False, "waiting"
        return True, "PONG"

    monkeypatch.setattr(startup, "_probe_once", flaky)
    monkeypatch.setattr(startup.time, "sleep", lambda *_: None)
    ok, detail = startup.wait_ready(spec, timeout=10.0)
    assert ok is True
    assert detail == "PONG"
    assert attempts["n"] == 3


def test_default_mode_is_core():
    args = startup.parse_args([])
    assert args.core is True
    assert args.all is False


def test_probe_docker_runtime_invokes_docker_exec(monkeypatch):
    """runtime=docker must execute the probe via `docker exec` in the ECS container,
    NOT via the host-python engine path."""
    spec = startup.TECH_BY_NAME["aurora mysql"]  # probe_control = MYX-002
    host_called = {"n": 0}

    def _host(_cid):
        host_called["n"] += 1
        return False

    captured: dict[str, list] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, '{"ok": true, "rows_returned": 1}\n', "")

    monkeypatch.setattr(startup, "find_running_container", lambda *_a, **_k: "ecs-ecs-1")
    monkeypatch.setattr(startup, "list_running_containers", lambda: [{"name": "ecs-ecs-1"}])
    monkeypatch.setattr(startup, "_run_probe_on_host", _host)
    monkeypatch.setattr(subprocess, "run", fake_run)

    ok = startup.probe_connector(spec, "docker")
    assert ok is True
    # docker exec was used, targeting the detected ECS container + the control id.
    assert captured["cmd"][:3] == ["docker", "exec", "ecs-ecs-1"]
    assert "python" in captured["cmd"] and "-c" in captured["cmd"]
    assert "MYX-002" in captured["cmd"][-1]
    # the host execution path was NOT used.
    assert host_called["n"] == 0


def test_probe_host_runtime_invokes_local_execution(monkeypatch):
    """runtime=host-python must use the local engine path and NOT docker exec."""
    spec = startup.TECH_BY_NAME["aurora mysql"]
    docker_called = {"n": 0}

    def _no_docker(_cid):
        docker_called["n"] += 1
        return False

    monkeypatch.setattr(startup, "_run_probe_in_docker", _no_docker)
    monkeypatch.setattr(startup, "_run_probe_on_host", lambda _cid: True)

    ok = startup.probe_connector(spec, "host-python")
    assert ok is True
    assert docker_called["n"] == 0


def test_probe_none_runtime_skips_execution(monkeypatch):
    """runtime=none must skip execution entirely (no docker exec, no host run)."""
    spec = startup.TECH_BY_NAME["sonarqube"]  # probe_control = APP-001
    calls = {"docker": 0, "host": 0}

    monkeypatch.setattr(startup, "_run_probe_in_docker",
                        lambda _cid: calls.__setitem__("docker", calls["docker"] + 1) or False)
    monkeypatch.setattr(startup, "_run_probe_on_host",
                        lambda _cid: calls.__setitem__("host", calls["host"] + 1) or False)

    ok = startup.probe_connector(spec, "none")
    # Skipped -> reported True so a non-running ECS never manufactures a failure.
    assert ok is True
    assert calls == {"docker": 0, "host": 0}


@pytest.mark.parametrize("control_spec", ["aurora mysql", "sonarqube"])
def test_successful_docker_probe_reports_success(monkeypatch, control_spec):
    """A successful in-container probe (ok=true) reports success for MYX-002/APP-001."""
    spec = startup.TECH_BY_NAME[control_spec]

    def fake_run(cmd, **kwargs):
        # engine may emit log lines before the JSON payload; ensure we parse JSON.
        out = "INFO some log line\n" + json.dumps({"ok": True, "rows_returned": 1}) + "\n"
        return subprocess.CompletedProcess(cmd, 0, out, "")

    monkeypatch.setattr(startup, "find_running_container", lambda *_a, **_k: "ecs-ecs-1")
    monkeypatch.setattr(startup, "list_running_containers", lambda: [{"name": "ecs-ecs-1"}])
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert startup.probe_connector(spec, "docker") is True


def test_docker_probe_success_eliminates_false_warn(monkeypatch):
    """When the Docker probe succeeds, build_rows must NOT emit a false WARN/FAIL
    for MYX-002 (Aurora MySQL) purely from a host-side connector failure."""
    # Force docker runtime + a healthy, ready mysql-demo, ECS reachable.
    monkeypatch.setattr(startup, "ecs_runtime", lambda: "docker")
    monkeypatch.setattr(startup, "find_running_container",
                        lambda name, *_a, **_k: "ecs-ecs-1" if name == startup.ECS_SERVICE else "mysql-demo")
    monkeypatch.setattr(startup, "list_running_containers", lambda: [{"name": "mysql-demo"}, {"name": "ecs-ecs-1"}])
    monkeypatch.setattr(startup, "load_compose_services", lambda: {"mysql-demo": {"host_ports": [3306], "profiles": ("db-targets",)}})
    monkeypatch.setattr(startup, "_probe_once", lambda _s, _p: (True, "SELECT 1"))
    monkeypatch.setattr(startup, "load_connector_config", lambda _n: {"host": "mysql-demo", "user": "ecs_user", "password": "ecs_password"})
    monkeypatch.setattr(startup, "dns_from_container", lambda *_a, **_k: (True, "10.0.0.2"))
    monkeypatch.setattr(startup, "ecs_app_ready", lambda: True)
    # In-container probe succeeds (the real behaviour the user verified manually).
    monkeypatch.setattr(startup, "_run_probe_in_docker", lambda _cid: True)
    # Host path would fail if (wrongly) used — proves docker path is taken.
    monkeypatch.setattr(startup, "_run_probe_on_host", lambda _cid: False)

    rows = startup.build_rows({"mysql-demo"}, wait=False, probe_connectors=True)
    myx = next(r for r in rows if r["technology"] == "Aurora MySQL")
    assert myx["status"] == startup.STATUS_PASS, myx


def test_json_output_includes_matrix(monkeypatch, capsys):
    monkeypatch.setattr(startup, "docker_available", lambda: True)
    monkeypatch.setattr(startup, "compose_config_valid", lambda: (True, "valid"))
    monkeypatch.setattr(startup, "ecs_runtime", lambda: "docker")
    monkeypatch.setattr(startup, "stop_conflicting_ecs_python", lambda *_: [])
    monkeypatch.setattr(startup, "ecs_port_blocked", lambda: False)
    monkeypatch.setattr(startup, "compose_up", lambda *_a, **_k: None)
    monkeypatch.setattr(startup, "wait_core_backing", lambda *_: [])
    monkeypatch.setattr(startup, "ecs_needs_recreate", lambda: (False, ""))
    monkeypatch.setattr(startup, "ecs_app_ready", lambda: True)
    monkeypatch.setattr(startup, "load_env", lambda: "test")
    monkeypatch.setattr(startup, "detect_port_conflicts", lambda *_a, **_k: [])
    monkeypatch.setattr(
        startup,
        "build_rows",
        lambda *_a, **_k: [{"technology": "PostgreSQL", "target": "postgres-demo", "container": "-",
                            "dns": "postgres-demo", "check": "-", "connector": "ok", "status": "PASS"}],
    )
    rc = startup.main(["--core", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["matrix"]
    assert payload["ecs_runtime"] == "docker"
