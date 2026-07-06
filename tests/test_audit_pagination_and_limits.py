"""Pagination + response-limit tests for the Audit Intelligence API.

Verifies that large/list responses are bounded and that invalid pagination
parameters are handled safely (coerced to defaults, never a crash, never an
unbounded payload). Covers assets, evidence/repository, observations, runs,
mapping, and packs.

Runs against the FastAPI app via TestClient in DEMO_MODE (auth bypassed). Offline.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.routes.routes_audit_intelligence import (
    _DEFAULT_LIMIT,
    _MAX_LIMIT,
    _paginate,
)

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"


@pytest.fixture(autouse=True)
def _clean():
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()
    yield
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()


def _get(path: str):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}{Q}")


def _seed_evidence(n: int) -> None:
    for i in range(n):
        repo.store_evidence(
            control_id=f"NGX-{i:03d}", content=f"content-{i}", technology="NGINX",
            asset_id=f"web-{i}", frameworks=("PCI DSS",), verdict="PASS",
        )


def _seed_observations(n: int) -> None:
    from modules.audit_intelligence.models import ValidationResult, VERDICT_FAIL

    for i in range(n):
        vr = ValidationResult(
            control_id=f"NGX-{i:03d}", technology="NGINX", verdict=VERDICT_FAIL,
            control_status="Non-Compliant", rule_id="assertion.negative_signal",
            frameworks=("PCI DSS",), rationale=f"disabled-{i}",
        )
        obs.generate_observation(vr, asset_id=f"web-{i}")


# --------------------------------------------------------------------------- #
# _paginate helper unit tests (fast, no app)
# --------------------------------------------------------------------------- #
def test_paginate_defaults_and_meta():
    items = list(range(500))
    page, meta = _paginate(items, _DEFAULT_LIMIT, 0)
    assert len(page) == _DEFAULT_LIMIT
    assert meta == {"total": 500, "limit": _DEFAULT_LIMIT, "offset": 0,
                    "returned": _DEFAULT_LIMIT, "has_more": True}


def test_paginate_clamps_to_max_limit():
    items = list(range(5000))
    page, meta = _paginate(items, 999999, 0)
    assert len(page) == _MAX_LIMIT
    assert meta["limit"] == _MAX_LIMIT


def test_paginate_handles_invalid_params():
    items = list(range(10))
    # Non-numeric / negative / zero limit -> default; negative offset -> 0.
    page, meta = _paginate(items, "abc", -5)  # type: ignore[arg-type]
    assert meta["limit"] == _DEFAULT_LIMIT and meta["offset"] == 0
    assert page == items
    page, meta = _paginate(items, 0, "xyz")  # type: ignore[arg-type]
    assert meta["limit"] == _DEFAULT_LIMIT and meta["offset"] == 0


def test_paginate_handles_non_list_and_none():
    page, meta = _paginate(None, 10, 0)  # type: ignore[arg-type]
    assert page == [] and meta["total"] == 0
    page, meta = _paginate((1, 2, 3), 2, 0)
    assert page == [1, 2] and meta["total"] == 3


def test_paginate_offset_past_end_is_empty():
    page, meta = _paginate(list(range(5)), 10, 100)
    assert page == [] and meta["returned"] == 0 and meta["has_more"] is False


# --------------------------------------------------------------------------- #
# Evidence / repository pagination
# --------------------------------------------------------------------------- #
def test_evidence_pagination_limit_and_offset():
    _seed_evidence(25)
    r1 = _get("/api/audit/evidence?limit=10&offset=0")
    assert r1.status_code == 200
    b1 = r1.json()
    assert len(b1["evidence"]) == 10
    assert b1["page"]["total"] == 25 and b1["page"]["has_more"] is True

    r2 = _get("/api/audit/evidence?limit=10&offset=20")
    b2 = r2.json()
    assert len(b2["evidence"]) == 5 and b2["page"]["has_more"] is False


def test_repository_alias_pagination():
    _seed_evidence(15)
    r = _get("/api/audit/repository?limit=5&offset=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body["evidence"]) == 5
    assert body["page"]["offset"] == 5 and body["page"]["total"] == 15


def test_evidence_max_limit_enforced():
    _seed_evidence(3)
    r = _get("/api/audit/evidence?limit=10000000")
    assert r.status_code == 200
    assert r.json()["page"]["limit"] == _MAX_LIMIT


def test_evidence_invalid_params_do_not_crash():
    _seed_evidence(3)
    for qs in ("limit=abc", "offset=-10", "limit=-1&offset=notanint", "limit=0"):
        r = _get(f"/api/audit/evidence?{qs}")
        assert r.status_code == 200, f"{qs} -> {r.status_code}"
        assert r.json()["ok"] is True
        assert r.json()["page"]["limit"] <= _MAX_LIMIT


# --------------------------------------------------------------------------- #
# Observations pagination
# --------------------------------------------------------------------------- #
def test_observations_pagination():
    _seed_observations(12)
    r = _get("/api/audit/observations?limit=5&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert len(body["observations"]) == 5
    assert body["page"]["total"] == 12 and body["page"]["has_more"] is True


def test_observations_invalid_params_safe():
    _seed_observations(4)
    r = _get("/api/audit/observations?limit=notnum&offset=-3")
    assert r.status_code == 200
    assert r.json()["page"]["limit"] == _DEFAULT_LIMIT


# --------------------------------------------------------------------------- #
# Runs pagination
# --------------------------------------------------------------------------- #
def test_runs_pagination():
    for _ in range(6):
        orch.create_run(scope_kind="control", scope_value="NGX-001")
    r = _get("/api/audit/runs?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert len(body["runs"]) == 2
    assert body["page"]["total"] == 6 and body["page"]["has_more"] is True


# --------------------------------------------------------------------------- #
# Assets pagination (already present; verify contract holds)
# --------------------------------------------------------------------------- #
def test_assets_pagination_contract():
    r = _get("/api/audit/assets?limit=3&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert len(body["inventory"]) <= 3
    assert "page" in body and body["page"]["limit"] == 3
    assert "coverage" in body  # coverage is a summary, not paginated


def test_assets_invalid_params_safe():
    r = _get("/api/audit/assets?limit=-99&offset=abc")
    assert r.status_code == 200
    assert r.json()["page"]["limit"] == _DEFAULT_LIMIT


# --------------------------------------------------------------------------- #
# Mapping pagination
# --------------------------------------------------------------------------- #
def test_mapping_search_pagination():
    r = _get("/api/audit/mapping/search?limit=5&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) <= 5
    assert body["page"]["returned"] == len(body["results"])


def test_mapping_root_pagination():
    r = _get("/api/audit/mapping?limit=7")
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) <= 7
    assert body["page"]["limit"] == 7


# --------------------------------------------------------------------------- #
# Packs item pagination (bounded items, integrity preserved)
# --------------------------------------------------------------------------- #
def test_pack_items_are_bounded_but_count_preserved():
    _seed_evidence(20)
    r = _get("/api/audit/packs/framework/PCI DSS?limit=5&offset=0")
    assert r.status_code == 200
    pack = r.json()["pack"]
    # Full count preserved (pack identity intact), but only a page of items returned.
    assert pack["item_count"] == 20
    assert len(pack["items"]) == 5
    assert pack["items_page"]["total"] == 20 and pack["items_page"]["has_more"] is True
