"""Batch 1 use-case tests — core evidence workflows.

Covers (all offline, real in-memory repositories):
  UC1 Manual evidence upload  + UC3 Bulk evidence upload -> bridged into the
      audit-intelligence evidence repository (real evidence, SHA-256).
  UC2 Automated scheduled evidence pull -> asset scheduler over REST (plan/dry-run).
  UC4 Metadata tagging & naming convention -> naming-preview + validate-metadata.
  UC5 Evidence dashboard & hash integrity -> per-evidence integrity verify.
  UC6 ECS Admin: users, roles, applications -> RBAC-guarded admin API.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.operations.engines import evidence_repository as mvp_repo
from modules.shared.services import admin_service as adm

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    ai_repo.reset_repository()
    mvp_repo.evidence_repository.clear()
    mvp_repo.upload_tracker.clear()
    mvp_repo.evidence_reuse_map.clear()
    adm.reset_users()
    yield
    ai_repo.reset_repository()
    adm.reset_users()


# --------------------------------------------------------------------------- #
# UC1 / UC3 — upload bridge into the audit-intelligence repository
# --------------------------------------------------------------------------- #
def test_manual_upload_bridges_into_audit_repository():
    rec = mvp_repo.register_upload("tde.pdf", b"ssl on", "app_owner",
                                   "PCI DSS", "Net Banking", "DB-001")
    assert rec["audit_repository_synced"] is True
    latest = ai_repo.all_latest()
    assert len(latest) == 1
    art = latest[0]
    assert art.control_id == "DB-001"
    assert art.content_hash and len(art.content_hash) == 64  # sha256 hex
    assert art.source == "manual_upload"
    assert any(t.startswith("app:Net Banking") for t in art.tags)
    # Technology/frameworks enriched from the existing control mapping.
    assert art.technology == "PostgreSQL"
    assert "PCI DSS" in art.frameworks


def test_manual_upload_bridge_enriches_unknown_control_gracefully():
    rec = mvp_repo.register_upload("adhoc.txt", b"x", "app_owner", "PCI DSS", "Mobile Banking", "")
    assert rec["audit_repository_synced"] is True
    art = ai_repo.all_latest()[0]
    assert art.content_hash  # still hashed + stored even without a mapped control


def test_bulk_upload_endpoint_bridges_each_file():
    files = [
        ("files", ("a.pdf", b"aaa", "application/pdf")),
        ("files", ("b.pdf", b"bbb", "application/pdf")),
    ]
    r = client.post("/mvp/upload/bulk", data={"role": "owner", "user": "owner",
                    "framework": "PCI DSS", "application": "Net Banking"},
                    files=files, follow_redirects=False)
    assert r.status_code in (200, 303)
    assert len(mvp_repo.evidence_repository) == 2
    assert len(ai_repo.all_latest()) == 2  # both bridged into the audit repo


# --------------------------------------------------------------------------- #
# UC4 — metadata tagging & naming convention
# --------------------------------------------------------------------------- #
def test_naming_preview_reuses_enforce_naming():
    r = client.get("/api/evidence/naming-preview",
                   params={"filename": "report.pdf", "framework": "PCI DSS",
                           "application": "Net Banking"})
    assert r.status_code == 200
    body = r.json()
    assert body["standardized_filename"].startswith("PCI_DSS_")
    assert body["standardized_filename"].endswith("report.pdf")


def test_naming_preview_requires_filename():
    assert client.get("/api/evidence/naming-preview").status_code == 400


def test_validate_metadata_flags_missing():
    r = client.post("/api/evidence/validate-metadata", json={"filename": "x.pdf"})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert set(body["missing_fields"]) == {"framework", "application"}


def test_validate_metadata_ok_when_complete():
    r = client.post("/api/evidence/validate-metadata",
                    json={"filename": "x.pdf", "framework": "PCI DSS",
                          "application": "Net Banking", "control": "DB-001"})
    assert r.json()["valid"] is True


# --------------------------------------------------------------------------- #
# UC5 — hash integrity verification
# --------------------------------------------------------------------------- #
def test_integrity_endpoint_for_uploaded_evidence():
    rec = mvp_repo.register_upload("log.csv", b"data", "app_owner", "PCI DSS",
                                   "Net Banking", "DB-001")
    r = client.get(f"/api/evidence/{rec['evidence_id']}/integrity")
    assert r.status_code == 200
    body = r.json()
    assert body["algorithm"] == "sha256"
    assert body["integrity_valid"] is True
    assert len(body["stored_hash"]) == 64
    assert body["audit_repository_synced"] is True


def test_integrity_endpoint_unknown_404():
    assert client.get("/api/evidence/NOPE/integrity").status_code == 404


# --------------------------------------------------------------------------- #
# UC2 — scheduled pull over REST
# --------------------------------------------------------------------------- #
def test_scheduler_plan_endpoint():
    r = client.get("/api/audit/scheduler/plan")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and "plan" in body and "summary" in body["plan"]


def test_scheduler_dry_run_endpoint_no_side_effects():
    r = client.post("/api/audit/scheduler/dry-run", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "dry-run"
    assert "plan" in body and "connector_readiness" in body


# --------------------------------------------------------------------------- #
# UC6 — ECS Admin: users, roles, applications
# --------------------------------------------------------------------------- #
def test_admin_roles_are_canonical_readonly():
    r = client.get("/api/admin/roles")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 9
    keys = {x["key"] for x in body["roles"]}
    assert "system_admin" in keys and "application_owner" in keys
    # capabilities reflect real predicates
    sysadmin = next(x for x in body["roles"] if x["key"] == "system_admin")
    assert sysadmin["capabilities"]["can_admin_platform"] is True


def test_admin_applications_list():
    r = client.get("/api/admin/applications")
    assert r.status_code == 200 and r.json()["count"] >= 1


def test_admin_users_list_seeded():
    r = client.get("/api/admin/users")
    assert r.status_code == 200
    assert r.json()["count"] >= 1
    assert "summary" in r.json()


def test_admin_create_user_requires_admin_role():
    # Non-admin -> 403
    denied = client.post("/api/admin/users", params={"role": "auditor"},
                         json={"email": "x@ecs.local", "assign_role": "auditor"})
    assert denied.status_code == 403
    # Admin -> 200
    ok = client.post("/api/admin/users", params={"role": "system_admin"},
                     json={"email": "new@ecs.local", "display_name": "New",
                           "assign_role": "application_owner"})
    assert ok.status_code == 200
    assert ok.json()["user"]["role"] == "application_owner"


def test_admin_create_user_validation():
    bad_email = client.post("/api/admin/users", params={"role": "system_admin"},
                            json={"email": "not-an-email", "assign_role": "auditor"})
    assert bad_email.status_code == 400
    bad_role = client.post("/api/admin/users", params={"role": "system_admin"},
                           json={"email": "ok@ecs.local", "assign_role": "not_a_role"})
    assert bad_role.status_code == 400


def test_admin_update_role_and_active():
    created = client.post("/api/admin/users", params={"role": "system_admin"},
                          json={"email": "u1@ecs.local", "assign_role": "auditor"}).json()
    uid = created["user"]["user_id"]
    upd = client.post(f"/api/admin/users/{uid}/role", params={"role": "system_admin"},
                      json={"assign_role": "compliance_officer"})
    assert upd.status_code == 200 and upd.json()["user"]["role"] == "compliance_officer"
    deact = client.post(f"/api/admin/users/{uid}/active", params={"role": "system_admin"},
                        json={"active": False})
    assert deact.status_code == 200 and deact.json()["user"]["active"] is False
    # unknown user
    assert client.post("/api/admin/users/NOPE/role", params={"role": "system_admin"},
                       json={"assign_role": "auditor"}).status_code == 404


def test_admin_ui_page_renders():
    r = client.get("/admin/users-roles", params={"role": "system_admin"})
    assert r.status_code == 200
    assert "ECS Admin" in r.text
    assert 'id="users-body"' in r.text


def test_admin_ui_alias_and_nonadmin_notice():
    assert client.get("/mvp/admin/users-roles", params={"role": "system_admin"}).status_code == 200
    # A non-admin still sees the page but with a restriction notice.
    r = client.get("/admin/users-roles", params={"role": "auditor"})
    assert r.status_code == 200 and "administrator role" in r.text.lower()
