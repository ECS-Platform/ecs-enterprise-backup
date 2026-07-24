"""Regression tests for FCM YAML caching on the evidence enrichment hot path."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.frameworks.repositories.framework_control_repository import (
    FileFrameworkControlRepository,
    clear_framework_control_repository_cache,
    get_framework_control_repository,
)
from modules.operations.engines import evidence_repository as ops_repo
from modules.shared.services.evidence_authoritative_reader import (
    _enrich_fcm_mappings,
    collect_authoritative_evidence_rows,
)


@pytest.fixture(autouse=True)
def _reset_fcm_cache():
    clear_framework_control_repository_cache()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    yield
    clear_framework_control_repository_cache()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()


def _append_row_without_fcm(*, evidence_id: str, body: bytes) -> None:
    """Simulate scheduler/PQ rows that lack pre-enriched FCM metadata."""
    ops_repo.evidence_repository.append(
        {
            "evidence_id": evidence_id,
            "filename": f"{evidence_id}.pdf",
            "original_filename": f"{evidence_id}.pdf",
            "framework_tags": ["PCI DSS"],
            "application_tags": ["Net Banking"],
            "control": "PCI-C-01",
            "uploaded_by": "scheduler",
            "uploaded_at": "2026-07-23T12:00:00+00:00",
            "sha256": f"sha-{evidence_id}",
            "metadata": {"collection_source": "predefined_query"},
            "status": "Collected",
            "environment": "Production",
        }
    )


def test_repeated_enrichment_does_not_reparse_yaml_per_row():
    row_count = 8
    for i in range(row_count):
        _append_row_without_fcm(evidence_id=f"PGX-{i:03d}", body=f"body-{i}".encode())

    clear_framework_control_repository_cache()
    import modules.frameworks.repositories.framework_control_repository as fcm_repo

    real_load = fcm_repo._load_yaml
    load_calls = 0

    def counting_load(path):
        nonlocal load_calls
        load_calls += 1
        return real_load(path)

    with patch.object(fcm_repo, "_load_yaml", side_effect=counting_load):
        rows = collect_authoritative_evidence_rows()

    assert len(rows) == row_count
    # Without caching this would be >> row_count (catalog + framework per row).
    assert load_calls < row_count
    assert load_calls <= 12


def test_authoritative_output_unchanged_with_shared_repository_cache():
    _append_row_without_fcm(evidence_id="EQ-001", body=b"one")
    _append_row_without_fcm(evidence_id="EQ-002", body=b"two")

    clear_framework_control_repository_cache()
    baseline = collect_authoritative_evidence_rows()
    cached = collect_authoritative_evidence_rows()

    assert [r["evidence_id"] for r in baseline] == [r["evidence_id"] for r in cached]
    for before, after in zip(baseline, cached, strict=True):
        assert before["metadata"].get("fcm_framework_id") == after["metadata"].get(
            "fcm_framework_id"
        )
        assert before["metadata"].get("fcm_control_id") == after["metadata"].get(
            "fcm_control_id"
        )
        assert before["metadata"].get("policy_refs") == after["metadata"].get("policy_refs")


def test_enrich_fcm_mappings_uses_singleton_repository():
    meta = {}
    repo_first = get_framework_control_repository()
    enriched = _enrich_fcm_mappings(meta, framework="PCI DSS", control="PCI-C-01")
    repo_second = get_framework_control_repository()
    assert repo_first is repo_second
    assert enriched.get("fcm_control_id") == "PCI-C-01"
    assert enriched.get("fcm_framework_id") == "pci_dss"


def test_clear_cache_allows_fresh_reads_after_catalog_touch(tmp_path):
    import shutil

    catalog_src = (
        FileFrameworkControlRepository()._catalog_dir  # noqa: SLF001 — test helper
    )
    work = tmp_path / "fcm"
    shutil.copytree(catalog_src, work)

    repo = FileFrameworkControlRepository(catalog_dir=work)
    before = repo.get_framework("pci_dss")
    assert before is not None

    fw_path = work / "frameworks" / "pci_dss.yaml"
    text = fw_path.read_text(encoding="utf-8")
    fw_path.write_text(text.replace("PCI DSS", "PCI DSS CACHED"), encoding="utf-8")

    # mtime-based YAML cache should pick up the edit without explicit clear.
    after = FileFrameworkControlRepository(catalog_dir=work).get_framework("pci_dss")
    assert after is not None
    assert "CACHED" in str(after["framework"].get("name", ""))

    clear_framework_control_repository_cache()
    repo.clear_cache()
