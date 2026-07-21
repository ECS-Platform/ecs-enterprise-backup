"""Tests for the Evidence Repository (Milestone 3). Deterministic/offline."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import evidence_repository as repo


@pytest.fixture(autouse=True)
def _clean():
    import time as _time

    repo.reset_repository()
    # Skip live PostgreSQL on search()/stats() hydration in unit tests.
    repo._last_canonical_failure_at = _time.monotonic()
    yield
    repo.reset_repository()
    try:
        from modules.audit_intelligence.services import persistence as P

        P.reset_persistence()
    except Exception:  # noqa: BLE001
        pass
    os.environ.pop("AUDIT_WORKFLOW_ENABLED", None)


def test_store_creates_v1_with_hash():
    a = repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX", asset_id="web-1")
    assert a.version == 1
    assert len(a.content_hash) == 64  # sha256 hex
    assert a.checksum == a.content_hash[:8]
    assert a.size_bytes == len("ssl on")


def test_versioning_increments_and_hash_changes():
    a1 = repo.store_evidence(control_id="C", content="v1", asset_id="x")
    a2 = repo.store_evidence(control_id="C", content="v2", asset_id="x")
    assert (a1.version, a2.version) == (1, 2)
    assert a1.content_hash != a2.content_hash
    assert repo.get_latest(a1.evidence_key).version == 2
    assert len(repo.get_versions(a1.evidence_key)) == 2


def test_identical_content_same_hash_new_version():
    a1 = repo.store_evidence(control_id="C", content="same", asset_id="x")
    a2 = repo.store_evidence(control_id="C", content="same", asset_id="x")
    assert a1.content_hash == a2.content_hash  # unchanged content detectable
    assert a2.version == 2                      # but still a new version


def test_make_key_stability():
    assert repo.make_evidence_key("web-1", "NGX-003") == "web-1::NGX-003"
    assert repo.make_evidence_key("", "C") == "global::C"


def test_timeline_records_events():
    repo.store_evidence(control_id="C", content="a", asset_id="x")
    repo.store_evidence(control_id="C", content="b", asset_id="x")
    tl = repo.timeline(repo.make_evidence_key("x", "C"))
    assert len(tl) == 2
    assert all(e["event"] == "stored" for e in tl)


def test_search_filters():
    repo.store_evidence(control_id="C1", content="x", technology="NGINX", asset_id="a1", frameworks=("PCI DSS",), verdict="PASS")
    repo.store_evidence(control_id="C2", content="y", technology="Redis", asset_id="a2", frameworks=("ISO27001",), verdict="FAIL")
    assert len(repo.search(technology="NGINX")) == 1
    assert len(repo.search(framework="ISO27001")) == 1
    assert len(repo.search(asset_id="a1")) == 1
    assert len(repo.search(verdict="FAIL")) == 1
    assert len(repo.search(query="c2")) == 1


def test_connector_evidence_appears_in_listing_and_filename_search():
    """Persisted connector evidence is listed and findable by filename / id."""
    art = repo.store_evidence(
        control_id="A.8.24",
        content="encryption at rest policy",
        asset_id="Net-Banking",
        frameworks=("ISO27001",),
        source="connector",
        filename="ISO27001_NET-BANKIN_20260721_encryption_evidence.txt",
        evidence_id="EVID-SP-001",
        source_connector="sharepoint_graph",
        object_uri="s3://ecs-evidence/Net-Banking/A.8.24/encryption_evidence.txt",
        custody_mode="SNAPSHOT",
        metadata={"original_filename": "encryption_evidence.txt", "application": "Net-Banking"},
    )
    listed = repo.search(latest_only=True)
    assert any(a.evidence_id == "EVID-SP-001" for a in listed)

    by_name = repo.search(query="encryption_evidence.txt")
    assert len(by_name) == 1
    assert by_name[0].evidence_id == art.evidence_id
    assert by_name[0].source_connector == "sharepoint_graph"

    by_id = repo.search(query="EVID-SP-001")
    assert len(by_id) == 1
    assert by_id[0].filename.endswith("encryption_evidence.txt")

    by_uri = repo.search(query="ecs-evidence/Net-Banking")
    assert len(by_uri) == 1
    by_connector = repo.search(query="sharepoint_graph")
    assert len(by_connector) == 1
    by_control = repo.search(query="A.8.24")
    assert len(by_control) == 1
    by_app = repo.search(query="Net-Banking")
    assert len(by_app) == 1


def test_search_empty_query_still_lists_all_latest():
    repo.store_evidence(control_id="C1", content="a", asset_id="x", filename="one.txt")
    repo.store_evidence(control_id="C2", content="b", asset_id="y", filename="two.txt")
    assert len(repo.search(query="")) == 2
    assert repo.stats()["evidence_keys"] == 2


def test_latest_only_vs_all():
    repo.store_evidence(control_id="C", content="v1", asset_id="x")
    repo.store_evidence(control_id="C", content="v2", asset_id="x")
    assert len(repo.search(latest_only=True)) == 1
    assert len(repo.search(latest_only=False)) == 2


def test_stats():
    repo.store_evidence(control_id="C1", content="x", technology="NGINX", asset_id="a", verdict="PASS")
    repo.store_evidence(control_id="C1", content="x2", technology="NGINX", asset_id="a", verdict="PASS")
    s = repo.stats()
    assert s["evidence_keys"] == 1
    assert s["total_versions"] == 2
    assert s["technologies"] == 1
    assert s["by_technology"]["NGINX"] == 1


def test_stats_falls_back_to_unknown_unassessed_only_when_source_empty():
    """Confirmed behavior: `Unknown`/`Unassessed` in stats reflect genuinely-empty
    technology/verdict on the source records (e.g. framework-evidence uploads that
    carry frameworks but no technology and are not yet validated) — NOT a wrong
    field mapping. Records that DO carry technology/verdict are reported verbatim.
    """
    # Framework-evidence-style records: frameworks present, technology + verdict empty
    # (mirrors modules/operations/engines/evidence_repository._mirror_to_audit_repository,
    # which stores verdict=""/control_status="" for unassessed uploads and only
    # enriches technology when the control resolves in the mapping).
    repo.store_evidence(control_id="Req 3.4 — Encryption at Rest", content="a",
                        asset_id="Net Banking", frameworks=("PCI DSS",),
                        technology="", verdict="", source="manual_upload")
    repo.store_evidence(control_id="Req 4.1 — Encryption in Transit", content="b",
                        asset_id="Payments", frameworks=("PCI DSS",),
                        technology="", verdict="", source="manual_upload")
    # One properly-classified record proves the fallback is value-driven, not global.
    repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")

    s = repo.stats()
    assert s["evidence_keys"] == 3
    # Empty-source records fall back; the classified record is reported as-is.
    assert s["by_technology"] == {"NGINX": 1, "Unknown": 2}
    assert s["by_verdict"] == {"PASS": 1, "Unassessed": 2}
    # Technologies KPI counts only real non-empty values (not synthetic Unknown).
    assert s["technologies"] == 1


def test_repository_kpi_stats_semantics(monkeypatch):
    """Evidence Repository KPI cards: keys vs versions, timeline, technologies, hydration."""
    s0 = repo.stats()
    assert s0["evidence_keys"] == 0
    assert s0["total_versions"] == 0
    assert s0["timeline_events"] == 0
    assert s0["technologies"] == 0

    # A. / E. New evidence key increases Evidence Keys.
    a1 = repo.store_evidence(control_id="C1", content="v1", technology="NGINX", asset_id="app-a")
    s1 = repo.stats()
    assert s1["evidence_keys"] == 1
    assert s1["total_versions"] == 1
    assert s1["timeline_events"] == 1
    assert s1["technologies"] == 1

    # B. / F. New version on same key: versions + timeline grow; keys unchanged.
    repo.store_evidence(control_id="C1", content="v2", technology="NGINX", asset_id="app-a")
    s2 = repo.stats()
    assert s2["evidence_keys"] == 1
    assert s2["total_versions"] == 2
    assert s2["timeline_events"] == 2
    assert s2["technologies"] == 1

    # C. Timeline events match real _TIMELINE length (one per store_evidence version).
    assert s2["timeline_events"] == len(repo.timeline())

    # D. / G. Blank technology does not count; a new real technology does.
    repo.store_evidence(control_id="C2", content="blank-tech", technology="", asset_id="app-b")
    s3 = repo.stats()
    assert s3["evidence_keys"] == 2
    assert s3["technologies"] == 1  # still only NGINX
    repo.store_evidence(control_id="C3", content="redis", technology="Redis", asset_id="app-c")
    s4 = repo.stats()
    assert s4["technologies"] == 2  # NGINX + Redis

    # H. Repeated unchanged canonical hydration does not inflate KPIs.
    row = {
        "evidence_uid": "EVD-KPI-1",
        "source_system": "sharepoint_graph",
        "source_object_id": "item-kpi-1",
        "object_type": "file",
        "title": "kpi_evidence.txt",
        "content": "kpi body",
        "url": "http://example/kpi",
        "application": "Net-Banking",
        "content_hash": "kpi-hash-001",
        "metadata": {
            "control": "A.8.24",
            "framework": "ISO27001",
            "environment": "Production",
            "custody_mode": "SNAPSHOT",
            "object_uri": "http://minio/kpi",
            "original_filename": "kpi_evidence.txt",
        },
    }

    class _Fake:
        def search_evidence(self, *, limit: int = 1000):
            return [row]

        def close(self):
            pass

    monkeypatch.setattr("ecs_platform.repository.EvidenceRepository", lambda: _Fake())
    before = repo.stats()
    assert repo.hydrate_from_canonical_repository(force=True) == 1
    after_first = repo.stats()
    assert after_first["evidence_keys"] == before["evidence_keys"] + 1
    assert after_first["total_versions"] == before["total_versions"] + 1
    assert after_first["timeline_events"] == before["timeline_events"] + 1

    assert repo.hydrate_from_canonical_repository(force=True) == 0
    assert repo.hydrate_from_canonical_repository(force=True) == 0
    after_repeat = repo.stats()
    assert after_repeat["evidence_keys"] == after_first["evidence_keys"]
    assert after_repeat["total_versions"] == after_first["total_versions"]
    assert after_repeat["timeline_events"] == after_first["timeline_events"]
    assert after_repeat["technologies"] == after_first["technologies"]

    # I. Mutation then stats() returns updated (not stale) values.
    repo.store_evidence(control_id="C4", content="new", technology="PostgreSQL", asset_id="app-d")
    s5 = repo.stats()
    assert s5["evidence_keys"] == after_repeat["evidence_keys"] + 1
    assert s5["total_versions"] == after_repeat["total_versions"] + 1
    assert s5["technologies"] == after_repeat["technologies"] + 1
    assert a1.evidence_key in {a.evidence_key for a in repo.all_latest()}


def test_store_from_run_like_object():
    class Rec:
        def __init__(self, cid, ok):
            self.control_id = cid
            self.ok = ok
            self.output_excerpt = "out"
            self.technology = "NGINX"
            self.asset_id = "a"
            self.frameworks = ("PCI DSS",)
            self.evidence_filename = "f.txt"

    class Run:
        run_id = "RUN-1"
        records = [Rec("C1", True), Rec("C2", False)]

    stored = repo.store_from_run(Run(), results_by_control={"C1": {"verdict": "PASS", "evidence_quality": 0.9}})
    assert len(stored) == 1  # only ok records stored
    assert stored[0].verdict == "PASS"
