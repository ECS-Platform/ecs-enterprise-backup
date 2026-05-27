"""Persistent exception / TD workflow state — survives navigation and refresh."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from app.audit_trail import log_event

WORKFLOW_STATES = (
    "Draft", "Submitted", "Pending Approval", "Under Review", "Approved", "Rejected", "Expired", "Closed", "Active",
)

_SEED_EXCEPTIONS: list[dict] = [
    {"exception_id": "EXC-2026-014", "control": "PCI DSS — TLS 1.0 disablement", "framework": "PCI DSS", "application": "Payments", "justification": "Legacy merchant SDK requires TLS 1.0 until Q3 migration.", "compensating_control": "WAF TLS downgrade block + enhanced monitoring", "td_expiry": "2026-06-30", "owner": "K. Reddy (App Owner)", "approving_authority": "CIO / CISO", "residual_risk": "High", "renewal_status": "Due for renewal", "status": "Under Review", "workflow_state": "Under Review", "expired": False, "risk": "High", "submitted_at": "2026-04-12 09:00 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-021", "control": "OS Baselining — Unsupported RHEL 7 host", "framework": "OS Baselining", "application": "Treasury", "justification": "Vendor CBS middleware not certified on RHEL 8 until vendor patch Q4.", "compensating_control": "Network segmentation + enhanced AV + monthly VA", "td_expiry": "2026-04-15", "owner": "S. Banerjee (App Owner)", "approving_authority": "Compliance Head", "residual_risk": "Critical", "renewal_status": "TD Expired", "status": "Expired", "workflow_state": "Expired", "expired": True, "risk": "Critical", "submitted_at": "2026-01-20 11:00 UTC", "resubmission_count": 1},
    {"exception_id": "EXC-2026-033", "control": "VAPT — Delayed critical remediation", "framework": "VAPT", "application": "Mobile Banking", "justification": "App store release freeze during regulatory audit window.", "compensating_control": "Temporary WAF rule + API rate limiting", "td_expiry": "2026-05-20", "owner": "A. Sharma (App Owner)", "approving_authority": "CISO", "residual_risk": "High", "renewal_status": "TD Expired", "status": "Expired", "workflow_state": "Expired", "expired": True, "risk": "High", "submitted_at": "2026-02-05 14:00 UTC", "resubmission_count": 2},
    {"exception_id": "EXC-2026-041", "control": "ITPP — Temporary firewall rule (DR test)", "framework": "ITPP", "application": "Net Banking", "justification": "Emergency DR validation required temporary inbound rule.", "compensating_control": "Time-bound ACL + SOC monitoring", "td_expiry": "2026-05-28", "owner": "R. Mehta (App Owner)", "approving_authority": "Network Head", "residual_risk": "Medium", "renewal_status": "Active", "status": "Submitted", "workflow_state": "Submitted", "expired": False, "risk": "Medium", "submitted_at": "2026-05-18 08:30 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-052", "control": "AppSec — Delayed MFA rollout (admin console)", "framework": "AppSec", "application": "Loan System", "justification": "Identity provider integration delayed by vendor.", "compensating_control": "IP allow-list + PAM session recording", "td_expiry": "2026-07-15", "owner": "M. Joshi (App Owner)", "approving_authority": "CISO", "residual_risk": "High", "renewal_status": "Approved", "status": "Approved", "workflow_state": "Approved", "expired": False, "risk": "High", "submitted_at": "2026-03-01 10:00 UTC", "approved_by": "Compliance Head", "approved_at": "2026-03-08 16:00 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-058", "control": "DB Baselining — Break-glass DB account", "framework": "DB Baselining", "application": "Treasury", "justification": "CBS emergency access account required for FX settlement incidents.", "compensating_control": "Dual approval + session replay + 24h auto-disable", "td_expiry": "2026-08-01", "owner": "S. Banerjee (App Owner)", "approving_authority": "DBA Head / CISO", "residual_risk": "Medium", "renewal_status": "Approved", "status": "Approved", "workflow_state": "Approved", "expired": False, "risk": "Medium", "submitted_at": "2026-04-01 09:00 UTC", "approved_by": "CISO", "approved_at": "2026-04-05 11:00 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-061", "control": "DPSC — UPI API rate limit waiver", "framework": "DPSC", "application": "UPI", "justification": "NPCI peak window throughput exception for settlement batch.", "compensating_control": "Enhanced fraud monitoring + manual reconciliation", "td_expiry": "2026-06-15", "owner": "P. Nair (App Owner)", "approving_authority": "Compliance Head", "residual_risk": "High", "renewal_status": "Pending CAB", "status": "Under Review", "workflow_state": "Under Review", "expired": False, "risk": "High", "submitted_at": "2026-05-10 07:00 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-067", "control": "Nginx Baselining — Legacy cipher suite", "framework": "Nginx Baselining", "application": "Net Banking", "justification": "Legacy merchant integration requires TLS 1.0 cipher until migration.", "compensating_control": "Dedicated WAF profile + cert pinning", "td_expiry": "2026-06-30", "owner": "R. Mehta (App Owner)", "approving_authority": "CISO", "residual_risk": "High", "renewal_status": "Rejected", "status": "Rejected", "workflow_state": "Rejected", "expired": False, "risk": "High", "submitted_at": "2026-04-22 13:00 UTC", "rejected_by": "Auditor", "rejected_at": "2026-04-25 09:00 UTC", "rejection_reason": "Compensating control insufficient — require network segmentation evidence", "resubmission_count": 1},
    {"exception_id": "EXC-2026-071", "control": "CSITE — SIEM use-case deferral", "framework": "CSITE", "application": "Payments", "justification": "SOC tuning window delayed due to SIEM upgrade.", "compensating_control": "Manual log review + enhanced alerting", "td_expiry": "2026-07-01", "owner": "K. Reddy (App Owner)", "approving_authority": "CISO", "residual_risk": "Medium", "renewal_status": "Draft", "status": "Draft", "workflow_state": "Draft", "expired": False, "risk": "Medium", "submitted_at": "2026-05-20 15:00 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-075", "control": "PCI DSS — Encryption at rest deferral", "framework": "PCI DSS", "application": "Mobile Banking", "justification": "TDE rollout scheduled post audit window.", "compensating_control": "Column masking + vault encryption for PAN fields", "td_expiry": "2026-08-15", "owner": "A. Sharma (App Owner)", "approving_authority": "QSA + CISO", "residual_risk": "Critical", "renewal_status": "Submitted", "status": "Submitted", "workflow_state": "Submitted", "expired": False, "risk": "Critical", "submitted_at": "2026-05-22 10:00 UTC", "resubmission_count": 0},
    {"exception_id": "EXC-2026-078", "control": "AppSec — SAST gate bypass (legacy module)", "framework": "AppSec", "application": "Wealth Portal", "justification": "COBOL bridge module pending decommission.", "compensating_control": "Manual secure code review each release", "td_expiry": "2026-09-30", "owner": "V. Rao (App Owner)", "approving_authority": "AppSec Lead", "residual_risk": "Medium", "renewal_status": "Approved", "status": "Approved", "workflow_state": "Approved", "expired": False, "risk": "Medium", "submitted_at": "2026-03-15 08:00 UTC", "approved_by": "Compliance Head", "approved_at": "2026-03-20 14:00 UTC", "resubmission_count": 0},
]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _seed_index() -> dict[str, dict]:
    if not hasattr(ecs_state, "exception_seed_loaded"):
        ecs_state.exception_seed_loaded = True
        for row in _SEED_EXCEPTIONS:
            eid = row["exception_id"]
            if eid not in ecs_state.exception_registry:
                ecs_state.exception_registry[eid] = dict(row)
    return ecs_state.exception_registry


def get_exception(exception_id: str) -> dict | None:
    reg = _seed_index()
    return reg.get(exception_id)


def get_all_exceptions(role: str = "owner") -> list[dict]:
    from app.role_filter_scope import apply_role_scope

    reg = _seed_index()
    rows = [dict(v) for v in reg.values()]
    for r in rows:
        r.setdefault("risk", r.get("residual_risk", "Medium"))
        r["expired"] = r.get("workflow_state") == "Expired" or r.get("status") == "Expired"
        if r.get("status") in ("Approved", "Active") and not r.get("expired"):
            r.setdefault("expired", False)
        fw_slug = (r.get("framework") or "FW").replace(" ", "")[:6].upper()
        cid = r.get("control_id") or r.get("control", "")[:12].replace(" ", "-")
        r.setdefault("observation_id", r.get("observation_id") or f"OBS-{fw_slug}-{cid.replace('.', '')[:8]}")
        r.setdefault("observation_title", r.get("control", "Technical debt observation")[:100])
        r.setdefault("observation_description", r.get("justification", "")[:200])
        r.setdefault("control_name", r.get("control", ""))
        r.setdefault("td_description", r.get("compensating_control") or r.get("justification", ""))
        r.setdefault("due_date", r.get("td_expiry", ""))
        r.setdefault("risk_rating", r.get("residual_risk", "Medium"))
    return apply_role_scope(rows, role)


def _status_badge(status: str) -> str:
    mapping = {
        "Approved": "success", "Rejected": "danger", "Expired": "dark",
        "Under Review": "warning text-dark", "Submitted": "info text-dark",
        "Draft": "secondary", "Closed": "secondary", "Active": "primary",
    }
    return mapping.get(status, "secondary")


def create_exception(
    *,
    framework: str,
    application: str,
    control: str,
    justification: str,
    user: str,
    role: str,
    control_id: str = "",
    compensating_control: str = "",
    observation_id: str = "",
    evidence_id: str = "",
    td_expiry: str = "2026-09-30",
    residual_risk: str = "Medium",
    submit: bool = True,
) -> tuple[str, dict]:
    """Create and persist a new exception / TD record."""
    reg = _seed_index()
    seq = max((int(k.split("-")[-1]) for k in reg if k.startswith("EXC-")), default=100) + 1
    eid = f"EXC-2026-{seq:03d}"
    ts = _ts()
    status = "Pending Approval" if submit else "Draft"
    workflow = "Submitted" if submit else "Draft"
    rec = {
        "exception_id": eid,
        "control": control or f"{framework} — {control_id or 'Control waiver'}",
        "control_id": control_id,
        "framework": framework,
        "application": application or "Net Banking",
        "justification": justification,
        "compensating_control": compensating_control or "Compensating controls to be validated by approver.",
        "td_expiry": td_expiry,
        "owner": f"{user} ({role.replace('_', ' ').title()})",
        "approving_authority": "Compliance Head / CISO",
        "residual_risk": residual_risk,
        "renewal_status": "Pending Approval" if submit else "Draft",
        "status": status,
        "workflow_state": workflow,
        "expired": False,
        "risk": residual_risk,
        "submitted_at": ts,
        "resubmission_count": 0,
        "observation_id": observation_id,
        "evidence_id": evidence_id,
        "audit_trail": [{
            "timestamp": ts,
            "action": "raise_exception",
            "actor": user,
            "role": role,
            "remarks": justification[:160],
            "status_after": status,
        }],
    }
    reg[eid] = rec
    log_event(
        "Exception Raised",
        user,
        framework,
        control_id or control[:40],
        f"Exception {eid} routed to approver workflow",
        evidence_id=eid,
        role=role,
    )
    return eid, rec


def apply_exception_action(exception_id: str, action: str, user: str, role: str, comment: str = "") -> str:
    reg = _seed_index()
    rec = reg.get(exception_id)
    if not rec:
        return f"Exception {exception_id} not found."

    history = rec.setdefault("audit_trail", [])
    ts = _ts()

    if action == "approve_exception":
        rec.update({
            "status": "Approved",
            "workflow_state": "Approved",
            "approved_by": user,
            "approved_at": ts,
            "approver_role": role,
            "renewal_status": "Approved",
            "expired": False,
            "comments": comment or "Approved with compensating controls validated.",
        })
        msg = f"Exception {exception_id} approved by {user}."
    elif action == "reject_exception":
        rec.update({
            "status": "Rejected",
            "workflow_state": "Rejected",
            "rejected_by": user,
            "rejected_at": ts,
            "rejection_reason": comment or "Rejected — insufficient compensating control evidence.",
            "renewal_status": "Rejected",
            "resubmission_count": rec.get("resubmission_count", 0) + 1,
        })
        msg = f"Exception {exception_id} rejected by {user}."
    elif action == "extend_td":
        rec.update({
            "status": "Under Review",
            "workflow_state": "Under Review",
            "renewal_status": "Extension Requested",
            "td_expiry": "2026-09-30",
            "comments": comment or "TD extension requested.",
        })
        msg = f"TD extension requested for {exception_id}."
    elif action == "renew_exception":
        rec.update({
            "status": "Submitted",
            "workflow_state": "Submitted",
            "renewal_status": "Renewal Submitted",
            "expired": False,
            "resubmission_count": rec.get("resubmission_count", 0) + 1,
        })
        msg = f"Renewal submitted for {exception_id}."
    elif action == "close_exception":
        rec.update({"status": "Closed", "workflow_state": "Closed", "comments": comment or "Closed."})
        msg = f"Exception {exception_id} closed."
    elif action == "escalate_expired_td":
        rec.update({"status": "Escalated", "workflow_state": "Under Review", "renewal_status": "Escalated"})
        msg = f"Expired TD {exception_id} escalated."
    else:
        msg = f"{action.replace('_', ' ').title()} recorded for {exception_id}."

    history.append({
        "timestamp": ts, "action": action, "actor": user, "role": role,
        "remarks": comment or msg, "status_after": rec.get("status"),
    })
    reg[exception_id] = rec
    log_event(f"Exception {action.replace('_', ' ').title()}", user, rec.get("framework", ""), rec.get("control", ""), msg, evidence_id=exception_id, role=role)
    return msg


def build_exception_kpis(rows: list[dict]) -> list[dict]:
    active = [r for r in rows if r.get("status") not in ("Closed", "Expired", "Rejected") and not r.get("expired")]
    expired = [r for r in rows if r.get("expired") or r.get("status") == "Expired"]
    approved = [r for r in rows if r.get("status") == "Approved"]
    rejected = [r for r in rows if r.get("status") == "Rejected"]
    pending = [r for r in rows if r.get("status") in ("Submitted", "Under Review", "Draft")]
    high_risk = [r for r in active if r.get("residual_risk") in ("Critical", "High")]
    expiring = [r for r in active if r.get("td_expiry", "").startswith("2026-06")]
    return [
        {"label": "Active Exceptions", "value": len(active), "tone": "primary"},
        {"label": "Approved TDs", "value": len(approved), "tone": "success"},
        {"label": "Rejected Exceptions", "value": len(rejected), "tone": "danger"},
        {"label": "Expiring This Month", "value": len(expiring), "tone": "warning"},
        {"label": "High-Risk Open TDs", "value": len(high_risk), "tone": "danger"},
        {"label": "Pending Review", "value": len(pending), "tone": "info"},
    ]


def build_governance_dashboard(role: str = "owner") -> dict:
    rows = get_all_exceptions(role)
    expired = [r for r in rows if r.get("expired")]
    approved_recent = sorted([r for r in rows if r.get("status") == "Approved"], key=lambda x: x.get("approved_at", ""), reverse=True)[:10]
    rejected_recent = sorted([r for r in rows if r.get("status") == "Rejected"], key=lambda x: x.get("rejected_at", ""), reverse=True)[:10]
    expiring = [r for r in rows if not r.get("expired") and r.get("td_expiry", "").startswith("2026-06")]
    pending_cab = [r for r in rows if "CAB" in r.get("renewal_status", "") or r.get("status") in ("Submitted", "Under Review")]
    by_fw: dict[str, int] = {}
    for r in rows:
        by_fw[r["framework"]] = by_fw.get(r["framework"], 0) + 1
    return {
        "rows": rows,
        "kpis": build_exception_kpis(rows),
        "expired": expired,
        "approved_recent": approved_recent,
        "rejected_recent": rejected_recent,
        "expiring_month": expiring,
        "pending_cab": pending_cab,
        "by_framework": [{"framework": k, "count": v} for k, v in sorted(by_fw.items(), key=lambda x: -x[1])],
        "role": role,
    }
