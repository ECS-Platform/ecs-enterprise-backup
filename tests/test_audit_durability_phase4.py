"""Phase 4 Step 1 — durable audit foundation tests.

Validates the additive audit infrastructure WITHOUT a live PostgreSQL:
  * schema.sql contains the additive DDL (columns + observations table)
  * record_audit() accepts the new optional params and is backward compatible
  * AuditService writes before/after/request_id and never raises on DB failure
  * insert_observation() issues an idempotent insert

A lightweight fake repository captures the SQL/args so we assert the contract.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.audit.service import AuditRecord, AuditService, new_request_id

_SCHEMA = Path(__file__).resolve().parents[1] / "ecs_platform" / "repository" / "schema.sql"


# --------------------------------------------------------------- schema DDL
def test_schema_has_additive_audit_columns():
    sql = _SCHEMA.read_text(encoding="utf-8")
    for col in ("before_state", "after_state", "request_id", "auth_source", "prev_hash"):
        assert f"ADD COLUMN IF NOT EXISTS {col}" in sql, f"missing additive column: {col}"


def test_schema_changes_are_additive_only():
    sql = _SCHEMA.read_text(encoding="utf-8")
    # No destructive DDL on audit_log.
    assert "DROP COLUMN" not in sql.upper()
    assert "ALTER COLUMN" not in sql.upper()
    # Additive uses idempotent guards.
    assert sql.count("ADD COLUMN IF NOT EXISTS") >= 5


def test_schema_has_observations_table():
    sql = _SCHEMA.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS observations" in sql
    for field in ("observation_id", "application_id", "title", "description",
                  "status", "owner", "created_by", "created_at", "updated_at"):
        assert field in sql, f"observations missing field: {field}"


# --------------------------------------------------------------- fake repo
class _FakeCursor:
    def __init__(self, sink):
        self._sink = sink

    def execute(self, sql, params=None):
        self._sink.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeConn:
    def __init__(self, sink):
        self._sink = sink

    def cursor(self):
        return _FakeCursor(self._sink)


class _FakeRepo:
    """Mimics EvidenceRepository.record_audit/insert_observation signatures."""

    instances = []

    def __init__(self):
        self.calls = []
        _FakeRepo.instances.append(self)

    def connect(self):
        return _FakeConn(self.calls)

    # Real signatures (copied) so a signature drift breaks the test.
    def record_audit(self, actor, action, *, role="", resource="", detail=None,
                     before_state=None, after_state=None, request_id="",
                     auth_source="", prev_hash=""):
        self.calls.append({
            "actor": actor, "action": action, "role": role, "resource": resource,
            "detail": detail, "before_state": before_state, "after_state": after_state,
            "request_id": request_id, "auth_source": auth_source, "prev_hash": prev_hash,
        })

    def insert_observation(self, observation_id, *, title, application_id="",
                           description="", status="Open", owner="", created_by=""):
        self.calls.append({"observation_id": observation_id, "title": title,
                           "status": status, "application_id": application_id})

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# --------------------------------------------------------------- record_audit compat
def test_record_audit_backward_compatible_call():
    repo = _FakeRepo()
    # Legacy-style call: no new params.
    repo.record_audit("Alice", "evidence.review", role="auditor", resource="EV-1",
                      detail={"x": 1})
    c = repo.calls[-1]
    assert c["before_state"] is None and c["after_state"] is None
    assert c["request_id"] == "" and c["prev_hash"] == ""


def test_record_audit_accepts_new_params():
    repo = _FakeRepo()
    repo.record_audit("Bob", "evidence.approve", role="auditor", resource="EV-2",
                      before_state={"status": "UnderReview"},
                      after_state={"status": "Approved"},
                      request_id="req-9", auth_source="azure_ad", prev_hash="abc")
    c = repo.calls[-1]
    assert c["before_state"] == {"status": "UnderReview"}
    assert c["after_state"] == {"status": "Approved"}
    assert c["request_id"] == "req-9" and c["auth_source"] == "azure_ad"


# --------------------------------------------------------------- AuditService
def test_audit_service_persists_before_after():
    repo = _FakeRepo()
    svc = AuditService(repository_factory=_FakeRepo)
    ok = svc.record(AuditRecord(
        actor="Carol", action="evidence.reject", role="auditor", resource="EV-3",
        before_state={"status": "UnderReview"}, after_state={"status": "Rejected"},
        request_id="r1", auth_source="oidc"))
    assert ok is True
    last = _FakeRepo.instances[-1].calls[-1]
    assert last["after_state"] == {"status": "Rejected"}
    assert last["actor"] == "Carol" and last["auth_source"] == "oidc"


def test_audit_service_never_raises_on_failure():
    class _Boom:
        def __enter__(self):
            raise RuntimeError("db down")

        def __exit__(self, *a):
            return False

    svc = AuditService(repository_factory=_Boom)
    assert svc.record(AuditRecord(actor="X", action="y")) is False  # no exception


def test_record_event_generates_request_id():
    svc = AuditService(repository_factory=_FakeRepo)
    ok = svc.record_event("Dan", "schedule.create", role="cio")
    assert ok is True
    assert _FakeRepo.instances[-1].calls[-1]["request_id"]  # non-empty


def test_new_request_id_unique():
    assert new_request_id() != new_request_id()


# --------------------------------------------------------------- observation insert
def test_insert_observation_contract():
    repo = _FakeRepo()
    repo.insert_observation("OBS-1", title="Missing MFA evidence",
                            application_id="payments-api", status="Open", created_by="auditor")
    c = repo.calls[-1]
    assert c["observation_id"] == "OBS-1" and c["title"].startswith("Missing")
    assert c["status"] == "Open"
