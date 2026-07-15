"""Focused tests for durable evidence-repository persistence wiring.

Covers first insert, duplicate retry, changed-content versioning, restart/reload,
SQL-disabled fallback, and SharePoint-style metadata preservation.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.sql_persistence import (
    SqlAuditPersistence,
    sqlite_file_factory,
)
from modules.operations.engines import evidence_repository as ops_repo


@pytest.fixture(autouse=True)
def _clean():
    P.reset_persistence()
    repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    yield
    P.reset_persistence()
    repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()


def _install_sql(tmp_path, filename: str = "audit.db") -> SqlAuditPersistence:
    backend = SqlAuditPersistence(sqlite_file_factory(str(tmp_path / filename)))
    P.set_persistence(backend)
    return backend


def _sharepoint_kwargs() -> dict:
    return {
        "source_connector": "sharepoint",
        "source_item_id": "sp-doc-001",
        "source_url": "https://contoso.sharepoint.com/sites/GRC/doc.pdf",
        "environment": "Production",
        "mime_type": "application/pdf",
        "metadata": {"site": "GRC", "library": "Evidence", "size": "1024"},
    }


def test_first_insert_persists_to_sql(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    _install_sql(tmp_path)
    art = repo.store_evidence(
        control_id="Req 3.4",
        content="tde report body",
        asset_id="Net Banking",
        frameworks=("PCI DSS",),
        filename="PCI_TDE.pdf",
        **_sharepoint_kwargs(),
    )
    assert art.version == 1
    persisted = P.get_persistence().get_evidence_versions(art.evidence_key)
    assert len(persisted) == 1
    assert persisted[0].content_hash == art.content_hash
    assert persisted[0].source_item_id == "sp-doc-001"
    assert dict(persisted[0].metadata) == _sharepoint_kwargs()["metadata"]


def test_duplicate_retry_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    _install_sql(tmp_path)
    kwargs = _sharepoint_kwargs()
    a1 = repo.store_evidence(control_id="C", content="same body", asset_id="app", **kwargs)
    a2 = repo.store_evidence(control_id="C", content="same body", asset_id="app", **kwargs)
    assert a1.version == a2.version == 1
    assert a1.content_hash == a2.content_hash
    assert len(repo.get_versions(a1.evidence_key)) == 1
    assert len(P.get_persistence().get_evidence_versions(a1.evidence_key)) == 1


def test_changed_content_creates_new_version(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    _install_sql(tmp_path)
    kwargs = _sharepoint_kwargs()
    a1 = repo.store_evidence(control_id="C", content="version-one", asset_id="app", **kwargs)
    a2 = repo.store_evidence(control_id="C", content="version-two", asset_id="app", **kwargs)
    assert (a1.version, a2.version) == (1, 2)
    assert a1.content_hash != a2.content_hash
    assert a2.source_item_id == kwargs["source_item_id"]
    assert len(P.get_persistence().get_evidence_versions(a1.evidence_key)) == 2


def test_restart_reload_hydrates_without_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    db = str(tmp_path / "audit.db")
    b1 = SqlAuditPersistence(sqlite_file_factory(db))
    P.set_persistence(b1)
    art = repo.store_evidence(
        control_id="C",
        content="durable",
        asset_id="app",
        source_item_id="item-42",
        source_connector="sharepoint",
    )
    repo.reset_repository()
    assert repo.all_latest() == []

    b2 = SqlAuditPersistence(sqlite_file_factory(db))
    P.set_persistence(b2)
    hydrated = repo.hydrate_from_persistence()
    assert hydrated == 1
    latest = repo.get_latest(art.evidence_key)
    assert latest is not None
    assert latest.version == 1
    assert latest.content_hash == art.content_hash

    # Second hydrate must not duplicate in-memory rows.
    assert repo.hydrate_from_persistence() == 0
    assert len(repo.get_versions(art.evidence_key)) == 1


def test_sql_disabled_fallback_uses_memory_only(monkeypatch):
    monkeypatch.delenv("AUDIT_WORKFLOW_ENABLED", raising=False)
    # Default provider is in-memory SQL-off mode; writes still succeed.
    art = repo.store_evidence(control_id="C", content="local only", asset_id="app")
    assert art.version == 1
    assert len(repo.get_versions(art.evidence_key)) == 1
    assert isinstance(P.get_persistence(), P.InMemoryAuditPersistence)

    repo.reset_repository()
    assert repo.hydrate_from_persistence() == 0
    assert repo.all_latest() == []


def test_sharepoint_metadata_preserved_via_register_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    _install_sql(tmp_path)
    record = ops_repo.register_upload(
        "policy.pdf",
        b"sharepoint policy text",
        "scheduler",
        framework="PCI DSS",
        application="Net Banking",
        control="Req 12.1",
        source_connector="sharepoint",
        source_item_id="graph-id-778",
        source_url="https://bank.sharepoint.com/sites/GRC/policy.pdf",
        environment="Production",
        mime_type="application/pdf",
        metadata={"library": "Evidence", "webUrl": "https://bank.sharepoint.com/sites/GRC/policy.pdf"},
    )
    assert record.get("audit_repository_synced") is True
    key = repo.make_evidence_key("Net Banking", "Req 12.1")
    versions = repo.get_versions(key)
    assert len(versions) == 1
    art = versions[0]
    assert art.source_connector == "sharepoint"
    assert art.source_item_id == "graph-id-778"
    assert art.source_url.endswith("policy.pdf")
    assert art.environment == "Production"
    assert art.mime_type == "application/pdf"
    assert dict(art.metadata)["library"] == "Evidence"
    assert art.evidence_id == record["evidence_id"]

    persisted = P.get_persistence().find_evidence_by_source_hash(
        "graph-id-778", art.content_hash,
    )
    assert persisted is not None
    assert persisted.filename == record["filename"]
