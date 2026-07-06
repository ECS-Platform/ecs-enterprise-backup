"""Unit tests for scripts/check_predefined_technology_environment.py.

Focus: resilient Docker container detection that does NOT depend on the Compose
project prefix, for the INFRASTRUCTURE demo targets (NGINX, Linux/ubuntu-demo,
RHEL 8/9, Oracle). No live Docker is required — ``docker ps`` output is mocked.

Mirrors the resilient-detection approach already covered for the extended and DB
diagnostics: match by Compose service label, exact container name, and safe name
heuristics (project-prefixed / startswith).
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

diag = importlib.import_module("scripts.check_predefined_technology_environment")


def _mk_run(rows, returncode: int = 0):
    """Fake subprocess.run yielding tab-separated `docker ps` rows.

    Each row is (name, compose_service_label, compose_project_label).
    """
    stdout = "".join(f"{n}\t{s}\t{p}\n" for (n, s, p) in rows)

    class _R:
        pass

    def _run(*_a, **_k):
        r = _R()
        r.returncode = returncode
        r.stdout = stdout
        r.stderr = ""
        return r

    return _run


# Realistic infra demo set. All declare container_name so name == service today,
# but detection must still work under any project prefix / label-only match.
_INFRA_ROWS = [
    ("nginx-demo", "nginx-demo", "ecs"),
    ("ubuntu-demo", "ubuntu-demo", "ecs"),
    ("rhel8-demo", "rhel8-demo", "ecs"),
    ("rhel9-demo", "rhel9-demo", "ecs"),
    ("oracle-demo", "oracle-demo", "ecs"),
]


# --------------------------------------------------------------------------- #
# find_running_container / container_running
# --------------------------------------------------------------------------- #
def test_infra_exact_names_detected(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_INFRA_ROWS))
    for name in ("nginx-demo", "ubuntu-demo", "rhel8-demo", "rhel9-demo", "oracle-demo"):
        assert diag.container_running(name) is True, name


def test_infra_detection_independent_of_project_prefix(monkeypatch):
    rows = [
        ("myproj-nginx-demo-1", "nginx-demo", "myproj"),
        ("myproj-ubuntu-demo-1", "ubuntu-demo", "myproj"),
        ("myproj-rhel8-demo-1", "rhel8-demo", "myproj"),
        ("myproj-rhel9-demo-1", "rhel9-demo", "myproj"),
        ("myproj-oracle-demo-1", "oracle-demo", "myproj"),
    ]
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("nginx-demo") is True
    assert diag.container_running("ubuntu-demo") is True
    assert diag.container_running("rhel8-demo") is True
    assert diag.container_running("rhel9-demo") is True
    assert diag.container_running("oracle-demo") is True
    running = diag.list_running_containers()
    assert diag.find_running_container("rhel9-demo", running) == "myproj-rhel9-demo-1"


def test_infra_detection_via_service_label_only(monkeypatch):
    """Different container name, correct compose service label still matches."""
    rows = [("weird-name-abc", "nginx-demo", "ecs")]
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("nginx-demo") is True
    assert diag.find_running_container("nginx-demo", diag.list_running_containers()) == "weird-name-abc"


def test_infra_detection_via_name_when_labels_absent(monkeypatch):
    rows = [("ecs-rhel8-demo-1", "", ""), ("ecs-ubuntu-demo-1", "", "")]
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("rhel8-demo") is True
    assert diag.container_running("ubuntu-demo") is True


def test_infra_absent_is_false(monkeypatch):
    rows = [("nginx-demo", "nginx-demo", "ecs")]  # only nginx running
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("oracle-demo") is False
    assert diag.container_running("rhel9-demo") is False


def test_infra_docker_down_is_none(monkeypatch):
    def _boom(*_a, **_k):
        raise FileNotFoundError("docker missing")

    monkeypatch.setattr(diag.subprocess, "run", _boom)
    assert diag.list_running_containers() is None
    assert diag.container_running("nginx-demo") is None


# --------------------------------------------------------------------------- #
# build_report end-to-end (mocked docker)
# --------------------------------------------------------------------------- #
def _args(**over):
    base = dict(expect_oracle=False, no_docker_check=False, json=False)
    base.update(over)
    return argparse.Namespace(**base)


def test_build_report_all_infra_running(monkeypatch):
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_INFRA_ROWS))
    report = diag.build_report(_args())
    by_tech = {c["technology"]: c for c in report["checks"]}
    assert by_tech["NGINX"]["container_status"] == "RUNNING"
    assert by_tech["Linux"]["container_status"] == "RUNNING"
    assert by_tech["Red Hat Enterprise Linux 8.x"]["container_status"] == "RUNNING"
    assert by_tech["Red Hat Enterprise Linux 9.x"]["container_status"] == "RUNNING"
    assert by_tech["Oracle"]["container_status"] == "RUNNING"
    assert report["ok"] is True


def test_build_report_records_matched_container_with_prefix(monkeypatch):
    rows = [("ecs-nginx-demo-1", "nginx-demo", "ecs")]
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    report = diag.build_report(_args())
    nginx = next(c for c in report["checks"] if c["technology"] == "NGINX")
    assert nginx["container_status"] == "RUNNING"
    assert nginx["matched_container"] == "ecs-nginx-demo-1"


def test_oracle_optional_unless_expected(monkeypatch):
    """Oracle missing does not fail overall unless --expect-oracle."""
    rows = [
        ("nginx-demo", "nginx-demo", "ecs"),
        ("ubuntu-demo", "ubuntu-demo", "ecs"),
        ("rhel8-demo", "rhel8-demo", "ecs"),
        ("rhel9-demo", "rhel9-demo", "ecs"),
    ]  # no oracle-demo
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))

    report = diag.build_report(_args(expect_oracle=False))
    assert report["ok"] is True  # oracle not expected -> pass

    report_strict = diag.build_report(_args(expect_oracle=True))
    assert report_strict["ok"] is False  # oracle expected + missing -> fail
    oracle = next(c for c in report_strict["checks"] if c["technology"] == "Oracle")
    assert oracle["container_status"] == "NOT RUNNING"


def test_no_docker_check_skips_docker(monkeypatch):
    def _fail(*_a, **_k):
        raise AssertionError("docker must not be queried under --no-docker-check")

    monkeypatch.setattr(diag.subprocess, "run", _fail)
    report = diag.build_report(_args(no_docker_check=True))
    for c in report["checks"]:
        assert c["container_status"] is None
    assert report["ok"] is True


def test_docker_unavailable_does_not_fail(monkeypatch):
    """Docker down -> UNKNOWN, and cannot prove failure (ok stays True)."""
    monkeypatch.setattr(diag, "docker_available", lambda: True)

    def _boom(*_a, **_k):
        raise FileNotFoundError("docker missing")

    monkeypatch.setattr(diag.subprocess, "run", _boom)
    report = diag.build_report(_args(expect_oracle=True))
    for c in report["checks"]:
        assert c["container_status"] == "UNKNOWN"
    assert report["ok"] is True


def test_report_never_leaks_oracle_password(monkeypatch):
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_INFRA_ROWS))
    monkeypatch.setenv("ECS_ORACLE_PASSWORD", "super-secret-oracle")
    report = diag.build_report(_args())
    text = diag.render_text(report)
    assert "super-secret-oracle" not in text
