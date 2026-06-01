"""AI SDLC Governance — workflow execution engine (framework → control → evidence)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import BANKING_APPLICATIONS, BANKING_OWNERS, between, pick, seed

ANCHOR = date(2026, 5, 28)

SUPPORTED_FRAMEWORKS: list[dict[str, str]] = [
    {"id": "vapt", "name": "VAPT", "label": "VAPT"},
    {"id": "dpsc", "name": "DPSC", "label": "DPSC (Digital Payment Security Controls)"},
    {"id": "os-baselining", "name": "OS Baselining", "label": "OS Baselining"},
    {"id": "db-baselining", "name": "Database Baselining", "label": "Database Baselining"},
    {"id": "mw-baselining", "name": "Middleware Baselining", "label": "Middleware Baselining"},
    {"id": "csite", "name": "CSITE", "label": "CSITE"},
    {"id": "regulatory", "name": "Regulatory Controls", "label": "Regulatory Controls"},
    {"id": "internal-audit", "name": "Internal Audit Controls", "label": "Internal Audit Controls"},
    {"id": "ai-governance", "name": "AI Governance Controls", "label": "AI Governance Controls"},
    {"id": "itpp", "name": "ITPP", "label": "Information Technology Policy Framework (ITPP)"},
]

ITPP_DOMAINS: list[dict[str, str]] = [
    {"id": "capacity", "name": "Capacity Management", "prefix": "CP"},
    {"id": "availability", "name": "Availability Management", "prefix": "AV"},
    {"id": "incident", "name": "Incident Management", "prefix": "IM"},
    {"id": "problem", "name": "Problem Management", "prefix": "PM"},
    {"id": "change", "name": "Change Management", "prefix": "CM"},
    {"id": "release", "name": "Release Management", "prefix": "RM"},
    {"id": "backup", "name": "Backup Management", "prefix": "BK"},
    {"id": "dr", "name": "Disaster Recovery", "prefix": "DR"},
    {"id": "access", "name": "Access Management", "prefix": "AM"},
    {"id": "patch", "name": "Patch Management", "prefix": "PT"},
    {"id": "config", "name": "Configuration Management", "prefix": "CF"},
    {"id": "monitoring", "name": "Monitoring & Alerting", "prefix": "MA"},
    {"id": "vendor", "name": "Vendor Management", "prefix": "VM"},
    {"id": "asset", "name": "Asset Management", "prefix": "AS"},
    {"id": "continuity", "name": "Service Continuity", "prefix": "SC"},
    {"id": "ops-gov", "name": "Operations Governance", "prefix": "OG"},
]

STAGE_KEYS = ("requirement", "design", "development", "testing", "go-live")
STAGE_LABELS = {
    "requirement": "Requirements",
    "design": "Design",
    "development": "Development",
    "testing": "Testing",
    "go-live": "Go-Live",
}

STAGE_ARTIFACTS: dict[str, list[str]] = {
    "requirement": [
        "Requirement Document", "Business Requirement Document",
        "Control Requirement Document", "Security Requirement",
    ],
    "design": [
        "Solution Architecture", "Technical Architecture", "HLD", "LLD",
        "Security Design", "Threat Model",
    ],
    "development": [
        "Code Review", "Configuration Standard", "Build Configuration",
        "Deployment Configuration", "Change Record",
    ],
    "testing": [
        "Test Case", "Test Execution", "VAPT Result", "DPSC Result",
        "Security Validation", "Remediation Verification",
    ],
    "go-live": [
        "Requirement Approved", "Design Approved", "Development Completed", "Testing Passed",
    ],
}

STATUSES = ["Pending", "In Review", "Approved", "Rejected", "Needs Rework", "Overdue", "Awaiting Upload"]
FINDING_STATUSES = ["Open", "In Progress", "Remediated", "Verified", "Closed"]
SEVERITIES = ["Critical", "High", "Medium", "Low"]
CRITICALITIES = ["Critical", "High", "Medium", "Low"]
REG_CLASSES = ["Tier-1 Payment", "Tier-1 Digital", "Tier-2 Internal", "Tier-3 Support"]

CONTROL_NAME_POOL = [
    "Secure API Authentication",
    "Critical Vulnerability Remediation",
    "Linux Baseline Compliance",
    "Database Encryption at Rest",
    "Middleware Patch Compliance",
    "Privileged Access Monitoring",
    "Change Advisory Approval",
    "Incident Response Playbook",
    "DR Failover Validation",
    "Payment Channel Segregation",
    "Prompt Injection Guardrail",
    "Model Risk Assessment",
]


def control_name_for(control_id: str) -> str:
    return pick(seed("ctrlname", control_id), CONTROL_NAME_POOL)


def enrich_row_control(row: dict[str, Any], stage: str = "") -> dict[str, Any]:
    cid = row.get("control_id") or row.get("control", "")
    cname = row.get("control_name") or control_name_for(cid)
    out = {
        **row,
        "control_id": cid,
        "control_name": cname,
        "control_display": f"{cid} | {cname}",
        "stage": stage or row.get("stage", ""),
    }
    if "control" not in out or not out["control"]:
        out["control"] = cid
    return out


_DPSC_DOMAINS = [
    ("Authentication", "AUTH"),
    ("Encryption", "ENC"),
    ("Transaction Monitoring", "TXN"),
    ("Key Management", "KEY"),
    ("Access Control", "ACC"),
    ("Logging", "LOG"),
]


def _controls_for_framework(fw_name: str, count: int = 6) -> list[dict[str, str]]:
    if fw_name == "ITPP":
        controls = []
        for i, dom in enumerate(ITPP_DOMAINS[:count]):
            controls.append({
                "control_id": f"{dom['prefix']}-{i % 3 + 1:03d}",
                "domain": dom["name"],
                "framework": fw_name,
            })
        return controls
    if fw_name == "DPSC":
        controls = []
        for i, (dom_name, dom_pfx) in enumerate(_DPSC_DOMAINS[:count]):
            controls.append({
                "control_id": f"DPSC-{dom_pfx}-{i % 3 + 1:02d}",
                "domain": dom_name,
                "framework": fw_name,
            })
        return controls
    prefix_map = {
        "VAPT": "VAPT", "DPSC": "DPSC", "OS Baselining": "OSB", "Database Baselining": "DBB",
        "Middleware Baselining": "MWB", "CSITE": "CSI", "Regulatory Controls": "REG",
        "Internal Audit Controls": "IAC", "AI Governance Controls": "AIG",
    }
    pfx = prefix_map.get(fw_name, "CTL")
    return [
        {"control_id": f"{pfx}-{i+1:03d}", "domain": "General", "framework": fw_name}
        for i in range(count)
    ]


def _onboarded_applications() -> list[dict[str, Any]]:
    apps = []
    fw_ids = [f["name"] for f in SUPPORTED_FRAMEWORKS]
    for i, app in enumerate(BANKING_APPLICATIONS[:14]):
        s = seed("onboard", app)
        selected = [fw_ids[j] for j in range(len(fw_ids)) if (s >> j) & 1 or j < 4]
        if not selected:
            selected = fw_ids[:4]
        apps.append({
            "application_id": f"APP-{i+1:03d}",
            "application_name": app,
            "business_owner": pick(s >> 2, BANKING_OWNERS),
            "application_owner": pick(s >> 4, BANKING_OWNERS),
            "criticality": pick(s >> 6, CRITICALITIES),
            "regulatory_classification": pick(s >> 8, REG_CLASSES),
            "frameworks": selected,
            "control_count": sum(len(_controls_for_framework(f)) for f in selected[:5]),
        })
    return apps


def _worklist_items(stage_key: str, count: int = 48) -> list[dict[str, Any]]:
    apps = _onboarded_applications()
    artifacts = STAGE_ARTIFACTS[stage_key]
    rows = []
    for i in range(count):
        s = seed("wl", stage_key, i)
        app = pick(s, apps)
        fw = pick(s >> 2, app["frameworks"])
        ctrl = pick(s >> 4, _controls_for_framework(fw))
        ctrl_id = ctrl["control_id"]
        status = pick(s >> 6, STATUSES)
        due = ANCHOR + timedelta(days=between(s >> 8, -14, 30))
        row: dict[str, Any] = enrich_row_control({
            "activity_id": f"ACT-{stage_key[:3].upper()}-{i+1:04d}",
            "application": app["application_name"],
            "framework": fw,
            "domain": ctrl["domain"],
            "control": ctrl_id,
            "owner": pick(s >> 10, BANKING_OWNERS),
            "status": status,
            "due_date": due.strftime("%Y-%m-%d"),
            "stage": STAGE_LABELS[stage_key],
        }, stage=STAGE_LABELS[stage_key])
        row["row_actions"] = ["Upload", "Review", "Approve", "Reject", "Request Rework"]
        if stage_key == "go-live":
            row["artifact_required"] = pick(s >> 12, artifacts)
            row["readiness_check"] = row["artifact_required"]
        else:
            row["artifact_required"] = pick(s >> 12, artifacts)
        from modules.ai_sdlc.engines.ai_sdlc_controlled_documents import enrich_worklist_row
        rows.append(enrich_worklist_row(row, stage_key))
    return rows


def _evidence_queue(count: int = 60) -> list[dict[str, Any]]:
    apps = _onboarded_applications()
    artifact_types = [
        "Policy Document", "Scan Report", "Configuration Export", "Test Result",
        "Approval Record", "Architecture Diagram", "Change Ticket", "Audit Log",
    ]
    rows = []
    for i in range(count):
        s = seed("evq", i)
        app = pick(s, apps)
        fw = pick(s >> 2, app["frameworks"])
        ctrl = pick(s >> 4, _controls_for_framework(fw))
        due = ANCHOR + timedelta(days=between(s >> 6, -7, 21))
        rows.append(enrich_row_control({
            "evidence_id": f"EV-AISDLC-{i+1:04d}",
            "application": app["application_name"],
            "framework": fw,
            "domain": ctrl["domain"],
            "control": ctrl["control_id"],
            "artifact_type": pick(s >> 8, artifact_types),
            "due_date": due.strftime("%Y-%m-%d"),
            "status": pick(s >> 10, STATUSES),
            "stage": "Evidence Collection",
            "evidence_view_url": f"/mvp/ai-sdlc/evidence/view/EV-AISDLC-{i+1:04d}",
            "row_actions": ["Upload", "Review", "Approve", "Reject", "Request Rework"],
        }, stage="Evidence Collection"))
    return rows


def _findings(count: int = 45) -> list[dict[str, Any]]:
    apps = _onboarded_applications()
    sources = ["Audit Finding", "VAPT Finding", "DPSC Finding", "Regulatory Finding", "Internal Control Gap"]
    rows = []
    for i in range(count):
        s = seed("find", i)
        app = pick(s, apps)
        fw = pick(s >> 2, app["frameworks"])
        ctrl = pick(s >> 4, _controls_for_framework(fw))
        target = ANCHOR + timedelta(days=between(s >> 6, 5, 45))
        rows.append({
            "finding_id": f"FND-{i+1:05d}",
            "source": pick(s >> 8, sources),
            "application": app["application_name"],
            "framework": fw,
            "domain": ctrl["domain"],
            "control": ctrl["control_id"],
            "severity": pick(s >> 10, SEVERITIES),
            "owner": pick(s >> 12, BANKING_OWNERS),
            "target_date": target.strftime("%Y-%m-%d"),
            "status": pick(s >> 14, FINDING_STATUSES),
            "actions": ["Assign", "Update", "Close", "Reopen"],
        })
    return rows


def build_landing_workbench() -> dict[str, Any]:
    apps = _onboarded_applications()
    return {
        "my_applications": apps[:8],
        "summary_counts": {
            "controls_pending_requirements": 42,
            "controls_pending_design": 38,
            "controls_pending_development": 51,
            "controls_pending_testing": 33,
            "controls_pending_golive": 19,
            "evidence_awaiting_submission": 27,
            "open_findings": 14,
            "overdue_activities": 9,
        },
        "overdue_activities": _worklist_items("requirement", 9)[:9],
    }


def build_onboarding_view() -> dict[str, Any]:
    return {
        "frameworks": SUPPORTED_FRAMEWORKS,
        "itpp_domains": ITPP_DOMAINS,
        "applications": _onboarded_applications(),
        "sample_matrix": _build_control_matrix(_onboarded_applications()[0]),
    }


def _build_control_matrix(app: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for fw in app["frameworks"][:4]:
        for ctrl in _controls_for_framework(fw, 4):
            rows.append({
                "application": app["application_name"],
                "framework": fw,
                "domain": ctrl["domain"],
                "control": ctrl["control_id"],
            })
    return rows


def build_stage_worklist(stage_key: str) -> dict[str, Any]:
    from modules.ai_sdlc.engines.ai_sdlc_controlled_documents import DOC_TYPES
    title_map = {
        "requirement": "My Requirement Activities",
        "design": "My Design Activities",
        "development": "My Development Activities",
        "testing": "My Testing Activities",
        "go-live": "My Go-Live Activities",
    }
    meta = DOC_TYPES[stage_key]
    items = _worklist_items(stage_key)
    return {
        "stage_key": stage_key,
        "title": title_map[stage_key],
        "items": items,
        "rows": items,
        "columns": _stage_columns(stage_key),
        "document_column": {
            "label": meta["column_label"],
            "link_label": meta["link_label"],
        },
        "row_actions": ["Upload", "Review", "Approve", "Reject", "Request Rework"] if stage_key != "go-live"
        else ["Approve", "Reject", "Escalate"],
    }


def _stage_columns(stage_key: str) -> list[dict[str, str]]:
    base = [
        {"key": "application", "label": "Application", "wrap": True},
        {"key": "framework", "label": "Framework"},
        {"key": "domain", "label": "Domain", "wrap": True},
        {"key": "control_id", "label": "Control ID"},
        {"key": "control_name", "label": "Control Name", "wrap": True},
        {"key": "stage", "label": "Stage"},
    ]
    if stage_key == "go-live":
        base.append({"key": "readiness_check", "label": "Go-Live Readiness", "wrap": True})
    else:
        base.append({"key": "artifact_required", "label": "Artifact Required", "wrap": True})
    base.extend([
        {"key": "owner", "label": "Owner"},
        {"key": "status", "label": "Status"},
        {"key": "due_date", "label": "Due Date"},
    ])
    return base


def build_evidence_collection() -> dict[str, Any]:
    return {
        "title": "Evidence Collection",
        "subtitle": "Primary ECS workspace — upload, review, approve evidence against controls",
        "items": _evidence_queue(),
        "rows": _evidence_queue(),
        "columns": [
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "domain", "label": "Domain", "wrap": True},
            {"key": "control_id", "label": "Control ID"},
            {"key": "control_name", "label": "Control Name", "wrap": True},
            {"key": "stage", "label": "Stage"},
            {"key": "artifact_type", "label": "Artifact Type", "wrap": True},
            {"key": "due_date", "label": "Due Date"},
            {"key": "status", "label": "Status"},
            {"key": "evidence_view_url", "label": "Evidence", "wrap": True},
        ],
    }


def build_findings_remediation() -> dict[str, Any]:
    return {
        "title": "Findings & Remediation",
        "items": _findings(),
        "rows": _findings(),
        "columns": [
            {"key": "finding_id", "label": "Finding ID"},
            {"key": "source", "label": "Source", "wrap": True},
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "domain", "label": "Domain", "wrap": True},
            {"key": "control", "label": "Control"},
            {"key": "severity", "label": "Severity"},
            {"key": "owner", "label": "Owner"},
            {"key": "target_date", "label": "Target Date"},
            {"key": "status", "label": "Status"},
        ],
    }


def build_reports_hub() -> dict[str, Any]:
    return {
        "title": "Reports",
        "subtitle": "Reporting is consolidated here — no reporting elsewhere in AI SDLC Governance",
        "reports": [
            {"id": "app-compliance", "name": "Application Compliance Report", "desc": "Application → Framework → Domain → Control implementation status", "href": "/mvp/ai-sdlc/reports/app-compliance"},
            {"id": "fw-compliance", "name": "Framework Compliance Report", "desc": "Framework-level completion and compliance across applications", "href": "/mvp/ai-sdlc/reports/fw-compliance"},
            {"id": "readiness", "name": "Readiness Report", "desc": "Application readiness by framework across SDLC gates", "href": "/mvp/ai-sdlc/reports/readiness"},
            {"id": "control-impl", "name": "Control Implementation Report", "desc": "Requirement, Design, Development, Testing, Go-Live completion status", "href": "/mvp/ai-sdlc/reports/control-impl"},
            {"id": "evidence-status", "name": "Evidence Collection Status Report", "desc": "Required vs Submitted vs Approved evidence", "href": "/mvp/ai-sdlc/reports/evidence-status"},
            {"id": "findings", "name": "Findings & Remediation Report", "desc": "Open findings by application, framework, owner and severity", "href": "/mvp/ai-sdlc/reports/findings"},
        ],
        "supporting_capabilities": [
            {"label": "AI Model & Prompt Registry", "href": "/mvp/ai-registry", "note": "Supporting capability — approved model inventory"},
            {"label": "AI Governance Posture", "href": "/mvp/ai-governance", "note": "Supporting capability — runtime AI monitoring"},
            {"label": "Governance Quality Scan", "href": "/mvp/governance-quality", "note": "Supporting capability — QA engine diagnostics"},
        ],
    }
