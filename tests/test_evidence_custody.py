"""Focused tests for evidence content custody (local/injected storage only)."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")

import pytest

from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.services import evidence_custody as custody
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.connector_executor import _ingest_items
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.operations.engines import evidence_repository as ops_repo


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "false")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "REFERENCE_ONLY")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    P.reset_persistence()
    P.set_persistence(SqlAuditPersistence())
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    yield
    reset_object_store()
    P.reset_persistence()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()


def test_reference_only_default_persists_source_metadata(tmp_path):
    result = custody.resolve_custody(
        source_connector="sharepoint_graph",
        source_item_id="sp-001",
        source_url="https://contoso.sharepoint.com/doc.pdf",
        source_modified_at="2026-07-01T10:00:00Z",
        filename="doc.pdf",
        mime_type="application/pdf",
        evidence_key="Net Banking::Req 3.4",
        version=1,
    )
    assert result.custody_mode == custody.CUSTODY_REFERENCE_ONLY
    assert result.object_uri == ""
    assert len(result.content_hash) == 64
    assert result.source_item_id == "sp-001"
    assert result.source_url.endswith("doc.pdf")
    assert result.source_modified_at == "2026-07-01T10:00:00Z"


def test_snapshot_stores_immutable_object(monkeypatch, tmp_path):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    body = b"%PDF-1.4 snapshot bytes"
    r1 = custody.resolve_custody(
        source_connector="sharepoint_graph",
        source_item_id="sp-002",
        source_url="https://contoso.sharepoint.com/snap.pdf",
        source_modified_at="2026-07-01T11:00:00Z",
        filename="snap.pdf",
        mime_type="application/pdf",
        evidence_key="Payments::Req 10.1",
        version=1,
        content=body,
    )
    assert r1.custody_mode == custody.CUSTODY_SNAPSHOT
    assert r1.stored is True
    assert r1.object_uri.startswith("file://")
    assert r1.content_hash
    assert r1.size_bytes == len(body)

    r2 = custody.resolve_custody(
        source_connector="sharepoint_graph",
        source_item_id="sp-002",
        source_url="https://contoso.sharepoint.com/snap.pdf",
        source_modified_at="2026-07-01T11:00:00Z",
        filename="snap.pdf",
        mime_type="application/pdf",
        evidence_key="Payments::Req 10.1",
        version=1,
        content=body,
    )
    assert r2.stored is False
    assert r2.reason == "immutable_exists"
    assert r2.object_uri == r1.object_uri


def test_snapshot_falls_back_when_download_unavailable(monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    result = custody.resolve_custody(
        source_connector="sharepoint_graph",
        source_item_id="sp-003",
        source_url="https://contoso.sharepoint.com/missing.pdf",
        source_modified_at="2026-07-02T09:00:00Z",
        filename="missing.pdf",
        mime_type="application/pdf",
        evidence_key="Treasury::Req 1.1",
        version=1,
        content=None,
    )
    assert result.custody_mode == custody.CUSTODY_REFERENCE_ONLY
    assert result.reason == "snapshot_unavailable"


def test_size_limit_enforced(monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    monkeypatch.setenv("ECS_EVIDENCE_MAX_BYTES", "16")
    result = custody.resolve_custody(
        source_connector="sharepoint_graph",
        source_item_id="sp-004",
        source_url="https://contoso.sharepoint.com/big.pdf",
        source_modified_at="2026-07-02T10:00:00Z",
        filename="big.pdf",
        mime_type="application/pdf",
        evidence_key="Net Banking::Req 3.4",
        version=1,
        content=b"this payload is definitely larger than sixteen bytes",
    )
    assert result.custody_mode == custody.CUSTODY_REFERENCE_ONLY
    assert result.reason == "size_limit_exceeded"


def test_mime_type_limit_enforced(monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    result = custody.resolve_custody(
        source_connector="sharepoint_graph",
        source_item_id="sp-005",
        source_url="https://contoso.sharepoint.com/evil.exe",
        source_modified_at="2026-07-02T11:00:00Z",
        filename="evil.exe",
        mime_type="application/octet-stream",
        evidence_key="Net Banking::Req 3.4",
        version=1,
        content=b"MZ",
    )
    assert result.custody_mode == custody.CUSTODY_REFERENCE_ONLY
    assert result.reason == "mime_type_not_allowed"


def test_register_upload_reference_only_metadata(monkeypatch):
    record = ops_repo.register_upload(
        "policy.pdf",
        b"",
        "scheduler",
        framework="PCI DSS",
        application="Net Banking",
        control="Req 12.1",
        source_connector="sharepoint_graph",
        source_item_id="graph-99",
        source_url="https://bank.sharepoint.com/policy.pdf",
        environment="Production",
        mime_type="application/pdf",
        source_modified_at="2026-06-01T08:00:00Z",
    )
    assert record["custody_mode"] == custody.CUSTODY_REFERENCE_ONLY
    key = ai_repo.make_evidence_key("Net Banking", "Req 12.1")
    art = ai_repo.get_latest(key)
    assert art is not None
    assert art.custody_mode == custody.CUSTODY_REFERENCE_ONLY
    assert art.source_item_id == "graph-99"
    assert art.source_modified_at == "2026-06-01T08:00:00Z"
    assert art.object_uri == ""


def test_connector_ingest_snapshot_with_injected_bytes(monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    items = [{
        "item_id": "sp-100",
        "web_url": "https://bank.sharepoint.com/evidence/tde.pdf",
        "modified_datetime": "2026-05-01T12:00:00Z",
        "filename": "tde.pdf",
        "mime_type": "application/pdf",
        "environment": "Production",
        "framework": "PCI DSS",
        "control_or_observation": "Req 3.4",
        "content_bytes": b"%PDF-1.4 injected",
    }]
    receipts = _ingest_items(
        "sharepoint_graph",
        items,
        framework="PCI DSS",
        application="Net Banking",
        control="Req 3.4",
        collected_by="test",
        max_items=10,
    )
    assert receipts[0]["custody_mode"] == custody.CUSTODY_SNAPSHOT
    assert receipts[0]["object_uri"].startswith("file://")
    key = ai_repo.make_evidence_key("Net Banking", "Req 3.4")
    art = ai_repo.get_latest(key)
    assert art.custody_mode == custody.CUSTODY_SNAPSHOT
    assert art.object_uri.startswith("file://")
    assert art.source_modified_at == "2026-05-01T12:00:00Z"
