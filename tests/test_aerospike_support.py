"""Scoped, mocked tests for ECS Aerospike support.

Fully offline + deterministic: no Aerospike container, no docker, no network.
Covers the Docker Compose service definition, config placeholders, the predefined
query catalog + technology dropdown, run-query routing (demo output), technology
fingerprinting, UAT asset-scheduler classification, and secret/IP safety.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"

#: The 20 Aerospike control IDs expected in the supplementary catalog.
_EXPECTED_ASX = [f"ASX-{i:03d}" for i in range(1, 21)]


# --------------------------------------------------------------------------- #
# 1. Docker Compose service exists + host port defaults to 13000
# --------------------------------------------------------------------------- #
def test_aerospike_compose_service_exists():
    text = COMPOSE.read_text(encoding="utf-8")
    assert "aerospike:" in text
    assert "aerospike/aerospike-server:latest" in text
    assert "container_name: ecs-aerospike" in text


def _aerospike_block() -> str:
    """Return just the aerospike service block text (for scoped assertions)."""
    text = COMPOSE.read_text(encoding="utf-8")
    after = text.split("\n  aerospike:", 1)[1]
    # Stop at the next top-level service (2-space indent + name + colon).
    return "  aerospike:" + re.split(r"\n  [a-z0-9_-]+:", after, maxsplit=1)[0]


def test_aerospike_compose_uses_13000_not_3000():
    block = _aerospike_block()
    # Host port default 13000 -> container 3000 (never host 3000: Gitea uses it).
    assert "${AEROSPIKE_HOST_PORT:-13000}:3000" in block
    assert "${AEROSPIKE_FABRIC_PORT:-13001}:3001" in block
    assert "${AEROSPIKE_HEARTBEAT_PORT:-13002}:3002" in block
    # Ensure the Aerospike service does NOT map host port 3000 (Gitea owns it).
    assert '"3000:3000"' not in block
    assert ":-3000}" not in block  # default host port is never 3000


def test_aerospike_compose_profiles():
    """Service must be opt-in via the aerospike + demo profiles."""
    text = COMPOSE.read_text(encoding="utf-8")
    # Find the aerospike service block and check its profiles line.
    block = text.split("aerospike:", 1)[1].split("restart:", 1)[0]
    assert "aerospike" in block and "demo" in block
    assert "profiles:" in block


def test_compose_is_valid_yaml():
    import yaml

    data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert "aerospike" in data.get("services", {})
    svc = data["services"]["aerospike"]
    assert svc["image"] == "aerospike/aerospike-server:latest"
    assert svc["container_name"] == "ecs-aerospike"
    assert set(svc["profiles"]) >= {"aerospike", "demo"}


# --------------------------------------------------------------------------- #
# 2. Config placeholders exist
# --------------------------------------------------------------------------- #
def test_aerospike_config_placeholders_present():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for var in ("AEROSPIKE_HOST", "AEROSPIKE_PORT", "AEROSPIKE_NAMESPACE",
                "AEROSPIKE_USER", "AEROSPIKE_PASSWORD", "AEROSPIKE_TLS_ENABLED",
                "AEROSPIKE_HOST_PORT", "AEROSPIKE_FABRIC_PORT", "AEROSPIKE_HEARTBEAT_PORT"):
        assert f"{var}=" in text, f".env.example missing {var}"


def test_aerospike_default_values():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "AEROSPIKE_HOST=localhost" in text
    assert "AEROSPIKE_PORT=13000" in text
    assert "AEROSPIKE_NAMESPACE=test" in text
    assert "AEROSPIKE_TLS_ENABLED=false" in text


def test_aerospike_secret_placeholders_blank():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for secret in ("AEROSPIKE_USER", "AEROSPIKE_PASSWORD"):
        m = re.search(rf"^{secret}=(.*)$", text, re.MULTILINE)
        assert m and m.group(1).strip() == "", f"{secret} must be a blank placeholder"


# --------------------------------------------------------------------------- #
# 3-4. Technology catalog + predefined queries load
# --------------------------------------------------------------------------- #
def _engine():
    from modules.operations.engines import predefined_queries_engine as e
    return e


def test_aerospike_supplementary_queries_load():
    from modules.operations.engines.supplementary_query_catalog import (
        AEROSPIKE_QUERIES,
        SHELL_CONTROL_IDS,
        supplementary_controls,
    )
    ids = [q["control_id"] for q in AEROSPIKE_QUERIES]
    assert ids == _EXPECTED_ASX  # exactly the 20 requested, in order
    # All are shell controls (asinfo/asadm CLI).
    for cid in _EXPECTED_ASX:
        assert cid in SHELL_CONTROL_IDS
    # Present in the merged supplementary set.
    supp_ids = {c["control_id"] for c in supplementary_controls()}
    assert set(_EXPECTED_ASX) <= supp_ids


def test_aerospike_controls_in_catalog():
    e = _engine()
    aero = [c for c in e.get_all_controls() if c.get("technology") == "Aerospike"]
    assert len(aero) == 20
    # Every Aerospike control is predefined + technology-classified.
    for c in aero:
        assert c["predefined"] is True
        assert c["technology"] == "Aerospike"


def test_aerospike_queries_use_expected_commands():
    e = _engine()
    by_id = {c["control_id"]: c for c in e.get_all_controls()}
    assert by_id["ASX-001"]["query"] == 'asinfo -v "build"'
    assert by_id["ASX-002"]["query"] == 'asinfo -v "status"'
    assert by_id["ASX-003"]["query"] == 'asinfo -v "namespaces"'
    assert "asadm" in by_id["ASX-006"]["query"]
    assert "sindex" in by_id["ASX-019"]["query"]


# --------------------------------------------------------------------------- #
# 5. Technology dropdown source includes Aerospike (RCA fix)
# --------------------------------------------------------------------------- #
def test_technology_dropdown_includes_aerospike():
    e = _engine()
    opts = e.get_technology_filter_options()
    assert "Aerospike" in opts


def test_existing_technologies_still_in_dropdown():
    """Adding Aerospike must not remove any existing technology (regression guard)."""
    e = _engine()
    opts = set(e.get_technology_filter_options())
    for tech in ("PostgreSQL", "Oracle", "SQL Server", "MongoDB", "Redis", "NGINX",
                 "Apache HTTPD", "Tomcat", "Kubernetes", "OpenShift", "SonarQube",
                 "Aurora MySQL", "YugabyteDB", "Linux"):
        assert tech in opts, f"{tech} disappeared from the dropdown"


def test_detect_technology_aerospike():
    e = _engine()
    assert e.detect_technology('asinfo -v "build"') == "Aerospike"
    assert e.detect_technology('asadm -e "show users"') == "Aerospike"


# --------------------------------------------------------------------------- #
# 6. Aerospike queries appear when filtering technology=Aerospike
# --------------------------------------------------------------------------- #
def test_filter_controls_by_aerospike():
    e = _engine()
    rows = e.filter_controls(technology="Aerospike")
    assert len(rows) == 20
    assert all(r["technology"] == "Aerospike" for r in rows)


# --------------------------------------------------------------------------- #
# 7. Run-query routes Aerospike queries (demo-mode deterministic output)
# --------------------------------------------------------------------------- #
def test_run_query_routes_aerospike_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    e = _engine()
    r = e.run_predefined_query("ASX-001", "tester")
    assert r["ok"] is True
    assert "build" in r["output"]
    assert "[DEMO]" in r["output"]  # deterministic demo output, not a live call


def test_run_query_aerospike_resolves_namespace(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("AEROSPIKE_NAMESPACE", "test")
    e = _engine()
    r = e.run_predefined_query("ASX-004", "tester")
    assert r["ok"] is True
    # The ${AEROSPIKE_NAMESPACE:-test} placeholder must be resolved (no literal ${}).
    assert "${" not in r["output"]
    assert "id=test" in r["output"]


def test_run_query_unknown_aerospike_control_is_safe():
    e = _engine()
    r = e.run_predefined_query("ASX-999", "tester")
    assert r["ok"] is False
    assert r["error_type"] in ("missing_control", "unsupported_control")


# --------------------------------------------------------------------------- #
# 7b. A persisted Aerospike run produces evidence + review-workflow enrollment
#     IDENTICALLY to a working DB technology (PGX-001) — same repository, same
#     App Owner / Auditor queues, same source_connector. No parallel mechanism.
# --------------------------------------------------------------------------- #
def test_aerospike_persisted_run_matches_working_technology(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    from app import ecs_state
    from modules.governance.engines import workflow_module as wf
    from modules.operations.engines import evidence_repository as ops_repo
    from modules.operations.engines.predefined_query_evidence import (
        get_latest_evidence_for_control,
    )
    from modules.shared.services import evidence_workflow_engine as ewf

    e = _engine()

    for state in (
        ecs_state.submitted_controls, ecs_state.uploaded_evidence_enrollments,
        ecs_state.predefined_query_fingerprint_index, ecs_state.predefined_query_content_index,
    ):
        state.clear()
    ops_repo.evidence_repository.clear()

    pgx = e.run_predefined_query("PGX-001", "tester", persist=True)
    asx = e.run_predefined_query("ASX-001", "tester", persist=True)

    assert asx["ok"] is True and asx["evidence_persisted"] is True
    assert asx["evidence_id"]

    asx_enr = ewf.get_enrollment(evidence_id=asx["evidence_id"])
    pgx_enr = ewf.get_enrollment(evidence_id=pgx["evidence_id"])
    # Same enrollment shape as the working technology (casing-agnostic).
    assert asx_enr["source_connector"] == pgx_enr["source_connector"]
    assert asx_enr["source_connector"].lower() == "predefined_query"
    assert asx_enr["query_id"] == "ASX-001"
    assert asx_enr["object_key"] and asx_enr["sha256"]
    assert set(pgx_enr) == set(asx_enr)  # identical enrollment record shape

    # App Owner evidence view + pending-review queue.
    owner_items = wf.build_owner_work_queue(limit=500)
    assert any(i["evidence_id"] == asx["evidence_id"] for i in owner_items)
    assert get_latest_evidence_for_control("ASX-001") is not None

    # After App Owner submits (existing review workflow), it reaches the Auditor
    # pending-review queue — same route the working technologies use.
    from fastapi.testclient import TestClient
    from app.main import app

    resp = TestClient(app).post(
        "/evidence/review/submit",
        data={
            "framework_name": asx_enr["framework"],
            "control_name": asx_enr["control_name"],
            "evidence_id": asx["evidence_id"],
            "role": "owner",
            "user": "App Owner",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    auditor_items = wf.build_auditor_review_queue(limit=500)
    assert any(i["evidence_id"] == asx["evidence_id"] for i in auditor_items)


def test_aerospike_connector_config_defaults(monkeypatch):
    # Config resolves safe local defaults without any container.
    for v in ("AEROSPIKE_HOST", "AEROSPIKE_PORT", "AEROSPIKE_NAMESPACE"):
        monkeypatch.delenv(v, raising=False)
    from modules.operations.engines.aerospike_connector import get_aerospike_config
    cfg = get_aerospike_config()
    assert cfg["host"] == "localhost"
    assert cfg["port"] == 13000
    assert cfg["namespace"] == "test"
    assert cfg["container"] == "ecs-aerospike"


# --------------------------------------------------------------------------- #
# 8. Fingerprinting classifies Aerospike
# --------------------------------------------------------------------------- #
def _fp():
    from modules.audit_intelligence.engines import technology_fingerprint as fp
    return fp


def test_fingerprint_aerospike_by_image():
    r = _fp().fingerprint_asset({"image": "aerospike/aerospike-server:latest"})
    assert r.technology == "Aerospike"


def test_fingerprint_aerospike_by_name():
    r = _fp().fingerprint_asset({"name": "ecs-aerospike"})
    assert r.technology == "Aerospike"


def test_fingerprint_aerospike_by_technology_hint():
    r = _fp().fingerprint_asset({"technology": "aerospike"})
    assert r.technology == "Aerospike"


def test_fingerprint_aerospike_by_port():
    assert _fp().fingerprint_asset({"ports": [3000]}).technology == "Aerospike"
    assert _fp().fingerprint_asset({"ports": ["13000:3000"]}).technology == "Aerospike"


# --------------------------------------------------------------------------- #
# 9. UAT asset scheduler classifies Aerospike
# --------------------------------------------------------------------------- #
def test_asset_scheduler_classifies_aerospike():
    from modules.audit_intelligence.engines import asset_discovery as ad
    from modules.audit_intelligence.services import asset_scheduler as s
    from modules.audit_intelligence.services.asset_scheduler import ROUTE_BASELINE

    asset = ad.discover_from_manual([{
        "asset_id": "aero1", "hostname": "ecs-aerospike",
        "image": "aerospike/aerospike-server:latest", "ports": ["13000:3000"],
    }])[0]
    c = s.classify_asset(asset)
    assert c.technology == "Aerospike"
    assert c.route == ROUTE_BASELINE     # baseline collector (predefined queries)
    assert c.scope_kind == "technology" and c.scope_value == "Aerospike"
    assert len(c.control_ids) == 20


# --------------------------------------------------------------------------- #
# 10. No real IPs / secrets introduced
# --------------------------------------------------------------------------- #
def test_no_real_ips_or_secrets_in_aerospike_artifacts():
    files = [
        COMPOSE, ENV_EXAMPLE,
        ROOT / "modules/operations/engines/aerospike_connector.py",
        ROOT / "modules/operations/engines/supplementary_query_catalog.py",
    ]
    ip_re = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
    sec_re = re.compile(
        r"(password|secret|api[_-]?token|access[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9/+=_-]{12,}",
        re.I,
    )
    for f in files:
        # Scope to Aerospike-relevant lines only (avoid unrelated pre-existing
        # content such as the Postgres demo password in docker-compose.yml).
        for line in f.read_text(encoding="utf-8").splitlines():
            if "aerospike" not in line.lower():
                continue
            for ip in ip_re.findall(line):
                assert ip.startswith(("127.", "0.0.0.0")), f"non-loopback IP in {f.name}: {ip}"
            assert not sec_re.search(line), f"possible secret in {f.name}: {line!r}"
