"""In-memory AI SDLC workflow state — status transitions, evidence, audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import (
    STAGE_LABELS,
    build_evidence_collection,
    build_stage_worklist,
    enrich_row_control,
)
from modules.shared.utils.demo_data_standards import pick, seed

_STORE: dict[str, Any] = {
    "activities": {},
    "evidence": {},
    "audit": [],
    "initialized": False,
}

_VALID_TRANSITIONS = {
    "upload": {"from": {"Pending", "Awaiting Upload", "Needs Rework", "Rejected"}, "to": "In Review"},
    "approve": {"from": {"Pending", "In Review", "Needs Rework"}, "to": "Approved"},
    "reject": {"from": {"Pending", "In Review", "Needs Rework"}, "to": "Rejected"},
    "rework": {"from": {"Pending", "In Review"}, "to": "Needs Rework"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _audit_entry(item_id: str, item_type: str, action: str, actor: str, detail: str) -> dict[str, str]:
    entry = {
        "timestamp": _now(),
        "item_id": item_id,
        "item_type": item_type,
        "action": action,
        "actor": actor,
        "detail": detail,
    }
    _STORE["audit"].append(entry)
    return entry


def reset_store_for_tests() -> None:
    """Clear in-memory workflow state (test isolation only)."""
    _STORE["activities"] = {}
    _STORE["evidence"] = {}
    _STORE["audit"] = []
    _STORE["initialized"] = False


def _ensure_init() -> None:
    if _STORE["initialized"]:
        return
    for stage_key in ("requirement", "design", "development", "testing", "go-live"):
        wl = build_stage_worklist(stage_key)
        for row in wl["rows"]:
            rid = row["activity_id"]
            _STORE["activities"][rid] = {**row, "item_type": "activity", "comments": [], "files": []}
    ev = build_evidence_collection()
    for row in ev["rows"]:
        eid = row["evidence_id"]
        doc = enrich_row_control(row, stage=row.get("stage", "Evidence Collection"))
        _STORE["evidence"][eid] = {
            **doc,
            "item_type": "evidence",
            "document_name": f"{doc.get('artifact_type', 'Evidence')}_{eid}.pdf",
            "uploaded_by": pick(seed("upby", eid), ["R. Mehta", "A. Sharma", "App Owner"]),
            "upload_date": "2026-05-22",
            "control_description": f"Control {doc['control_id']} — {doc['control_name']} for {doc['framework']} in {doc['domain']}.",
            "comments": [],
            "files": [{"name": f"{doc.get('artifact_type', 'Evidence')}_{eid}.pdf", "uploaded_at": "2026-05-22"}],
            "approval_history": [],
        }
    _STORE["initialized"] = True


def get_activity(activity_id: str) -> dict[str, Any] | None:
    _ensure_init()
    return _STORE["activities"].get(activity_id)


def get_evidence(evidence_id: str) -> dict[str, Any] | None:
    _ensure_init()
    return _STORE["evidence"].get(evidence_id)


def get_item(item_id: str, item_type: str = "") -> dict[str, Any] | None:
    _ensure_init()
    if item_type == "evidence" or item_id.startswith("EV-"):
        return _STORE["evidence"].get(item_id)
    if item_type == "activity" or item_id.startswith("ACT-"):
        return _STORE["activities"].get(item_id)
    return _STORE["evidence"].get(item_id) or _STORE["activities"].get(item_id)


def list_activities(stage_key: str) -> list[dict[str, Any]]:
    _ensure_init()
    return [r for r in _STORE["activities"].values() if _activity_stage_key(r) == stage_key]


def list_evidence() -> list[dict[str, Any]]:
    _ensure_init()
    return list(_STORE["evidence"].values())


def _activity_stage_key(row: dict) -> str:
    label = row.get("stage", "")
    for k, v in STAGE_LABELS.items():
        if v == label:
            return k
    return "requirement"


def item_audit_trail(item_id: str) -> list[dict[str, str]]:
    _ensure_init()
    return [e for e in _STORE["audit"] if e["item_id"] == item_id]


def build_review_payload(item_id: str, item_type: str = "") -> dict[str, Any] | None:
    item = get_item(item_id, item_type)
    if not item:
        return None
    audit = item_audit_trail(item_id)
    return {
        **item,
        "audit_trail": audit,
        "approval_history": item.get("approval_history", []),
        "metadata": {
            "application": item.get("application"),
            "framework": item.get("framework"),
            "domain": item.get("domain"),
            "control_id": item.get("control_id"),
            "control_name": item.get("control_name"),
            "stage": item.get("stage"),
            "artifact_type": item.get("artifact_type") or item.get("artifact_required"),
            "status": item.get("status"),
            "owner": item.get("owner"),
        },
    }


def build_evidence_viewer(evidence_id: str) -> dict[str, Any] | None:
    item = get_evidence(evidence_id)
    if not item:
        return None
    return {
        **item,
        "audit_trail": item_audit_trail(evidence_id),
        "approval_history": item.get("approval_history", []),
    }


def perform_upload(
    item_id: str,
    *,
    actor: str,
    file_name: str = "",
    comments: str = "",
    application: str = "",
    framework: str = "",
    domain: str = "",
    control_id: str = "",
    stage: str = "",
    artifact_type: str = "",
    item_type: str = "",
) -> dict[str, Any]:
    _ensure_init()
    item = get_item(item_id, item_type)
    if not item:
        return {"ok": False, "error": "Item not found"}
    bucket = _STORE["evidence"] if item.get("item_type") == "evidence" else _STORE["activities"]
    current = bucket[item_id]
    if application:
        current["application"] = application
    if framework:
        current["framework"] = framework
    if domain:
        current["domain"] = domain
    if control_id:
        current["control_id"] = control_id
        current["control"] = control_id
    if stage:
        current["stage"] = stage
    if artifact_type:
        current["artifact_type"] = artifact_type
        current["artifact_required"] = artifact_type
    fname = file_name or f"upload_{item_id}.pdf"
    current["files"].append({"name": fname, "uploaded_at": _now(), "uploaded_by": actor})
    if comments:
        current["comments"].append({"author": actor, "text": comments, "at": _now()})
    prev = current["status"]
    current["status"] = _VALID_TRANSITIONS["upload"]["to"]
    if item.get("item_type") == "evidence":
        current["document_name"] = fname
        current["uploaded_by"] = actor
        current["upload_date"] = _now()[:10]
    _audit_entry(item_id, current["item_type"], "Upload", actor, f"Uploaded {fname}. Status {prev} → {current['status']}. {comments}".strip())
    return {"ok": True, "item": current, "audit_trail": item_audit_trail(item_id)}


def perform_status_action(
    item_id: str,
    action: str,
    *,
    actor: str,
    comments: str = "",
    item_type: str = "",
) -> dict[str, Any]:
    _ensure_init()
    action = action.lower().replace(" ", "_")
    if action == "request_rework":
        action = "rework"
    if action not in _VALID_TRANSITIONS:
        return {"ok": False, "error": f"Unknown action: {action}"}
    item = get_item(item_id, item_type)
    if not item:
        return {"ok": False, "error": "Item not found"}
    bucket = _STORE["evidence"] if item.get("item_type") == "evidence" else _STORE["activities"]
    current = bucket[item_id]
    if action == "reject" and not comments.strip():
        return {"ok": False, "error": "Rejection comments are mandatory"}
    rule = _VALID_TRANSITIONS[action]
    if current["status"] not in rule["from"] and action != "approve":
        pass  # allow demo flexibility for approve from more states
    prev = current["status"]
    new_status = rule["to"]
    current["status"] = new_status
    label = action.replace("_", " ").title()
    if action == "rework":
        label = "Request Rework"
        current["owner"] = current.get("owner") or "App Owner"
    hist = {
        "timestamp": _now(),
        "action": label,
        "actor": actor,
        "from_status": prev,
        "to_status": new_status,
        "comments": comments,
    }
    current.setdefault("approval_history", []).append(hist)
    if comments:
        current["comments"].append({"author": actor, "text": comments, "at": _now()})
    detail = f"{label}: {prev} → {new_status}."
    if comments:
        detail += f" Comments: {comments}"
    if action == "rework":
        detail += f" Work item assigned to {current.get('owner', 'App Owner')}."
    _audit_entry(item_id, current["item_type"], label, actor, detail)
    return {"ok": True, "item": current, "audit_trail": item_audit_trail(item_id)}
