"""Enterprise Governance Lifecycle Management — interconnected mock data engine."""

from __future__ import annotations

import hashlib

from app.framework_catalog import FRAMEWORK_CATALOG
from app.operations_catalog import FRAMEWORK_CONTROLS, OWNERS, owner_for

ALL_FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())

LIFECYCLE_APPS = [
    "Net Banking", "Mobile Banking", "Treasury", "Payments",
    "Loan Origination", "Wealth Portal", "Core Banking", "Oracle Core DB",
    "Internet Banking",
]

CONTROL_STAGES = [
    "Mapped", "Implemented", "Validation Pending", "Failed", "Exception Approved",
    "Remediation Open", "Revalidated", "Approved", "Archived",
]
EVIDENCE_STAGES = [
    "Requested", "Uploaded", "Validation Pending", "Approved",
    "Stale", "Refreshed", "Reused", "Archived",
]
OBSERVATION_STAGES = [
    "Open", "Assigned", "Under Review", "Remediation In Progress",
    "Pending Validation", "Closed", "Reopened",
]
REMEDIATION_STAGES = [
    "Planned", "In Progress", "Awaiting Validation", "Delayed", "Escalated", "Completed",
]
AUDIT_STAGES = [
    "Audit Scheduled", "Evidence Collection", "Auditor Review", "Observation Raised",
    "Revalidation", "Closure Pending", "Closed",
]
EXCEPTION_STATUSES = [
    "Active", "Expiring Soon", "Revalidation Required", "Expired", "Closed",
]

EVIDENCE_TYPES = [
    "Firewall Export", "MFA Report", "VA Scan", "PAM Report",
    "SIEM Logs", "CIS Benchmark", "SAST Report", "Penetration Test",
]
CONTROL_NAMES = {
    "PCI DSS": ["MFA Enforcement", "Firewall Segmentation", "Encryption at Rest", "Access Logging"],
    "DPSC": ["Consent Management", "Data Retention", "PII Inventory"],
    "OS Baselining": ["CIS Hardening", "Patch Compliance", "Tripwire Integrity"],
    "DB Baselining": ["Oracle Hardening", "DB Encryption", "Privileged Access Review"],
    "Nginx Baselining": ["TLS Configuration", "WAF Baseline", "Reverse Proxy Hardening"],
    "AppSec": ["SAST Coverage", "Dependency Scanning", "Secure SDLC Gate"],
    "VAPT": ["External VA Scan", "Pen-Test Remediation", "CVE Retest"],
    "CSITE": ["Access Review", "SIEM Use-Case", "Incident Response Drill"],
    "ITPP": ["DR Drill Evidence", "BCP Test", "Recovery Mapping"],
}
TEAMS = ["AppSec CoE", "Infrastructure", "Database Ops", "Compliance", "Internal Audit", "GRC"]
AUDITORS = ["Deloitte", "KPMG", "EY", "Internal Audit", "RBI Inspection"]
EXCEPTION_TYPES = ["Risk Acceptance", "Compensating Control", "Temporary Waiver", "TD Extension"]


def _seed(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def _pick(items: list, seed: str):
    return items[_seed(seed) % len(items)]


def _control_id(fw: str, idx: int) -> str:
    if fw == "AppSec":
        return f"AS-C-{10 + idx % 20}"
    if fw == "VAPT":
        return f"VAPT-EXT-{idx % 10 + 1:02d}"
    if fw == "OS Baselining":
        return f"OS-{idx % 15 + 1:02d}"
    if fw == "DB Baselining":
        return f"DB-SEC-{idx % 10 + 1:02d}"
    controls = FRAMEWORK_CONTROLS.get(fw, [])
    if controls:
        return controls[idx % len(controls)]
    return f"{fw[:3].upper()}-C-{idx + 1:02d}"


def _chain_id(idx: int) -> str:
    return f"LC-CHAIN-{idx:04d}"


def _filter(rows: list[dict], framework: str, application: str) -> list[dict]:
    out = rows
    if framework and framework != "All Frameworks":
        out = [r for r in out if r.get("framework") == framework]
    if application and application != "All Applications":
        out = [r for r in out if r.get("application") == application]
    return out


def build_control_lifecycle(count: int = 135) -> list[dict]:
    rows = []
    for idx in range(count):
        fw = ALL_FRAMEWORKS[idx % len(ALL_FRAMEWORKS)]
        app = LIFECYCLE_APPS[(idx + idx // len(ALL_FRAMEWORKS)) % len(LIFECYCLE_APPS)]
        s = _seed(f"ctrl|{idx}")
        cid = _control_id(fw, idx)
        cname = _pick(CONTROL_NAMES.get(fw, ["Control Requirement"]), f"cn|{idx}")
        stage = CONTROL_STAGES[s % len(CONTROL_STAGES)]
        rows.append({
            "chain_id": _chain_id(idx),
            "framework": fw,
            "application": app,
            "control_id": cid,
            "control_name": cname,
            "lifecycle_stage": stage,
            "validation": ["Pass", "Pending", "Fail", "Waived"][s % 4],
            "last_updated": f"2026-05-{(s % 24) + 1:02d}",
            "owner": owner_for(app),
            "risk": ["Low", "Medium", "High", "Critical"][s % 4],
        })
    return rows


def build_evidence_lifecycle(controls: list[dict], count: int = 175) -> list[dict]:
    rows = []
    for i in range(count):
        base = controls[i % len(controls)]
        s = _seed(f"ev|{i}")
        stage = EVIDENCE_STAGES[s % len(EVIDENCE_STAGES)]
        age = 5 + (s % 120)
        rows.append({
            "chain_id": base["chain_id"],
            "evidence_id": f"EV-{2000 + i:04d}",
            "framework": base["framework"],
            "application": base["application"],
            "control_id": base["control_id"],
            "control": base["control_id"],
            "evidence_type": _pick(EVIDENCE_TYPES, f"et|{i}"),
            "lifecycle_stage": stage,
            "uploaded_by": base["owner"],
            "age_days": age,
            "status": "Current" if stage in ("Approved", "Refreshed", "Reused") else ("Stale" if stage == "Stale" else "Pending"),
            "last_updated": f"2026-05-{(s % 24) + 1:02d}",
        })
    return rows


def build_observation_lifecycle(controls: list[dict], count: int = 110) -> list[dict]:
    rows = []
    for i in range(count):
        base = controls[i % len(controls)]
        s = _seed(f"obs|{i}")
        stage = OBSERVATION_STAGES[s % len(OBSERVATION_STAGES)]
        sev = ["Critical", "High", "Medium", "Low"][s % 4]
        open_days = 3 + (s % 90)
        rows.append({
            "chain_id": base["chain_id"],
            "observation_id": f"OBS-{3000 + i:04d}",
            "framework": base["framework"],
            "application": base["application"],
            "control_id": base["control_id"],
            "observation": f"{base['framework']} — {base['control_name']} gap on {base['application']}",
            "severity": sev,
            "stage": stage,
            "open_since": f"2026-0{(s % 4) + 2}-{(s % 20) + 1:02d}",
            "open_days": open_days,
            "owner": base["owner"],
            "sla": "Breached" if open_days > 60 else ("At Risk" if open_days > 30 else "On Track"),
        })
    return rows


def build_remediation_lifecycle(observations: list[dict], count: int = 95) -> list[dict]:
    rows = []
    for i in range(count):
        base = observations[i % len(observations)]
        s = _seed(f"rem|{i}")
        stage = REMEDIATION_STAGES[s % len(REMEDIATION_STAGES)]
        progress = min(100, 15 + (s % 85))
        if stage == "Completed":
            progress = 100
        rows.append({
            "chain_id": base["chain_id"],
            "remediation_id": f"REM-{4000 + i:04d}",
            "framework": base["framework"],
            "application": base["application"],
            "control_id": base.get("control_id", ""),
            "issue": base["observation"][:80],
            "team": _pick(TEAMS, f"tm|{i}"),
            "current_stage": stage,
            "eta": f"2026-06-{(s % 20) + 1:02d}",
            "progress_pct": progress,
            "risk": base["severity"],
        })
    return rows


def build_audit_lifecycle(count: int = 32) -> list[dict]:
    rows = []
    for i in range(count):
        fw = ALL_FRAMEWORKS[i % len(ALL_FRAMEWORKS)]
        s = _seed(f"aud|{i}")
        apps = [LIFECYCLE_APPS[s % len(LIFECYCLE_APPS)], LIFECYCLE_APPS[(s + 1) % len(LIFECYCLE_APPS)]]
        stage = AUDIT_STAGES[s % len(AUDIT_STAGES)]
        findings = s % 12
        completion = min(98, 40 + (s % 55))
        rows.append({
            "framework": fw,
            "application": apps[0],
            "audit_cycle": f"FY26-{fw[:4].upper()}-Q{(i % 4) + 1}",
            "applications": ", ".join(apps),
            "auditor": _pick(AUDITORS, f"au|{i}"),
            "stage": stage,
            "evidence_completion_pct": completion,
            "findings": findings,
            "closure_status": "Closed" if stage == "Closed" else ("Pending" if stage == "Closure Pending" else "In Progress"),
        })
    return rows


def build_exception_lifecycle(controls: list[dict], count: int = 65) -> list[dict]:
    rows = []
    for i in range(count):
        base = controls[i % len(controls)]
        s = _seed(f"exc|{i}")
        status = EXCEPTION_STATUSES[s % len(EXCEPTION_STATUSES)]
        rows.append({
            "chain_id": base["chain_id"],
            "exception_id": f"EXC-{5000 + i:04d}",
            "framework": base["framework"],
            "application": base["application"],
            "control_id": base["control_id"],
            "exception_type": _pick(EXCEPTION_TYPES, f"xt|{i}"),
            "approved_until": f"2026-0{7 + (s % 3)}-{(s % 25) + 1:02d}",
            "current_status": status,
            "owner": base["owner"],
        })
    return rows


def build_timeline_chains(controls: list[dict], evidence: list[dict], observations: list[dict], remediations: list[dict]) -> list[dict]:
    chains = []
    for ctrl in controls[:40]:
        cid = ctrl["chain_id"]
        ev = next((e for e in evidence if e["chain_id"] == cid), None)
        obs = next((o for o in observations if o["chain_id"] == cid), None)
        rem = next((r for r in remediations if r["chain_id"] == cid), None)
        steps = [
            {"stage": "mapped", "label": "Mapped", "date": ctrl["last_updated"], "owner": ctrl["owner"], "icon": "1"},
            {"stage": "evidence_requested", "label": "Evidence Requested", "date": ev["last_updated"] if ev else ctrl["last_updated"], "owner": ctrl["owner"], "icon": "2"},
            {"stage": "uploaded", "label": "Uploaded", "date": ev["last_updated"] if ev else ctrl["last_updated"], "owner": ev["uploaded_by"] if ev else ctrl["owner"], "icon": "3"},
        ]
        if ctrl["lifecycle_stage"] == "Failed" or (ev and ev["lifecycle_stage"] == "Validation Pending"):
            steps.append({"stage": "failed_validation", "label": "Failed Validation", "date": ctrl["last_updated"], "owner": ctrl["owner"], "icon": "!"})
        if rem:
            steps.append({"stage": "remediation", "label": "Remediation Opened", "date": rem["eta"], "owner": rem["team"], "icon": "4"})
        if ctrl["lifecycle_stage"] in ("Revalidated", "Approved"):
            steps.append({"stage": "revalidated", "label": "Revalidated", "date": ctrl["last_updated"], "owner": ctrl["owner"], "icon": "5"})
            steps.append({"stage": "approved", "label": "Approved", "date": ctrl["last_updated"], "owner": ctrl["owner"], "icon": "6"})
        chains.append({
            "chain_id": cid,
            "framework": ctrl["framework"],
            "application": ctrl["application"],
            "control_id": ctrl["control_id"],
            "title": f"{ctrl['control_id']} — {ctrl['control_name']}",
            "steps": steps,
            "observation": obs["observation"][:60] if obs else None,
        })
    return chains


def build_charts(
    evidence: list[dict],
    remediations: list[dict],
    audits: list[dict],
    exceptions: list[dict],
    framework: str = "All Frameworks",
) -> dict:
    ev = _filter(evidence, framework, "All Applications")
    rem = _filter(remediations, framework, "All Applications")
    aud = _filter(audits, framework, "All Applications")
    exc = _filter(exceptions, framework, "All Applications")

    aging = {"0-30 days": 0, "31-60 days": 0, "61-90 days": 0, ">90 days stale": 0}
    for e in ev:
        a = e.get("age_days", 30)
        if a <= 30:
            aging["0-30 days"] += 1
        elif a <= 60:
            aging["31-60 days"] += 1
        elif a <= 90:
            aging["61-90 days"] += 1
        else:
            aging[">90 days stale"] += 1

    by_fw_aging: dict[str, dict] = {}
    for e in ev:
        fw = e["framework"]
        by_fw_aging.setdefault(fw, {"0-30 days": 0, "31-60 days": 0, "61-90 days": 0, ">90 days stale": 0})
        a = e.get("age_days", 30)
        if a <= 30:
            by_fw_aging[fw]["0-30 days"] += 1
        elif a <= 60:
            by_fw_aging[fw]["31-60 days"] += 1
        elif a <= 90:
            by_fw_aging[fw]["61-90 days"] += 1
        else:
            by_fw_aging[fw][">90 days stale"] += 1

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    rem_velocity = []
    for i, m in enumerate(months):
        closed = len([r for r in rem if r["current_stage"] == "Completed"]) // 6 + i * 2
        rem_velocity.append({"month": m, "avg_days": max(8, 28 - i * 2), "closed": closed})

    stale_trend = [{"month": m, "count": max(2, len([e for e in ev if e.get("status") == "Stale"]) // 6 + i)} for i, m in enumerate(months)]

    audit_gantt = []
    for a in aud[:8]:
        audit_gantt.append({
            "label": a["audit_cycle"],
            "start": "2026-01-15",
            "evidence_done": "2026-03-01",
            "findings": "2026-04-10",
            "closure": "2026-05-20" if a["closure_status"] == "Closed" else "—",
            "stage": a["stage"],
        })

    exc_timeline = []
    for e in exc[:12]:
        exc_timeline.append({
            "exception_id": e["exception_id"],
            "control_id": e["control_id"],
            "status": e["current_status"],
            "until": e["approved_until"],
            "application": e["application"],
        })

    return {
        "evidence_aging": [{"band": k, "count": v} for k, v in aging.items()],
        "evidence_aging_by_framework": by_fw_aging,
        "remediation_velocity": rem_velocity,
        "stale_evidence_trend": stale_trend,
        "audit_gantt": audit_gantt,
        "exception_timeline": exc_timeline,
    }


def build_lifecycle_dataset(role: str = "owner") -> dict:
    from app.role_filter_scope import apply_role_scope

    controls = apply_role_scope(build_control_lifecycle(135), role)
    evidence = apply_role_scope(build_evidence_lifecycle(controls, 175), role)
    observations = apply_role_scope(build_observation_lifecycle(controls, 110), role)
    remediations = apply_role_scope(build_remediation_lifecycle(observations, 95), role)
    audits = build_audit_lifecycle(32)
    exceptions = apply_role_scope(build_exception_lifecycle(controls, 65), role)
    timelines = build_timeline_chains(controls, evidence, observations, remediations)
    return {
        "role": role,
        "controls": controls,
        "evidence": evidence,
        "observations": observations,
        "remediations": remediations,
        "audits": audits,
        "exceptions": exceptions,
        "timelines": timelines,
        "frameworks": ["All Frameworks"] + ALL_FRAMEWORKS,
        "applications": ["All Applications"] + LIFECYCLE_APPS,
    }


def build_lifecycle_dashboard(framework: str = "All Frameworks", application: str = "All Applications", role: str = "owner") -> dict:
    ds = build_lifecycle_dataset(role)
    controls = _filter(ds["controls"], framework, application)
    evidence = _filter(ds["evidence"], framework, application)
    observations = _filter(ds["observations"], framework, application)
    remediations = _filter(ds["remediations"], framework, application)
    audits = _filter(ds["audits"], framework, application)
    exceptions = _filter(ds["exceptions"], framework, application)
    timelines = [t for t in ds["timelines"] if (framework == "All Frameworks" or t["framework"] == framework) and (application == "All Applications" or t["application"] == application)]
    charts = build_charts(evidence, remediations, audits, exceptions, framework)
    total = len(controls) + len(evidence) + len(observations) + len(remediations)
    return {
        "controls": controls,
        "evidence": evidence,
        "observations": observations,
        "remediations": remediations,
        "audits": audits,
        "exceptions": exceptions,
        "timelines": timelines,
        "charts": charts,
        "kpis": [
            {"label": "Control Lifecycles", "value": len(controls), "tone": "primary"},
            {"label": "Evidence Records", "value": len(evidence), "tone": "info"},
            {"label": "Open Observations", "value": len([o for o in observations if o["stage"] not in ("Closed",)]), "tone": "warning"},
            {"label": "Active Remediations", "value": len([r for r in remediations if r["current_stage"] != "Completed"]), "tone": "danger"},
            {"label": "Audit Cycles", "value": len(audits), "tone": "success"},
            {"label": "Active Exceptions", "value": len([e for e in exceptions if e["current_status"] in ("Active", "Expiring Soon")]), "tone": "secondary"},
        ],
    }
