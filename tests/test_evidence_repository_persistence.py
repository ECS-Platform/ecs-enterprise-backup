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
    import time as _time

    P.reset_persistence()
    repo.reset_repository()
    # Skip live PostgreSQL on search()/stats() hydration in unit tests.
    # Canonical hydration tests that need the DAL use force=True + monkeypatch.
    repo._last_canonical_failure_at = _time.monotonic()
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


# --------------------------------------------------------------------------- #
# Canonical PostgreSQL -> Audit Intelligence hydration bridge
# --------------------------------------------------------------------------- #
class _FakeCanonicalRepo:
    """Mocks ``ecs_platform.repository.EvidenceRepository`` for hydration tests."""

    calls = 0

    def __init__(self, rows=None, raise_on_search: bool = False):
        self._rows = list(rows or [])
        self._raise = raise_on_search

    def search_evidence(self, *, limit: int = 1000):
        _FakeCanonicalRepo.calls += 1
        if self._raise:
            raise RuntimeError("connection refused")
        return self._rows

    def close(self):
        pass


def _canonical_row(uid="EVD-00705", title="encryption_evidence.txt"):
    return {
        "evidence_uid": uid,
        "source_system": "sharepoint_graph",
        "source_object_id": "file-1",
        "object_type": "file",
        "title": title,
        "content": "encryption at rest policy body",
        "url": "http://minio:9000/ecs-evidence/Net-Banking/encryption_evidence.txt",
        "application": "Net-Banking",
        "content_hash": "fallback-hash-abc",
        "metadata": {
            "control": "A.8.24",
            "framework": "ISO27001",
            "environment": "Production",
            "object_uri": "http://minio:9000/ecs-evidence/Net-Banking/encryption_evidence.txt",
            "custody_mode": "SNAPSHOT",
            "original_filename": title,
            "modified_datetime": "2026-07-20T10:00:00Z",
            "web_url": "https://contoso.sharepoint.com/sites/GRC/encryption_evidence.txt",
        },
        "collected_timestamp": "2026-07-21T08:00:00Z",
    }


def test_canonical_hydration_preserves_metadata_fields(monkeypatch):
    """Canonical DAL fields (metadata + source_object_id) survive hydration mapping."""
    row = _canonical_row()
    monkeypatch.setattr(
        "ecs_platform.repository.EvidenceRepository",
        lambda: _FakeCanonicalRepo(rows=[row]),
    )
    assert repo.hydrate_from_canonical_repository(force=True) == 1

    found = repo.search(query="EVD-00705")
    assert len(found) == 1
    art = found[0]
    assert art.evidence_id == "EVD-00705"
    assert art.frameworks == ("ISO27001",)
    assert art.environment == "Production"
    assert art.source_item_id == "file-1"
    assert art.custody_mode == "SNAPSHOT"
    assert art.object_uri == row["metadata"]["object_uri"]
    assert art.source_modified_at == "2026-07-20T10:00:00Z"
    assert art.source_connector == "sharepoint_graph"
    assert art.source_url == row["metadata"]["web_url"]
    assert art.content_hash == "fallback-hash-abc"
    assert art.filename == "encryption_evidence.txt"


def test_canonical_hydration_idempotent_no_duplicate_versions(monkeypatch):
    """Repeated hydration of the same canonical row must not create new versions."""
    row = _canonical_row()
    fake = _FakeCanonicalRepo(rows=[row])
    monkeypatch.setattr("ecs_platform.repository.EvidenceRepository", lambda: fake)

    assert repo.hydrate_from_canonical_repository(force=True) == 1
    assert repo.hydrate_from_canonical_repository(force=True) == 0
    assert repo.hydrate_from_canonical_repository(force=True) == 0

    versions = repo.get_versions(repo.make_evidence_key("Net-Banking", "A.8.24"))
    assert len(versions) == 1


def test_canonical_hydration_preserves_existing_baseline_evidence(monkeypatch):
    """Existing in-memory (baseline/demo) evidence must survive hydration."""
    baseline = repo.store_evidence(control_id="NGX-003", content="ssl on",
                                   technology="NGINX", asset_id="web-1")
    row = _canonical_row()
    monkeypatch.setattr(
        "ecs_platform.repository.EvidenceRepository",
        lambda: _FakeCanonicalRepo(rows=[row]),
    )
    repo.hydrate_from_canonical_repository(force=True)

    assert repo.get_latest(baseline.evidence_key) is not None
    assert repo.get_latest(baseline.evidence_key).content_hash == baseline.content_hash
    assert repo.stats()["evidence_keys"] >= 2


def test_canonical_repository_failure_is_non_fatal(monkeypatch):
    """An unreachable/erroring canonical repository must never break search()/stats()."""
    monkeypatch.setattr(
        "ecs_platform.repository.EvidenceRepository",
        lambda: _FakeCanonicalRepo(raise_on_search=True),
    )
    n = repo.hydrate_from_canonical_repository(force=True)
    assert n == 0
    # search()/stats() call hydration internally and must still work.
    assert repo.search(query="") == []
    assert repo.stats()["evidence_keys"] == 0


def test_canonical_hydration_refresh_guard_throttles_repeated_calls(monkeypatch):
    """Within the refresh interval, non-forced hydration must not re-invoke the DAL."""
    row = _canonical_row()
    fake = _FakeCanonicalRepo(rows=[row])
    monkeypatch.setattr("ecs_platform.repository.EvidenceRepository", lambda: fake)

    # Clear autouse failure throttle so this test measures the success refresh guard.
    repo._last_canonical_failure_at = 0.0
    repo._last_canonical_success_at = 0.0
    _FakeCanonicalRepo.calls = 0

    assert repo.hydrate_from_canonical_repository(force=True) == 1
    assert _FakeCanonicalRepo.calls == 1

    # Non-forced calls (as search()/stats() make) within the refresh interval
    # must be a no-op — no additional DAL invocation.
    assert repo.hydrate_from_canonical_repository() == 0
    assert repo.hydrate_from_canonical_repository() == 0
    assert _FakeCanonicalRepo.calls == 1
    assert repo.search(query="encryption_evidence.txt")
    assert _FakeCanonicalRepo.calls == 1
