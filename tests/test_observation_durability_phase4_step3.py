"""Phase 4 Step 3 — durable observation persistence tests.

Validates the write-through observation store without Azure AD, LLM, Ollama, or a
vector DB, and without a live PostgreSQL: a FakeRepo implements the observation
CRUD contract in memory and is injected via store.repository_factory.

Covered:
  1. Observation creation (persist_observation -> new row, observation.create audit)
  2. Observation update (persist_observation again -> observation.update audit)
  3. Observation close (persist_close -> status/closed fields)
  4. Observation reopen (persist_reopen -> clears closure)
  5. Observation retrieval (get/list/search)
  6. Restart durability (clear in-memory state, hydrate from DB)
  7. Audit integration (records emitted via AuditService)
  8. Flag OFF = no-op (existing behavior unchanged)
  9. Idempotent migration (memory -> durable, safe re-run)
"""

from __future__ import annotations

import os

import pytest

import app.observations.store as store
import app.audit.service as audit_svc


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeRepo:
    """In-memory stand-in for EvidenceRepository's observation surface."""

    _DB: dict[str, dict] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_observation(self, oid):
        row = self._DB.get(oid)
        return dict(row) if row else None

    def upsert_observation(self, observation_id, *, title="", application_id="",
                           framework="", control_id="", description="", severity="",
                           status="Open", owner="", due_date="", remediation_plan="",
                           comments=None, created_by="", updated_by=""):
        row = self._DB.get(observation_id)
        if row is None:
            self._DB[observation_id] = {
                "observation_id": observation_id, "title": title or observation_id,
                "application_id": application_id, "framework": framework,
                "control_id": control_id, "description": description, "severity": severity,
                "status": status, "owner": owner, "due_date": due_date,
                "remediation_plan": remediation_plan, "comments": comments or [],
                "created_by": created_by, "updated_by": updated_by or created_by,
                "closed_by": None, "closed_at": None,
            }
        else:
            for k, v in {"application_id": application_id, "framework": framework,
                         "control_id": control_id, "title": title,
                         "description": description, "severity": severity,
                         "owner": owner, "due_date": due_date,
                         "remediation_plan": remediation_plan}.items():
                if v:
                    row[k] = v
            row["status"] = status
            if updated_by:
                row["updated_by"] = updated_by

    def update_observation(self, observation_id, **fields):
        row = self._DB.get(observation_id)
        if row:
            row.update(fields)

    def close_observation(self, observation_id, *, closed_by="", status="Closed"):
        row = self._DB.get(observation_id)
        if row:
            row.update({"status": status, "closed_by": closed_by, "closed_at": "2026-01-01"})

    def reopen_observation(self, observation_id, *, reopened_by="", status="Open"):
        row = self._DB.get(observation_id)
        if row:
            row.update({"status": status, "closed_by": None, "closed_at": None})

    def list_observations(self, *, status=None, application_id=None, framework=None, limit=1000):
        rows = list(self._DB.values())
        if status:
            rows = [r for r in rows if r["status"] == status]
        return [dict(r) for r in rows][:limit]

    def search_observations(self, term, *, limit=200):
        t = term.lower()
        return [dict(r) for r in self._DB.values()
                if t in (r["observation_id"] + r.get("title", "")).lower()][:limit]


class CaptureAudit:
    def __init__(self):
        self.records = []

    def record(self, rec):
        self.records.append(rec)
        return True


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def fresh_db():
    FakeRepo._DB = {}
    yield
    FakeRepo._DB = {}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("OBSERVATIONS_DURABLE_ENABLED", "true")
    monkeypatch.setattr(store, "repository_factory", lambda: FakeRepo())
    cap = CaptureAudit()
    monkeypatch.setattr(audit_svc, "default_audit_service", cap)
    return cap


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("OBSERVATIONS_DURABLE_ENABLED", raising=False)
    assert store.durable_observations_enabled() is False


def test_flag_off_is_noop(monkeypatch):
    monkeypatch.delenv("OBSERVATIONS_DURABLE_ENABLED", raising=False)
    monkeypatch.setattr(store, "repository_factory", lambda: FakeRepo())
    assert store.persist_observation("OBS-1", title="x") is False
    assert FakeRepo._DB == {}


def test_create_then_update_emits_audit(enabled):
    ok = store.persist_observation("OBS-PCI-1000", title="MFA gap",
                                   application_id="Net Banking", framework="PCI DSS",
                                   control_id="8.3", severity="High", actor="alice")
    assert ok is True
    assert FakeRepo._DB["OBS-PCI-1000"]["status"] == "Open"
    assert enabled.records[-1].action == "observation.create"

    ok2 = store.persist_observation("OBS-PCI-1000", status="Submitted for Review", actor="bob")
    assert ok2 is True
    assert FakeRepo._DB["OBS-PCI-1000"]["status"] == "Submitted for Review"
    assert enabled.records[-1].action == "observation.update"


def test_close_and_reopen(enabled):
    store.persist_observation("OBS-2", title="t", actor="a")
    assert store.persist_close("OBS-2", closed_by="auditor") is True
    assert FakeRepo._DB["OBS-2"]["status"] == "Closed"
    assert FakeRepo._DB["OBS-2"]["closed_by"] == "auditor"

    assert store.persist_reopen("OBS-2", reopened_by="cio") is True
    assert FakeRepo._DB["OBS-2"]["status"] == "Open"
    assert FakeRepo._DB["OBS-2"]["closed_by"] is None


def test_close_creates_row_if_missing(enabled):
    # Write-through: closing an unknown id still produces a durable closed row.
    assert store.persist_close("OBS-NEW", closed_by="auditor") is True
    assert FakeRepo._DB["OBS-NEW"]["status"] == "Closed"


def test_retrieval(enabled):
    store.persist_observation("OBS-A", title="Alpha gap", actor="a")
    store.persist_observation("OBS-B", title="Beta gap", actor="a")
    store.persist_close("OBS-B", closed_by="a")
    with store.repository_factory() as repo:
        assert repo.get_observation("OBS-A")["title"] == "Alpha gap"
        assert len(repo.list_observations()) == 2
        assert len(repo.list_observations(status="Closed")) == 1
        assert repo.search_observations("alpha")[0]["observation_id"] == "OBS-A"


def test_restart_durability(enabled):
    """Persist, wipe in-memory state (simulate restart), hydrate back."""
    from modules.shared.services import ecs_state

    store.persist_observation("OBS-OPEN", title="Open gap", framework="PCI DSS",
                              control_id="1.1", status="Pending Upload", actor="a")
    store.persist_observation("OBS-DONE", title="Done gap", actor="a")
    store.persist_close("OBS-DONE", closed_by="auditor")

    # Simulate a process restart: in-memory observation state is empty.
    ecs_state.missing_evidence_registry.pop("OBS-OPEN", None)
    ecs_state.closed_observations.pop("OBS-DONE", None)

    hydrated = store.hydrate_into_memory()
    assert hydrated >= 2
    assert "OBS-OPEN" in ecs_state.missing_evidence_registry
    assert ecs_state.missing_evidence_registry["OBS-OPEN"]["framework"] == "PCI DSS"
    assert "OBS-DONE" in ecs_state.closed_observations
    assert ecs_state.closed_observations["OBS-DONE"]["closed_by"] == "auditor"


def test_hydrate_does_not_overwrite_memory(enabled):
    from modules.shared.services import ecs_state

    store.persist_observation("OBS-KEEP", title="db title", actor="a")
    ecs_state.missing_evidence_registry["OBS-KEEP"] = {"observation_id": "OBS-KEEP",
                                                       "control": "memory title"}
    store.hydrate_into_memory()
    # Memory wins for the current process.
    assert ecs_state.missing_evidence_registry["OBS-KEEP"]["control"] == "memory title"


def test_migration_idempotent(enabled):
    from modules.shared.services import ecs_state

    ecs_state.missing_evidence_registry["OBS-MIG"] = {
        "observation_id": "OBS-MIG", "control": "Mig gap", "framework": "ISO 27001",
        "control_id": "A.5", "status": "Pending Upload", "application": "Core",
    }
    ecs_state.closed_observations["OBS-MIGCLOSED"] = {
        "observation_id": "OBS-MIGCLOSED", "control": "Closed gap", "closed_by": "auditor",
    }
    r1 = store.migrate_memory_to_durable()
    assert r1["registry"] >= 1 and r1["closed"] >= 1
    # Re-run is safe (upserts); row count stays stable.
    before = len(FakeRepo._DB)
    store.migrate_memory_to_durable()
    assert len(FakeRepo._DB) == before
    assert FakeRepo._DB["OBS-MIGCLOSED"]["status"] == "Closed"


def test_never_raises_on_backend_failure(monkeypatch):
    monkeypatch.setenv("OBSERVATIONS_DURABLE_ENABLED", "true")

    class Boom:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_observation(self, oid):
            raise RuntimeError("db down")

    monkeypatch.setattr(store, "repository_factory", lambda: Boom())
    assert store.persist_observation("OBS-X", title="x") is False
    assert store.persist_close("OBS-X") is False
    assert store.persist_reopen("OBS-X") is False
    assert store.hydrate_into_memory() == 0
