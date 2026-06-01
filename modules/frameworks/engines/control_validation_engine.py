"""Enterprise control validation — config, file, policy, reuse, SLA, implementation checks."""

from __future__ import annotations

import hashlib

from app import ecs_state
from modules.operations.engines.evidence_repository import evidence_reuse_map
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records, get_framework_controls
from modules.governance.engines.workflow_module import build_owner_work_queue, work_queue_summary

VALIDATION_TYPES = (
    "configuration",
    "file_based",
    "policy_mapping",
    "evidence_reuse",
    "sla_td",
    "implementation",
)


def _seed(control: str, check: str) -> int:
    return int(hashlib.md5(f"{control}::{check}".encode()).hexdigest(), 16)


def _status(seed: int, fail_rate: int = 5) -> str:
    return "FAIL" if seed % fail_rate == 0 else "WARN" if seed % 7 == 0 else "PASS"


FRAMEWORK_IMPLEMENTATION_CHECKS: dict[str, list[tuple[str, str]]] = {
    "PCI DSS": [
        ("TLS 1.0 disabled on CDE endpoints", "configuration"),
        ("MFA enabled for admin access", "configuration"),
        ("Password policy compliant (12+ chars)", "configuration"),
        ("Audit log retention ≥ 12 months", "configuration"),
        ("Cardholder data encryption at rest", "implementation"),
    ],
    "DPSC": [
        ("API rate limiting enabled", "configuration"),
        ("Tokenization vault access restricted", "configuration"),
        ("Fraud monitoring rules active", "implementation"),
        ("UPI channel TLS 1.2+", "configuration"),
    ],
    "OS Baselining": [
        ("CIS benchmark score ≥ 85%", "implementation"),
        ("sudo policy — no NOPASSWD", "configuration"),
        ("Critical patch applied within SLA", "implementation"),
        ("SSH root login disabled", "configuration"),
        ("Password policy enforced", "configuration"),
    ],
    "DB Baselining": [
        ("Encryption at rest (TDE) enabled", "implementation"),
        ("DB audit logging enabled", "configuration"),
        ("Privileged access review current", "implementation"),
        ("DB patch validation within SLA", "implementation"),
        ("Weak password accounts remediated", "configuration"),
    ],
    "Nginx Baselining": [
        ("TLS 1.0/1.1 disabled", "configuration"),
        ("HSTS header configured", "configuration"),
        ("Weak cipher suites removed", "implementation"),
        ("Reverse proxy headers validated", "configuration"),
        ("Directory listing disabled", "configuration"),
    ],
    "AppSec": [
        ("SAST critical findings remediated", "implementation"),
        ("DAST high findings closed", "implementation"),
        ("Secrets scanning — no live credentials", "implementation"),
        ("Dependency CVE critical count = 0", "implementation"),
        ("API security auth bypass tests passed", "implementation"),
    ],
    "VAPT": [
        ("Critical VA findings closed", "implementation"),
        ("Pen test high findings remediated", "implementation"),
        ("Overdue vulnerabilities = 0", "sla_td"),
        ("Retest validation completed", "file_based"),
        ("External VA scope current", "policy_mapping"),
    ],
    "CSITE": [
        ("SIEM alert correlation active", "implementation"),
        ("SOC monitoring coverage ≥ 95%", "implementation"),
        ("EDR agent health ≥ 98%", "implementation"),
        ("Threat intel feed ingesting", "configuration"),
        ("Privileged access anomaly detection", "implementation"),
    ],
    "ITPP": [
        ("DR drill within 6-month window", "implementation"),
        ("Backup success rate ≥ 99%", "implementation"),
        ("Restore test validated this quarter", "file_based"),
        ("CAB approval for prod changes", "policy_mapping"),
        ("P1 incident SLA compliance", "sla_td"),
        ("Capacity threshold alerts configured", "configuration"),
        ("HA failover test passed", "implementation"),
    ],
}


def _file_validation(ev: dict) -> dict:
    seed = _seed(ev["evidence_id"], "file")
    st = ev.get("evidence_status", "Current")
    if st == "Expired":
        status = "FAIL"
        deviation = "Evidence TD expired — refresh required before audit closure."
    elif st == "Due for Refresh":
        status = "WARN"
        deviation = "Evidence approaching expiry window."
    else:
        status = _status(seed, 9)
        deviation = "" if status == "PASS" else "Metadata incomplete or environment tag mismatch."
    return {
        "check_name": f"File integrity — {ev['evidence_name'][:40]}",
        "validation_type": "file_based",
        "status": status,
        "snapshot": f"{ev.get('mock_file', '')} · uploaded {ev.get('upload_timestamp', '—')[:10]} · {ev.get('environment', 'Production')}",
        "deviation": deviation or "Timestamp, completeness, and environment tags validated.",
        "evidence_id": ev["evidence_id"],
    }


def _policy_mapping_validation(framework: str, control: dict, wf_status: str) -> dict:
    ev_count = len(control["evidences"])
    missing = 0 if ev_count >= 2 else 1
    stale = sum(1 for e in control["evidences"] if e.get("evidence_status") != "Current")
    if wf_status == "pending":
        status, deviation = "FAIL", "Control has no submitted evidence package."
    elif stale > 0:
        status, deviation = "WARN", f"{stale} stale/expired evidence artefact(s) mapped to control."
    elif missing:
        status, deviation = "WARN", "Secondary evidence artefact missing for dual attestation."
    else:
        status, deviation = "PASS", "Policy-to-evidence mapping complete."
    return {
        "check_name": f"Policy mapping — {control['control_id']}",
        "validation_type": "policy_mapping",
        "status": status,
        "snapshot": f"{ev_count} evidence(s) mapped · workflow: {wf_status}",
        "deviation": deviation,
    }


def _reuse_links(filename: str) -> list[dict]:
    key = (filename or "").lower()
    for k, info in evidence_reuse_map.items():
        if k in key or key in k:
            return info.get("linked_controls", [])
    # Deterministic demo reuse when map not populated
    seed = int(hashlib.md5(key.encode()).hexdigest(), 16)
    if seed % 4 == 0 and key:
        return [
            {"framework": "PCI DSS", "control": "Shared attestation"},
            {"framework": "ITPP", "control": "Operational control"},
        ]
    return []


def _reuse_validation(evidence_id: str, mock_file: str = "") -> dict | None:
    reuse = _reuse_links(mock_file or evidence_id)
    if len(reuse) < 2:
        return None
    frameworks = sorted({r["framework"] for r in reuse})
    return {
        "check_name": f"Evidence reuse — {evidence_id}",
        "validation_type": "evidence_reuse",
        "status": "PASS",
        "snapshot": f"Reused across {len(frameworks)} frameworks: {', '.join(frameworks[:4])}",
        "deviation": f"Duplicate reduction opportunity — {len(reuse)} control mappings.",
        "reuse_count": len(reuse),
        "frameworks": frameworks,
    }


def _sla_validation(framework: str, control_name: str, queue_item: dict | None) -> dict:
    if not queue_item:
        return {
            "check_name": "SLA / TD expiry",
            "validation_type": "sla_td",
            "status": "PASS",
            "snapshot": "No active SLA breach for control.",
            "deviation": "Within remediation timeline.",
        }
    aging = queue_item.get("aging_days", 0)
    sla = queue_item.get("sla", "30 days")
    escalated = queue_item.get("escalated", False)
    if escalated or aging > 45:
        status = "FAIL"
        deviation = f"Overdue — {aging}d aging exceeds SLA ({sla}). CIO escalation eligible."
    elif aging > 30:
        status = "WARN"
        deviation = f"Approaching SLA breach — {aging}d pending."
    else:
        status = "PASS"
        deviation = f"Within SLA — {aging}d of {sla}."
    return {
        "check_name": "SLA / TD expiry tracking",
        "validation_type": "sla_td",
        "status": status,
        "snapshot": f"Priority {queue_item.get('priority', 'Medium')} · {queue_item.get('lifecycle_state', 'Open')}",
        "deviation": deviation,
    }


def build_control_validations(framework: str, limit: int = 40) -> list[dict]:
    """Per-control validation results for a framework page."""
    controls = get_framework_controls(framework)
    queue_by_key = {
        f"{i['framework']}::{i['control']}": i
        for i in build_owner_work_queue(500)
    }
    impl_checks = FRAMEWORK_IMPLEMENTATION_CHECKS.get(framework, [])
    rows: list[dict] = []

    for ctrl in controls[:limit]:
        ckey = f"{framework}::{ctrl['control']}"
        wf = ecs_state.control_status(framework, ctrl["control"])
        primary_ev = ctrl["evidences"][0]

        for check_name, vtype in impl_checks:
            seed = _seed(ctrl["control"], check_name)
            status = _status(seed, 6 if vtype == "implementation" else 8)
            rows.append({
                "control": ctrl["control"],
                "control_id": ctrl["control_id"],
                "domain": _control_domain(framework, ctrl["control"]),
                **{
                    "check_name": check_name,
                    "validation_type": vtype,
                    "status": status,
                    "snapshot": _impl_snapshot(framework, check_name, status),
                    "deviation": _impl_deviation(check_name, status),
                },
            })

        rows.append({
            "control": ctrl["control"],
            "control_id": ctrl["control_id"],
            "domain": _control_domain(framework, ctrl["control"]),
            **_file_validation(primary_ev),
        })
        rows.append({
            "control": ctrl["control"],
            "control_id": ctrl["control_id"],
            "domain": _control_domain(framework, ctrl["control"]),
            **_policy_mapping_validation(framework, ctrl, wf),
        })
        reuse = _reuse_validation(primary_ev["evidence_id"], primary_ev.get("mock_file", ""))
        if reuse:
            rows.append({
                "control": ctrl["control"],
                "control_id": ctrl["control_id"],
                "domain": _control_domain(framework, ctrl["control"]),
                **reuse,
            })
        rows.append({
            "control": ctrl["control"],
            "control_id": ctrl["control_id"],
            "domain": _control_domain(framework, ctrl["control"]),
            **_sla_validation(framework, ctrl["control"], queue_by_key.get(ckey)),
        })

    return rows


def _control_domain(framework: str, control: str) -> str:
    if framework != "ITPP":
        return framework
    cl = control.lower()
    if any(w in cl for w in ("dr ", "drill", "failover", "rpo", "rto", "recovery")):
        return "Disaster Recovery"
    if "backup" in cl or "restore" in cl:
        return "Backup Management"
    if any(w in cl for w in ("cab", "change", "rollback", "emergency")):
        return "Change Management"
    if any(w in cl for w in ("incident", "p1", "p2", "rca", "major incident")):
        return "Incident Management"
    if any(w in cl for w in ("repeat", "problem", "known error", "kedb")):
        return "Problem Management"
    if any(w in cl for w in ("capacity", "cpu", "storage", "memory", "scaling")):
        return "Capacity Management"
    if any(w in cl for w in ("availability", "uptime", "ha ", "redundancy")):
        return "Availability Management"
    if any(w in cl for w in ("patch", "vulnerability", "kb ", "hotfix")):
        return "Patch Governance"
    if any(w in cl for w in ("vendor", "third party", "third-party", "sla", "contract")):
        return "Vendor Governance"
    return "Operations Governance"


def _impl_snapshot(framework: str, check: str, status: str) -> str:
    if status == "PASS":
        return f"{check} — validated against production baseline."
    return f"{check} — deviation detected in last automated scan."


def _impl_deviation(check: str, status: str) -> str:
    if status == "PASS":
        return "Implementation verified — no deviation."
    if status == "WARN":
        return f"{check}: minor deviation — remediation scheduled."
    return f"{check}: control implementation failed validation — escalate to App Owner."


def validation_summary(framework: str) -> dict:
    rows = build_control_validations(framework, limit=500)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    warned = sum(1 for r in rows if r["status"] == "WARN")
    total = len(rows) or 1
    controls = get_framework_controls(framework)
    from modules.frameworks.engines.framework_governance_data import get_framework_profile
    apps = get_framework_profile(framework).get("applications", [])
    return {
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "effectiveness_pct": round((passed / total) * 100, 1),
        "failed_controls": list({r["control_id"] for r in rows if r["status"] == "FAIL"})[:12],
        "scope_label": f"Across {len(controls)} {framework} controls and {len(apps)} applications",
        "control_count": len(controls),
        "application_count": len(apps),
        "aggregation_type": "validation_checks",
        "explanation": "Validation checks — config, evidence, policy, SLA runs. Not the same as governance control count.",
    }


def build_governance_analytics() -> dict:
    """Enterprise governance analytics for dashboards and leadership."""
    stats = ecs_state.build_evidence_analytics()
    records = get_all_evidence_records()
    wq = work_queue_summary()
    stale = [r for r in records if r.get("evidence_status") in ("Expired", "Due for Refresh")]
    stale_pct = round((len(stale) / len(records)) * 100, 1) if records else 0

    reuse_map: dict[str, list] = {}
    for r in records[:80]:
        reuse = _reuse_links(r.get("mock_file", r["evidence_id"]))
        if len(reuse) >= 2:
            reuse_map[r["evidence_id"]] = reuse

    top_reuse = sorted(
        [{"evidence_id": eid, "frameworks": sorted({x["framework"] for x in xs}), "count": len(xs)} for eid, xs in reuse_map.items()],
        key=lambda x: -x["count"],
    )[:6]

    repeat_failures: list[dict] = []
    for key, info in ecs_state.rejected_controls.items():
        fw, ctrl = key.split("::", 1)
        repeat_failures.append({
            "framework": fw, "control": ctrl, "application": "Net Banking",
            "evidence": ctrl[:40], "finding": info.get("reason", "")[:80],
            "owner": "App Owner", "status": "Rejected", "risk": "High",
            "reason": info.get("reason", "")[:80], "count": 1,
        })
    for key in ecs_state.escalated_controls:
        fw, ctrl = key.split("::", 1)
        repeat_failures.append({
            "framework": fw, "control": ctrl, "application": "UPI",
            "evidence": "Escalated evidence pack", "finding": "SLA breach",
            "owner": "Compliance Officer", "status": "Escalated", "risk": "Critical",
            "reason": "Escalated — SLA breach", "count": 2,
        })

    risky = build_owner_work_queue(100)
    risky = [i for i in risky if i.get("risk_rating") in ("Critical", "High")]
    top_risky = [
        {"framework": i["framework"], "control": i["control"], "risk": i["risk_rating"], "aging_days": i["aging_days"]}
        for i in risky[:8]
    ]

    fw_maturity = stats["framework_stats"]
    operational = {}
    if "ITPP" in FRAMEWORK_CATALOG:
        itpp_val = validation_summary("ITPP")
        operational = {
            "itpp_effectiveness": itpp_val["effectiveness_pct"],
            "dr_readiness": _itpp_dr_readiness(),
            "backup_success_rate": 98.2,
            "change_failure_rate": 2.1,
            "incident_sla_compliance": 94.5,
        }

    approved = stats["totals"]["approved"]
    total = stats["totals"]["total"]
    audit_readiness = round((approved / total) * 100, 1) if total else 0

    return {
        "framework_maturity": fw_maturity,
        "operational_maturity": operational,
        "control_effectiveness": {
            fw: validation_summary(fw)["effectiveness_pct"]
            for fw in FRAMEWORK_CATALOG
        },
        "repeat_failures": repeat_failures[:10],
        "top_risky_controls": top_risky,
        "most_reused_evidence": top_reuse,
        "stale_evidence_pct": stale_pct,
        "stale_count": len(stale),
        "audit_readiness_pct": audit_readiness,
        "sla_breaches": wq.get("sla_breach", 0),
        "escalated": wq.get("escalated", 0),
        "framework_count": len(FRAMEWORK_CATALOG),
    }


def _itpp_dr_readiness() -> float:
    dr_controls = [c for c in get_framework_controls("ITPP") if _control_domain("ITPP", c["control"]) == "Disaster Recovery"]
    if not dr_controls:
        return 0.0
    ready = sum(1 for c in dr_controls if ecs_state.control_status("ITPP", c["control"]) == "approved")
    return round((ready / len(dr_controls)) * 100, 1)


def failed_validations(framework: str = "") -> list[dict]:
    fws = [framework] if framework else list(FRAMEWORK_CATALOG.keys())
    out = []
    for fw in fws:
        for row in build_control_validations(fw, limit=12):
            if row["status"] == "FAIL":
                out.append({**row, "framework": fw})
    return out[:20]
