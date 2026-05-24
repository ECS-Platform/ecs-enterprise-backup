"""Enterprise workflow queues for App Owner and Auditor dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import ecs_state
from app.framework_catalog import FRAMEWORK_CATALOG, get_framework_controls

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

LIFECYCLE_STATES = {
    "draft": "Draft",
    "submitted": "Submitted",
    "pending_auditor_review": "Pending Auditor Review",
    "rejected": "Rejected",
    "resubmission_required": "Resubmission Required",
    "escalated": "Escalated",
    "approved": "Approved",
    "closed": "Closed",
    "clarification": "Clarification Required",
    "cancelled": "Cancelled",
}

FRAMEWORK_DESCRIPTIONS = {
    "PCI DSS": (
        "Payment Card Industry Data Security Standard — cardholder data protection, "
        "encryption, access control, logging, and vulnerability management."
    ),
    "DPSC": (
        "Digital Payment Security Controls — API security, tokenization, fraud monitoring, "
        "and UPI/card switch hardening for retail payments."
    ),
    "OS Baselining": (
        "Operating system hardening baseline — CIS-aligned build standards, patch cadence, "
        "and production server configuration compliance."
    ),
    "DB Baselining": (
        "Database security baseline — Oracle/SQL hardening, privileged access, "
        "audit logging, and encryption-at-rest for CBS and treasury systems."
    ),
    "Nginx Baselining": (
        "Web tier and reverse-proxy baseline — TLS configuration, WAF rules, "
        "header security, and DMZ edge hardening."
    ),
    "CSITE": (
        "Cyber Security IT Evaluation — enterprise security governance, SOC integration, "
        "incident response readiness, and third-party risk."
    ),
    "AppSec": (
        "Application Security — SAST/DAST, dependency and secrets scanning, "
        "API security, and secure code review evidence for digital channels."
    ),
    "VAPT": (
        "Vulnerability Assessment & Penetration Testing — internal/external VA, "
        "penetration test remediation, and closure validation evidence."
    ),
    "ITPP": (
        "Information Technology Policies & Procedures — operational governance for "
        "disaster recovery, backup, change, incident, problem, capacity, and availability management."
    ),
}


def _parse_ts(ts: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts[:19] if "UTC" in ts else ts, fmt.replace(" UTC", ""))
        except ValueError:
            continue
    return None


def aging_days_from(ts: str, fallback: int = 12) -> int:
    parsed = _parse_ts(ts)
    if not parsed:
        return fallback
    delta = datetime.now(timezone.utc).replace(tzinfo=None) - parsed
    return max(0, delta.days)


def _due_date_from_expiry(expiry: str) -> str:
    return expiry if expiry else "2026-06-30"


def _risk_rating(priority: str, evidence_status: str, escalated: bool) -> str:
    if escalated or priority == "Critical":
        return "Critical"
    if priority == "High" or evidence_status in ("Expired", "Due for Refresh"):
        return "High"
    if priority == "Medium":
        return "Medium"
    return "Low"


def _priority_for(
    workflow_status: str,
    action_type: str,
    evidence_status: str,
    aging_days: int,
    escalated: bool,
) -> str:
    if escalated or workflow_status == "rejected":
        return "Critical" if aging_days > 14 else "High"
    if evidence_status == "Expired":
        return "Critical"
    if evidence_status == "Due for Refresh":
        return "High"
    if action_type == "Auditor clarification pending":
        return "High"
    if aging_days > 30:
        return "High"
    if aging_days > 14:
        return "Medium"
    return "Low"


def _workflow_label(key: str) -> tuple[str, str]:
    if key in ecs_state.approved_controls:
        return "approved", "Observation Closed — Auditor Approved"
    if key in ecs_state.rejected_controls:
        if ecs_state.rejected_controls[key].get("internal"):
            return "rejected", "Rejected Internally — Owner Review"
        return "rejected", "Rejected By Auditor"
    if key in ecs_state.submitted_controls:
        return "submitted", "Pending Auditor Review"
    if key in ecs_state.clarification_controls:
        return "clarification", "Auditor Clarification Pending"
    if key in ecs_state.cancelled_drafts:
        return "cancelled", "Draft Cancelled"
    if key in ecs_state.owner_drafts:
        return "draft", "Draft Saved"
    return "pending", "Draft — Pending Owner Review"


def _action_type(key: str, evidence_status: str) -> str:
    status, _ = _workflow_label(key)
    if status == "rejected":
        return "Rejected evidence requires resubmission"
    if status == "submitted":
        return "Observation closure pending"
    if status == "clarification":
        return "Auditor clarification pending"
    if evidence_status == "Expired":
        return "Expiring evidence"
    if evidence_status == "Due for Refresh":
        return "Expiring evidence"
    if status == "pending":
        return "Evidence upload pending"
    return "Missing evidence"


def _auditor_comment(key: str, primary_ev: dict) -> str:
    if key in ecs_state.rejected_controls:
        return ecs_state.rejected_controls[key]["reason"]
    if key in ecs_state.clarification_controls:
        return ecs_state.clarification_controls[key]["message"]
    if key in ecs_state.submitted_controls:
        return primary_ev.get("comments", "Awaiting auditor review.")
    return primary_ev.get("comments", "—")


def _catalog_ctrl(framework: str, control: str) -> dict | None:
    return next((c for c in get_framework_controls(framework) if c["control"] == control), None)


def _queue_item(
    framework: str,
    ctrl: dict,
    ev: dict,
    *,
    include_closed: bool = False,
) -> dict | None:
    key = ecs_state.control_key(framework, ctrl["control"])
    wf_status, wf_label = _workflow_label(key)

    if wf_status == "cancelled":
        return None
    if wf_status == "approved" and not include_closed:
        return None

    upload_ts = ev.get("upload_timestamp", "2026-04-01 09:00:00 UTC")
    meta = ecs_state.submitted_meta.get(key, {})
    submitted_ts = meta.get("submitted_at", upload_ts if wf_status == "submitted" else "—")
    aging = aging_days_from(submitted_ts if submitted_ts != "—" else upload_ts)
    evidence_status = ev.get("evidence_status", "Current")
    action_type = _action_type(key, evidence_status)
    escalated = key in ecs_state.escalated_controls
    priority = _priority_for(wf_status, action_type, evidence_status, aging, escalated)

    expiry_risk = "None"
    if evidence_status == "Expired":
        expiry_risk = "Expired"
    elif evidence_status == "Due for Refresh":
        expiry_risk = "Due within 30 days"

    evidence_health = "Valid"
    if evidence_status == "Expired":
        evidence_health = "Expired — refresh required"
    elif evidence_status == "Due for Refresh":
        evidence_health = "Due for refresh"
    elif wf_status == "rejected":
        evidence_health = "Rejected artefact"

    return {
        "key": key,
        "framework": framework,
        "application": ev.get("application_name", "Enterprise Application"),
        "control": ctrl["control"],
        "control_id": ctrl.get("control_id", ""),
        "evidence_name": ev.get("evidence_name", ""),
        "evidence_id": ev.get("evidence_id", ""),
        "mock_file": ev.get("mock_file", ""),
        "evidence_status": evidence_status,
        "auditor_comments": _auditor_comment(key, ev),
        "due_date": _due_date_from_expiry(ev.get("expiry_date", "")),
        "aging_days": aging,
        "priority": priority,
        "submitted_timestamp": submitted_ts,
        "expiry_date": ev.get("expiry_date", "—"),
        "workflow_status": wf_label,
        "workflow_code": wf_status,
        "action_type": action_type,
        "app_owner": ev.get("uploaded_by", "R. Mehta (App Owner)"),
        "risk_rating": _risk_rating(priority, evidence_status, escalated),
        "evidence_health": evidence_health,
        "expiry_risk": expiry_risk,
        "escalated": escalated,
        "server_name": ev.get("server_name", ""),
        "environment": ev.get("environment", ""),
        "region": ev.get("region", ""),
        "owner_comments": ecs_state.owner_comments.get(key, []),
    }


def get_lifecycle_state(key: str) -> str:
    if key in ecs_state.approved_controls:
        return LIFECYCLE_STATES["closed"]
    if key in ecs_state.escalated_controls and key in ecs_state.submitted_controls:
        return LIFECYCLE_STATES["escalated"]
    if key in ecs_state.rejected_controls:
        return LIFECYCLE_STATES["resubmission_required"]
    if key in ecs_state.clarification_controls:
        return LIFECYCLE_STATES["clarification"]
    if key in ecs_state.submitted_controls:
        return LIFECYCLE_STATES["pending_auditor_review"]
    if key in ecs_state.cancelled_drafts:
        return LIFECYCLE_STATES["cancelled"]
    return LIFECYCLE_STATES["draft"]


def _pending_with(key: str) -> str:
    state = get_lifecycle_state(key)
    if state in (LIFECYCLE_STATES["closed"], LIFECYCLE_STATES["approved"]):
        return "—"
    if state == LIFECYCLE_STATES["pending_auditor_review"]:
        return "Auditor Queue"
    if state == LIFECYCLE_STATES["escalated"]:
        return "Compliance Leadership"
    if state in (LIFECYCLE_STATES["resubmission_required"], LIFECYCLE_STATES["clarification"]):
        return "App Owner"
    return "App Owner"


def _sla_status(aging_days: int, evidence_status: str) -> tuple[str, str]:
    if aging_days > 30 or evidence_status == "Expired":
        return "Breached", "text-danger"
    if aging_days > 14 or evidence_status == "Due for Refresh":
        return "At Risk", "text-warning"
    return "On Track", "text-success"


def _last_updated(key: str, ev: dict) -> str:
    meta = ecs_state.submitted_meta.get(key, {})
    return meta.get("submitted_at", ev.get("upload_timestamp", "2026-05-01 09:00 UTC"))


def framework_pending_count(framework: str, role: str = "owner") -> int:
    """Live actionable count per framework for the given role."""
    if role == "auditor":
        return len([i for i in build_auditor_review_queue(limit=500) if i["framework"] == framework])
    if role in ("cio", "vertical_head", "compliance_head", "functional_head"):
        return len([i for i in build_leadership_queue(role, limit=500) if i["framework"] == framework])
    return len([i for i in build_owner_work_queue(limit=500) if i["framework"] == framework])


def framework_open_count(framework: str) -> int:
    """Total non-closed workflow items for a framework (all roles)."""
    owner = len([i for i in build_owner_work_queue(limit=500) if i["framework"] == framework])
    auditor = len([i for i in build_auditor_review_queue(limit=500) if i["framework"] == framework])
    return owner + auditor


def _owner_actionable(key: str) -> bool:
    if key in ecs_state.approved_controls or key in ecs_state.cancelled_drafts:
        return False
    if key in ecs_state.submitted_controls:
        return False
    return True


def _enrich_queue_item(item: dict) -> dict:
    enriched = dict(item)
    sla_label, sla_class = _sla_status(enriched["aging_days"], enriched["evidence_status"])
    enriched["lifecycle_state"] = get_lifecycle_state(enriched["key"])
    enriched["pending_with"] = _pending_with(enriched["key"])
    enriched["sla"] = sla_label
    enriched["sla_class"] = sla_class
    enriched["last_updated"] = _last_updated(
        enriched["key"], {"upload_timestamp": enriched.get("submitted_timestamp", "")}
    )
    if enriched["workflow_code"] == "rejected":
        enriched["lifecycle_state"] = LIFECYCLE_STATES["resubmission_required"]
    elif enriched["workflow_code"] == "submitted":
        enriched["lifecycle_state"] = LIFECYCLE_STATES["pending_auditor_review"]
    elif enriched.get("escalated"):
        enriched["lifecycle_state"] = LIFECYCLE_STATES["escalated"]
    return enriched


def build_owner_work_queue(limit: int = 80) -> list[dict]:
    items: list[dict] = []
    seen_keys: set[str] = set()

    for framework, controls in FRAMEWORK_CATALOG.items():
        for ctrl in controls:
            key = ecs_state.control_key(framework, ctrl["control"])
            if key in ecs_state.cancelled_drafts or key in ecs_state.approved_controls:
                continue
            if key in ecs_state.submitted_controls:
                continue

            primary = ctrl["evidences"][0]
            primary_item = _queue_item(framework, ctrl, primary)
            if primary_item and key not in seen_keys:
                seen_keys.add(key)
                items.append(primary_item)

            for ev in ctrl["evidences"][1:]:
                if ev.get("evidence_status") in ("Expired", "Due for Refresh"):
                    if key in ecs_state.submitted_controls:
                        continue
                    extra = _queue_item(framework, ctrl, ev)
                    if extra:
                        dedupe = f"{key}::{ev['evidence_id']}"
                        if dedupe not in seen_keys:
                            seen_keys.add(dedupe)
                            extra["action_type"] = "Expiring evidence"
                            items.append(extra)

    items.sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 9), -x["aging_days"]))
    return [_enrich_queue_item(i) for i in items[:limit]]


def build_auditor_review_queue(limit: int = 80) -> list[dict]:
    items: list[dict] = []

    for key in list(ecs_state.submitted_controls.keys()):
        framework, control = key.split("::", 1)
        ctrl = _catalog_ctrl(framework, control)
        if not ctrl:
            continue
        ev = ctrl["evidences"][0]
        item = _queue_item(framework, ctrl, ev, include_closed=False)
        if item and item["workflow_code"] == "submitted":
            items.append(item)

    for key, info in ecs_state.escalated_controls.items():
        if key not in ecs_state.submitted_controls:
            continue
        framework, control = key.split("::", 1)
        ctrl = _catalog_ctrl(framework, control)
        if ctrl:
            for row in items:
                if row["key"] == key:
                    row["escalated"] = True
                    row["risk_rating"] = "Critical"
                    row["auditor_comments"] = info.get("reason", row["auditor_comments"])
                    break

    items.sort(
        key=lambda x: (
            0 if x.get("escalated") else 1,
            PRIORITY_ORDER.get(x["priority"], 9),
            -x["aging_days"],
        )
    )
    return [_enrich_queue_item(i) for i in items[:limit]]


def work_queue_summary() -> dict:
    owner_q = build_owner_work_queue(limit=500)
    auditor_q = build_auditor_review_queue(limit=500)
    return {
        "owner_pending": len(owner_q),
        "auditor_pending": len(auditor_q),
        "escalated": len(ecs_state.escalated_controls),
        "clarifications": len(ecs_state.clarification_controls),
        "rejected": len(ecs_state.rejected_controls),
    }


def build_leadership_queue(role: str, limit: int = 30) -> list[dict]:
    items_by_key: dict[str, dict] = {}
    for key in list(ecs_state.escalated_controls.keys()):
        framework, control = key.split("::", 1)
        ctrl = _catalog_ctrl(framework, control)
        if not ctrl:
            continue
        ev = ctrl["evidences"][0]
        item = _queue_item(framework, ctrl, ev, include_closed=False)
        if item:
            item["escalated"] = True
            item["executive_action"] = "Review Escalation"
            items_by_key[key] = item

    for key in list(ecs_state.submitted_controls.keys()):
        if key in items_by_key:
            continue
        framework, control = key.split("::", 1)
        ctrl = _catalog_ctrl(framework, control)
        if not ctrl:
            continue
        ev = ctrl["evidences"][0]
        item = _queue_item(framework, ctrl, ev)
        if item and item.get("aging_days", 0) > 14:
            item["executive_action"] = "SLA Breach Review"
            items_by_key[key] = item

    for key in ecs_state.rejected_controls:
        if key in items_by_key:
            continue
        framework, control = key.split("::", 1)
        ctrl = _catalog_ctrl(framework, control)
        if not ctrl:
            continue
        ev = ctrl["evidences"][0]
        item = _queue_item(framework, ctrl, ev)
        if item and role in ("compliance_head", "cio"):
            item["executive_action"] = "Policy Gap Review"
            items_by_key[key] = item

    items = list(items_by_key.values())
    if role == "vertical_head":
        items = [i for i in items if i.get("priority") in ("Critical", "High") or i.get("escalated")]
    elif role == "cio":
        items = sorted(items, key=lambda x: (0 if x.get("escalated") else 1, -x["aging_days"]))
    elif role == "compliance_head":
        items = [i for i in items if i["framework"] in ("PCI DSS", "DPSC", "CSITE", "ITPP") or i.get("escalated")]

    items.sort(key=lambda x: (0 if x.get("escalated") else 1, PRIORITY_ORDER.get(x["priority"], 9), -x["aging_days"]))
    return [_enrich_queue_item(i) for i in items[:limit]]


def build_universal_workflow_rows(
    *,
    framework: str | None = None,
    module: str | None = None,
    role: str = "owner",
    limit: int = 40,
) -> list[dict]:
    """Page-level actionable rows filtered by framework or MVP module."""
    if role == "auditor":
        base = build_auditor_review_queue(limit=500)
    elif role in ("cio", "vertical_head", "compliance_head", "functional_head"):
        base = build_leadership_queue(role, limit=500)
    else:
        base = build_owner_work_queue(limit=500)

    if framework:
        base = [i for i in base if i["framework"] == framework]

    if module:
        mod = module.lower()
        if mod == "scheduler":
            base = [i for i in base if i.get("evidence_status") in ("Due for Refresh", "Expired") or i["aging_days"] > 14]
        elif mod in ("upload", "evidence_health"):
            base = [i for i in base if i["evidence_status"] in ("Expired", "Due for Refresh", "Current")]
        elif mod == "completeness":
            base = [i for i in base if i["workflow_code"] in ("pending", "rejected", "clarification")]
        elif mod == "audit_prep":
            base = sorted(base, key=lambda x: PRIORITY_ORDER.get(x["priority"], 9))
        elif mod == "lifecycle":
            base = [i for i in base if i["lifecycle_state"] != LIFECYCLE_STATES["closed"]]
        elif mod == "enterprise":
            base = [i for i in base if i.get("escalated") or i["priority"] in ("Critical", "High")]
        elif mod == "reports":
            base = [i for i in base if i["workflow_code"] in ("pending", "rejected", "submitted")]
        elif mod == "trends":
            base = [i for i in base if i["lifecycle_state"] not in (LIFECYCLE_STATES["closed"],)]
        elif mod == "onboarding":
            base = [i for i in base if i["workflow_code"] in ("pending", "rejected", "clarification")]
        elif mod == "pan_india":
            base = [i for i in base if i.get("region") and i["workflow_code"] != "approved"]
        elif mod == "reuse":
            base = [i for i in base if i["evidence_status"] == "Current" and i["workflow_code"] in ("pending", "submitted")]
        elif mod == "comparison":
            base = [i for i in base if i.get("priority") in ("Critical", "High") or i.get("risk_rating") in ("Critical", "High")]
        elif mod == "integrations":
            base = [i for i in base if i["aging_days"] > 7 or i.get("escalated")]
        elif mod == "search":
            base = [i for i in base if i["workflow_code"] in ("pending", "submitted", "rejected", "clarification")]

    return base[:limit]


def framework_explanation(name: str) -> str | None:
    return FRAMEWORK_DESCRIPTIONS.get(name)
