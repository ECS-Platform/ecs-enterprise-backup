"""ECS Enterprise Mock Data Engine.

A single deterministic façade that generates every dataset required for
walkthrough / CIO / regulator demos without any external imports.

Existing engines (`framework_catalog`, `audit_schedule_engine`,
`framework_intelligence`, `evidence_workflow_engine`) are wrapped here so
callers can access them in one consistent shape; all *new* mock datasets
required by the demo brief — banking applications registry, ServiceNow
tickets, AI governance, prompt audit, hallucination alerts, token usage,
multi-year audit history, baselining drift, evidence lineage, VAPT
findings, CIO executive snapshot — are generated inside this module.

Everything is hash-seeded so the demo stays stable across page loads,
but counts are tuned to feel like a live banking governance platform.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from app import ecs_state
from app.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records

DEMO_MODE = True
DEMO_ANCHOR_DATE = date(2026, 5, 28)


# ---------------------------------------------------------------------------
# Banking applications registry
# ---------------------------------------------------------------------------

_APP_META = {
    "Net Banking": {"owner": "R. Mehta", "vertical": "Retail Digital", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Java · Oracle · Nginx"},
    "Mobile Banking": {"owner": "A. Sharma", "vertical": "Retail Digital", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Kotlin · Swift · API GW"},
    "Mobile Banking Edge": {"owner": "A. Sharma", "vertical": "Retail Digital", "region": "Pan-India", "criticality": "High", "tech_stack": "Nginx · WAF · CDN"},
    "Internet Banking": {"owner": "R. Mehta", "vertical": "Retail Digital", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Java · Postgres · Nginx"},
    "Retail Banking": {"owner": "K. Reddy", "vertical": "Retail Banking", "region": "Pan-India", "criticality": "High", "tech_stack": "Mainframe · CICS"},
    "Core Banking": {"owner": "S. Banerjee", "vertical": "Core Banking", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Oracle · Tuxedo · AIX"},
    "CBS Oracle": {"owner": "S. Banerjee", "vertical": "Core Banking", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Oracle DB Cluster"},
    "UPI": {"owner": "P. Nair", "vertical": "Digital Payments", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Spring Boot · Redis"},
    "Payments": {"owner": "A. Sharma", "vertical": "Digital Payments", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Switch · HSM"},
    "Payment Switch": {"owner": "A. Sharma", "vertical": "Digital Payments", "region": "Pan-India", "criticality": "Critical", "tech_stack": "BASE24 · HSM"},
    "Card Platform": {"owner": "A. Sharma", "vertical": "Cards", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Postilion · TMS"},
    "Treasury": {"owner": "S. Banerjee", "vertical": "Wholesale", "region": "Pan-India", "criticality": "High", "tech_stack": "Murex · Oracle"},
    "Wealth Portal": {"owner": "V. Rao", "vertical": "Wealth", "region": "Pan-India", "criticality": "High", "tech_stack": "Angular · Mongo"},
    "API Gateway": {"owner": "P. Nair", "vertical": "Platform", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Kong · Nginx · Kubernetes"},
    "Loan System": {"owner": "V. Rao", "vertical": "Lending", "region": "Pan-India", "criticality": "High", "tech_stack": "Java · DB2"},
    "Loan Origination": {"owner": "V. Rao", "vertical": "Lending", "region": "Pan-India", "criticality": "High", "tech_stack": "Newgen · Postgres"},
    "Digital Lending": {"owner": "M. D'Souza", "vertical": "Lending", "region": "Pan-India", "criticality": "High", "tech_stack": "Node.js · Postgres · Kubernetes"},
    "Customer Onboarding": {"owner": "M. D'Souza", "vertical": "Retail Digital", "region": "Pan-India", "criticality": "High", "tech_stack": "Camunda · Spring Boot"},
    "Customer Onboarding Platform": {"owner": "M. D'Souza", "vertical": "Retail Digital", "region": "Pan-India", "criticality": "High", "tech_stack": "Camunda · Spring Boot"},
    "Enterprise Payments Hub": {"owner": "A. Sharma", "vertical": "Digital Payments", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Switch · HSM · API GW"},
    "Digital Lending Platform": {"owner": "M. D'Souza", "vertical": "Lending", "region": "Pan-India", "criticality": "High", "tech_stack": "Node.js · Postgres · Kubernetes"},
    "Core Banking Platform": {"owner": "S. Banerjee", "vertical": "Core Banking", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Oracle · Tuxedo · AIX"},
    "AML Engine": {"owner": "P. Nair", "vertical": "Risk & Compliance", "region": "Pan-India", "criticality": "Critical", "tech_stack": "Actimize · Hadoop"},
    "Fraud Monitoring": {"owner": "P. Nair", "vertical": "Risk & Compliance", "region": "Pan-India", "criticality": "Critical", "tech_stack": "SAS · Kafka · Elastic"},
}


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def _seed(*parts: Any) -> int:
    return int(hashlib.md5("::".join(str(p) for p in parts).encode()).hexdigest(), 16)


def _pick(seed: int, items: list[Any]) -> Any:
    return items[seed % len(items)] if items else None


def _between(seed: int, low: int, high: int) -> int:
    return low + (seed % max(high - low + 1, 1))


# ---------------------------------------------------------------------------
# Banking applications registry — owner, risk, region, readiness, etc.
# ---------------------------------------------------------------------------


def list_banking_applications() -> list[dict[str, Any]]:
    apps: list[dict] = []
    framework_keys = list(FRAMEWORK_CATALOG.keys())
    for name in ecs_state.BANKING_APPLICATIONS:
        meta = _APP_META.get(name, {"owner": "Unassigned", "vertical": "—", "region": "Pan-India", "criticality": "Medium", "tech_stack": "—"})
        seed = _seed("app", name)
        risk_score = _between(seed, 35, 92)
        readiness = max(45, min(96, 100 - risk_score + _between(seed >> 3, -5, 8)))
        maturity = max(2, min(5, _between(seed >> 5, 2, 5)))
        pending_obs = _between(seed >> 7, 1, 18)
        evidence_count = _between(seed >> 9, 28, 220)
        risk_label = ("Critical" if risk_score >= 80 else
                      "High" if risk_score >= 65 else
                      "Medium" if risk_score >= 45 else "Low")
        # frameworks_applicable = 4-9 frameworks deterministically chosen
        fw_count = _between(seed >> 11, 4, min(9, len(framework_keys)))
        fws = sorted({framework_keys[(seed >> (13 + 2 * i)) % len(framework_keys)] for i in range(fw_count)})
        apps.append({
            "application": name,
            "owner": meta["owner"],
            "vertical": meta["vertical"],
            "region": meta["region"],
            "criticality": meta["criticality"],
            "tech_stack": meta["tech_stack"],
            "risk_score": risk_score,
            "risk_label": risk_label,
            "audit_readiness_pct": readiness,
            "maturity_score": maturity,
            "pending_observations": pending_obs,
            "evidence_count": evidence_count,
            "frameworks_applicable": fws,
            "framework_count": len(fws),
        })
    return apps


# ---------------------------------------------------------------------------
# Frameworks registry (wraps existing catalog with control / evidence counts)
# ---------------------------------------------------------------------------


def list_frameworks_catalog() -> list[dict[str, Any]]:
    apps_meta = {a["application"]: a for a in list_banking_applications()}
    rows: list[dict] = []
    for fw, controls in FRAMEWORK_CATALOG.items():
        evidences = sum(len(c.get("evidences", [])) for c in controls)
        owner_apps = sorted({(c["evidences"][0].get("application") if c.get("evidences") else "") for c in controls if c.get("evidences")})
        owner_apps = [a for a in owner_apps if a]
        seed = _seed("fw", fw)
        avg_readiness = round(
            sum(apps_meta[a]["audit_readiness_pct"] for a in owner_apps if a in apps_meta)
            / max(len([a for a in owner_apps if a in apps_meta]), 1),
            1,
        )
        rows.append({
            "framework": fw,
            "category": _pick(seed, [
                "Regulatory", "Security", "Audit", "Resilience", "Infra"
            ]),
            "control_count": len(controls),
            "evidence_count": evidences,
            "applications_covered": owner_apps[:8],
            "readiness_pct": avg_readiness or _between(seed >> 3, 68, 92),
            "audit_cycle": _pick(seed >> 5, ["Quarterly", "Annual", "Continuous"]),
        })
    return sorted(rows, key=lambda r: -r["control_count"])


# ---------------------------------------------------------------------------
# ServiceNow tickets — CHG / INC / PRB / RITM
# ---------------------------------------------------------------------------


_SNOW_TYPES = [
    {"prefix": "CHG", "label": "Change Request", "states": ["New", "Scheduled", "Implement", "Review", "Closed"]},
    {"prefix": "INC", "label": "Incident", "states": ["New", "In Progress", "Resolved", "Closed"]},
    {"prefix": "PRB", "label": "Problem", "states": ["New", "Investigation", "Workaround", "Resolved"]},
    {"prefix": "RITM", "label": "Service Request", "states": ["Open", "Work in Progress", "Closed Complete"]},
]

_SNOW_TITLES = [
    ("CHG", "Firewall rule update — CDE perimeter", "Firewall ACL export Q2-2026"),
    ("CHG", "TLS cipher hardening — Internet Banking edge", "TLS configuration evidence"),
    ("CHG", "Production patch window — CBS Oracle cluster", "Patch compliance attestation"),
    ("CHG", "Nginx WAF ruleset upgrade", "WAF rule effectiveness report"),
    ("INC", "SIEM correlation alert — UPI switch latency", "SIEM alert summary"),
    ("INC", "DAST critical finding — Mobile Banking API", "DAST scan results"),
    ("INC", "Privileged session breach detected — Treasury", "PAM session recording"),
    ("INC", "DLP incident — outbound email", "DLP incident register"),
    ("INC", "Stale evidence escalation — PCI DSS Req 3.4", "TDE attestation"),
    ("PRB", "Recurring SoD violation — Payments admin role", "SoD conflict closure log"),
    ("PRB", "Recurring DB privileged commands during off-hours", "DB audit log export"),
    ("RITM", "Evidence re-upload — MFA enforcement screenshot", "IAM MFA evidence"),
    ("RITM", "Auditor access provisioning — Deloitte Q2 cycle", "External auditor access form"),
    ("RITM", "VA scan request — Wealth Portal quarterly", "Quarterly VA scan report"),
    ("RITM", "Encryption key escrow attestation", "Key custodian attestation"),
]


def generate_servicenow_tickets(count: int = 60) -> list[dict[str, Any]]:
    tickets: list[dict] = []
    apps = ecs_state.BANKING_APPLICATIONS
    frameworks = list(FRAMEWORK_CATALOG.keys())
    today = DEMO_ANCHOR_DATE
    for i in range(count):
        seed = _seed("snow", i)
        spec = _SNOW_TITLES[seed % len(_SNOW_TITLES)]
        prefix = spec[0]
        ttype = next(t for t in _SNOW_TYPES if t["prefix"] == prefix)
        number = f"{prefix}{(seed >> 3) % 999900 + 100000:06d}"
        state = ttype["states"][(seed >> 5) % len(ttype["states"])]
        created_days = _between(seed >> 7, 1, 90)
        app = _pick(seed >> 9, apps)
        fw = _pick(seed >> 11, frameworks)
        controls = FRAMEWORK_CATALOG.get(fw, [])
        ctrl = controls[(seed >> 13) % len(controls)] if controls else {}
        opened_at = (today - timedelta(days=created_days)).isoformat()
        closed_at = (today - timedelta(days=max(0, created_days - _between(seed >> 15, 1, 14)))).isoformat() if state in ("Closed", "Resolved", "Closed Complete") else ""
        tickets.append({
            "ticket_id": number,
            "type": ttype["prefix"],
            "type_label": ttype["label"],
            "title": spec[1],
            "linked_evidence": spec[2],
            "state": state,
            "priority": _pick(seed >> 17, ["P1", "P2", "P3", "P4"]),
            "owner": _APP_META.get(app, {}).get("owner", "Unassigned"),
            "application": app,
            "framework": fw,
            "linked_control": ctrl.get("control_id", "—"),
            "control_name": ctrl.get("control", "—"),
            "opened_at": opened_at,
            "closed_at": closed_at,
            "age_days": created_days,
        })
    tickets.sort(key=lambda t: t["opened_at"], reverse=True)
    return tickets


# ---------------------------------------------------------------------------
# AI Governance — prompt audit, hallucination alerts, token usage,
# unsafe prompts, policy violations
# ---------------------------------------------------------------------------


_AI_MODELS = ["gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet", "gemini-pro", "internal-llm-r1"]
_AI_TEAMS = ["Compliance", "Audit", "Risk", "App Owners", "CISO Office", "SOC"]
_PROMPT_SAMPLES = [
    ("Explain PCI Req 3.4 evidence requirements", "Compliance", 0.18),
    ("Summarise UPI Q2 audit findings for executives", "Audit", 0.21),
    ("Draft remediation plan for stale firewall rules", "Risk", 0.42),
    ("Generate executive summary of CSITE readiness", "CIO", 0.16),
    ("Map MFA controls across PCI, RBI, SOC2", "Compliance", 0.12),
    ("Suggest test cases for DR drill validation", "App Owners", 0.35),
    ("Extract IOC list from latest threat brief", "SOC", 0.25),
    ("Predict next month patch SLA breach risk", "Risk", 0.55),
    ("Validate evidence file metadata against PCI mapping", "Audit", 0.10),
    ("Explain regulator escalation pathway for incident", "CISO Office", 0.20),
]
_HALLUCINATION_FINDINGS = [
    "Cited PCI requirement number that does not exist (Req 3.99).",
    "Invented an auditor name not in the directory.",
    "Referenced a non-existent ServiceNow ticket pattern.",
    "Quoted RBI annex that has been superseded.",
    "Predicted SLA breach with abnormal confidence < 50%.",
]
_UNSAFE_PROMPT_REASONS = [
    "Prompt attempted to extract production credentials from documentation.",
    "Prompt asked the model to bypass DLP scanning policy.",
    "Prompt requested PII export without anonymisation.",
    "Prompt contained social engineering language targeting auditors.",
]


def generate_prompt_audit(count: int = 80) -> list[dict[str, Any]]:
    rows: list[dict] = []
    today = DEMO_ANCHOR_DATE
    for i in range(count):
        seed = _seed("prompt", i)
        prompt_text, team, base_risk = _PROMPT_SAMPLES[seed % len(_PROMPT_SAMPLES)]
        model = _pick(seed >> 3, _AI_MODELS)
        ts = today - timedelta(days=_between(seed >> 5, 0, 30), hours=_between(seed >> 7, 0, 23))
        tokens_in = _between(seed >> 9, 80, 2200)
        tokens_out = _between(seed >> 11, 120, 3800)
        risk = round(min(0.95, max(0.05, base_risk + (((seed >> 13) % 30) - 15) / 100)), 2)
        flag_hall = risk > 0.45
        flag_unsafe = risk > 0.7
        rows.append({
            "prompt_id": f"PRMPT-{seed % 99999:05d}",
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "user": f"{team.split()[0].lower()}.user@bank.com",
            "role": _pick(seed >> 15, ["auditor", "compliance_head", "owner", "cio", "risk_analyst"]),
            "team": team,
            "model": model,
            "prompt": prompt_text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_in + tokens_out,
            "risk_score": risk,
            "hallucination_flag": flag_hall,
            "unsafe_flag": flag_unsafe,
            "review_status": (
                "Quarantined" if flag_unsafe else
                "Flagged for review" if flag_hall else
                "Approved"
            ),
        })
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    return rows


def generate_hallucination_alerts(prompts: list[dict] | None = None) -> list[dict[str, Any]]:
    prompts = prompts if prompts is not None else generate_prompt_audit()
    alerts: list[dict] = []
    for p in prompts:
        if not p["hallucination_flag"]:
            continue
        seed = _seed("hallu", p["prompt_id"])
        alerts.append({
            "alert_id": f"HALU-{seed % 99999:05d}",
            "prompt_id": p["prompt_id"],
            "timestamp": p["timestamp"],
            "user": p["user"],
            "model": p["model"],
            "confidence_pct": round(_between(seed, 35, 78), 1),
            "risk_score": p["risk_score"],
            "fabrication_signal": _HALLUCINATION_FINDINGS[seed % len(_HALLUCINATION_FINDINGS)],
            "recommendation": (
                "Escalate to AI Governance Officer for manual validation."
                if p["unsafe_flag"]
                else "Add to retraining feedback loop and notify prompt author."
            ),
            "status": "Open" if p["unsafe_flag"] else "Triaged",
        })
    return alerts[:40]


def generate_unsafe_prompts(prompts: list[dict] | None = None) -> list[dict[str, Any]]:
    prompts = prompts if prompts is not None else generate_prompt_audit()
    rows: list[dict] = []
    for p in prompts:
        if not p["unsafe_flag"]:
            continue
        seed = _seed("unsafe", p["prompt_id"])
        rows.append({
            "incident_id": f"AISEC-{seed % 99999:05d}",
            "prompt_id": p["prompt_id"],
            "timestamp": p["timestamp"],
            "user": p["user"],
            "team": p["team"],
            "model": p["model"],
            "reason": _UNSAFE_PROMPT_REASONS[seed % len(_UNSAFE_PROMPT_REASONS)],
            "action_taken": "Blocked + auto-redacted",
            "review_status": "Under Investigation" if seed % 4 else "Closed",
        })
    return rows[:25]


def generate_token_usage() -> dict[str, Any]:
    prompts = generate_prompt_audit(count=120)
    by_team: dict[str, dict] = {}
    by_app: dict[str, dict] = {}
    for p in prompts:
        bt = by_team.setdefault(p["team"], {"team": p["team"], "tokens": 0, "prompts": 0, "cost_usd": 0.0})
        bt["tokens"] += p["tokens_total"]
        bt["prompts"] += 1
        bt["cost_usd"] = round(bt["tokens"] / 1000 * 0.012, 2)
    apps = list_banking_applications()
    for i, p in enumerate(prompts):
        app = apps[i % len(apps)]["application"]
        ba = by_app.setdefault(app, {"application": app, "tokens": 0, "prompts": 0, "cost_usd": 0.0})
        ba["tokens"] += p["tokens_total"]
        ba["prompts"] += 1
        ba["cost_usd"] = round(ba["tokens"] / 1000 * 0.012, 2)
    # Hourly peak: bucket prompts into 24-hour histogram
    hour_buckets = [0] * 24
    for p in prompts:
        h = int(p["timestamp"][11:13])
        hour_buckets[h] += p["tokens_total"]
    peak_hour = hour_buckets.index(max(hour_buckets))
    return {
        "total_tokens": sum(p["tokens_total"] for p in prompts),
        "total_cost_usd": round(sum(p["tokens_total"] for p in prompts) / 1000 * 0.012, 2),
        "total_prompts": len(prompts),
        "by_team": sorted(by_team.values(), key=lambda r: -r["tokens"]),
        "by_application": sorted(by_app.values(), key=lambda r: -r["tokens"])[:10],
        "hourly_histogram": [{"hour": h, "tokens": t} for h, t in enumerate(hour_buckets)],
        "peak_hour": peak_hour,
        "peak_hour_tokens": hour_buckets[peak_hour],
    }


def generate_ai_governance() -> dict[str, Any]:
    prompts = generate_prompt_audit()
    halls = generate_hallucination_alerts(prompts)
    unsafe = generate_unsafe_prompts(prompts)
    tokens = generate_token_usage()
    avg_risk = round(sum(p["risk_score"] for p in prompts) / max(len(prompts), 1), 2)
    return {
        "summary": {
            "prompts_audited": len(prompts),
            "hallucination_alerts": len(halls),
            "unsafe_prompts": len(unsafe),
            "policy_violations": len([p for p in prompts if p["risk_score"] > 0.65]),
            "avg_risk_score": avg_risk,
            "model_coverage": sorted({p["model"] for p in prompts}),
        },
        "prompts": prompts[:25],
        "hallucinations": halls,
        "unsafe": unsafe,
        "tokens": tokens,
        "model_usage": [
            {"model": m, "prompts": sum(1 for p in prompts if p["model"] == m)}
            for m in sorted({p["model"] for p in prompts})
        ],
    }


# ---------------------------------------------------------------------------
# Multi-year audit history (3-5 years of regulator + internal closures)
# ---------------------------------------------------------------------------


def generate_audit_history(years: int = 5) -> list[dict[str, Any]]:
    rows: list[dict] = []
    today = DEMO_ANCHOR_DATE
    frameworks = list(FRAMEWORK_CATALOG.keys())
    for yr_offset in range(years):
        year = today.year - yr_offset
        for fw in frameworks:
            seed = _seed("hist", fw, year)
            findings = _between(seed, 2, 24)
            closed = _between(seed >> 3, max(findings - 4, 1), findings)
            readiness = _between(seed >> 5, 60 + yr_offset * 4, 95 + yr_offset * 2 // 3)
            readiness = max(50, min(98, readiness))
            recurring = _between(seed >> 7, 0, max(2, findings // 5))
            rows.append({
                "year": year,
                "framework": fw,
                "auditor": _pick(seed >> 9, ["Deloitte", "KPMG", "EY", "PwC", "Internal Audit", "RBI Inspection"]),
                "findings_raised": findings,
                "findings_closed": closed,
                "closure_pct": round(closed / max(findings, 1) * 100, 1),
                "recurring_findings": recurring,
                "readiness_pct": readiness,
                "audit_window": f"{year - 1}-Q4 to {year}-Q3",
                "maturity_level": min(5, max(1, 2 + yr_offset // 2 + (seed % 2))),
            })
    rows.sort(key=lambda r: (r["year"], r["framework"]), reverse=False)
    return rows


def summarize_audit_history(rows: list[dict] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else generate_audit_history()
    by_year: dict[int, dict] = {}
    by_framework: dict[str, dict] = {}
    for r in rows:
        by = by_year.setdefault(r["year"], {"year": r["year"], "findings_raised": 0, "findings_closed": 0, "recurring_findings": 0, "readiness_sum": 0, "n": 0})
        by["findings_raised"] += r["findings_raised"]
        by["findings_closed"] += r["findings_closed"]
        by["recurring_findings"] += r["recurring_findings"]
        by["readiness_sum"] += r["readiness_pct"]
        by["n"] += 1
        bf = by_framework.setdefault(r["framework"], {"framework": r["framework"], "trend": []})
        bf["trend"].append({"year": r["year"], "readiness_pct": r["readiness_pct"], "findings": r["findings_raised"]})
    year_trend = [
        {
            "year": y["year"],
            "findings_raised": y["findings_raised"],
            "findings_closed": y["findings_closed"],
            "closure_pct": round(y["findings_closed"] / max(y["findings_raised"], 1) * 100, 1),
            "avg_readiness_pct": round(y["readiness_sum"] / max(y["n"], 1), 1),
            "recurring_findings": y["recurring_findings"],
        }
        for y in sorted(by_year.values(), key=lambda x: x["year"])
    ]
    for fw in by_framework.values():
        fw["trend"].sort(key=lambda x: x["year"])
    return {
        "year_trend": year_trend,
        "framework_trends": sorted(by_framework.values(), key=lambda x: x["framework"]),
    }


# ---------------------------------------------------------------------------
# Risk heatmaps (application × framework, evidence aging, observation density)
# ---------------------------------------------------------------------------


def build_risk_heatmap() -> dict[str, Any]:
    apps = list_banking_applications()
    frameworks = list(FRAMEWORK_CATALOG.keys())
    matrix: list[dict] = []
    for app in apps:
        cells = []
        for fw in frameworks:
            seed = _seed("heat", app["application"], fw)
            covered = fw in app["frameworks_applicable"]
            base = app["audit_readiness_pct"]
            cell_pct = max(40, min(98, base + _between(seed, -15, 12) if covered else 0))
            tone = (
                "tone-green" if cell_pct >= 85 else
                "tone-amber" if cell_pct >= 70 else
                "tone-red" if cell_pct >= 50 else
                "tone-dark-red"
            ) if covered else "tone-empty"
            cells.append({
                "framework": fw,
                "value": cell_pct,
                "tone": tone,
                "covered": covered,
            })
        matrix.append({
            "application": app["application"],
            "owner": app["owner"],
            "risk_score": app["risk_score"],
            "readiness_pct": app["audit_readiness_pct"],
            "cells": cells,
        })
    aging_buckets = [
        {"bucket": "0-30 days", "count": 0, "tone": "tone-green"},
        {"bucket": "31-60 days", "count": 0, "tone": "tone-amber"},
        {"bucket": "61-90 days", "count": 0, "tone": "tone-amber"},
        {"bucket": "90+ days", "count": 0, "tone": "tone-red"},
    ]
    for ev in get_all_evidence_records():
        seed = _seed("ev_age", ev.get("evidence_id", "?"))
        age = _between(seed, 1, 180)
        if age <= 30:
            aging_buckets[0]["count"] += 1
        elif age <= 60:
            aging_buckets[1]["count"] += 1
        elif age <= 90:
            aging_buckets[2]["count"] += 1
        else:
            aging_buckets[3]["count"] += 1
    return {
        "matrix": matrix,
        "frameworks": frameworks,
        "evidence_aging": aging_buckets,
    }


# ---------------------------------------------------------------------------
# Baselining drift analytics — OS / DB / Nginx / unauthorized changes
# ---------------------------------------------------------------------------


_DRIFT_CATEGORIES = [
    {"key": "os", "label": "OS Drift", "framework": "OS Baselining"},
    {"key": "db", "label": "DB Drift", "framework": "DB Baselining"},
    {"key": "nginx", "label": "Nginx Drift", "framework": "Nginx Baselining"},
    {"key": "patching", "label": "Patching Delays", "framework": "OS Baselining"},
    {"key": "config", "label": "Unauthorized Config Changes", "framework": "ITPP"},
    {"key": "stale", "label": "Stale Configurations", "framework": "Hardening Reviews"},
]


def generate_baselining_drift() -> dict[str, Any]:
    apps = list_banking_applications()
    drift: list[dict] = []
    for app in apps[:14]:
        for cat in _DRIFT_CATEGORIES:
            seed = _seed("drift", app["application"], cat["key"])
            count = _between(seed, 0, 12)
            if count == 0 and seed % 4 != 0:
                continue
            severity = (
                "Critical" if count >= 8 else
                "High" if count >= 4 else
                "Medium" if count >= 1 else "Low"
            )
            drift.append({
                "application": app["application"],
                "category_key": cat["key"],
                "category": cat["label"],
                "framework": cat["framework"],
                "drift_count": count,
                "severity": severity,
                "last_scan": (DEMO_ANCHOR_DATE - timedelta(days=_between(seed >> 3, 1, 12))).isoformat(),
                "remediation_owner": app["owner"],
                "remediation_eta": (DEMO_ANCHOR_DATE + timedelta(days=_between(seed >> 5, 5, 45))).isoformat(),
            })
    # Aggregate by category
    by_cat: dict[str, dict] = {}
    for d in drift:
        bc = by_cat.setdefault(d["category"], {"category": d["category"], "total": 0, "critical": 0, "high": 0, "medium": 0})
        bc["total"] += d["drift_count"]
        bc[d["severity"].lower()] = bc.get(d["severity"].lower(), 0) + d["drift_count"]
    return {
        "by_category": sorted(by_cat.values(), key=lambda r: -r["total"]),
        "by_application": drift,
        "critical_drift": [d for d in drift if d["severity"] == "Critical"],
    }


# ---------------------------------------------------------------------------
# Evidence lineage — where evidence originated, reused frameworks/controls
# ---------------------------------------------------------------------------


def generate_evidence_lineage(limit: int = 25) -> list[dict[str, Any]]:
    records = get_all_evidence_records()
    try:
        from app.framework_intelligence import classify_control_themes, build_control_index
        index = build_control_index()
    except Exception:
        index = []
    by_evidence_id: dict[str, list[dict]] = {}
    for c in index:
        for ev in c.get("evidences", []):
            by_evidence_id.setdefault(ev.get("evidence_id", ""), []).append(c)
    lineage: list[dict] = []
    seen: set[str] = set()
    for ev in records:
        eid = ev.get("evidence_id")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        seed = _seed("lin", eid)
        peer_controls = by_evidence_id.get(eid, [])
        linked_frameworks = sorted({c["framework"] for c in peer_controls})
        linked_controls = [{"framework": c["framework"], "control": c["control_name"]} for c in peer_controls[:6]]
        reused_in = [fw for fw in linked_frameworks if fw != ev["framework"]]
        lineage.append({
            "evidence_id": eid,
            "evidence_name": ev["evidence_name"],
            "original_framework": ev["framework"],
            "original_control": ev["control"],
            "application": ev["application"],
            "owner": ev.get("evidence_owner") or "Unassigned",
            "uploaded_at": ev.get("upload_timestamp") or ev.get("upload_date") or "",
            "audit_status": ev.get("audit_status", ""),
            "evidence_status": ev.get("evidence_status", ""),
            "linked_frameworks": linked_frameworks,
            "reused_in_frameworks": reused_in,
            "linked_controls": linked_controls,
            "linked_observations": [
                f"OBS-{(seed >> (3 + i)) % 99999:05d}"
                for i in range(_between(seed, 0, 3))
            ],
            "linked_audit_cycle": _pick(seed >> 11, ["Q1 2026", "Q4 2025", "Annual 2026"]),
            "lineage_confidence_pct": round(min(95, 60 + len(peer_controls) * 5), 1),
        })
        if len(lineage) >= limit:
            break
    return lineage


# ---------------------------------------------------------------------------
# VAPT findings dashboard
# ---------------------------------------------------------------------------


_VAPT_FINDINGS = [
    ("SSRF in mobile login API", "Critical", 9.6),
    ("Stored XSS in admin console", "High", 7.4),
    ("Auth bypass via OAuth scope confusion", "Critical", 9.2),
    ("Outdated TLS 1.0 cipher offered", "Medium", 5.3),
    ("Verbose error pages reveal stack", "Low", 3.1),
    ("Missing rate limit on transfer API", "High", 7.8),
    ("Unencrypted JDBC connection string", "High", 7.9),
    ("Sensitive headers leaked over proxy", "Medium", 6.0),
    ("Privilege escalation via role swap endpoint", "Critical", 9.4),
    ("Insecure deserialization in legacy queue", "Critical", 9.0),
    ("Weak password policy in admin portal", "Medium", 5.6),
    ("Reflected XSS in error parameter", "Low", 3.5),
    ("Cleartext password storage in cache", "Critical", 9.1),
    ("XXE in legacy SOAP service", "High", 7.3),
    ("Open S3 bucket containing logs", "High", 8.2),
]


def generate_vapt_findings() -> dict[str, Any]:
    apps = list_banking_applications()
    findings: list[dict] = []
    for i in range(48):
        seed = _seed("vapt", i)
        finding_spec = _VAPT_FINDINGS[seed % len(_VAPT_FINDINGS)]
        app = apps[seed % len(apps)]
        status = _pick(seed >> 3, ["Open", "In Remediation", "Remediated", "Risk Accepted", "Retest Pending"])
        findings.append({
            "finding_id": f"VAPT-{seed % 99999:05d}",
            "title": finding_spec[0],
            "severity": finding_spec[1],
            "cvss": finding_spec[2],
            "application": app["application"],
            "owner": app["owner"],
            "discovered_at": (DEMO_ANCHOR_DATE - timedelta(days=_between(seed >> 5, 3, 120))).isoformat(),
            "remediation_eta": (DEMO_ANCHOR_DATE + timedelta(days=_between(seed >> 7, 5, 60))).isoformat(),
            "status": status,
            "framework_links": ["VAPT", "AppSec"],
        })
    sev_counts = {s: 0 for s in ("Critical", "High", "Medium", "Low")}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
    open_count = sum(1 for f in findings if f["status"] in ("Open", "In Remediation", "Retest Pending"))
    return {
        "summary": {
            "total_findings": len(findings),
            "open": open_count,
            "remediated": sum(1 for f in findings if f["status"] == "Remediated"),
            "risk_accepted": sum(1 for f in findings if f["status"] == "Risk Accepted"),
            "critical": sev_counts.get("Critical", 0),
            "high": sev_counts.get("High", 0),
            "medium": sev_counts.get("Medium", 0),
            "low": sev_counts.get("Low", 0),
            "avg_cvss": round(sum(f["cvss"] for f in findings) / max(len(findings), 1), 2),
        },
        "findings": findings,
        "severity_breakdown": sev_counts,
        "by_application": [
            {
                "application": app["application"],
                "open_findings": sum(1 for f in findings if f["application"] == app["application"] and f["status"] != "Remediated"),
            }
            for app in apps[:10]
        ],
    }


# ---------------------------------------------------------------------------
# CIO executive dashboard snapshot
# ---------------------------------------------------------------------------

_DEMO_TOP_RISK_PIN: list[tuple[str, str | None]] = [
    ("Customer Onboarding Platform", "Customer Onboarding"),
    ("Mobile Banking Edge", None),
    ("Enterprise Payments Hub", "Payments"),
    ("Digital Lending Platform", "Digital Lending"),
    ("Core Banking Platform", "Core Banking"),
]


def _pin_top_risk_apps(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure demo walkthrough names appear first with high risk scores."""
    by_name = {a["application"]: dict(a) for a in apps}
    pinned: list[dict[str, Any]] = []
    used: set[str] = set()
    for i, (display, source) in enumerate(_DEMO_TOP_RISK_PIN):
        base_name = source or display
        row = dict(by_name.get(base_name) or _synthetic_top_risk_row(display))
        row["application"] = display
        row["risk_score"] = max(int(row.get("risk_score", 70)), 88 - i)
        row["readiness_pct"] = row.get("audit_readiness_pct", row.get("readiness_pct", 62))
        pinned.append(row)
        used.add(display)
        if base_name != display:
            used.add(base_name)
    rest = sorted(
        (a for a in apps if a["application"] not in used),
        key=lambda a: a["risk_score"],
        reverse=True,
    )
    return pinned + rest[: max(25 - len(pinned), 0)]


def _synthetic_top_risk_row(name: str) -> dict[str, Any]:
    meta = _APP_META.get(name, {"owner": "Unassigned", "criticality": "High"})
    seed = _seed("top-risk-pin", name)
    return {
        "application": name,
        "owner": meta["owner"],
        "risk_score": _between(seed, 82, 94),
        "audit_readiness_pct": _between(seed >> 3, 48, 72),
        "readiness_pct": _between(seed >> 3, 48, 72),
        "criticality": meta.get("criticality", "High"),
    }


def generate_cio_executive() -> dict[str, Any]:
    apps = list_banking_applications()
    history = generate_audit_history(years=5)
    history_summary = summarize_audit_history(history)
    vapt = generate_vapt_findings()
    drift = generate_baselining_drift()
    ai_gov = generate_ai_governance()
    enterprise_readiness = round(sum(a["audit_readiness_pct"] for a in apps) / max(len(apps), 1), 1)
    risky_apps = _pin_top_risk_apps(apps)
    framework_coverage = len(FRAMEWORK_CATALOG)
    closure_velocity_pct = history_summary["year_trend"][-1]["closure_pct"] if history_summary["year_trend"] else 0
    return {
        "kpis": [
            {"label": "Enterprise Readiness", "value": f"{enterprise_readiness}%", "tone": "primary", "metric": "applications"},
            {"label": "Frameworks Live", "value": framework_coverage, "tone": "info", "metric": "frameworks"},
            {"label": "Applications In Scope", "value": len(apps), "tone": "primary", "metric": "applications"},
            {"label": "Open VAPT Findings", "value": vapt["summary"]["open"], "tone": "danger", "metric": "vapt"},
            {"label": "AI Hallucination Alerts", "value": ai_gov["summary"]["hallucination_alerts"], "tone": "warning", "metric": "hallucinations"},
            {"label": "Drift (Critical)", "value": len(drift["critical_drift"]), "tone": "danger", "metric": "drift"},
            {"label": "Audit Closure Velocity", "value": f"{closure_velocity_pct}%", "tone": "success", "metric": "audit_history"},
            {"label": "Regulator Readiness", "value": "Green" if enterprise_readiness >= 80 else "Amber", "tone": "success" if enterprise_readiness >= 80 else "warning", "metric": "frameworks"},
        ],
        "top_risk_apps": [
            {
                "application": a["application"],
                "risk_score": a["risk_score"],
                "owner": a["owner"],
                "readiness_pct": a["audit_readiness_pct"],
                "criticality": a["criticality"],
            }
            for a in risky_apps
        ],
        "audit_year_trend": history_summary["year_trend"],
        "ai_governance_posture": {
            "hallucinations": ai_gov["summary"]["hallucination_alerts"],
            "unsafe": ai_gov["summary"]["unsafe_prompts"],
            "avg_risk": ai_gov["summary"]["avg_risk_score"],
            "model_coverage": ai_gov["summary"]["model_coverage"],
        },
    }


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------


def build_demo_overview() -> dict[str, Any]:
    apps = list_banking_applications()
    frameworks = list_frameworks_catalog()
    tickets = generate_servicenow_tickets()
    ai_gov = generate_ai_governance()
    history = generate_audit_history()
    history_summary = summarize_audit_history(history)
    risk_heat = build_risk_heatmap()
    drift = generate_baselining_drift()
    lineage = generate_evidence_lineage()
    vapt = generate_vapt_findings()
    cio = generate_cio_executive()
    return {
        "demo_mode": DEMO_MODE,
        "anchor_date": DEMO_ANCHOR_DATE.isoformat(),
        "kpis": [
            {"label": "Banking Applications", "value": len(apps), "tone": "primary", "metric": "applications"},
            {"label": "Frameworks", "value": len(frameworks), "tone": "info", "metric": "frameworks"},
            {"label": "Controls", "value": sum(f["control_count"] for f in frameworks), "tone": "primary", "metric": "controls"},
            {"label": "Evidence Records", "value": sum(f["evidence_count"] for f in frameworks), "tone": "success", "metric": "evidence"},
            {"label": "ServiceNow Tickets", "value": len(tickets), "tone": "warning", "metric": "tickets"},
            {"label": "AI Prompts Audited", "value": ai_gov["summary"]["prompts_audited"], "tone": "primary", "metric": "prompts"},
            {"label": "Hallucination Alerts", "value": ai_gov["summary"]["hallucination_alerts"], "tone": "danger", "metric": "hallucinations"},
            {"label": "Open VAPT", "value": vapt["summary"]["open"], "tone": "danger", "metric": "vapt"},
            {"label": "Critical Drift", "value": len(drift["critical_drift"]), "tone": "danger", "metric": "drift"},
            {"label": "5-Yr Avg Closure", "value": f"{round(sum(t['closure_pct'] for t in history_summary['year_trend']) / max(len(history_summary['year_trend']), 1), 1)}%", "tone": "success", "metric": "audit_history"},
        ],
        "banking_applications": apps,
        "frameworks": frameworks,
        "servicenow_tickets": tickets,
        "ai_governance": ai_gov,
        "audit_history": history,
        "audit_history_summary": history_summary,
        "risk_heatmap": risk_heat,
        "baselining_drift": drift,
        "evidence_lineage": lineage,
        "vapt": vapt,
        "cio_executive": cio,
    }
