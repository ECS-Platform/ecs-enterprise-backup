"""Unit tests for scripts/check_predefined_db_environment.py.

No live Docker or databases are required — socket connectivity, docker subprocess
calls, and DB driver connections are mocked. Focus areas:
  * password masking (SET/MISSING; never the real value)
  * missing .env handling
  * successful PostgreSQL / YugabyteDB config checks
  * MySQL authentication failure -> actionable recommendation
  * JSON output mode does not reveal passwords
  * skip flags
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

diag = importlib.import_module("scripts.check_predefined_db_environment")


def _args(**over):
    base = dict(
        skip_postgres=False, skip_yugabyte=False, skip_mysql=False,
        no_docker_check=True, json=False,
    )
    base.update(over)
    return argparse.Namespace(**base)


# --------------------------------------------------------------------------- #
# Password masking
# --------------------------------------------------------------------------- #
def test_mask_set_and_missing():
    assert diag._mask("hunter2") == "SET"
    assert diag._mask("") == "MISSING"
    assert diag._mask(None) == "MISSING"


# --------------------------------------------------------------------------- #
# .env handling
# --------------------------------------------------------------------------- #
def test_missing_env_handled(monkeypatch, tmp_path):
    # Point ROOT at a temp dir with no .env; load_env must not raise.
    monkeypatch.setattr(diag, "ROOT", tmp_path)
    status = diag.load_env()
    assert "no .env" in status.lower()


# --------------------------------------------------------------------------- #
# Successful PostgreSQL / YugabyteDB checks (mock TCP + login)
# --------------------------------------------------------------------------- #
def test_postgres_success(monkeypatch):
    monkeypatch.setattr(diag, "tcp_check", lambda h, p, timeout=3.0: True)
    monkeypatch.setattr(diag, "_login_postgres", lambda cfg: (True, "SELECT 1 succeeded"))
    cfg = {"host": "localhost", "port": 5432, "database": "ecs_demo",
           "user": "ecs_user", "password": "secret", "sslmode": "disable", "timeout_sec": 5}
    res = diag.check_database("PostgreSQL", cfg, "postgres-demo", False, "sslmode", diag._login_postgres)
    assert res["ok"] is True
    assert res["tcp"] == "PASS"
    assert res["login"] == "PASS"
    assert res["config"]["password"] == "SET"  # masked


def test_yugabyte_success(monkeypatch):
    monkeypatch.setattr(diag, "tcp_check", lambda h, p, timeout=3.0: True)
    cfg = {"host": "localhost", "port": 5433, "database": "yugabyte",
           "user": "yugabyte", "password": "", "sslmode": "disable", "timeout_sec": 5}
    res = diag.check_database(
        "YugabyteDB", cfg, "yugabyte", False, "sslmode",
        lambda c: (True, "SELECT 1 succeeded"),
    )
    assert res["ok"] is True
    assert res["config"]["password"] == "MISSING"  # no password set


# --------------------------------------------------------------------------- #
# MySQL authentication failure -> actionable recommendation
# --------------------------------------------------------------------------- #
def test_mysql_auth_failure_actionable(monkeypatch):
    monkeypatch.setattr(diag, "tcp_check", lambda h, p, timeout=3.0: True)  # reachable
    cfg = {"host": "localhost", "port": 3306, "database": "ecs_demo",
           "user": "root", "password": "wrong", "ssl": False, "timeout_sec": 5}
    res = diag.check_database(
        "Aurora MySQL", cfg, "mysql-demo", False, "ssl",
        lambda c: (False, "Authentication failed."),
    )
    assert res["ok"] is False
    assert res["tcp"] == "PASS"
    assert res["login"] == "FAIL"
    assert res["reason"] == "Authentication failed."
    action = res["recommended_action"]
    assert "MYSQL_ROOT_PASSWORD" in action or "ECS_MYSQL_USER" in action
    assert "ECS_MYSQL_PASSWORD" in action


def test_unreachable_recommends_start_container(monkeypatch):
    monkeypatch.setattr(diag, "tcp_check", lambda h, p, timeout=3.0: False)  # unreachable
    cfg = {"host": "localhost", "port": 5432, "database": "d", "user": "u",
           "password": "p", "sslmode": "", "timeout_sec": 5}
    res = diag.check_database("PostgreSQL", cfg, "postgres-demo", False, "sslmode", diag._login_postgres)
    assert res["ok"] is False
    assert res["tcp"] == "FAIL"
    assert "not reachable" in res["recommended_action"].lower()


# --------------------------------------------------------------------------- #
# Error classification (never echoes credentials)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Access denied for user 'root'@'localhost' (using password: YES)", "Authentication failed."),
        ("password authentication failed for user \"ecs_user\"", "Authentication failed."),
        ("Unknown database 'nope'", "Database not found."),
        ("connection timed out", "Connection timed out."),
        ("could not connect to server: Connection refused", "Connection refused / host unreachable."),
    ],
)
def test_classify_error_is_safe(raw, expected):
    out = diag._classify_error(raw)
    assert out == expected
    # The classified reason must not leak the raw message content.
    assert "root" not in out
    assert "ecs_user" not in out


# --------------------------------------------------------------------------- #
# JSON output mode does not reveal passwords
# --------------------------------------------------------------------------- #
def test_json_output_masks_passwords(monkeypatch, capsys):
    monkeypatch.setenv("ECS_PG_PASSWORD", "pg-super-secret")
    monkeypatch.setenv("ECS_MYSQL_PASSWORD", "mysql-super-secret")
    monkeypatch.setattr(diag, "tcp_check", lambda h, p, timeout=3.0: False)
    monkeypatch.setattr(diag, "load_env", lambda: "test")
    rc = diag.main([
        "--json", "--no-docker-check", "--skip-yugabyte",
    ])
    out = capsys.readouterr().out
    assert "pg-super-secret" not in out
    assert "mysql-super-secret" not in out
    data = json.loads(out)
    for check in data["checks"]:
        assert check["config"]["password"] in ("SET", "MISSING")
    assert rc == 1  # unreachable -> failure exit code


# --------------------------------------------------------------------------- #
# Skip flags
# --------------------------------------------------------------------------- #
def test_skip_flags_limit_checks(monkeypatch):
    monkeypatch.setattr(diag, "tcp_check", lambda h, p, timeout=3.0: True)
    monkeypatch.setattr(diag, "_login_postgres", lambda cfg: (True, "ok"))
    monkeypatch.setattr(diag, "_login_mysql", lambda cfg: (True, "ok"))
    report = diag.build_report(_args(skip_postgres=True, skip_mysql=True))
    techs = {c["technology"] for c in report["checks"]}
    assert techs == {"YugabyteDB"}


def test_all_skipped_is_ok(monkeypatch):
    report = diag.build_report(_args(skip_postgres=True, skip_yugabyte=True, skip_mysql=True))
    assert report["checks"] == []
    assert report["ok"] is True


# --------------------------------------------------------------------------- #
# Login functions handle missing drivers / mocked drivers safely
# --------------------------------------------------------------------------- #
def test_login_mysql_missing_driver(monkeypatch):
    monkeypatch.setitem(sys.modules, "pymysql", None)  # force ImportError
    ok, reason = diag._login_mysql(
        {"host": "h", "port": 3306, "database": "d", "user": "u", "password": "p", "timeout_sec": 2}
    )
    assert ok is False
    assert "PyMySQL" in reason


def test_login_mysql_success_with_mock(monkeypatch):
    """A fully mocked pymysql module yields a successful SELECT 1."""
    import types

    class _Cursor:
        def execute(self, q):
            return None

        def fetchone(self):
            return (1,)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Conn:
        def cursor(self):
            return _Cursor()

        def close(self):
            return None

    fake = types.ModuleType("pymysql")
    fake.connect = lambda **kw: _Conn()
    monkeypatch.setitem(sys.modules, "pymysql", fake)
    ok, reason = diag._login_mysql(
        {"host": "h", "port": 3306, "database": "d", "user": "u", "password": "p", "timeout_sec": 2}
    )
    assert ok is True
    assert "SELECT 1" in reason


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


# Realistic running set for the DB demo targets. Yugabyte uses Compose default
# naming (ecs-yugabyte-1, service=yugabyte); postgres-demo / mysql-demo declare
# container_name so name == service.
_DB_ROWS = [
    ("postgres-demo", "postgres-demo", "ecs"),
    ("ecs-yugabyte-1", "yugabyte", "ecs"),
    ("mysql-demo", "mysql-demo", "ecs"),
]


def test_container_running_mocked(monkeypatch):
    """Back-compat: exact container name still detected; absent -> False."""
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DB_ROWS))
    assert diag.container_running("postgres-demo") is True
    assert diag.container_running("not-there") is False


def test_db_detection_exact_names(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DB_ROWS))
    assert diag.container_running("postgres-demo") is True
    assert diag.container_running("mysql-demo") is True


def test_db_detection_yugabyte_via_service_label(monkeypatch):
    """`ecs-yugabyte-1` (service=yugabyte) is matched for target `yugabyte`."""
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DB_ROWS))
    assert diag.container_running("yugabyte") is True
    running = diag.list_running_containers()
    assert diag.find_running_container("yugabyte", running) == "ecs-yugabyte-1"


def test_db_detection_independent_of_project_prefix(monkeypatch):
    rows = [
        ("myproj-postgres-demo-1", "postgres-demo", "myproj"),
        ("myproj-yugabyte-1", "yugabyte", "myproj"),
        ("myproj-mysql-demo-1", "mysql-demo", "myproj"),
    ]
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("postgres-demo") is True
    assert diag.container_running("yugabyte") is True
    assert diag.container_running("mysql-demo") is True


def test_db_detection_via_name_when_labels_absent(monkeypatch):
    rows = [("ecs-yugabyte-1", "", ""), ("ecs-postgres-demo-1", "", "")]
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(rows))
    assert diag.container_running("yugabyte") is True
    assert diag.container_running("postgres-demo") is True


def test_db_detection_absent_is_false(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DB_ROWS))
    assert diag.container_running("sqlserver-demo") is False


def test_db_detection_docker_down_is_none(monkeypatch):
    def _boom(*_a, **_k):
        raise FileNotFoundError("docker missing")

    monkeypatch.setattr(diag.subprocess, "run", _boom)
    assert diag.list_running_containers() is None
    assert diag.container_running("postgres-demo") is None


def test_db_detection_nonzero_returncode_is_none(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DB_ROWS, returncode=1))
    assert diag.container_running("postgres-demo") is None


def test_db_check_database_records_matched_container(monkeypatch):
    """check_database() records the matched container name for yugabyte."""
    monkeypatch.setattr(diag.subprocess, "run", _mk_run(_DB_ROWS))
    monkeypatch.setattr(diag, "tcp_check", lambda *a, **k: False)  # no live DB
    res = diag.check_database(
        "YugabyteDB",
        {"host": "localhost", "port": 5433, "database": "yugabyte", "user": "u",
         "password": "p", "sslmode": ""},
        "yugabyte", True, "sslmode", lambda cfg: (False, "n/a"),
    )
    assert res["container_status"] == "RUNNING"
    assert res["matched_container"] == "ecs-yugabyte-1"
