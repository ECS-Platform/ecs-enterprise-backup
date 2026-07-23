"""Focused validation tests for Phase-1 Common Control Library."""

from __future__ import annotations

import hashlib
import json
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.frameworks.services.common_controls_service import get_common_controls_service
from modules.operations.engines import common_controls_collector as cc
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines.common_controls_catalog import (
    COMMON_CONTROLS,
    FCM_FRAMEWORK_NAMES,
)


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    P.reset_persistence()
    P.set_persistence(SqlAuditPersistence())
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    yield
    reset_object_store()
    P.reset_persistence()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()


def test_catalog_covers_ten_framework_independent_controls():
    assert len(COMMON_CONTROLS) == 10
    slugs = {c.slug for c in COMMON_CONTROLS}
    assert "encryption-at-rest" in slugs
    assert "network-security" in slugs
    for ctrl in COMMON_CONTROLS:
        assert ctrl.frameworks == FCM_FRAMEWORK_NAMES
        assert ctrl.to_dict()["framework_independent"] is True


def test_manifest_frameworks_match_fcm_phase1():
    expected = set(FCM_FRAMEWORK_NAMES)
    for ctrl in COMMON_CONTROLS:
        manifest = cc.load_manifest(cc.common_controls_root() / ctrl.slug)
        assert set(manifest.get("frameworks") or []) == expected


def test_fcm_cross_reference_mapping_without_duplicating_controls():
    svc = get_common_controls_service()
    refs = svc.resolve_fcm_references("encryption-at-rest")
    assert refs
    sample = refs[0]
    assert sample["common_control_id"] == "CC-ENCRYPTION_AT_REST"
    assert sample["framework_id"]
    assert sample["control_id"]
    assert sample["policy_refs"]
    assert sample["procedure_ids"]
    assert sample["evidence_requirement_ids"]
    fw_ids = {r["framework_id"] for r in refs}
    assert "pci_dss" in fw_ids
    assert "database_baseline" in fw_ids


def test_collection_tags_metadata_version_and_sha256():
    folder = cc.common_controls_root() / "encryption-at-rest"
    receipt = cc.collect_common_control_folder(folder, user="tester", run_id="CC-META")
    assert receipt.collected
    latest = ai_repo.get_latest(receipt.evidence_key)
    assert latest.version >= 1
    meta = dict(latest.metadata or ())
    assert str(meta.get("framework_independent")).lower() == "true"
    assert meta.get("collection_source") == "CommonControls"
    assert meta.get("content_sha256")
    assert len(meta.get("content_sha256", "")) == 64
    assert int(meta.get("fcm_reference_count") or 0) > 0
    assert "ITPP" in (meta.get("framework_refs") or [])


def test_identical_recollect_is_sha256_duplicate_without_extra_ops_row():
    folder = cc.common_controls_root() / "audit-logging"
    first = cc.collect_common_control_folder(folder, user="tester", run_id="CC-DUP-1")
    second = cc.collect_common_control_folder(folder, user="tester", run_id="CC-DUP-2")
    assert first.collected and second.collected
    assert len(ops_repo.evidence_repository) == 1
    assert len(ai_repo.get_versions(first.evidence_key)) == 1


def test_changed_evidence_creates_new_version(tmp_path):
    src = cc.common_controls_root() / "backup-restore"
    folder = tmp_path / "backup-restore"
    folder.mkdir()
    for name in ("manifest.json", "evidence.json"):
        (folder / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")
    first = cc.collect_common_control_folder(folder, user="tester", run_id="CC-V1")
    evidence_path = folder / "evidence.json"
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    payload["rpo_hours"] = 6
    evidence_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    second = cc.collect_common_control_folder(folder, user="tester", run_id="CC-V2")
    assert second.collected
    versions = ai_repo.get_versions(first.evidence_key)
    assert len(versions) >= 2
    assert versions[-1].content_hash != versions[0].content_hash


def test_common_controls_api_exposure():
    client = TestClient(app)
    listing = client.get("/api/common-controls")
    assert listing.status_code == 200
    body = listing.json()
    assert body["count"] == 10
    assert body["frameworks"]

    detail = client.get("/api/common-controls/encryption-in-transit")
    assert detail.status_code == 200
    dbody = detail.json()
    assert dbody["ok"] is True
    assert dbody["framework_mappings"]

    fw = client.get("/api/common-controls/framework/pci_dss")
    assert fw.status_code == 200
    assert fw.json()["count"] >= 1


def test_authoritative_reader_includes_common_control_rows():
    cc.collect_common_control_folder(
        cc.common_controls_root() / "network-security",
        user="tester",
        run_id="CC-READ",
    )
    from modules.shared.services.evidence_authoritative_reader import (
        collect_authoritative_evidence_rows,
    )

    rows = [
        r
        for r in collect_authoritative_evidence_rows()
        if r.get("source_connector") == "common_controls"
    ]
    assert rows
    assert rows[0].get("sha256") == hashlib.sha256(
        (cc.common_controls_root() / "network-security" / "evidence.json").read_bytes()
    ).hexdigest()
