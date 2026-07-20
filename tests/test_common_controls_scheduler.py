"""Tests for Phase-1 Common Control Library scheduler collection."""

from __future__ import annotations

import json
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")

import pytest

from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.engines import observation_generation as obs_gen
from modules.audit_intelligence.models import VERDICT_FAIL, VERDICT_PASS
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.operations.engines import common_controls_collector as cc
from modules.operations.engines import scheduler_module as sm
from modules.operations.engines.common_controls_catalog import COMMON_CONTROLS
from modules.operations.engines import evidence_repository as ops_repo


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    P.reset_persistence()
    P.set_persistence(SqlAuditPersistence())
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    obs_gen.reset_observations()
    yield
    reset_object_store()
    P.reset_persistence()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    obs_gen.reset_observations()


@pytest.mark.parametrize("control", COMMON_CONTROLS, ids=lambda c: c.slug)
def test_common_control_folder_discovered(control):
    folders = cc.discover_common_control_folders()
    slugs = {p.name for p in folders}
    assert control.slug in slugs


@pytest.mark.parametrize("control", COMMON_CONTROLS, ids=lambda c: c.slug)
def test_common_control_collection_persists_metadata_and_storage(control):
    folder = cc.common_controls_root() / control.slug
    receipt = cc.collect_common_control_folder(folder, user="tester", run_id="CC-TEST")
    assert receipt.discovered is True
    assert receipt.collected is True, receipt.error
    assert receipt.metadata_persisted is True
    assert receipt.object_stored is True
    assert receipt.verdict in (VERDICT_PASS, VERDICT_FAIL)
    latest = ai_repo.get_latest(receipt.evidence_key)
    assert latest is not None
    assert latest.source == "common_controls"
    assert latest.source_connector == "common_controls"
    meta = dict(latest.metadata or ())
    assert meta.get("common_control_slug") == control.slug
    assert meta.get("collection_source") == "CommonControls"
    assert any(ops["control"] == receipt.control_id for ops in ops_repo.evidence_repository)


@pytest.mark.parametrize("control", COMMON_CONTROLS, ids=lambda c: c.slug)
def test_validation_failure_generates_observation(control):
    manifest = cc.load_manifest(cc.common_controls_root() / control.slug)
    payload = {"collected_at": "2026-07-17T00:00:00Z"}
    vr = cc.validate_evidence(manifest, payload)
    assert vr.verdict == VERDICT_FAIL
    before = len(obs_gen.list_observations())
    obs = obs_gen.generate_observation(vr, asset_id="ECS Common Controls", control_name=control.name)
    assert obs is not None
    assert len(obs_gen.list_observations()) == before + 1


def test_certificate_management_scheduler_run_creates_observation():
    obs_gen.reset_observations()
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    run = cc.collect_all_common_controls(user="scheduler", run_id="CC-CERT-FAIL")
    cert = next(r for r in run.receipts if r.slug == "certificate-management")
    assert cert.collected is True
    assert cert.verdict == VERDICT_FAIL
    assert cert.observation_id
    assert obs_gen.get_observation(cert.observation_id) is not None
    assert run.observations >= 1


def test_scheduler_run_includes_common_controls(monkeypatch):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "true")
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.load_assets",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.plan_evidence",
        lambda *a, **k: __import__(
            "modules.audit_intelligence.services.asset_scheduler", fromlist=["EvidencePlan"]
        ).EvidencePlan(jobs=[], unsupported=[]),
    )
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.execute_plan",
        lambda *a, **k: [],
    )
    result = sm.run_scheduler_collection(user="tester")
    assert result["common_controls_collected"] == len(COMMON_CONTROLS)
    assert result["ingested"] >= len(COMMON_CONTROLS)
    assert result["common_controls"]["folders_discovered"] == len(COMMON_CONTROLS)


def test_collect_all_covers_every_catalog_control():
    run = cc.collect_all_common_controls(user="tester", run_id="CC-ALL")
    assert run.folders_discovered == len(COMMON_CONTROLS)
    assert run.collected == len(COMMON_CONTROLS)
    slugs = {r.slug for r in run.receipts}
    assert slugs == {c.slug for c in COMMON_CONTROLS}


def test_manifest_predefined_query_ids_match_catalog():
    for control in COMMON_CONTROLS:
        manifest = cc.load_manifest(cc.common_controls_root() / control.slug)
        manifest_ids = set(manifest.get("predefined_query_ids") or [])
        assert manifest_ids == set(control.predefined_query_ids)
