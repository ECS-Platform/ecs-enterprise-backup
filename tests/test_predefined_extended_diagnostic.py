"""Unit tests for scripts/check_predefined_extended_environment.py.

Focus: resilient Docker container detection that does NOT depend on the Compose
project prefix. No live Docker is required — ``docker ps`` output is mocked.

Regression under test: a Redis container named ``ecs-redis-1`` (Compose default
naming ``<project>-<service>-<index>``, service label ``redis``) must be detected
as RUNNING even though the connector's configured container short-name is
``redis`` — the previous exact ``name=^/redis$`` filter reported NOT RUNNING.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

diag = importlib.import_module("scripts.check_predefined_extended_environment")


# --------------------------------------------------------------------------- #
# docker ps mock
# --------------------------------------------------------------------------- #
def _mk_run(rows: list[tuple[str, str, str]], returncode: int = 0):
    """Build a fake subprocess.run returning tab-separated `docker ps` rows.

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


# A realistic running set: Redis uses default compose naming (ecs-redis-1),
# others declare container_name so name == service.
_DEFAULT_ROWS = [
    ("ecs-redis-1", "redis", "ecs"),
    ("mongodb-demo", "mongodb-demo", "ecs"),
    ("apache-demo", "apache-demo", "ecs"),
    ("tomcat-demo", "tomcat-demo", "ecs"),
]


# --------------------------------------------------------------------------- #
# find_running_container / container_running
# --------------------------------------------------------------------------- #
def test_redis_detected_via_compose_service_label(monkeypatch):
    """`ecs-redis-1` (service=redis) is matched for target `redis`."""
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS))
    assert diag.container_running("redis") is True
    running = diag.list_running_containers()
    assert diag.find_running_container("redis", running) == "ecs-redis-1"


def test_detection_independent_of_project_prefix(monkeypatch):
    """Any Compose project prefix still resolves (myproj-redis-1)."""
    rows = [("myproj-redis-1", "redis", "myproj")]
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("redis") is True
    assert diag.find_running_container("redis", diag.list_running_containers()) == "myproj-redis-1"


def test_detection_via_prefixless_name_without_labels(monkeypatch):
    """When labels are empty, name heuristics still catch project-prefixed names."""
    rows = [("ecs-redis-1", "", "")]  # no compose labels available
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("redis") is True


def test_exact_container_name_matches(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS))
    assert diag.container_running("mongodb-demo") is True
    assert diag.container_running("apache-demo") is True
    assert diag.container_running("tomcat-demo") is True


def test_not_running_when_absent(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS))
    # sqlserver-demo is not in the running set
    assert diag.container_running("sqlserver-demo") is False
    assert diag.find_running_container("sqlserver-demo", diag.list_running_containers()) is None


def test_docker_unavailable_returns_none(monkeypatch):
    def _boom(*_a, **_k):
        raise FileNotFoundError("docker not installed")

    monkeypatch.setattr(diag.subprocess, "run", _boom)
    assert diag.list_running_containers() is None
    assert diag.container_running("redis") is None


def test_nonzero_returncode_returns_none(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS, returncode=1))
    assert diag.list_running_containers() is None
    assert diag.container_running("redis") is None


def test_name_matcher_strategies():
    m = diag._container_name_matches
    assert m("redis", "redis") is True            # exact
    assert m("redis", "ecs-redis-1") is True       # <project>-<svc>-<index>
    assert m("redis", "ecs-redis") is True         # startswith ecs-<target>
    assert m("redis", "redis-demo") is True        # startswith target
    assert m("redis", "myproj-redis-1") is True    # any project prefix
    assert m("redis", "redisson") is True          # startswith target (acceptable superset)
    assert m("redis", "cache") is False            # unrelated
    assert m("redis", "") is False
    assert m("", "redis") is False


# --------------------------------------------------------------------------- #
# build_report end-to-end (mocked docker)
# --------------------------------------------------------------------------- #
def _args(**over):
    base = dict(strict=False, no_docker_check=False, json=False)
    base.update(over)
    return argparse.Namespace(**base)


def test_build_report_marks_redis_running_and_records_matched(monkeypatch):
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS))
    report = diag.build_report(_args())
    by_tech = {c["technology"]: c for c in report["checks"]}
    assert by_tech["Redis"]["status"] == "RUNNING"
    assert by_tech["Redis"]["matched_container"] == "ecs-redis-1"
    assert by_tech["Apache HTTPD"]["status"] == "RUNNING"
    # sqlserver-demo not running -> NOT RUNNING but never crashes
    assert by_tech["SQL Server"]["status"] == "NOT RUNNING"


def test_no_docker_check_reports_none_status(monkeypatch):
    # Even if docker would be queried, --no-docker-check must skip it entirely.
    def _fail(*_a, **_k):
        raise AssertionError("docker must not be queried under --no-docker-check")

    monkeypatch.setattr(diag.subprocess, "run", _fail)
    report = diag.build_report(_args(no_docker_check=True))
    by_tech = {c["technology"]: c for c in report["checks"]}
    assert by_tech["Redis"]["status"] is None
    assert by_tech["Redis"]["matched_container"] is None


def test_strict_fails_when_expected_container_missing(monkeypatch):
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS))
    report = diag.build_report(_args(strict=True))
    # sqlserver-demo is NOT RUNNING, so strict mode should fail overall.
    assert report["ok"] is False


def test_report_never_leaks_secrets(monkeypatch):
    monkeypatch.setattr(diag, "docker_available", lambda: True)
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DEFAULT_ROWS))
    monkeypatch.setenv("ECS_REDIS_PASSWORD", "super-secret-value")
    monkeypatch.setenv("ECS_SERVICENOW_CLIENT_SECRET", "snow-secret")
    report = diag.build_report(_args())
    text = diag.render_text(report)
    assert "super-secret-value" not in text
    assert "snow-secret" not in text
