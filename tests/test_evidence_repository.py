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
    repo.reset_repository()
    yield
    repo.reset_repository()


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
    assert s["by_technology"]["NGINX"] == 1


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
