"""Regression: persist uses fcm_control_id; OS Baseline enrichment resolves."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from ecs_platform.evidence_completeness import STATUS_COMPLETE, compute_evidence_completeness
from modules.frameworks.repositories.framework_control_repository import (
    clear_framework_control_repository_cache,
)
from modules.operations.engines import evidence_repository as ops_repo
from modules.shared.services.evidence_authoritative_reader import (
    _enrich_fcm_mappings,
    collect_authoritative_evidence_rows,
    get_authoritative_evidence,
)


@pytest.fixture(autouse=True)
def _clean():
    from modules.audit_intelligence.engines import evidence_repository as ai_repo

    clear_framework_control_repository_cache()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    yield
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    clear_framework_control_repository_cache()


class _CapturingCanonicalRepo:
    """Capture upsert_evidence payloads without touching PostgreSQL."""

    def __init__(self):
        self.items: list[dict] = []

    def upsert_evidence(self, item: dict) -> int:
        self.items.append(dict(item))
        item.setdefault("evidence_uid", item.get("evidence_uid") or "EVD-CAP-1")
        return 1

    def close(self):
        pass


@pytest.mark.parametrize(
    "framework_label",
    [
        "OS Baseline",
        "OS Baselining",
        "Operating System Baseline",
        "os_baseline",
    ],
)
def test_os_baseline_framework_labels_resolve_same_fcm(framework_label):
    meta = _enrich_fcm_mappings(
        {},
        framework=framework_label,
        control="OSB-C-01",
    )
    assert meta.get("fcm_framework_id") == "os_baseline"
    assert meta.get("fcm_control_id") == "OSB-C-01"
    assert meta.get("evidence_requirement_ids")


def test_os_baseline_title_control_enriches_to_fcm_id():
    meta = _enrich_fcm_mappings(
        {},
        framework="OS Baselining",
        control="Linux Server Hardening — CIS L2",
    )
    assert meta.get("fcm_framework_id") == "os_baseline"
    assert meta.get("fcm_control_id") == "OSB-C-01"


def test_persist_prefers_fcm_control_id_for_control_map(monkeypatch):
    fake = _CapturingCanonicalRepo()
    monkeypatch.setattr(
        "ecs_platform.repository.repository.EvidenceRepository",
        lambda: fake,
    )
    record = {
        "evidence_id": "EVD-OSB-001",
        "filename": "hardening.pdf",
        "control": "Linux Server Hardening — CIS L2",
        "framework_tags": ["OS Baselining"],
        "application_tags": ["Net Banking"],
        "uploaded_by": "owner",
        "source_connector": "upload",
        "mime_type": "application/pdf",
        "metadata": {
            "fcm_framework_id": "os_baseline",
            "fcm_control_id": "OSB-C-01",
        },
    }
    ops_repo._persist_upload_to_canonical(record, "body", stored=None)
    assert record.get("canonical_persisted") is True
    assert fake.items, "expected canonical upsert"
    assert fake.items[0]["control_mapping"] == ["OSB-C-01"]


def test_legacy_persist_without_fcm_control_id_keeps_control_string(monkeypatch):
    fake = _CapturingCanonicalRepo()
    monkeypatch.setattr(
        "ecs_platform.repository.repository.EvidenceRepository",
        lambda: fake,
    )
    record = {
        "evidence_id": "EVD-LEGACY-001",
        "filename": "legacy.pdf",
        "control": "Legacy-Control-Title",
        "framework_tags": ["Custom Framework"],
        "application_tags": ["Net Banking"],
        "uploaded_by": "owner",
        "source_connector": "upload",
        "mime_type": "application/pdf",
        "metadata": {},
    }
    ops_repo._persist_upload_to_canonical(record, "legacy body", stored=None)
    assert record.get("canonical_persisted") is True
    assert fake.items[0]["control_mapping"] == ["Legacy-Control-Title"]
    assert "fcm_control_id" not in (fake.items[0].get("metadata") or {})


def test_pci_enrichment_and_persist_still_map_pci_c_01(monkeypatch):
    fake = _CapturingCanonicalRepo()
    monkeypatch.setattr(
        "ecs_platform.repository.repository.EvidenceRepository",
        lambda: fake,
    )
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
    # Canonical write may no-op if PG import path differs; force persist path.
    ops_repo._persist_upload_to_canonical(rec, "network segmentation evidence", stored=None)
    assert fake.items
    assert fake.items[-1]["control_mapping"] == ["PCI-C-01"]


def test_os_baseline_mapped_evidence_is_complete(monkeypatch):
    """After persist prefers OSB-C-01, completeness classifies that control Complete."""

    class _OsFcm:
        def resolve_framework_id(self, framework_id: str) -> str:
            key = (framework_id or "").strip().lower().replace(" ", "_").replace("-", "_")
            if key in {"os_baseline", "os_baselining"}:
                return "os_baseline"
            return key

        def get_framework(self, framework_id: str):
            if framework_id != "os_baseline":
                return None
            return {
                "framework": {
                    "id": "os_baseline",
                    "code": "OSB",
                    "name": "OS Baseline",
                    "display_name": "Operating System Baseline",
                },
                "controls": [
                    {"id": "OSB-C-01", "title": "Linux Server Hardening — CIS L2", "domain": "Hardening"},
                    {"id": "OSB-C-02", "title": "Other", "domain": "Access"},
                ],
            }

        def list_framework_summaries(self):
            return [
                {
                    "id": "os_baseline",
                    "code": "OSB",
                    "name": "OS Baseline",
                    "display_name": "Operating System Baseline",
                }
            ]

    by_control = {
        "OSB-C-01": [
            {"evidence_uid": "EVD-OSB-001", "review_status": "Approved", "valid_until": None}
        ],
        "OSB-C-02": [],
    }
    monkeypatch.setattr(
        "ecs_platform.evidence_completeness._fetch_evidence_by_control",
        lambda *a, **k: (by_control, {}),
    )
    result = compute_evidence_completeness(
        "Net Banking",
        "OS Baseline",
        repo=object(),
        fcm_repo=_OsFcm(),
    )
    assert result["ok"] is True
    by_id = {c["control_id"]: c for c in result["controls"]}
    assert by_id["OSB-C-01"]["status"] == STATUS_COMPLETE
    assert by_id["OSB-C-01"]["reason"] == "Approved evidence exists"


def test_pci_completeness_still_works(monkeypatch):
    from tests.test_evidence_completeness import _FakeFcmRepo

    by_control = {
        "PCI-C-01": [
            {"evidence_uid": "EVD-PCI-1", "review_status": "Approved", "valid_until": None}
        ],
        "PCI-C-02": [],
        "PCI-C-03": [],
    }
    monkeypatch.setattr(
        "ecs_platform.evidence_completeness._fetch_evidence_by_control",
        lambda *a, **k: (by_control, {}),
    )
    result = compute_evidence_completeness(
        "Net Banking", "PCI DSS", repo=object(), fcm_repo=_FakeFcmRepo()
    )
    assert result["ok"] is True
    by_id = {c["control_id"]: c for c in result["controls"]}
    assert by_id["PCI-C-01"]["status"] == STATUS_COMPLETE


def test_existing_evidence_remains_readable_after_enrichment():
    rec = ops_repo.register_upload(
        "hardening.pdf",
        b"cis scan export",
        "owner",
        "OS Baselining",
        "Net Banking",
        "OSB-C-01",
    )
    eid = rec["evidence_id"]
    meta = rec.get("metadata") or {}
    assert meta.get("fcm_control_id") == "OSB-C-01"
    assert meta.get("fcm_framework_id") == "os_baseline"

    rows = collect_authoritative_evidence_rows()
    assert any(r["evidence_id"] == eid for r in rows)
    found = get_authoritative_evidence(eid)
    assert found is not None
    assert found["evidence_id"] == eid
    assert (found.get("metadata") or {}).get("fcm_control_id") == "OSB-C-01"
