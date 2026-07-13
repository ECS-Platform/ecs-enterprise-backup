"""AI-driven application onboarding workflow simulator — deterministic per-app results."""

from __future__ import annotations

import hashlib
from typing import Any

ALL_FRAMEWORKS = [
    "PCI DSS",
    "DPSC",
    "OS Baselining",
    "DB Baselining",
    "Nginx Baselining",
    "AppSec",
    "VAPT",
    "CSITE",
    "ITPP",
]

FRAMEWORK_META: dict[str, dict[str, Any]] = {
    "PCI DSS": {
        "prefix": "PCI",
        "base_controls": 18,
        "risk_bias": 0.15,
        "controls": [
            ("PCI-7.2", "CDE access restriction", "Firewall / segmentation"),
            ("PCI-8.3", "MFA for privileged access", "CyberArk PAM"),
            ("PCI-10.6", "Log review & SIEM monitoring", "Splunk SIEM"),
            ("PCI-11.3", "External vulnerability scan", "Qualys VA"),
        ],
    },
    "DPSC": {
        "prefix": "DP",
        "base_controls": 12,
        "risk_bias": 0.12,
        "controls": [
            ("DP-C-04", "Consent management", "OneTrust"),
            ("DP-C-07", "Data retention policy", "SharePoint"),
            ("DP-C-09", "PII inventory mapping", "ServiceNow CMDB"),
        ],
    },
    "OS Baselining": {
        "prefix": "OSB",
        "base_controls": 14,
        "risk_bias": 0.1,
        "controls": [
            ("OSB-11", "Linux hardening baseline", "Tripwire"),
            ("OSB-14", "Patch compliance", "CrowdStrike"),
            ("OSB-18", "CIS benchmark attestation", "Qualys PC"),
        ],
    },
    "DB Baselining": {
        "prefix": "DBB",
        "base_controls": 11,
        "risk_bias": 0.14,
        "controls": [
            ("DBB-03", "DB encryption at rest", "Prisma Cloud"),
            ("DBB-06", "Privileged DB access review", "ServiceNow"),
            ("DBB-09", "Audit logging enabled", "Splunk SIEM"),
        ],
    },
    "Nginx Baselining": {
        "prefix": "NGX",
        "base_controls": 9,
        "risk_bias": 0.11,
        "controls": [
            ("NGX-02", "TLS configuration hardening", "Prisma Cloud"),
            ("NGX-05", "WAF rule baseline", "F5 ASM"),
            ("NGX-08", "Reverse proxy access logs", "Splunk SIEM"),
        ],
    },
    "AppSec": {
        "prefix": "APPSEC",
        "base_controls": 13,
        "risk_bias": 0.18,
        "controls": [
            ("APPSEC-9", "SAST integration gate", "Checkmarx"),
            ("APPSEC-12", "Dependency scanning", "SonarQube"),
            ("APPSEC-15", "Secure SDLC attestation", "Jira"),
        ],
    },
    "VAPT": {
        "prefix": "VAPT",
        "base_controls": 10,
        "risk_bias": 0.16,
        "controls": [
            ("VAPT-4", "External VA scan cadence", "Qualys VA"),
            ("VAPT-7", "Pen-test remediation tracking", "ServiceNow GRC"),
            ("VAPT-9", "Critical finding SLA", "Jira"),
        ],
    },
    "CSITE": {
        "prefix": "CS",
        "base_controls": 15,
        "risk_bias": 0.13,
        "controls": [
            ("CS-C-03", "Access review certification", "ServiceNow GRC"),
            ("CS-C-05", "Log retention compliance", "Splunk SIEM"),
            ("CS-C-08", "Incident response readiness", "ServiceNow ITSM"),
        ],
    },
    "ITPP": {
        "prefix": "ITPP",
        "base_controls": 12,
        "risk_bias": 0.1,
        "controls": [
            ("ITPP-DR-02", "DR drill evidence", "SharePoint"),
            ("ITPP-BCP-05", "BCP test attestation", "ServiceNow GRC"),
            ("ITPP-REC-03", "Recovery time objective mapping", "CMDB"),
        ],
    },
}

EVIDENCE_SOURCES = [
    "SharePoint",
    "ServiceNow",
    "SonarQube",
    "Prisma",
    "Checkmarx",
    "Jira",
    "Tripwire",
    "CMDB",
]

WORKFLOW_STEPS = [
    "Loading application data",
    "Loading CMDB data",
    "Populating ECS metadata",
    "Loading object-storage files",
    "Loading relational metadata",
    "Loading configuration files",
    "Mapping frameworks and controls",
    "Onboarding complete",
]

# Legacy alias — older UI/tests referenced the previous step labels.
_LEGACY_WORKFLOW_STEPS = [
    "Discovering application metadata",
    "CMDB sync",
    "Infra fingerprinting",
    "Security tool mapping",
    "Framework applicability analysis",
    "Control inheritance mapping",
    "Evidence source registration",
    "Compliance readiness estimation",
]

_DEMO_REMAINING_APPLICATIONS = 52
_onboarder_running: str | None = None
_onboarder_failed_count = 0
_onboarder_queue_offset = 0

_DEMO_QUEUE_NAMES = [
    "Trade Finance Hub", "Corporate Lending Portal", "Digital Onboarding Suite",
    "FX Trading Platform", "Securities Settlement", "Branch Teller System",
    "Contact Center CRM", "HR Self-Service", "Vendor Portal", "Data Lake Ingest",
    "Open Banking API", "Regulatory Reporting Hub", "Collateral Management",
    "Credit Scoring Engine", "Document Imaging", "E-Statement Portal",
    "Fixed Deposit System", "Insurance Cross-Sell", "KYC Verification Hub",
    "Liquidity Management", "Merchant Acquiring", "NEFT RTGS Gateway",
    "Portfolio Analytics", "Reconciliation Engine", "Risk Data Warehouse",
    "SWIFT Messaging Hub", "Tax Reporting Suite", "Virtual Account Platform",
]

REMEDIATION_TEMPLATES = [
    "MFA evidence missing for privileged access path",
    "DR drill evidence stale — last test > 90 days",
    "SAST token expired — Checkmarx integration auth failed",
    "Linux patch baseline outdated on {count} hosts",
    "External VAPT overdue — scan window exceeded",
    "DB retention controls incomplete for PII schema",
    "Consent log export gap in mobile channel",
    "WAF baseline drift detected on ingress tier",
    "Privileged access review not signed for Q2",
    "SIEM use-case not mapped for new application tier",
]


def _seed(app: str, salt: str) -> int:
    digest = hashlib.sha256(f"{app.strip().lower()}|{salt}".encode()).hexdigest()
    return int(digest[:8], 16)


def _cmdb_source_mode() -> str:
    try:
        from modules.operations.integrations import servicenow_cmdb
        return "live" if servicenow_cmdb.is_configured() else "simulated"
    except Exception:  # noqa: BLE001
        return "simulated"


def _progress_step_modes() -> list[dict[str, str]]:
    cmdb = _cmdb_source_mode()
    return [
        {"label": "Loading application data", "mode": "simulated"},
        {"label": "Loading CMDB data", "mode": cmdb},
        {"label": "Populating ECS metadata", "mode": "simulated"},
        {"label": "Loading object-storage files", "mode": "simulated"},
        {"label": "Loading relational metadata", "mode": "simulated"},
        {"label": "Loading configuration files", "mode": "simulated"},
        {"label": "Mapping frameworks and controls", "mode": "simulated"},
        {"label": "Onboarding complete", "mode": "simulated"},
    ]


def _frameworks_for_payload(payload: dict[str, Any]) -> list[str]:
    """Apply in-scope toggles — excludes frameworks marked out of scope."""
    scope_map = {
        "PCI DSS": payload.get("pci_dss_in_scope", "Yes"),
        "DPSC": payload.get("dpsc_in_scope", "Yes"),
        "CSITE": payload.get("rbi_csite_in_scope", "Yes"),
        "ITPP": payload.get("internal_audit_in_scope", "Yes"),
    }
    out: list[str] = []
    for fw in ALL_FRAMEWORKS:
        flag = scope_map.get(fw, "Yes")
        if str(flag).lower() in ("yes", "true", "1", "y"):
            out.append(fw)
        elif fw not in scope_map:
            out.append(fw)
    return out or list(ALL_FRAMEWORKS)


def _next_queue_application() -> str:
    global _onboarder_queue_offset
    pool = _DEMO_QUEUE_NAMES
    idx = _onboarder_queue_offset % max(len(pool), 1)
    _onboarder_queue_offset += 1
    base = pool[idx]
    suffix = (_onboarder_queue_offset // len(pool)) + 1
    return base if suffix <= 1 else f"{base} #{suffix}"


def build_application_onboarder_dashboard(onboarded: list[str] | None = None) -> dict[str, Any]:
    """Scheduler summary for the Application Onboarder — demo queue when CMDB is not live."""
    from app import ecs_state

    onboarded = onboarded if onboarded is not None else ecs_state.onboarded_applications
    completed = len(onboarded)
    remaining = _DEMO_REMAINING_APPLICATIONS
    running = 1 if _onboarder_running else 0
    failed = _onboarder_failed_count
    total = completed + remaining + running + failed
    cmdb_mode = _cmdb_source_mode()

    app_rows: list[dict[str, Any]] = []
    if _onboarder_running:
        app_rows.append({
            "application": _onboarder_running,
            "status": "Running",
            "progress_pct": 45,
            "owner": "Application Onboarder",
            "stage": "Mapping frameworks and controls",
        })
    for i, name in enumerate(onboarded[-5:]):
        app_rows.append({
            "application": name,
            "status": "Completed",
            "progress_pct": 100,
            "owner": "Application Onboarder",
            "stage": "Onboarding complete",
        })
    for i in range(min(8, remaining)):
        app_rows.append({
            "application": _DEMO_QUEUE_NAMES[i % len(_DEMO_QUEUE_NAMES)],
            "status": "Queued",
            "progress_pct": 0,
            "owner": "—",
            "stage": "Pending",
        })

    return {
        "cmdb_mode": cmdb_mode,
        "simulated": cmdb_mode != "live",
        "disclaimer": (
            "Deterministic demo queue (52 remaining applications). "
            "No live bank network scan — CMDB steps are simulated unless ServiceNow CMDB is configured."
            if cmdb_mode != "live"
            else "ServiceNow CMDB connector configured — CMDB load steps use approved integration transport."
        ),
        "summary": {
            "total_applications": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "remaining": remaining,
        },
        "applications": app_rows,
    }


def run_application_onboarder() -> dict[str, Any]:
    """Process one queued application through the existing onboarding simulator."""
    global _onboarder_running, _DEMO_REMAINING_APPLICATIONS, _onboarder_failed_count

    if _DEMO_REMAINING_APPLICATIONS <= 0:
        return {
            "ok": True,
            "message": "Onboarder queue empty (demo)",
            "dashboard": build_application_onboarder_dashboard(),
        }

    app_name = _next_queue_application()
    _onboarder_running = app_name
    try:
        result = simulate_onboarding({
            "application_name": app_name,
            "owner": "Application Onboarder",
            "business_unit": "Operations & IT",
            "environment": "PROD",
        })
        from app import ecs_state
        if app_name not in ecs_state.onboarded_applications:
            ecs_state.onboarded_applications.append(app_name)
        _DEMO_REMAINING_APPLICATIONS = max(0, _DEMO_REMAINING_APPLICATIONS - 1)
        return {
            "ok": True,
            "processed": app_name,
            "readiness_pct": result.get("overall_readiness"),
            "result": result,
            "dashboard": build_application_onboarder_dashboard(),
        }
    except Exception as exc:  # noqa: BLE001
        _onboarder_failed_count += 1
        _DEMO_REMAINING_APPLICATIONS = max(0, _DEMO_REMAINING_APPLICATIONS - 1)
        return {
            "ok": False,
            "processed": app_name,
            "error": type(exc).__name__,
            "dashboard": build_application_onboarder_dashboard(),
        }
    finally:
        _onboarder_running = None


def _pick(items: list, app: str, salt: str):
    return items[_seed(app, salt) % len(items)]


def _risk_label(score: float) -> str:
    if score >= 0.35:
        return "High"
    if score >= 0.2:
        return "Medium"
    return "Low"


def simulate_onboarding(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate realistic onboarding results unique to application name + metadata."""
    app_name = (payload.get("application_name") or payload.get("application") or "New Application").strip()
    if not app_name:
        app_name = "New Application"

    owner = (payload.get("owner") or _pick(
        ["R. Mehta", "A. Sharma", "V. Rao", "K. Iyer", "S. Banerjee"], app_name, "owner"
    )).strip()
    business_unit = payload.get("business_unit") or _pick(
        ["Retail Banking", "Corporate Banking", "Wealth Management", "Digital Channels", "Operations & IT"],
        app_name,
        "bu",
    )
    environment = payload.get("environment") or _pick(["PROD", "UAT", "DR"], app_name, "env")
    criticality = (
        payload.get("customer_criticality")
        or payload.get("criticality")
        or _pick(["High", "Medium", "Low"], app_name, "crit")
    )
    internet_facing = payload.get("internet_facing") or _pick(["Yes", "No"], app_name, "inet")
    hosting = payload.get("hosting") or _pick(["Cloud", "On-Prem", "Hybrid"], app_name, "host")
    auth_type = payload.get("auth_type") or _pick(
        ["SAML SSO", "OAuth 2.0", "LDAP + MFA", "Certificate-based"], app_name, "auth"
    )
    data_class = payload.get("data_classification") or _pick(
        ["Restricted", "Confidential", "Internal"], app_name, "class"
    )
    customer_facing = payload.get("customer_facing") or _pick(["Yes", "No"], app_name, "cust")

    metadata = {
        "application_name": app_name,
        "business_unit": business_unit,
        "owner": owner,
        "environment": environment,
        "criticality": criticality,
        "customer_criticality": criticality,
        "customer_facing": customer_facing,
        "internet_facing": internet_facing,
        "hosting": hosting,
        "auth_type": auth_type,
        "data_classification": data_class,
        "pci_dss_in_scope": payload.get("pci_dss_in_scope", "Yes"),
        "dpsc_in_scope": payload.get("dpsc_in_scope", "Yes"),
        "rbi_csite_in_scope": payload.get("rbi_csite_in_scope", "Yes"),
        "internal_audit_in_scope": payload.get("internal_audit_in_scope", "Yes"),
        "dr_required": payload.get("dr_required", "Yes"),
        "backup_required": payload.get("backup_required", "Yes"),
        "database_technology": payload.get("database_technology")
        or _pick(["Oracle", "PostgreSQL", "SQL Server", "MongoDB"], app_name, "db"),
        "middleware_technology": payload.get("middleware_technology")
        or _pick(["WebLogic", "JBoss", "Tomcat", "IIS", "Nginx"], app_name, "mw"),
        "object_storage_location": payload.get("object_storage_location")
        or _pick(["S3 / Azure Blob", "SharePoint", "On-prem NAS", "GCS bucket"], app_name, "obj"),
        "cmdb_identifier": payload.get("cmdb_identifier")
        or f"CI-{_seed(app_name, 'cmdb') % 900000 + 100000}",
    }

    active_frameworks = _frameworks_for_payload(payload)
    framework_results: list[dict[str, Any]] = []
    discovered_controls: list[dict[str, Any]] = []
    total_discovered = 0
    total_implemented = 0
    total_missing = 0
    total_failed = 0
    total_reuse = 0
    total_sources = 0

    crit_mult = {"High": 1.15, "Medium": 1.0, "Low": 0.85}.get(criticality, 1.0)
    inet_mult = 1.1 if internet_facing == "Yes" else 0.95

    for fw in active_frameworks:
        meta = FRAMEWORK_META[fw]
        base = meta["base_controls"]
        s = _seed(app_name, fw)
        discovered = base + (s % 7) - 2
        discovered = max(6, min(28, int(discovered * crit_mult * inet_mult)))

        impl_ratio = 0.62 + ((s >> 4) % 24) / 100
        if criticality == "High":
            impl_ratio -= 0.03
        implemented = max(1, min(discovered - 1, int(discovered * impl_ratio)))
        failed = max(0, min(3, (s % 4) if (s % 3) == 0 else (s % 2)))
        missing = max(0, discovered - implemented - failed)
        inherited = max(0, min(6, (s % 5) + 1))
        reuse = max(0, min(5, (s >> 8) % 6))
        sources = max(2, min(8, 3 + (s % 6)))
        readiness = round((implemented / discovered) * 100 - failed * 2 + min(3, reuse * 0.6), 1)
        readiness = max(68, min(94, readiness))
        risk_score = meta["risk_bias"] + (failed / max(discovered, 1)) * 0.4 + (missing / max(discovered, 1)) * 0.25
        if criticality == "High":
            risk_score += 0.05

        framework_results.append({
            "framework": fw,
            "applicable_controls": discovered,
            "implemented": implemented,
            "missing": missing,
            "failed": failed,
            "inherited": inherited,
            "reusable_evidence": reuse,
            "evidence_sources": sources,
            "readiness_pct": readiness,
            "risk": _risk_label(risk_score),
        })

        total_discovered += discovered
        total_implemented += implemented
        total_missing += missing
        total_failed += failed
        total_reuse += reuse
        total_sources += sources

        for ctrl_id, ctrl_name, integration in meta["controls"]:
            cs = _seed(app_name, f"{fw}:{ctrl_id}")
            states = ["Implemented", "Missing", "Failed validation", "Pending scan", "Inherited"]
            weights = [implemented, missing, failed, missing // 2 + 1, inherited]
            idx = cs % sum(max(1, w) for w in weights)
            cumulative = 0
            state = states[0]
            for i, w in enumerate(weights):
                cumulative += max(1, w)
                if idx < cumulative:
                    state = states[i]
                    break

            evidence_states = ["Available", "Missing", "Stale", "Partial"]
            ev_state = evidence_states[cs % 4] if state != "Implemented" else _pick(
                ["Available", "Partial"], app_name, ctrl_id
            )

            discovered_controls.append({
                "control_id": ctrl_id,
                "control_name": ctrl_name,
                "framework": fw,
                "application": app_name,
                "owner": owner,
                "implementation_state": state,
                "evidence_availability": ev_state,
                "integration_source": integration,
            })

    overall_readiness = round(
        sum(f["readiness_pct"] for f in framework_results) / len(framework_results), 1
    )

    evidence_sources = []
    for src in EVIDENCE_SOURCES:
        ss = _seed(app_name, src)
        if ss % 11 == 0:
            status = "Failed authentication"
        elif ss % 5 == 0:
            status = "Partially synced"
        else:
            status = "Synced successfully"
        evidence_sources.append({
            "source": src,
            "status": status,
            "records": 12 + (ss % 180),
            "last_sync": f"2026-05-{(ss % 20) + 1:02d} {(ss % 12) + 8:02d}:{ss % 60:02d} UTC",
        })

    remediation: list[str] = []
    used: set[str] = set()
    for i in range(5):
        tpl = REMEDIATION_TEMPLATES[(_seed(app_name, f"rem{i}") % len(REMEDIATION_TEMPLATES))]
        host_count = 3 + (_seed(app_name, f"hc{i}") % 12)
        msg = tpl.format(count=host_count)
        if msg not in used:
            used.add(msg)
            remediation.append(msg)

    high_risk_controls = [c for c in discovered_controls if c["implementation_state"] in (
        "Missing", "Failed validation", "Pending scan"
    )][:3]
    insight_risks = [f"{c['control_id']} — {c['control_name']} ({c['implementation_state'].lower()})"
                     for c in high_risk_controls]
    if not insight_risks:
        insight_risks = ["No critical blockers — schedule baseline scan within 14 days"]

    copilot = {
        "headline": (
            f"New application '{app_name}' is {overall_readiness:.0f}% audit ready across "
            f"{len(active_frameworks)} frameworks."
        ),
        "risks": insight_risks,
        "recommendations": [
            "Trigger first evidence collection for missing controls",
            "Schedule baseline scan within 7 days for internet-facing tier" if internet_facing == "Yes"
            else "Map DR/BCP evidence sources before production sign-off",
            f"Assign control owners in {business_unit} before audit window",
        ],
    }

    kpis = {
        "frameworks_onboarded": len(active_frameworks),
        "controls_discovered": total_discovered,
        "controls_implemented": total_implemented,
        "controls_missing": total_missing,
        "failed_validations": total_failed,
        "reusable_evidence_mappings": total_reuse,
        "readiness_score": overall_readiness,
        "evidence_sources_connected": len([e for e in evidence_sources if e["status"] == "Synced successfully"]),
    }

    return {
        "metadata": metadata,
        "workflow_steps": WORKFLOW_STEPS,
        "progress_steps": _progress_step_modes(),
        "cmdb_mode": _cmdb_source_mode(),
        "framework_results": framework_results,
        "kpis": kpis,
        "discovered_controls": discovered_controls,
        "evidence_sources": evidence_sources,
        "remediation_gaps": remediation,
        "copilot_insights": copilot,
        "overall_readiness": overall_readiness,
        "session_id": hashlib.md5(f"{app_name}:{owner}".encode()).hexdigest()[:12],
    }


def export_onboarding_summary(result: dict[str, Any]) -> str:
    """Plain-text onboarding package for download."""
    meta = result["metadata"]
    lines = [
        "ECS APPLICATION ONBOARDING SUMMARY",
        "=" * 42,
        f"Application: {meta['application_name']}",
        f"Business Unit: {meta['business_unit']}",
        f"Owner: {meta['owner']}",
        f"Environment: {meta['environment']} | Criticality: {meta['criticality']}",
        f"Hosting: {meta['hosting']} | Internet Facing: {meta['internet_facing']}",
        f"Overall Readiness: {result['overall_readiness']}%",
        "",
        "FRAMEWORK RESULTS",
        "-" * 42,
    ]
    for f in result["framework_results"]:
        lines.append(
            f"{f['framework']}: {f['applicable_controls']} applicable | "
            f"{f['implemented']} impl | {f['missing']} missing | "
            f"{f['failed']} failed | {f['readiness_pct']}% ready | Risk: {f['risk']}"
        )
    lines.extend(["", "IMMEDIATE GAPS", "-" * 42])
    for g in result["remediation_gaps"]:
        lines.append(f"• {g}")
    lines.extend(["", "Generated by ECS Onboarding Simulator"])
    return "\n".join(lines)


def recent_onboarding_suggestions(onboarded: list[str]) -> list[str]:
    """Autocomplete suggestions — recently onboarded + common banking apps."""
    defaults = [
        "WealthX Portal",
        "Trade Finance Hub",
        "Corporate Lending Portal",
        "Digital Onboarding Suite",
        "Wealth Portal",
        "Mobile Banking",
        "UPI",
        "Treasury",
        "Loan Origination",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for name in list(reversed(onboarded)) + defaults:
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out[:12]
