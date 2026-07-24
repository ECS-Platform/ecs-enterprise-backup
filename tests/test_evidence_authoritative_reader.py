"""Focused validation tests for Phase-1 authoritative evidence repository reads."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.governance.engines.search_module import search_evidences
from modules.operations.engines import evidence_repository as ops_repo
from modules.shared.services.common_evidence_queries import collect_persisted_evidence_rows
from modules.shared.services.evidence_authoritative_reader import (
    collect_authoritative_evidence_rows,
    get_authoritative_evidence,
    repository_stats,
)


@pytest.fixture(autouse=True)
def _clean():
    import time as _time

    from modules.frameworks.repositories.framework_control_repository import (
        clear_framework_control_repository_cache,
    )

    clear_framework_control_repository_cache()
    ai_repo.reset_repository()
    ai_repo._last_canonical_failure_at = _time.monotonic()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    yield
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    clear_framework_control_repository_cache()


def test_register_upload_sha256_duplicate_is_detected():
    first = ops_repo.register_upload("a.pdf", b"same-bytes", "owner", "PCI DSS", "Net Banking", "PCI-C-01")
    second = ops_repo.register_upload("b.pdf", b"same-bytes", "owner", "PCI DSS", "Net Banking", "PCI-C-01")
    assert first["status"] != "DUPLICATE"
    assert second["status"] == "DUPLICATE"
    assert second["evidence_id"] == first["evidence_id"]
    assert len(ops_repo.evidence_repository) == 1


def test_authoritative_reader_merges_ops_and_audit_rows():
    rec = ops_repo.register_upload(
        "policy.pdf",
        b"policy body",
        "scheduler",
        "PCI DSS",
        "Net Banking",
        "PCI-C-01",
        source_connector="predefined_query",
        environment="Production",
        metadata={"collection_source": "predefined_query"},
    )
    rows = collect_authoritative_evidence_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["evidence_id"] == rec["evidence_id"]
    assert row["sha256"] == rec["sha256"]
    assert row["environment"] == "Production"
    assert row["collection_source"] == "predefined_query"
    assert row["audit_repository_synced"] is True


def test_fcm_mapping_enriched_on_upload():
    rec = ops_repo.register_upload(
        "segmentation.pdf",
        b"network segmentation evidence",
        "owner",
        "PCI DSS",
        "Net Banking",
        "PCI-C-01",
    )
    meta = rec.get("metadata") or {}
    assert meta.get("fcm_framework_id") == "pci_dss"
    assert meta.get("fcm_control_id") == "PCI-C-01"
    assert meta.get("policy_refs")
    assert meta.get("procedure_ids")
    assert meta.get("evidence_requirement_ids")


def test_fcm_enrichment_reuses_shared_repository_across_rows(monkeypatch):
    """Authoritative collection must not construct a new FCM repo per evidence row."""
    from modules.frameworks.repositories import framework_control_repository as fcm_mod
    from modules.shared.services.evidence_authoritative_reader import _enrich_fcm_mappings

    fcm_mod.clear_framework_control_repository_cache()
    ctors = {"n": 0}
    real_init = fcm_mod.FileFrameworkControlRepository.__init__

    def _counting_init(self, *args, **kwargs):
        ctors["n"] += 1
        return real_init(self, *args, **kwargs)

    monkeypatch.setattr(fcm_mod.FileFrameworkControlRepository, "__init__", _counting_init)

    # Force enrichment path (empty meta) across many rows / calls.
    for i in range(25):
        out = _enrich_fcm_mappings(
            {},
            framework="PCI DSS",
            control="PCI-C-01",
        )
        assert out.get("fcm_framework_id") == "pci_dss"
        assert out.get("fcm_control_id") == "PCI-C-01"

    assert ctors["n"] == 1, f"expected one shared FCM repo ctor, got {ctors['n']}"

    for i in range(10):
        ops_repo.register_upload(
            f"row-{i}.pdf",
            f"body-{i}".encode(),
            "owner",
            "PCI DSS",
            "Net Banking",
            "PCI-C-01",
        )
    before = ctors["n"]
    rows = collect_authoritative_evidence_rows()
    assert len(rows) >= 10
    # Collection may construct at most one additional singleton if cache was cold;
    # with warm shared repo from enrich loop above, ctor count must not grow per row.
    assert ctors["n"] - before <= 1
    assert ctors["n"] <= 2


def test_fcm_enrichment_semantics_unchanged_via_shared_repo():
    from modules.frameworks.repositories.framework_control_repository import (
        FileFrameworkControlRepository,
        clear_framework_control_repository_cache,
        get_framework_control_repository,
    )
    from modules.shared.services.evidence_authoritative_reader import _enrich_fcm_mappings

    clear_framework_control_repository_cache()
    shared = get_framework_control_repository()
    direct = FileFrameworkControlRepository()

    via_shared = _enrich_fcm_mappings({}, framework="PCI DSS", control="PCI-C-01")
    # Mirror legacy direct-instance lookup path for semantic parity.
    fw_id = direct.resolve_framework_id("pci_dss")
    doc = direct.get_framework(fw_id)
    assert doc
    match = next(c for c in (doc.get("controls") or []) if c.get("id") == "PCI-C-01")
    assert via_shared.get("fcm_framework_id") == fw_id
    assert via_shared.get("fcm_control_id") == match.get("id")
    assert via_shared.get("policy_refs") == list(match.get("policy_refs") or [])
    assert shared is get_framework_control_repository()


def test_audit_only_artifact_visible_after_ops_clear():
    rec = ops_repo.register_upload("x.txt", b"hydrate-me", "owner", "PCI DSS", "Net Banking", "PCI-C-01")
    eid = rec["evidence_id"]
    ops_repo.evidence_repository.clear()

    rows = collect_authoritative_evidence_rows()
    assert len(rows) == 1
    assert rows[0]["evidence_id"] == eid
    assert get_authoritative_evidence(eid) is not None


def test_search_module_reads_persisted_metadata_only():
    ops_repo.register_upload("enc.txt", b"encryption proof", "owner", "PCI DSS", "Net Banking", "PCI-C-01")
    hits = search_evidences(q="enc.txt")
    assert len(hits) == 1
    assert hits[0]["type"] == "persisted"
    assert hits[0]["sha256"]
    assert hits[0]["collection_source"] in ("", "manual_upload", "connector")


def test_collect_persisted_rows_include_status_fields():
    ops_repo.register_upload("enc.txt", b"encryption proof", "owner", "PCI DSS", "Net Banking", "PCI-C-01")
    row = collect_persisted_evidence_rows()[0]
    for key in (
        "approval_status",
        "review_status",
        "audit_status",
        "object_reference",
        "file_location",
        "collected_at",
    ):
        assert key in row


def test_version_increments_in_audit_repository():
    key = ai_repo.make_evidence_key("app", "CTRL")
    a1 = ai_repo.store_evidence(
        control_id="CTRL",
        content="v1",
        asset_id="app",
        source_item_id="item-1",
        source_connector="sharepoint",
    )
    a2 = ai_repo.store_evidence(
        control_id="CTRL",
        content="v2",
        asset_id="app",
        source_item_id="item-1",
        source_connector="sharepoint",
    )
    assert (a1.version, a2.version) == (1, 2)
    assert len(ai_repo.get_versions(key)) == 2


def test_repository_stats_counts_rows():
    ops_repo.register_upload("a.pdf", b"one", "owner", "PCI DSS", "Net Banking", "PCI-C-01")
    stats = repository_stats()
    assert stats["total_records"] == 1
    assert stats["frameworks"] == 1
    assert stats["applications"] == 1
