"""Runtime enrichment of relational governance graphs — bulk banking-realistic mock data."""

from __future__ import annotations

import hashlib
from typing import Any

from modules.governance.engines.governance_relational_model import APP_OWNERS, _owner, get_framework_graph
from modules.frameworks.engines.framework_catalog import resolve_framework_name

CORE_APPS = ["Net Banking", "Mobile Banking", "Payments"]

LIFECYCLES = ["Approved", "Pending Review", "Rejected", "Draft", "Expired"]
EV_TYPES = {
    "AppSec": ["SAST Report", "DAST Report", "Secret Scan", "SCA Report", "Policy", "Pipeline Gate"],
    "VAPT": ["Pen-Test Report", "Retest Report", "VA Scan", "WAF Export", "Remediation Proof"],
    "PCI DSS": ["Firewall Export", "MFA Report", "SIEM Export", "VA Report", "PAM Export", "Segmentation Test"],
    "OS Baselining": ["CIS Scan", "Patch Report", "Integrity Scan", "Hardening Baseline"],
    "DB Baselining": ["TDE Report", "Audit Trail Export", "Backup Validation", "Access Review"],
    "Nginx Baselining": ["TLS Config", "Certificate Report", "Cipher Suite Export", "Proxy Config"],
    "CSITE": ["Access Review", "Audit Sign-off", "Observation Closure", "Log Retention Proof"],
    "DPSC": ["Consent Log", "Retention Policy", "PII Masking Report", "DSR Export"],
    "ITPP": ["Change Record", "Restore Test", "DR Drill Report", "CAB Approval", "Backup Report"],
}

INTEGRATION_SOURCES = {
    "AppSec": ["SonarQube Enterprise", "Checkmarx SAST", "SharePoint", "Jira Security Remediation"],
    "VAPT": ["Qualys VMDR", "SharePoint", "Jira Security Remediation", "Burp Enterprise"],
    "PCI DSS": ["CyberArk PAM", "Splunk SIEM", "SharePoint", "ServiceNow GRC"],
    "OS Baselining": ["Tripwire Enterprise", "CrowdStrike Falcon", "SharePoint"],
    "DB Baselining": ["Oracle Enterprise Manager", "SharePoint", "ServiceNow GRC"],
    "Nginx Baselining": ["Venafi", "F5 WAF", "SharePoint"],
    "CSITE": ["ServiceNow GRC", "Splunk SIEM", "SharePoint"],
    "DPSC": ["OneTrust", "SharePoint", "Confluence"],
    "ITPP": ["ServiceNow ITSM", "Veeam Backup", "SharePoint"],
}

PREFIX_BY_FW: dict[str, str] = {
    "AppSec": "AS-C", "VAPT": "VP-C", "PCI DSS": "PCI", "OS Baselining": "OS-C",
    "DB Baselining": "DB-C", "Nginx Baselining": "NGX-C", "CSITE": "CS-C",
    "DPSC": "DP-C", "ITPP": "IT-C",
}

RAF_TYPES = [
    "MFA gap waiver", "Patch window breach", "Encryption deferral", "Access review extension",
    "Consent refresh deferral", "Network segmentation exception", "Certificate renewal deferral",
    "Restore test extension", "SAST gate waiver", "Log retention extension",
]


def _seed(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def _existing_ids(items: list[dict], key: str = "evidence_id") -> set[str]:
    return {i[key] for i in items if key in i}


def _resolve_control_id(
    controls: list[dict[str, Any]],
    *,
    requested_control_id: str = "",
    requested_control_name: str = "",
    application: str = "",
    fallback_index: int = 0,
) -> tuple[str, str]:
    if not controls:
        return requested_control_id or "—", requested_control_name or "—"
    for c in controls:
        if requested_control_id and c.get("control_id") == requested_control_id:
            return c.get("control_id", "—"), c.get("control_name", c.get("control", "—"))
    if requested_control_name:
        rn = "".join(ch.lower() for ch in requested_control_name if ch.isalnum())
        for c in controls:
            cname = str(c.get("control_name", c.get("control", "")))
            cn = "".join(ch.lower() for ch in cname if ch.isalnum())
            if rn and (rn == cn or rn in cn):
                return c.get("control_id", "—"), c.get("control_name", c.get("control", "—"))
    if application:
        app_controls = [c for c in controls if c.get("application") == application]
        if app_controls:
            c = app_controls[fallback_index % len(app_controls)]
            return c.get("control_id", "—"), c.get("control_name", c.get("control", "—"))
    c = controls[fallback_index % len(controls)]
    return c.get("control_id", "—"), c.get("control_name", c.get("control", "—"))


def enrich_evidence(framework: str, existing: list[dict], controls: list[dict]) -> list[dict]:
    """Ensure 7–8 evidence rows per core app."""
    out = list(existing)
    seen = _existing_ids(out)
    types = EV_TYPES.get(framework, ["Policy", "Scan Report"])
    sources = INTEGRATION_SOURCES.get(framework, ["SharePoint"])
    prefix = PREFIX_BY_FW.get(framework, "EV")
    fw_tag = prefix if prefix != "EV" else framework.replace(" ", "")[:4].upper()

    for app in CORE_APPS:
        app_evs = [e for e in out if e.get("application") == app]
        target = 8
        for n in range(len(app_evs), target):
            idx = n + 1
            eid = f"EV-{fw_tag}-{app[:3].upper().replace(' ', '')}-{idx:02d}"
            if eid in seen:
                continue
            ctrl = controls[(n % max(len(controls), 1))] if controls else {}
            cid, cname = _resolve_control_id(controls, requested_control_id=ctrl.get("control_id", ""), application=app, fallback_index=n)
            lc = LIFECYCLES[_seed(f"{eid}lc", 0, len(LIFECYCLES) - 1)]
            val = "Validated" if lc == "Approved" else ("Failed" if lc == "Rejected" else "Warning")
            out.append({
                "evidence_id": eid,
                "name": f"{types[n % len(types)]} — {app} {framework} Q2-2026 #{idx}",
                "application": app,
                "control_id": cid,
                "control_name": cname,
                "uploaded_by": _owner(app),
                "type": types[n % len(types)],
                "lifecycle": lc,
                "validation": val,
                "expiry": f"2026-{6 + (n % 4):02d}-{(10 + n):02d}",
                "audit_cycle": "Q2 2026" if n % 2 == 0 else "H1 2026",
                "linked_findings": "—" if lc != "Rejected" else f"{fw_tag[:2]}-F-{idx:03d}",
                "reuse_eligible": lc == "Approved" and n % 3 == 0,
                "source_integration": sources[n % len(sources)],
            })
            seen.add(eid)
    return out


def _sync_evidence_workflow_fields(ev: dict, framework: str, controls: list[dict], findings: list[dict]) -> dict:
    """Attach control name, observation linkage, and live workflow state for repository UI."""
    from app import ecs_state
    from modules.shared.services.evidence_workflow_engine import observation_id_for, resolve_state

    fw = resolve_framework_name(framework)
    cid = ev.get("control_id", "")
    cname = ev.get("control_name") or ev.get("control") or ""
    if not cname and cid:
        for c in controls:
            if c.get("control_id") == cid:
                cname = c.get("control_name", cid)
                break
        if not cname:
            cname = cid
    ev["control_name"] = cname
    ev["control"] = cname
    ev["framework"] = fw
    obs = ev.get("linked_findings", "")
    if not obs or obs == "—":
        for f in findings:
            if f.get("linked_evidence") == ev.get("evidence_id") or f.get("linked_control") == cid:
                obs = f.get("finding_id", "")
                break
    if not obs or obs == "—":
        obs = observation_id_for(fw, cname, cid)
    ev["observation_id"] = obs
    if obs in ecs_state.closed_observations:
        ev["observation_status"] = "Closed"
    elif ev.get("lifecycle") == "Approved":
        ev["observation_status"] = "Pending Closure"
    elif ev.get("lifecycle") == "Rejected":
        ev["observation_status"] = "Open"
    else:
        ev["observation_status"] = ev.get("observation_status", "Open")
    key = ecs_state.control_key(fw, cname or cid)
    wf = resolve_state(key, framework=fw, control=cname, control_id=cid)
    ev["lifecycle_state"] = wf.get("owner_label", ev.get("lifecycle", "Draft"))
    ev["workflow_chip"] = wf.get("chip_text", "DRAFT")
    ev["workflow_code"] = wf.get("code", "draft")
    ev["auditor_approved"] = wf.get("code") == "approved"
    ev["reviewer"] = ev.get("reviewer") or ecs_state.approved_controls.get(key, {}).get("approved_by", "")
    if key in ecs_state.approved_controls:
        appr = ecs_state.approved_controls[key]
        if isinstance(appr, dict):
            ev["review_timestamp"] = appr.get("approved_at", "")
            ev["lifecycle"] = "Approved"
    return ev


def ensure_control_linked_evidence(framework: str, evidence: list[dict], controls: list[dict], findings: list[dict]) -> list[dict]:
    """Every control with evidence_id MUST have a repository row — synthesize if missing."""
    out = list(evidence)
    seen = {e.get("evidence_id") for e in out if e.get("evidence_id")}
    wf_to_lc = {"Approved": "Approved", "Rejected": "Rejected", "Pending Review": "Pending Review", "Draft": "Draft"}
    val_map = {"PASS": "Validated", "FAIL": "Failed", "WARN": "Warning"}

    for ctrl in controls:
        eid = ctrl.get("evidence_id", "")
        if not eid or eid in seen:
            continue
        cid = ctrl.get("control_id", "")
        obs = "—"
        for f in findings:
            if f.get("linked_control") == cid or f.get("linked_evidence") == eid:
                obs = f.get("finding_id", obs)
                break
        if obs == "—" and cid:
            fw_slug = framework.replace(" ", "")[:6].upper()
            obs = f"OBS-{fw_slug}-{cid.replace('.', '')}"
        ev_name = ctrl.get("evidence_name") or f"{ctrl.get('control_name', cid)} attestation Q2-2026"
        wf = ctrl.get("workflow", "Pending Review")
        out.append({
            "evidence_id": eid,
            "name": ev_name,
            "application": ctrl.get("application", "Net Banking"),
            "control_id": cid,
            "control_name": ctrl.get("control_name", cid),
            "uploaded_by": ctrl.get("owner", "App Owner"),
            "type": "Policy",
            "lifecycle": wf_to_lc.get(wf, "Pending Review"),
            "validation": val_map.get(ctrl.get("validation", ""), "Warning"),
            "expiry": "2026-08-31",
            "audit_cycle": ctrl.get("audit_cycle", "Q2 2026"),
            "linked_findings": obs,
            "reuse_eligible": wf == "Approved",
            "source_integration": "SharePoint",
            "uploaded_at": "2026-05-20 10:00 UTC",
        })
        seen.add(eid)
    return out


def enrich_observations(framework: str, existing: list[dict], controls: list[dict]) -> list[dict]:
    """Expand open observations + add recently closed."""
    out = list(existing)
    seen = {f["finding_id"] for f in out}
    fw_tag = framework.replace(" ", "").replace("Baselining", "")[:3].upper()
    obs_templates = [
        ("Stale evidence — quarterly refresh overdue", "Medium", "Open"),
        ("Control validation failed — remediation pending", "High", "Open"),
        ("Integration sync gap — evidence not auto-collected", "Medium", "In Progress"),
        ("Repeat observation from prior audit cycle", "High", "Open"),
        ("New auditor observation — policy attestation gap", "Critical", "Open"),
        ("Observation closure pending owner sign-off", "Medium", "Remediation"),
        ("MFA enrollment incomplete for privileged accounts", "High", "Open"),
        ("Evidence rejected — resubmission required", "High", "Open"),
    ]
    closed_templates = [
        ("Prior quarter access review — closed with compensating control", "Medium", "Closed", "2026-05-10"),
        ("Patch remediation verified — observation closed", "High", "Closed", "2026-05-18"),
        ("SIEM use-case gap remediated — auditor accepted", "Medium", "Closed", "2026-05-20"),
    ]
    apps_pool = CORE_APPS + [a["name"] for a in []]
    all_apps = list(dict.fromkeys(CORE_APPS + ["UPI", "Card Platform", "Treasury", "Internet Banking"]))
    sources = INTEGRATION_SOURCES.get(framework, ["ServiceNow GRC"])

    for i, (obs, sev, status) in enumerate(obs_templates):
        fid = f"{fw_tag}-F-{100 + i:03d}"
        if fid in seen:
            continue
        app = all_apps[i % len(all_apps)]
        ctrl = controls[i % max(len(controls), 1)] if controls else {}
        out.append({
            "finding_id": fid,
            "application": app,
            "observation": obs,
            "severity": sev,
            "source": sources[i % len(sources)],
            "integration": sources[i % len(sources)],
            "open_since": f"2026-0{(i % 4) + 4}-{(10 + i):02d}",
            "linked_control": ctrl.get("control_id", "—"),
            "linked_evidence": f"EV-{fw_tag}-{app[:3].upper()[:3]}-01",
            "owner": _owner(app),
            "status": status,
            "aging_days": 5 + i * 3,
            "escalation": "Audit Committee" if sev == "Critical" else "—",
            "auditor_notes": f"{framework} scope observation",
            "closure_dependency": "Evidence resubmission" if status == "Open" else "—",
            "closure_date": "",
        })
        seen.add(fid)

    for j, (obs, sev, status, closed) in enumerate(closed_templates):
        fid = f"{fw_tag}-F-{200 + j:03d}"
        if fid in seen:
            continue
        app = CORE_APPS[j % len(CORE_APPS)]
        out.append({
            "finding_id": fid,
            "application": app,
            "observation": obs,
            "severity": sev,
            "source": "Internal Audit",
            "integration": sources[0],
            "open_since": f"2026-0{3 + j}-15",
            "linked_control": controls[j % max(len(controls), 1)].get("control_id", "—") if controls else "—",
            "linked_evidence": "—",
            "owner": _owner(app),
            "status": status,
            "aging_days": 0,
            "escalation": "—",
            "auditor_notes": "Closed within SLA",
            "closure_dependency": "—",
            "closure_date": closed,
            "closure_note": "Verified by auditor — evidence accepted",
        })
        seen.add(fid)

    from app import ecs_state
    from modules.frameworks.engines.framework_catalog import resolve_framework_name
    fw_resolved = resolve_framework_name(framework)
    for obs_id, meta in ecs_state.closed_observations.items():
        if meta.get("framework") and resolve_framework_name(meta.get("framework", "")) != fw_resolved:
            continue
        if obs_id in seen:
            continue
        out.append({
            "finding_id": obs_id,
            "application": meta.get("application", "Net Banking"),
            "observation": meta.get("detail", "Observation closed — evidence approved"),
            "severity": "Medium",
            "source": "Auditor Closure",
            "integration": "ECS Workflow",
            "open_since": meta.get("closed_at", "")[:10],
            "linked_control": meta.get("control_id", "—"),
            "linked_evidence": meta.get("evidence_id", "—"),
            "owner": meta.get("closed_by", "Auditor"),
            "status": "Closed",
            "aging_days": 0,
            "escalation": "—",
            "auditor_notes": meta.get("detail", ""),
            "closure_dependency": "—",
            "closure_date": meta.get("closed_at", "")[:10],
            "closure_note": f"Closed by {meta.get('closed_by', 'Auditor')}",
        })
        seen.add(obs_id)
    return out


def merge_pending_and_gaps(framework: str, pending: list[dict], gaps: list[dict]) -> list[dict]:
    """Merge pending actions and open gaps into unified actionable rows."""
    merged: list[dict] = []
    seen_keys: set[str] = set()

    controls = get_framework_graph(framework).get("controls", [])

    def _add(row: dict, row_type: str, idx: int = 0) -> None:
        resolved_id, resolved_name = _resolve_control_id(
            controls,
            requested_control_id=row.get("control_id", ""),
            requested_control_name=row.get("control_name", row.get("control", "")),
            application=row.get("application", ""),
            fallback_index=idx,
        )
        key = f"{resolved_id}::{row.get('application')}::{row_type}"
        if key in seen_keys:
            return
        seen_keys.add(key)
        merged.append({
            "framework": row.get("framework", framework),
            "application": row["application"],
            "control_id": resolved_id,
            "control_name": resolved_name,
            "evidence_id": row.get("evidence_id", row.get("primary_evidence_id", "")),
            "item_type": row_type,
            "finding_id": row.get("finding_id", "—"),
            "owner": row.get("owner", _owner(row["application"])),
            "action": row.get("action") or row.get("description", "Resolve gap"),
            "description": row.get("description", row.get("action", "")),
            "gap_type": row.get("gap_type", "Pending action"),
            "due_date": row.get("due_date", "2026-06-15"),
            "sla_aging_days": row.get("sla_aging_days", _seed(key, 3, 28)),
            "risk": row.get("risk", row.get("risk_severity", "Medium")),
            "blocker": row.get("blocker", "—"),
        })

    for i, p in enumerate(pending):
        _add(p, "Pending Action", i)
    for j, g in enumerate(gaps):
        _add({**g, "action": g.get("description", "Close gap")}, "Open Gap", j)

    extra_actions = [
        ("Observation closure pending", "High", "Open Gap"),
        ("Stale evidence refresh required", "Medium", "Open Gap"),
        ("Integration sync — evidence not collected", "Medium", "Pending Action"),
        ("SLA breach — escalation required", "Critical", "Pending Action"),
        ("Failed validation — resubmit evidence", "High", "Open Gap"),
        ("Missing control attestation", "Medium", "Pending Action"),
        ("Auditor request — supplementary evidence", "High", "Pending Action"),
        ("Repeat observation — root cause pending", "High", "Open Gap"),
    ]
    for i, (desc, risk, rtype) in enumerate(extra_actions):
        app = CORE_APPS[i % len(CORE_APPS)]
        cid_prefix = PREFIX_BY_FW.get(framework, "XX-C")
        _add({
            "application": app,
            "control_name": desc[:40],
            "finding_id": "—" if i % 2 else f"OBS-{i:03d}",
            "owner": _owner(app),
            "action": desc,
            "description": desc,
            "gap_type": rtype,
            "due_date": f"2026-06-{(5 + i):02d}",
            "sla_aging_days": 4 + i * 2,
            "risk": risk,
            "blocker": ["Owner capacity", "CAB approval", "Vendor delay", "Integration auth"][i % 4],
        }, rtype, i)

    return merged


def enrich_exceptions(framework: str, existing: list[dict]) -> list[dict]:
    """Add RAF / TD breach metadata and expand count."""
    controls = get_framework_graph(framework).get("controls", [])
    out = []
    for i, ex in enumerate(existing):
        cid, cname = _resolve_control_id(
            controls,
            requested_control_id=ex.get("control_id", ""),
            requested_control_name=ex.get("control_name", ""),
            application=ex.get("application", ""),
            fallback_index=i,
        )
        out.append({
            **ex,
            "control_id": cid,
            "control_name": cname,
            "td_breach_type": ex.get("td_breach_type", RAF_TYPES[i % len(RAF_TYPES)]),
            "risk_access_form_id": ex.get("risk_access_form_id", f"RAF-2026-{1400 + i:04d}"),
            "submitted_via": "Bank Pay Risk Access Form (online)",
            "severity": ex.get("severity", ["Critical", "High", "Medium"][i % 3]),
        })
    apps = CORE_APPS + ["UPI", "Card Platform", "Treasury"]
    prefix = PREFIX_BY_FW.get(framework, "XX-C")
    for j in range(max(0, 6 - len(out))):
        app = apps[j % len(apps)]
        idx = len(out) + j + 1
        cid, cname = _resolve_control_id(controls, application=app, fallback_index=j)
        out.append({
            "id": f"TD-{framework[:2].upper()}-{100 + idx:03d}",
            "control_id": cid,
            "control_name": cname,
            "application": app,
            "title": f"{RAF_TYPES[(j + 2) % len(RAF_TYPES)]} — {app}",
            "td_breach_type": RAF_TYPES[(j + 2) % len(RAF_TYPES)],
            "risk_access_form_id": f"RAF-2026-{1500 + idx:04d}",
            "submitted_via": "Bank Pay Risk Access Form (online)",
            "justification": f"Business-critical {app} workload — CAB-approved deferral",
            "compensating": "Enhanced monitoring + network isolation",
            "approver": ["CISO Office", "QSA + CISO", "Risk Committee", "DPO", "IT Director"][j % 5],
            "expires": f"2026-{(8 + j % 4):02d}-{(15 + j):02d}",
            "status": ["Active", "Active", "Review Due", "Active", "Pending Approval"][j % 5],
            "severity": ["High", "Critical", "Medium"][j % 3],
        })
    return out


def enrich_integrations(framework: str, existing: list[dict]) -> list[dict]:
    """Add application-level sync challenges and evidence-collection confirmation."""
    out = []
    challenge_pool = [
        ("OAuth token expired — re-auth required", "High", "Resolved"),
        ("API rate limit — batch sync delayed 4h", "Medium", "Monitoring"),
        ("Application scope missing in connector config", "High", "Open"),
        ("Evidence pull blocked — insufficient IAM role", "Critical", "Open"),
        ("Webhook delivery failure — retry queue", "Medium", "Resolved"),
    ]
    bp_pool = ["Evidence Collection", "Observation Closure", "Control Mapping", "SLA Tracking", "Audit Package Export"]

    for i, ing in enumerate(existing):
        apps = ing.get("applications", CORE_APPS)
        challenges = []
        for j, app in enumerate(apps[:3]):
            tpl = challenge_pool[(i + j) % len(challenge_pool)]
            challenges.append({
                "application": app,
                "issue": tpl[0],
                "severity": tpl[1],
                "status": tpl[2],
            })
        ready = ing.get("health", "Healthy") == "Healthy" and ing.get("failed_jobs", 0) == 0
        out.append({
            **ing,
            "affected_applications": apps,
            "sync_challenges": challenges,
            "business_processes_enabled": bp_pool[: 2 + (i % 3)],
            "evidence_collection_ready": ready,
            "post_sync_confirmation": (
                "Evidence pull verified — business processes active"
                if ready else "BP blocked — resolve sync challenge before evidence collection"
            ),
        })
    return out


def enrich_reuse_mappings(framework: str, existing: list[dict]) -> list[dict]:
    """Expand cross-framework reuse with application context."""
    out = list(existing)
    cross = {
        "PCI DSS": [
            ("PCI-10.6", "CSITE", "CS-C-05 Log Retention", "Net Banking, Payments"),
            ("PCI-8.3", "AppSec", "AS-C-04 Secrets Detection", "Net Banking, Mobile Banking"),
            ("PCI-11.3", "VAPT", "VP-C-01 External Pentest Closure", "Internet Banking, Net Banking"),
            ("PCI-7.2", "Nginx Baselining", "NGX-C-01 TLS Enforcement", "Card Platform, UPI Gateway"),
        ],
        "VAPT": [
            ("VP-C-01", "PCI DSS", "PCI-11.3 External VA", "Internet Banking"),
            ("VP-C-02", "Nginx Baselining", "NGX-C-02 WAF Validation", "UPI"),
            ("VP-C-04", "OS Baselining", "OS-C-02 Critical Patch Within SLA", "Net Banking"),
        ],
        "AppSec": [
            ("AS-C-02", "PCI DSS", "PCI-6.3 Secure Development", "Mobile Banking"),
            ("AS-C-04", "VAPT", "VP-C-03 Retest Evidence Review", "Mobile Banking"),
        ],
    }
    for src_ctrl, tgt_fw, tgt_ctrl, apps in cross.get(framework, []):
        out.append({
            "source_framework": framework,
            "source_control": src_ctrl,
            "target_framework": tgt_fw,
            "target_control": tgt_ctrl,
            "shared_evidence": f"Shared {src_ctrl} evidence bundle",
            "confidence_pct": 85 + _seed(f"{src_ctrl}{tgt_fw}", 0, 12),
            "applications": apps,
            "reuse_type": "Cross-framework evidence reuse",
        })
    return out


def enrich_framework_graph(framework: str, graph: dict[str, Any]) -> dict[str, Any]:
    """Apply all enrichments to a framework graph."""
    controls = graph.get("controls", [])
    findings_seed = graph.get("findings", [])
    evidence = ensure_control_linked_evidence(
        framework, graph.get("evidence", []), controls, findings_seed,
    )
    evidence = enrich_evidence(framework, evidence, controls)
    findings = enrich_observations(framework, findings_seed, controls)
    evidence = [_sync_evidence_workflow_fields(dict(e), framework, controls, findings) for e in evidence]
    pending_merged = merge_pending_and_gaps(
        framework, graph.get("pending_actions", []), graph.get("open_gaps", []),
    )
    return {
        **graph,
        "evidence": evidence,
        "findings": findings,
        "open_findings": findings,
        "pending_actions": pending_merged,
        "pending_actions_and_gaps": pending_merged,
        "open_gaps": [],
        "integrations": enrich_integrations(framework, graph.get("integrations", [])),
        "integrations_detailed": enrich_integrations(framework, graph.get("integrations", [])),
        "exceptions": enrich_exceptions(framework, graph.get("exceptions", [])),
        "framework_exceptions": enrich_exceptions(framework, graph.get("exceptions", [])),
        "reuse_mappings": enrich_reuse_mappings(framework, graph.get("reuse_mappings", [])),
    }
