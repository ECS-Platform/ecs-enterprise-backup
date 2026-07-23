"""Evidence upload, submit, revalidate, repository, and audit package API helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app import ecs_state
from modules.governance.engines.audit_prep_data import build_audit_package_preview, build_export_bundle_preview
from modules.shared.services.audit_trail import log_event
from modules.operations.engines.evidence_repository import evidence_repository, register_upload

_package_store: dict[str, Any] = {}
_export_store: dict[str, Any] = {}


def _framework_evidence_id(framework: str) -> str:
    prefix = framework.replace(" ", "").replace("Baselining", "")[:3].upper()
    if framework == "PCI DSS":
        prefix = "PCI"
    seq = len([e for e in evidence_repository if framework in (e.get("framework_tags") or [])]) + 1
    year = datetime.now(timezone.utc).year
    return f"{prefix}-EV-{year}-{seq:04d}"


def upload_evidence(
    *,
    filename: str,
    content: bytes,
    framework: str,
    application: str,
    control: str,
    uploaded_by: str,
    comments: str = "",
    evidence_type: str = "Document",
    audit_cycle: str = "Q2 2026",
    owner: str = "",
) -> dict[str, Any]:
    record = register_upload(
        filename or "evidence_upload.pdf",
        content or b"mock-evidence-content",
        uploaded_by,
        framework,
        application,
        control,
    )
    ev_id = _framework_evidence_id(framework)
    record["display_evidence_id"] = ev_id
    record["evidence_type"] = evidence_type
    record["audit_cycle"] = audit_cycle
    record["comments"] = comments
    record["owner"] = owner or uploaded_by
    record["validation_status"] = "Pending Review"
    record["lifecycle"] = "Pending Review"
    record["status"] = "Pending Review"

    ckey = f"{framework}::{control}" if control else ""
    if ckey and framework:
        ecs_state.submitted_controls[ckey] = {
            "submitted_by": uploaded_by,
            "evidence_id": ev_id,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    log_event(
        "Evidence Uploaded",
        uploaded_by,
        framework,
        control,
        f"{ev_id} — {comments[:80] if comments else 'upload complete'}",
        record.get("evidence_id", ev_id),
    )

    return {
        "status": "success",
        "evidence_id": ev_id,
        "framework": framework,
        "application": application,
        "control": control,
        "uploaded_by": uploaded_by,
        "owner": owner or uploaded_by,
        "validation_status": "Pending Review",
        "evidence_type": evidence_type,
        "audit_cycle": audit_cycle,
        "repository_id": record.get("evidence_id"),
        "message": f"Evidence {ev_id} uploaded successfully for {application}.",
    }


def revalidate_evidence(
    *,
    framework: str,
    control: str,
    application: str,
    user: str,
) -> dict[str, Any]:
    ckey = f"{framework}::{control}" if control else ""
    log_event("Control Revalidation", user, framework, control, f"Revalidation triggered for {application}")
    return {
        "status": "success",
        "framework": framework,
        "application": application,
        "control": control,
        "validation_status": "Pending Review",
        "message": f"Revalidation queued for {control} on {application}.",
    }


def submit_evidence(
    *,
    framework: str,
    control: str,
    application: str,
    evidence_id: str,
    user: str,
) -> dict[str, Any]:
    ckey = f"{framework}::{control}" if control else ""
    if ckey:
        ecs_state.submitted_controls[ckey] = {
            "submitted_by": user,
            "evidence_id": evidence_id,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    log_event("Evidence Submitted for Review", user, framework, control, evidence_id)
    return {
        "status": "success",
        "evidence_id": evidence_id,
        "framework": framework,
        "application": application,
        "control": control,
        "workflow_status": "Pending Auditor Validation",
        "message": "Evidence submitted for auditor review.",
    }


def list_evidence_repository(limit: int = 100) -> dict[str, Any]:
    from modules.shared.services.evidence_authoritative_reader import (
        collect_authoritative_evidence_rows,
    )

    items = []
    for rec in reversed(collect_authoritative_evidence_rows()[-limit:]):
        items.append({
            "evidence_id": rec.get("display_evidence_id") or rec.get("evidence_id"),
            "repository_id": rec.get("evidence_id"),
            "framework": rec.get("framework"),
            "application": rec.get("application"),
            "control": rec.get("control_id") or rec.get("control") or "—",
            "filename": rec.get("filename"),
            "uploaded_by": rec.get("uploaded_by"),
            "validation_status": rec.get("validation_status") or rec.get("workflow_status") or rec.get("status", "Uploaded"),
            "lifecycle": rec.get("lifecycle", "Draft"),
            "uploaded_at": rec.get("uploaded_at") or rec.get("collected_at"),
            "sha256": rec.get("sha256"),
            "version": rec.get("version"),
            "custody_mode": rec.get("custody_mode"),
            "object_reference": rec.get("object_reference") or rec.get("object_uri"),
            "audit_status": rec.get("audit_status"),
            "review_status": rec.get("review_status"),
            "approval_status": rec.get("approval_status"),
        })
    return {"status": "success", "count": len(items), "items": items}


def get_evidence_by_id(evidence_id: str) -> dict[str, Any]:
    from modules.shared.services.evidence_authoritative_reader import (
        get_authoritative_evidence,
    )

    rec = get_authoritative_evidence(evidence_id)
    if rec is None:
        return {"status": "error", "message": f"Evidence {evidence_id} not found."}
    return {
        "status": "success",
        "evidence_id": rec.get("display_evidence_id") or rec.get("evidence_id"),
        "repository_id": rec.get("evidence_id"),
        "framework": rec.get("framework"),
        "application": rec.get("application"),
        "control": rec.get("control_id") or rec.get("control") or "—",
        "filename": rec.get("filename"),
        "uploaded_by": rec.get("uploaded_by"),
        "validation_status": rec.get("validation_status") or rec.get("workflow_status") or rec.get("status"),
        "lifecycle": rec.get("lifecycle"),
        "comments": rec.get("comments", ""),
        "evidence_type": rec.get("evidence_type", "Document"),
        "audit_cycle": rec.get("audit_cycle", "Q2 2026"),
        "sha256": rec.get("sha256"),
        "version": rec.get("version"),
        "custody_mode": rec.get("custody_mode"),
        "object_reference": rec.get("object_reference") or rec.get("object_uri"),
        "collection_source": rec.get("collection_source"),
        "collected_at": rec.get("collected_at"),
        "audit_status": rec.get("audit_status"),
        "review_status": rec.get("review_status"),
        "approval_status": rec.get("approval_status"),
        "metadata": rec.get("metadata") or {},
    }


def generate_audit_package(user: str = "User", role: str = "cio") -> dict[str, Any]:
    preview = build_audit_package_preview()
    pkg_id = hashlib.md5(preview["package_name"].encode()).hexdigest()[:12]
    result = {
        "status": "success",
        "package_id": pkg_id,
        **preview,
        "generated_by": user,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _package_store[pkg_id] = result
    log_event("Audit Package Generated", user, "", preview["package_name"], preview.get("auditor_notes", ""), role=role)
    return result


def export_audit_package(package_id: str = "") -> dict[str, Any]:
    preview = build_export_bundle_preview()
    export_id = package_id or hashlib.md5(preview["bundle_name"].encode()).hexdigest()[:12]
    result = {
        "status": "success",
        "export_id": export_id,
        **preview,
        "download_ready": True,
        "format": "ZIP",
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    _export_store[export_id] = result
    return result
