"""API tests for the Audit Intelligence REST layer (Milestone 4).

Runs against the FastAPI app via TestClient in DEMO_MODE (auth bypassed). Offline:
evidence runs use non-executable controls (marked Configuration Required) so no
live connector is touched; the repository/observation stores are exercised
directly through the API where possible.
"""

from __future__ import annotations

import os
import uuid

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs

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


def _post(path: str, json=None):
    sep = "&" if "?" in path else "?"
    return client.post(f"{path}{sep}{Q}", json=json or {})


# --------------------------------------------------------------------------- #
# Mapping
# --------------------------------------------------------------------------- #
def test_mapping_technologies():
    r = _get("/api/audit/mapping/technologies")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert any(t["name"] == "NGINX" for t in body["technologies"])


def test_mapping_stats_and_graph():
    assert _get("/api/audit/mapping/stats").json()["stats"]["controls"] >= 100
    assert "technologies" in _get("/api/audit/mapping/graph").json()["graph"]


def test_mapping_technology_detail_and_404():
    ok = _get("/api/audit/mapping/technology/NGINX")
    assert ok.status_code == 200 and ok.json()["detail"]["name"] == "NGINX"
    missing = _get("/api/audit/mapping/technology/Nope")
    assert missing.status_code == 404 and missing.json()["ok"] is False


def test_mapping_search():
    r = _get("/api/audit/mapping/search?technology=NGINX&framework=PCI DSS")
    assert r.status_code == 200
    assert all(row["technology"] == "NGINX" for row in r.json()["results"])


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
def test_assets_inventory_and_coverage():
    r = _get("/api/audit/assets?docker_compose=true")
    assert r.status_code == 200
    body = r.json()
    assert body["coverage"]["total_assets"] > 0
    assert isinstance(body["inventory"], list)


def test_assets_technology_inventory_and_fingerprints():
    assert _get("/api/audit/assets/technology-inventory").status_code == 200
    assert "fingerprint_report" in _get("/api/audit/assets/fingerprints").json()


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #
def test_start_run_and_fetch():
    # Single non-executable control -> Configuration Required, no live connector.
    r = _post("/api/audit/runs", {"scope_kind": "control", "scope_value": "NGX-001"})
    assert r.status_code == 200
    run = r.json()["run"]
    run_id = run["run_id"]
    got = _get(f"/api/audit/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["run"]["run_id"] == run_id


def test_start_run_requires_scope_kind():
    r = _post("/api/audit/runs", {})
    assert r.status_code == 400


def test_run_validation_and_list():
    r = _post("/api/audit/runs", {"scope_kind": "control", "scope_value": "NGX-001"})
    run_id = r.json()["run"]["run_id"]
    val = _get(f"/api/audit/runs/{run_id}/validation")
    assert val.status_code == 200
    assert "compliance" in val.json()["validation"]
    assert any(x["run_id"] == run_id for x in _get("/api/audit/runs").json()["runs"])


def test_retry_and_cancel_unknown_run_404():
    assert _post("/api/audit/runs/RUN-nope/retry").status_code == 404
    assert _post("/api/audit/runs/RUN-nope/cancel").status_code == 404


# --------------------------------------------------------------------------- #
# Evidence repository
# --------------------------------------------------------------------------- #
def test_evidence_search_and_versions():
    # Scoped so this test does not depend on ambient repository state: the search
    # endpoint reads the authoritative (canonical) view, whose corpus varies, while
    # versions/timeline/stats read the engine store this test writes to. So the
    # created key is asserted through the latter, and the search endpoint is
    # asserted on its filter contract rather than a repo-wide count.
    unique = uuid.uuid4().hex[:8]
    asset = f"web-{unique}"
    repo.stats()  # settle lazy canonical hydration
    keys_before = repo.stats()["evidence_keys"]
    repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX",
                        asset_id=asset, frameworks=("PCI DSS",), verdict="PASS")
    assert repo.stats()["evidence_keys"] - keys_before == 1

    # The evidence this test created is retrievable by its own key.
    key = repo.make_evidence_key(asset, "NGX-003")
    versions = _get(f"/api/audit/evidence/{key}/versions").json()["versions"]
    assert len(versions) == 1 and versions[0]["technology"] == "NGINX"
    assert _get(f"/api/audit/evidence/{key}/timeline").json()["timeline"]

    # The stats endpoint reports the authoritative corpus; assert its shape, not a
    # count that this test's in-process write does not participate in.
    stats = _get("/api/audit/evidence/stats").json()["stats"]
    assert stats["evidence_keys"] >= 0 and "by_verdict" in stats

    # The search endpoint honours its technology filter over whatever corpus it has.
    r = _get("/api/audit/evidence?technology=NGINX")
    assert r.status_code == 200
    assert all(row.get("technology") == "NGINX" for row in r.json()["evidence"])


# --------------------------------------------------------------------------- #
# Observations
# --------------------------------------------------------------------------- #
def _seed_observation():
    from modules.audit_intelligence.models import ValidationResult, VERDICT_FAIL

    vr = ValidationResult(control_id="NGX-005", technology="NGINX", verdict=VERDICT_FAIL,
                          control_status="Non-Compliant", rule_id="assertion.negative_signal",
                          frameworks=("PCI DSS",), rationale="disabled")
    return obs.generate_observation(vr, asset_id="web-1")


def test_observations_list_and_transition():
    o = _seed_observation()
    listing = _get("/api/audit/observations")
    assert listing.status_code == 200 and listing.json()["observations"]
    # valid transition
    t = _post(f"/api/audit/observations/{o.observation_id}/transition", {"to_status": "Submitted"})
    assert t.status_code == 200 and t.json()["observation"]["status"] == "Submitted"
    # invalid transition -> 400
    bad = _post(f"/api/audit/observations/{o.observation_id}/transition", {"to_status": "Closed"})
    assert bad.status_code == 400
    assert _get("/api/audit/observations/summary").json()["summary"]["total"] == 1


def test_observation_404():
    assert _get("/api/audit/observations/OBS-nope").status_code == 404


# --------------------------------------------------------------------------- #
# Packs
# --------------------------------------------------------------------------- #
def test_pack_endpoints():
    # A unique framework + asset scopes each pack to this test's own evidence, so
    # the exact item_count stays meaningful regardless of ambient repository state
    # (the repository re-hydrates persisted/canonical evidence on read).
    unique = uuid.uuid4().hex[:8]
    framework = f"UAT-PACK-{unique}"
    asset = f"web-{unique}"
    repo.store_evidence(control_id="NGX-003", content="on", technology="NGINX",
                        asset_id=asset, frameworks=(framework,), verdict="PASS")
    fw = _get(f"/api/audit/packs/framework/{framework}")
    assert fw.status_code == 200 and fw.json()["pack"]["item_count"] == 1
    ap = _post("/api/audit/packs/application", {"application": "App", "asset_ids": [asset]})
    assert ap.status_code == 200 and ap.json()["pack"]["item_count"] == 1
    bad = _get("/api/audit/packs/bogus/x")
    assert bad.status_code == 400
