"""pytest wiring for the ECS functional automation framework.

* Safe by default: functional tests are SKIPPED at collection unless execution is explicitly enabled
  (``--run-functional`` or ``ECS_FT_ENABLE=1``), so a plain ``pytest tests/`` never runs them against an environment.
* Markers (uc01..uc20 + functional categories) are registered here - no root pytest.ini is created or modified.
* Fixtures: environment config, API client (+ per-persona clients), database, storage, scheduler, test data, users/roles,
  and a ``case_runner`` that binds each workbook Functional Test ID to its orchestration.
* Hooks record result rows (reporting) and capture failure evidence. Nothing here executes at import time.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:  # same bootstrap as the repo-root conftest.py
    sys.path.insert(0, str(_ROOT))

from .framework import registry  # noqa: E402
from .framework.config import FunctionalConfig, load_config  # noqa: E402
from .framework.context import FunctionalContext  # noqa: E402
from .framework.errors import CapabilityBlocked  # noqa: E402
from .framework.results import ResultRecorder, ResultRow  # noqa: E402
from .framework.spec import run_case  # noqa: E402

UC_MARKERS = [f"uc{n:02d}" for n in range(1, 21)]
CATEGORY_MARKERS = {
    "functional": "workbook functional test", "api": "drives ECS HTTP API", "ui": "drives ECS UI (Playwright)",
    "database": "validates PostgreSQL state", "integration": "multi-component / connector / scheduler flow",
    "security": "security-related case", "rbac": "role-based access case", "audit": "audit-trail verification",
    "notification": "notification verification", "integrity": "hash / integrity verification", "dashboard": "dashboard / KPI case",
    "reporting": "report generation / export", "ai": "AI query / grounding / summary", "retention": "retention / archival / lifecycle",
    "concurrency": "parallel-operation scenario", "performance": "timed response vs SLA threshold",
    "negative": "workbook Test Type = Negative", "positive": "workbook Test Type = Positive",
    "priority_high": "workbook Priority = High", "priority_medium": "workbook Priority = Medium",
}

_RECORDER = ResultRecorder()


def pytest_addoption(parser):
    g = parser.getgroup("ecs-functional")
    g.addoption("--run-functional", action="store_true", default=False,
                help="Enable execution of the ECS functional suite (otherwise skipped). Same as ECS_FT_ENABLE=1.")
    g.addoption("--ft-env", action="store", default=None, help="Functional environment name (overrides ECS_FT_ENV).")


def pytest_configure(config):
    for m in UC_MARKERS:
        config.addinivalue_line("markers", f"{m}: ECS use case {m.upper()}")
    for name, desc in CATEGORY_MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {desc}")
    config.addinivalue_line("markers", "workbook_id(id): workbook Functional Test ID this test automates")
    if config.getoption("--ft-env", default=None):
        os.environ["ECS_FT_ENV"] = config.getoption("--ft-env")


def _enabled(config) -> bool:
    return bool(config.getoption("--run-functional") or os.environ.get("ECS_FT_ENABLE", "").lower() in ("1", "true", "yes"))


def pytest_collection_modifyitems(config, items):
    if _enabled(config):
        return
    skip = pytest.mark.skip(reason="ECS functional suite disabled (pass --run-functional or set ECS_FT_ENABLE=1)")
    for item in items:
        if "/tests/functional/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(skip)


# ---- fixtures ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def ft_config() -> FunctionalConfig:
    return load_config()


@pytest.fixture
def ft_context(ft_config):
    ctx = FunctionalContext(ft_config)
    yield ctx
    ctx.close()


@pytest.fixture
def api_client(ft_context):
    return ft_context.api


@pytest.fixture
def persona_client(ft_context):
    """Factory: ``persona_client('auditor')`` -> API client authenticated (per ECS auth mode) as that real ECS persona."""
    return ft_context.as_persona


@pytest.fixture
def authenticated_client(ft_context):
    return ft_context.as_persona("owner")


@pytest.fixture
def db(ft_context):
    return ft_context.db


@pytest.fixture
def storage(ft_context):
    return ft_context.storage


@pytest.fixture
def scheduler(ft_context):
    return ft_context.scheduler


@pytest.fixture
def test_data(ft_context):
    return ft_context.data


@pytest.fixture(scope="session")
def users(ft_config):
    """Personas = the real ECS roles declared in config/test_data.yaml."""
    return dict(ft_config.personas)


@pytest.fixture(scope="session")
def roles(ft_config):
    return ft_config.test_data.get("rbac_expectations", {})


@pytest.fixture
def ui(ft_context):
    """Playwright session (lazy; skipped when UI automation is disabled / Playwright missing)."""
    try:
        yield ft_context.ui()
    except CapabilityBlocked as exc:
        pytest.skip(exc.reason)


@pytest.fixture
def case_runner(ft_context):
    def run(case_id: str) -> None:
        try:
            run_case(case_id, ft_context)
        except CapabilityBlocked as blocked:
            pytest.skip(f"{blocked.reason} [requires: {blocked.requires or 'n/a'}]")

    return run


# ---- reporting + failure evidence hooks -------------------------------------------------------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    marker = item.get_closest_marker("workbook_id")
    if marker is None or rep.when not in ("call", "setup"):
        return
    if rep.when == "setup" and not rep.skipped and not rep.failed:
        return
    ctx = item.funcargs.get("ft_context")
    tid = marker.args[0]
    try:
        defn = registry.get(tid)
    except KeyError:
        return
    row = ResultRow(test_id=tid, uc_id=defn.uc, test_name=defn.name, priority=defn.priority, test_type=defn.type,
                    status="passed" if rep.passed else ("skipped" if rep.skipped else "failed"), duration_sec=round(rep.duration, 3))
    if rep.failed:
        row.error = str(rep.longrepr)[-2000:]
        if ctx is not None:
            try:
                from .framework.evidence_capture import capture_failure

                row.evidence = capture_failure(ctx, tid, str(rep.longrepr))
            except Exception as exc:  # noqa: BLE001 - never mask the real failure
                row.evidence = {"capture_error": str(exc)}
    if rep.skipped:
        row.skip_reason = str(rep.longrepr[-1]) if isinstance(rep.longrepr, tuple) else str(rep.longrepr)
        if "functional suite disabled" in row.skip_reason:
            return  # collection-time guard, not an execution result
    if ctx is not None:
        row.request_id = ctx.correlation.last("request_id")
        row.execution_id = ctx.correlation.last("run_id")
        row.evidence_id = ctx.correlation.last("evidence_id")
    _RECORDER.add(row)


def pytest_sessionfinish(session, exitstatus):
    _RECORDER.write()  # no-op when nothing ran (e.g. everything skipped at collection)
