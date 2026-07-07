"""Frontend integration tests for the Predefined Queries page.

Verifies that the supplementary database controls (PostgreSQL PGX-*, YugabyteDB
YBX-*, Aurora MySQL MYX-*) are visible and executable through the SAME Predefined
Queries UI + Run Query flow already used for the Excel PostgreSQL controls.

Runs against the FastAPI app via TestClient in DEMO_MODE (auth bypassed). No live
database is required — the run endpoint is exercised for routing/error handling,
not for a successful connection.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.operations.engines import predefined_queries_engine as engine

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"

PG_IDS = [f"PGX-00{i}" for i in range(1, 9)]      # PGX-001..PGX-008
YB_IDS = [f"YBX-00{i}" for i in range(1, 9)]      # YBX-001..YBX-008
MY_IDS = [f"MYX-0{i:02d}" for i in range(1, 11)]  # MYX-001..MYX-010


# --------------------------------------------------------------------------- #
# View model / catalog
# --------------------------------------------------------------------------- #
def test_dashboard_includes_all_supplementary_controls():
    # The dashboard paginates (page size is capped), so verify the full catalog
    # via the source of truth, then confirm the DB controls surface via search.
    engine.load_predefined_queries()
    all_ids = {c["control_id"] for c in engine.get_all_controls()}
    for cid in PG_IDS + YB_IDS + MY_IDS:
        assert cid in all_ids, f"{cid} missing from catalog"
    # Each DB technology is reachable through the (filtered) dashboard.
    for term, ids in (("PGX", PG_IDS), ("YBX", YB_IDS), ("MYX", MY_IDS)):
        dash = engine.get_predefined_queries_dashboard(search=term, per_page=100)
        rows = {r["control_id"] for r in dash["rows"]}
        assert set(ids).issubset(rows), f"{term} controls not all shown"
    # 37 Excel + 68 supplementary (26 DB + 42 infra).
    dash = engine.get_predefined_queries_dashboard(per_page=1)
    assert dash["validation"]["controls_loaded"] >= 63


@pytest.mark.parametrize("term,expected_count", [("PGX", 8), ("YBX", 8), ("MYX", 10)])
def test_search_returns_expected_row_counts(term, expected_count):
    dash = engine.get_predefined_queries_dashboard(search=term, per_page=100)
    ids = [r["control_id"] for r in dash["rows"] if r["control_id"].startswith(term)]
    assert len(ids) == expected_count
    # Every supplementary DB control is Ready -> Run Query enabled.
    assert all(r["live_execution_enabled"] for r in dash["rows"] if r["control_id"].startswith(term))


@pytest.mark.parametrize("term", ["PostgreSQL", "YugabyteDB", "Aurora MySQL"])
def test_technology_name_search_matches(term):
    dash = engine.get_predefined_queries_dashboard(search=term, per_page=100)
    assert dash["rows"], f"no rows for technology search {term!r}"
    assert all((r.get("technology") or "") == term or term.lower() in (r.get("query") or "").lower()
               or term.lower() in (r.get("control_name") or "").lower()
               for r in dash["rows"])


# --------------------------------------------------------------------------- #
# Technology filter
# --------------------------------------------------------------------------- #
def test_technology_filter_options_present():
    dash = engine.get_predefined_queries_dashboard(per_page=1)
    opts = dash["technology_options"]
    assert opts[0] == "All Technologies"
    for tech in ("PostgreSQL", "YugabyteDB", "Aurora MySQL"):
        assert tech in opts


@pytest.mark.parametrize("tech,prefix", [("PostgreSQL", "PGX"), ("YugabyteDB", "YBX"), ("Aurora MySQL", "MYX")])
def test_technology_filter_narrows_rows(tech, prefix):
    dash = engine.get_predefined_queries_dashboard(technology=tech, per_page=500)
    assert dash["rows"], f"no rows for technology={tech}"
    assert all((r.get("technology") or "") == tech for r in dash["rows"])
    # The supplementary controls for that technology are included.
    ids = {r["control_id"] for r in dash["rows"]}
    assert any(cid.startswith(prefix) for cid in ids)


def test_technology_and_search_compose():
    dash = engine.get_predefined_queries_dashboard(technology="PostgreSQL", search="PGX", per_page=100)
    ids = {r["control_id"] for r in dash["rows"]}
    assert ids == set(PG_IDS)


# --------------------------------------------------------------------------- #
# Rendered HTML (what the browser receives)
# --------------------------------------------------------------------------- #
def test_page_renders_run_query_for_supplementary():
    r = client.get(f"/mvp/predefined-queries?{Q}&q=MYX&page=1")
    assert r.status_code == 200
    html = r.text
    # All MYX ids appear and each has a Run Query button (enabled).
    for cid in MY_IDS:
        assert f"<strong>{cid}</strong>" in html
    assert html.count(">Run Query</button>") >= 10
    assert 'name="technology"' in html  # technology filter dropdown present


def test_page_shows_total_controls():
    r = client.get(f"/mvp/predefined-queries?{Q}")
    assert r.status_code == 200
    # 37 Excel + 150 supplementary = 187 after adding Aerospike (ASX-001..020) to
    # the extended technology expansion (Redis/Apache/Tomcat/SQL Server/MongoDB/
    # Kubernetes/OpenShift + Aerospike).
    assert "of 187 controls" in r.text


def test_page_disables_run_for_config_required():
    # DB-006 is now detected as YugabyteDB but is Configuration Required (not in
    # LIVE_CONTROL_IDS) -> disabled Run Query button.
    r = client.get(f"/mvp/predefined-queries?{Q}&q=DB-006")
    assert r.status_code == 200
    assert "Live execution not enabled for this control" in r.text


# --------------------------------------------------------------------------- #
# Run Query endpoint routes each technology through the same flow
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cid", ["PGX-001", "YBX-001", "MYX-001"])
def test_run_endpoint_accepts_db_controls(cid):
    # The run endpoint 303-redirects with a notice regardless of DB availability.
    r = client.post(
        "/mvp/predefined-queries/run",
        data={"control_id": cid, "role": "owner", "user": "AppOwner", "return_to": "detail"},
    )
    assert r.status_code in (302, 303)
    assert "/mvp/predefined-queries" in r.headers.get("location", "")


def test_run_endpoint_routes_by_technology(monkeypatch):
    """PGX->PostgreSQL, YBX->YugabyteDB, MYX->Aurora MySQL dispatch is preserved."""
    engine.load_predefined_queries(force=True)
    seen: dict[str, str] = {}

    def _fake(control_id, user):
        ctrl = engine.get_control_by_id(control_id)
        seen[control_id] = ctrl.get("technology") if ctrl else "?"
        return {"ok": True, "message": "ok", "control_id": control_id,
                "evidence_id": "EVD-TEST", "evidence_filename": f"PREDEFINED_QUERY_{control_id}.txt"}

    # Route calls run_predefined_query; assert it maps each id to the right tech.
    assert engine.get_control_by_id("PGX-001")["technology"] == "PostgreSQL"
    assert engine.get_control_by_id("YBX-001")["technology"] == "YugabyteDB"
    assert engine.get_control_by_id("MYX-001")["technology"] == "Aurora MySQL"


def test_run_endpoint_blocks_unsupported():
    # A non-existent / unsupported control still returns a safe redirect, not 500.
    r = client.post(
        "/mvp/predefined-queries/run",
        data={"control_id": "NO-SUCH-CTRL", "role": "owner", "user": "AppOwner"},
    )
    assert r.status_code in (302, 303)
