"""UI page tests for the Audit Intelligence layer (Milestones 5 & 6).

Runs the FastAPI app via TestClient in DEMO_MODE. Asserts each page renders (200),
contains its heading, and includes the shared sidebar/nav. Offline (no live
connectors); evidence/observation stores are seeded directly where needed.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"

PAGES = [
    ("/mvp/audit/executive-readiness", "Executive Readiness"),
    ("/mvp/audit/assets", "Asset Inventory"),
    ("/mvp/audit/technology-inventory", "Technology Inventory"),
    ("/mvp/audit/mapping", "Framework Mapping"),
    ("/mvp/audit/runs", "Evidence Runs"),
    ("/mvp/audit/repository", "Evidence Repository"),
    ("/mvp/audit/observations", "Observation Management"),
    ("/mvp/audit/packs", "Evidence Packs"),
    ("/mvp/audit/validation", "Validation Results"),
]


@pytest.fixture(autouse=True)
def _clean():
    repo.reset_repository()
    obs.reset_observations()
    yield
    repo.reset_repository()
    obs.reset_observations()


@pytest.mark.parametrize("path,heading", PAGES)
def test_page_renders(path, heading):
    r = client.get(f"{path}?{Q}")
    assert r.status_code == 200, f"{path} -> {r.status_code}"
    assert heading in r.text
    assert "ecs-nav-groups" in r.text
    assert "Audit Intelligence" not in r.text


def test_mapping_page_has_data():
    r = client.get(f"/mvp/audit/mapping?{Q}")
    assert r.status_code == 200
    assert "NGINX" in r.text
    assert "PCI DSS" in r.text


def test_mapping_filter_by_technology():
    r = client.get(f"/mvp/audit/mapping?technology=NGINX&{Q}")
    assert r.status_code == 200
    assert "NGX-001" in r.text


def test_assets_page_lists_discovered_assets():
    r = client.get(f"/mvp/audit/assets?{Q}")
    assert r.status_code == 200
    # docker-compose demo assets are discovered offline
    assert "postgres" in r.text.lower()


def test_repository_page_shows_seeded_evidence():
    repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")
    r = client.get(f"/mvp/audit/repository?{Q}")
    assert r.status_code == 200
    assert "web-1::NGX-003" in r.text


def test_observations_page_shows_seeded_observation():
    from modules.audit_intelligence.models import ValidationResult, VERDICT_FAIL

    vr = ValidationResult(control_id="NGX-005", technology="NGINX", verdict=VERDICT_FAIL,
                          control_status="Non-Compliant", rule_id="assertion.negative_signal",
                          frameworks=("PCI DSS",), rationale="disabled")
    obs.generate_observation(vr, asset_id="web-1")
    r = client.get(f"/mvp/audit/observations?{Q}")
    assert r.status_code == 200
    assert "Critical" in r.text


def test_packs_page_builds_pack():
    repo.store_evidence(control_id="NGX-003", content="on", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")
    r = client.get(f"/mvp/audit/packs?pack_type=framework&scope=PCI DSS&{Q}")
    assert r.status_code == 200
    assert "checksum" in r.text.lower()


def test_nav_group_registered_on_existing_page():
    r = client.get(f"/mvp/ecs-benchmark?{Q}")
    assert r.status_code == 200
    assert "ecs-nav-groups" in r.text
    assert "Operations" in r.text
    assert "Audit Intelligence" not in r.text
