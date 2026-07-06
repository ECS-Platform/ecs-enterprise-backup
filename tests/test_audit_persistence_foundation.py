"""Tests for the audit-intelligence durable persistence foundation.

Backends under test: the in-memory reference implementation and the SQL skeleton
backed by **in-memory SQLite** (stdlib ``sqlite3``). NO external/live database is
used. Verifies interface conformance for both backends, model round-tripping,
evidence versioning + latest selection, run/observation ordering, scheduler
history bounding, and the pluggable provider — plus that the existing in-memory
engines still work unchanged (persistence is additive).
"""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.models import (
    EvidenceArtifact,
    EvidenceRecord,
    EvidenceRun,
    Observation,
    STATUS_COMPLETED,
    ValidationResult,
    VERDICT_FAIL,
)
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services.sql_persistence import (
    SqlAuditPersistence,
    sqlite_file_factory,
)


# --------------------------------------------------------------------------- #
# Fixtures: one instance of each backend, cleared per test
# --------------------------------------------------------------------------- #
def _make_inmemory() -> P.AuditPersistence:
    b = P.InMemoryAuditPersistence()
    b.initialize()
    return b


def _make_sqlite() -> P.AuditPersistence:
    b = SqlAuditPersistence()  # shared in-memory SQLite
    b.initialize()
    b.clear()
    return b


@pytest.fixture(params=["inmemory", "sqlite"])
def backend(request) -> P.AuditPersistence:
    b = _make_inmemory() if request.param == "inmemory" else _make_sqlite()
    b.clear()
    return b


# --------------------------------------------------------------------------- #
# Sample builders
# --------------------------------------------------------------------------- #
def _run(run_id: str, created_at: str, status: str = STATUS_COMPLETED) -> EvidenceRun:
    run = EvidenceRun(run_id=run_id, scope_kind="technology", scope_value="NGINX",
                      requested_by="tester", status=status, created_at=created_at)
    run.records = [
        EvidenceRecord(control_id="NGX-003", technology="NGINX", status=STATUS_COMPLETED,
                       frameworks=("PCI DSS",), asset_id="A1", ok=True, rows_returned=1),
        EvidenceRecord(control_id="NGX-005", technology="NGINX", status=STATUS_COMPLETED,
                       frameworks=("RBI",), asset_id="A1", ok=True, rows_returned=2),
    ]
    run.audit_trail = [{"at": created_at, "event": "run_created", "detail": "2 controls"}]
    return run


def _artifact(key: str, version: int, asset_id: str = "A1") -> EvidenceArtifact:
    return EvidenceArtifact(
        evidence_key=key, version=version, control_id="NGX-003", technology="NGINX",
        asset_id=asset_id, frameworks=("PCI DSS",), run_id="RUN-1", verdict="PASS",
        control_status="Compliant", evidence_quality=0.9, content_hash="h" * 64,
        checksum="hhhhhhhh", size_bytes=10, source="evidence_run",
        collected_at="2026-01-01T00:00:0%d" % (version % 10), tags=("t",))


def _observation(obs_id: str, created_at: str, severity: str = "High") -> Observation:
    obs = Observation(observation_id=obs_id, technology="NGINX", asset_id="A1",
                      control_id="NGX-005", frameworks=("RBI",), severity=severity,
                      observation="finding", impact="impact", recommendation="fix",
                      status="Draft", created_at=created_at, updated_at=created_at)
    obs.history = [{"at": created_at, "event": "created", "status": "Draft"}]
    return obs


# --------------------------------------------------------------------------- #
# 1) Runs + 2) results
# --------------------------------------------------------------------------- #
def test_save_and_get_run_roundtrip(backend):
    run = _run("RUN-A", "2026-01-01T00:00:00")
    backend.save_run(run)
    got = backend.get_run("RUN-A")
    assert got is not None
    assert got.run_id == "RUN-A" and got.status == STATUS_COMPLETED
    assert got.scope_value == "NGINX"
    assert [r.control_id for r in got.records] == ["NGX-003", "NGX-005"]
    assert got.records[1].frameworks == ("RBI",)
    assert got.audit_trail and got.audit_trail[0]["event"] == "run_created"


def test_get_run_results(backend):
    backend.save_run(_run("RUN-A", "2026-01-01T00:00:00"))
    results = backend.get_run_results("RUN-A")
    assert len(results) == 2
    assert isinstance(results[0], EvidenceRecord)
    assert results[0].rows_returned == 1


def test_get_missing_run_returns_none(backend):
    assert backend.get_run("NOPE") is None
    assert backend.get_run_results("NOPE") == []


def test_list_runs_newest_first(backend):
    backend.save_run(_run("OLD", "2026-01-01T00:00:00"))
    backend.save_run(_run("NEW", "2026-06-01T00:00:00"))
    backend.save_run(_run("MID", "2026-03-01T00:00:00"))
    ids = [r.run_id for r in backend.list_runs()]
    assert ids == ["NEW", "MID", "OLD"]


def test_save_run_upsert_updates(backend):
    backend.save_run(_run("RUN-A", "2026-01-01T00:00:00", status="Running"))
    backend.save_run(_run("RUN-A", "2026-01-01T00:00:00", status=STATUS_COMPLETED))
    assert len(backend.list_runs()) == 1
    assert backend.get_run("RUN-A").status == STATUS_COMPLETED


def test_stored_run_is_isolated_from_caller_mutation(backend):
    run = _run("RUN-A", "2026-01-01T00:00:00")
    backend.save_run(run)
    run.records[0].control_id = "MUTATED"  # mutate after save
    assert backend.get_run("RUN-A").records[0].control_id == "NGX-003"


# --------------------------------------------------------------------------- #
# 3) Validation results
# --------------------------------------------------------------------------- #
def test_validation_results_roundtrip_and_order(backend):
    results = [
        ValidationResult(control_id="NGX-003", technology="NGINX", verdict="PASS",
                         control_status="Compliant", evidence_quality=0.9,
                         rule_id="r1", frameworks=("PCI DSS",)),
        ValidationResult(control_id="NGX-005", technology="NGINX", verdict=VERDICT_FAIL,
                         control_status="Non-Compliant", evidence_quality=0.2,
                         rule_id="assertion.negative", frameworks=("RBI",)),
    ]
    backend.save_validation_results("RUN-A", results)
    got = backend.get_validation_results("RUN-A")
    assert [r.control_id for r in got] == ["NGX-003", "NGX-005"]
    assert got[1].verdict == VERDICT_FAIL and got[1].frameworks == ("RBI",)


def test_validation_results_replace_on_resave(backend):
    backend.save_validation_results("RUN-A", [
        ValidationResult(control_id="X", verdict="PASS")])
    backend.save_validation_results("RUN-A", [
        ValidationResult(control_id="Y", verdict="FAIL"),
        ValidationResult(control_id="Z", verdict="PASS")])
    got = backend.get_validation_results("RUN-A")
    assert [r.control_id for r in got] == ["Y", "Z"]


# --------------------------------------------------------------------------- #
# 4) Observations
# --------------------------------------------------------------------------- #
def test_observation_roundtrip(backend):
    backend.save_observation(_observation("OBS-1", "2026-01-01T00:00:00"))
    got = backend.get_observation("OBS-1")
    assert got is not None and got.severity == "High"
    assert got.control_id == "NGX-005" and got.frameworks == ("RBI",)
    assert got.history and got.history[0]["event"] == "created"


def test_list_observations(backend):
    backend.save_observation(_observation("OBS-1", "2026-01-01T00:00:00"))
    backend.save_observation(_observation("OBS-2", "2026-02-01T00:00:00", severity="Low"))
    assert len(backend.list_observations()) == 2


def test_observation_upsert(backend):
    backend.save_observation(_observation("OBS-1", "2026-01-01T00:00:00", severity="Low"))
    backend.save_observation(_observation("OBS-1", "2026-01-01T00:00:00", severity="Critical"))
    assert len(backend.list_observations()) == 1
    assert backend.get_observation("OBS-1").severity == "Critical"


# --------------------------------------------------------------------------- #
# 5) Evidence versions
# --------------------------------------------------------------------------- #
def test_evidence_versioning_and_latest(backend):
    backend.append_evidence_version(_artifact("K1", 1))
    backend.append_evidence_version(_artifact("K1", 2))
    backend.append_evidence_version(_artifact("K2", 1))
    versions = backend.get_evidence_versions("K1")
    assert [a.version for a in versions] == [1, 2]
    latest = {a.evidence_key: a.version for a in backend.list_evidence_latest()}
    assert latest == {"K1": 2, "K2": 1}


def test_evidence_versions_unknown_key(backend):
    assert backend.get_evidence_versions("NOPE") == []


def test_evidence_artifact_fields_roundtrip(backend):
    backend.append_evidence_version(_artifact("K1", 1))
    a = backend.get_evidence_versions("K1")[0]
    assert a.content_hash == "h" * 64 and a.evidence_quality == 0.9
    assert a.frameworks == ("PCI DSS",) and a.tags == ("t",)


# --------------------------------------------------------------------------- #
# 6) Evidence packs
# --------------------------------------------------------------------------- #
def test_pack_roundtrip(backend):
    manifest = {"pack_type": "framework", "pack_scope": "RBI", "item_count": 3,
                "pack_hash": "abc", "generated_at": "2026-01-01T00:00:00", "items": []}
    backend.save_pack("PACK-1", manifest)
    got = backend.get_pack("PACK-1")
    assert got["pack_type"] == "framework" and got["item_count"] == 3
    assert backend.get_pack("NOPE") is None


def test_list_packs(backend):
    backend.save_pack("P1", {"generated_at": "2026-01-01T00:00:00", "item_count": 1})
    backend.save_pack("P2", {"generated_at": "2026-02-01T00:00:00", "item_count": 2})
    assert len(backend.list_packs()) == 2


# --------------------------------------------------------------------------- #
# 7) Scheduler history
# --------------------------------------------------------------------------- #
def test_scheduler_history_newest_first(backend):
    for i in range(3):
        backend.record_scheduler_event({"at": f"2026-01-0{i+1}T00:00:00",
                                        "schedule_id": f"S{i}", "action": "enqueue"})
    hist = backend.get_scheduler_history(limit=10)
    assert len(hist) == 3
    assert hist[0]["schedule_id"] == "S2"  # newest first


def test_scheduler_history_limit(backend):
    for i in range(5):
        backend.record_scheduler_event({"at": f"t{i}", "schedule_id": f"S{i}"})
    assert len(backend.get_scheduler_history(limit=2)) == 2


# --------------------------------------------------------------------------- #
# Cross-cutting
# --------------------------------------------------------------------------- #
def test_counts_and_clear(backend):
    backend.save_run(_run("RUN-A", "2026-01-01T00:00:00"))
    backend.save_observation(_observation("OBS-1", "2026-01-01T00:00:00"))
    backend.append_evidence_version(_artifact("K1", 1))
    backend.save_pack("P1", {"generated_at": "x"})
    backend.record_scheduler_event({"at": "x"})
    counts = backend.counts()
    assert counts["runs"] == 1 and counts["observations"] == 1
    assert counts["evidence_keys"] == 1 and counts["packs"] == 1
    assert counts["scheduler_events"] == 1
    backend.clear()
    assert backend.counts()["runs"] == 0
    assert backend.list_evidence_latest() == []


# --------------------------------------------------------------------------- #
# Serialization helpers (direct)
# --------------------------------------------------------------------------- #
def test_run_serialization_roundtrip_helper():
    run = _run("RUN-A", "2026-01-01T00:00:00")
    restored = P.run_from_dict(P.run_to_dict(run))
    assert restored.run_id == run.run_id
    assert [r.control_id for r in restored.records] == ["NGX-003", "NGX-005"]


def test_artifact_serialization_ignores_unknown_keys():
    d = P.artifact_to_dict(_artifact("K1", 1))
    d["some_future_field"] = "ignored"
    restored = P.artifact_from_dict(d)
    assert restored.evidence_key == "K1" and restored.version == 1


def test_observation_serialization_roundtrip_helper():
    obs = _observation("OBS-1", "2026-01-01T00:00:00")
    restored = P.observation_from_dict(P.observation_to_dict(obs))
    assert restored.observation_id == "OBS-1" and restored.history


# --------------------------------------------------------------------------- #
# Pluggable provider
# --------------------------------------------------------------------------- #
def test_provider_default_is_inmemory():
    P.reset_persistence()
    b = P.get_persistence()
    assert isinstance(b, P.InMemoryAuditPersistence)
    P.reset_persistence()


def test_provider_swap_to_sql_backend():
    P.reset_persistence()
    sql = SqlAuditPersistence()
    P.set_persistence(sql)
    assert P.get_persistence() is sql
    P.get_persistence().save_run(_run("RUN-A", "2026-01-01T00:00:00"))
    assert P.get_persistence().get_run("RUN-A") is not None
    P.reset_persistence()
    assert isinstance(P.get_persistence(), P.InMemoryAuditPersistence)
    P.reset_persistence()


# --------------------------------------------------------------------------- #
# SQLite file-backed durability (survives a new backend instance)
# --------------------------------------------------------------------------- #
def test_sqlite_file_backend_persists_across_instances(tmp_path):
    db = str(tmp_path / "audit.db")
    b1 = SqlAuditPersistence(sqlite_file_factory(db))
    b1.initialize()
    b1.clear()
    b1.save_run(_run("RUN-DUR", "2026-01-01T00:00:00"))

    b2 = SqlAuditPersistence(sqlite_file_factory(db))
    b2.initialize()
    got = b2.get_run("RUN-DUR")
    assert got is not None and got.run_id == "RUN-DUR"


# --------------------------------------------------------------------------- #
# Additivity: existing in-memory engines still work independently
# --------------------------------------------------------------------------- #
def test_engine_inmemory_stores_still_work():
    from modules.audit_intelligence.engines import evidence_orchestrator as orch

    orch.reset_runs()
    run = orch.create_run(scope_kind="technology", scope_value="NGINX",
                          control_ids=["NGX-003"], asset_id="A1")
    assert orch.get_run(run.run_id) is not None
    assert len(orch.list_runs()) == 1
    orch.reset_runs()
    assert orch.list_runs() == []
