"""Enterprise-scale demo data for Risk Register & Governance Analytics (presentation only)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app import ecs_state
from app.demo_data_standards import (
    BANKING_APPLICATIONS,
    BANKING_OWNERS,
    between,
    expand_catalog,
    generate_audit_trail,
    generate_monthly_trend,
    pick,
    seed,
)
from app.demo_metrics import FRAMEWORK_MATURITY_BASELINE
from app.enterprise_grc import RISK_CATEGORIES, RISK_TREATMENTS

ANCHOR = date(2026, 5, 28)

_RISK_TITLES = [
    "Legacy TLS 1.0 on payment gateway edge",
    "Delayed VAPT remediation — Mobile Banking",
    "DR drill overdue — Treasury FX core",
    "Cloud IAM excessive privileges — UPI cluster",
    "OS baselining drift — Net Banking middleware",
    "Third-party PSP API key rotation overdue",
    "DB encryption gap — Loan origination schema",
    "P1 net banking outage MTTR SLA breach",
    "NPCI settlement reconciliation control gap",
    "Privileged access review incomplete — Core Banking",
    "WAF bypass finding — Internet banking edge",
    "Stale PCI ASV scan evidence — Cards channel",
    "Consent log retention gap — Mobile onboarding",
    "SIEM use-case failure — fraud monitoring",
    "Unpatched critical CVE — ATM switch cluster",
    "Segregation of duties violation — Treasury deals",
    "API rate limiting absent — merchant portal",
    "Backup restore test failed — Data Lake",
    "Expired TD on encryption exception — Payments",
    "Model risk assessment overdue — AI assistant",
    "Incomplete SOX ITGC sampling — Core Banking",
    "Vendor SOC2 report expired — CRM integration",
    "Missing MFA on DBA jump hosts",
    "Insecure S3 bucket policy — analytics sandbox",
    "RBI cyber circular gap — incident reporting SLA",
]

_FRAMEWORKS = list(FRAMEWORK_MATURITY_BASELINE.keys()) + ["AI Governance", "Regulatory Mapping"]

_REJECTION_REASONS = [
    "Expired evidence", "Insufficient proof", "Incorrect scope",
    "Outdated screenshots", "Failed validations", "Missing attestation",
    "Wrong environment", "Incomplete sample period",
]


def _generate_risk_rows(count: int = 42) -> list[dict]:
    rows: list[dict] = []
    bus = ["Retail Banking", "Digital Banking", "Digital Payments", "Treasury", "Wholesale Banking", "Retail Lending", "IT Platform"]
    for i in range(count):
        s = seed("risk", i)
        app = pick(s, BANKING_APPLICATIONS)
        cat = pick(s >> 2, RISK_CATEGORIES)
        inherent = pick(s >> 4, ["Critical", "High", "High", "Medium", "Low"])
        residual = pick(s >> 6, ["Critical", "High", "Medium", "Low"])
        aging = between(s >> 8, 4, 220)
        open_d = ANCHOR - timedelta(days=aging)
        fw = pick(s >> 10, _FRAMEWORKS)
        owner = pick(s >> 12, BANKING_OWNERS)
        status = pick(s >> 14, ["Open", "Open", "Escalated", "Mitigation In Progress", "Accepted", "Closed"])
        title = _RISK_TITLES[i % len(_RISK_TITLES)]
        if i >= len(_RISK_TITLES):
            title = f"{title} — track {i + 1}"
        rid = f"RSK-2026-{i + 1:03d}"
        obs_count = between(s >> 16, 1, 4)
        rows.append({
            "risk_id": rid,
            "title": title,
            "description": f"Enterprise risk identified during {pick(s, ['Q2 audit', 'VAPT cycle', 'regulatory review', 'continuous monitoring'])} — {app}.",
            "category": cat,
            "business_unit": pick(s >> 18, bus),
            "application": app,
            "owner": f"{owner} (App Owner)",
            "inherent_risk": inherent,
            "residual_risk": residual,
            "treatment": pick(s >> 20, RISK_TREATMENTS),
            "acceptance": pick(s >> 22, ["Pending CIO", "Not accepted", "—", "CIO approved"]),
            "regulatory_impact": f"{fw}, RBI Cyber",
            "open_date": open_d.strftime("%Y-%m-%d"),
            "due_date": (ANCHOR + timedelta(days=between(s >> 24, 15, 120))).strftime("%Y-%m-%d"),
            "aging_days": aging,
            "status": status,
            "linked_control": f"{fw}::{pick(s, ['Access Control', 'Encryption', 'Logging', 'DR Drill', 'VAPT Finding'])}",
            "linked_framework": fw,
            "framework": fw,
            "risk": residual,
            "linked_observations": [
                {
                    "observation_id": f"OBS-{rid.replace('RSK-', '')}-{j + 1}",
                    "title": f"{title[:48]} — finding {j + 1}",
                    "status": pick(seed(rid, j), ["Open", "In Remediation", "Closed"]),
                    "framework": fw,
                }
                for j in range(obs_count)
            ],
            "impacted_applications": [app] + ([pick(seed(rid, "x"), BANKING_APPLICATIONS)] if i % 3 == 0 else []),
            "mitigation_plans": [
                f"Target remediation by {(ANCHOR + timedelta(days=30)).strftime('%Y-%m-%d')}",
                f"Owner action: {owner}",
                f"Compensating control review — {fw}",
            ],
            "evidence_gaps": [
                f"EVD-{rid[-3:]}-001 — attestation pending",
                f"EVD-{rid[-3:]}-002 — scan export missing",
            ][: between(s >> 26, 1, 2)],
        })
    return rows


def build_risk_register_demo(role: str = "owner") -> dict[str, Any]:
    risks = _generate_risk_rows(42)
    high_open = [r for r in risks if r["residual_risk"] in ("Critical", "High") and r["status"] not in ("Closed", "Accepted")]
    bu_exposure: dict[str, int] = {}
    for r in risks:
        bu_exposure[r["business_unit"]] = bu_exposure.get(r["business_unit"], 0) + 1
    category_counts: dict[str, int] = {}
    for r in risks:
        category_counts[r["category"]] = category_counts.get(r["category"], 0) + 1
    severity_chart = [
        {"label": cat.replace(" Risk", ""), "value": cnt, "tone": "red" if cnt >= 5 else "orange", "category": cat}
        for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1])
    ]
    aging_buckets = [(0, 30), (31, 60), (61, 90), (91, 120), (121, 180), (181, 9999)]
    aging_trend = [
        {"label": f"{lo}–{'+' if hi > 200 else hi}d", "value": len([r for r in risks if lo <= r["aging_days"] <= hi]), "lo": lo, "hi": hi}
        for lo, hi in aging_buckets
    ]
    escalation_timeline = sorted(
        [
            {"risk_id": r["risk_id"], "title": r["title"][:55], "date": r["open_date"], "severity": r["residual_risk"], "status": r["status"]}
            for r in risks if r["status"] in ("Escalated", "Open") and r["residual_risk"] in ("Critical", "High")
        ],
        key=lambda x: x["date"], reverse=True,
    )
    audit_history = generate_audit_trail(
        72, ANCHOR, years_back=3,
        detail_builder=lambda i, action, actor: f"{pick(seed('rah', i), risks)['risk_id']} — {action}",
    )
    return {
        "rows": risks,
        "kpis": [
            {"label": "Total Risks", "value": len(risks), "tone": "primary", "drill": "total"},
            {"label": "Open High/Critical", "value": len(high_open), "tone": "danger", "drill": "high_open"},
            {"label": "Escalated", "value": len([r for r in risks if r["status"] == "Escalated"]), "tone": "warning", "drill": "escalated"},
            {"label": "Avg Aging (days)", "value": round(sum(r["aging_days"] for r in risks) / len(risks)), "tone": "info", "drill": "aging"},
        ],
        "top_risks": sorted(risks, key=lambda x: (-{"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(x["residual_risk"], 0), x["aging_days"]))[:15],
        "high_open": high_open,
        "bu_exposure": [{"unit": k, "count": v} for k, v in sorted(bu_exposure.items(), key=lambda x: -x[1])],
        "severity_chart": severity_chart,
        "aging_trend": aging_trend,
        "escalation_timeline": escalation_timeline,
        "audit_history": audit_history,
        "role": role,
    }


def _monthly_governance_series(months: int = 14) -> list[dict]:
    points = generate_monthly_trend(
        months, ANCHOR, prefix="gov_cov",
        value_fn=lambda s, _i: between(s, 74, 92),
        label_fmt="%b %Y",
    )
    series = []
    for pt in points:
        s = seed("gov_m", pt["month_key"])
        opened = between(s, 12, 38)
        closed = between(s >> 2, 14, 42)
        rejections = between(s >> 4, 4, 18)
        submitted = max(rejections * 15, 95)
        series.append({
            **pt,
            "coverage_pct": pt["value"],
            "compliance": pt["value"],
            "controls_in_scope": between(s >> 6, 180, 320),
            "evidences_valid": between(s >> 8, 120, 280),
            "opened": opened,
            "closed": closed,
            "net": closed - opened,
            "rate_pct": round(rejections / submitted * 100, 1),
            "rejections": rejections,
            "submitted": submitted,
            "on_time_pct": between(s >> 10, 84, 97),
            "breaches": between(s >> 12, 2, 14),
            "observation_records": [
                {
                    "obs_id": f"OBS-{pt['month_key'].replace('-', '')}-{j + 1:03d}",
                    "application": pick(seed(pt["month_key"], j), BANKING_APPLICATIONS),
                    "framework": pick(seed("obf", pt["month_key"], j), _FRAMEWORKS),
                    "title": pick(seed("obt", j), ["Control gap", "Evidence stale", "VAPT finding", "Policy deviation"]),
                    "severity": pick(seed("obs", j), ["High", "Medium", "Critical"]),
                    "status": pick(seed("obst", j), ["Open", "Closed", "In Remediation"]),
                }
                for j in range(opened)
            ],
            "rejection_records": [
                {
                    "evidence_id": f"EVD-REJ-{pt['month_key'].replace('-', '')}-{j + 1:03d}",
                    "application": pick(seed("rej", pt["month_key"], j), BANKING_APPLICATIONS),
                    "framework": pick(seed("rjf", j), _FRAMEWORKS),
                    "reason": pick(seed("rjr", j), _REJECTION_REASONS),
                    "reviewer": pick(seed("rjv", j), ["S. Nair (Auditor)", "KPMG", "Internal Audit"]),
                }
                for j in range(rejections)
            ],
        })
    return series


def build_governance_analytics_demo(role: str = "cio", filters: dict | None = None) -> dict[str, Any]:
    series = _monthly_governance_series(14)
    current_cov = series[-1]["coverage_pct"]

    top_apps = expand_catalog([], 22, lambda n: {
        "application": pick(seed("gra", n), BANKING_APPLICATIONS),
        "compliance_pct": between(seed("grc", n), 68, 94),
        "open_observations": between(seed("gro", n), 2, 22),
        "high_risk_gaps": between(seed("grg", n), 1, 14),
        "stale_evidences": between(seed("grs", n), 1, 16),
        "sla_breaches": between(seed("grb", n), 0, 8),
        "risk": pick(seed("grr", n), ["Critical", "High", "Medium", "Low"]),
    })

    repeat_failures = expand_catalog([], 28, lambda n: {
        "framework": pick(seed("rfw", n), _FRAMEWORKS),
        "control": f"{pick(seed('rfc', n), ['AS-C', 'PCI', 'DP-C', 'IT-C'])}-{between(seed('rfn', n), 2, 48)} {pick(seed('rft', n), ['Encryption', 'MFA', 'Logging', 'DR', 'Access Review'])}",
        "reason": pick(seed("rfr", n), _REJECTION_REASONS + ["SLA breach", "Escalated"]),
        "count": between(seed("rfcnt", n), 1, 5),
        "application": pick(seed("rfa", n), BANKING_APPLICATIONS),
    })

    open_findings = expand_catalog([], 35, lambda n: {
        "finding_id": f"FND-2026-{n + 1:04d}",
        "framework": pick(seed("off", n), _FRAMEWORKS),
        "application": pick(seed("ofa", n), BANKING_APPLICATIONS),
        "control": f"CTRL-{between(seed('ofc', n), 100, 999)}",
        "severity": pick(seed("ofs", n), ["Critical", "High", "Medium"]),
        "owner": pick(seed("ofo", n), BANKING_OWNERS),
        "aging_days": between(seed("ofd", n), 5, 120),
        "status": pick(seed("ofst", n), ["Open", "In Remediation", "Pending Evidence"]),
    })

    high_risk_controls = expand_catalog([], 24, lambda n: {
        "framework": pick(seed("hrcf", n), _FRAMEWORKS),
        "control": f"{pick(seed('hrcc', n), ['Req', 'AS-C', 'DP-C'])}-{between(seed('hrcn', n), 1, 40)}",
        "risk": pick(seed("hrcr", n), ["Critical", "High"]),
        "aging_days": between(seed("hrca", n), 14, 95),
        "application": pick(seed("hrcap", n), BANKING_APPLICATIONS),
    })

    control_effectiveness = {fw: between(seed("cef", fw), 72, 96) for fw in _FRAMEWORKS}
    fw_effectiveness_rows = [
        {"framework": fw, "effectiveness_pct": pct, "controls_tested": between(seed("cet", fw), 24, 88), "gaps": between(seed("ceg", fw), 1, 12)}
        for fw, pct in control_effectiveness.items()
    ]

    rejection_reasons = []
    for i, reason in enumerate(_REJECTION_REASONS):
        s = seed("rejrs", i)
        cnt = between(s, 8, 42)
        rejection_reasons.append({
            "reason": reason, "pct": between(s >> 2, 8, 28), "count": cnt,
            "records": [
                {"evidence_id": f"EVD-RJ-{i+1:02d}-{j+1:03d}", "application": pick(seed("rjra", i, j), BANKING_APPLICATIONS),
                 "framework": pick(seed("rjrf", i, j), _FRAMEWORKS), "reviewer": "S. Nair (Auditor)"}
                for j in range(min(cnt, 15))
            ],
        })

    sla_framework = [
        {"framework": fw, "on_time_pct": between(seed("slaf", fw), 82, 97), "overdue": between(seed("slao", fw), 1, 10)}
        for fw in _FRAMEWORKS[:10]
    ]

    audit_history = generate_audit_trail(80, ANCHOR, years_back=3, actions=[
        "Audit Readiness Review", "Evidence Approved", "Finding Raised", "SLA Breach Escalated",
        "Framework Mapping Updated", "Remediation Closed", "Rejection Recorded",
    ])

    open_findings_count = len([f for f in open_findings if f["status"] != "Closed"])
    stale_pct = round(between(seed("stale"), 8, 14), 1)
    audit_readiness = round(current_cov * 0.98, 1)

    intel = {
        "scope_summary": "Enterprise-wide · all onboarded applications · last 14 months",
        "implementation_coverage": {
            "title": "Control Implementation Coverage",
            "tooltip": "Controls with valid evidence, active owner, and approved audit status.",
            "current_pct": current_cov,
            "series": [{k: v for k, v in row.items() if k not in ("observation_records", "rejection_records")} for row in series],
            "_series_full": series,
        },
        "observations": {
            "title": "Audit Observations Opened vs Closed",
            "tooltip": "Control observations, evidence gaps, audit findings, remediation tickets.",
            "series": [{"month": r["month"], "month_key": r["month_key"], "opened": r["opened"], "closed": r["closed"], "net": r["net"]} for r in series],
            "_series_full": series,
            "closure_rate_pct": round(sum(r["closed"] for r in series) / max(sum(r["opened"] for r in series), 1) * 100, 1),
            "avg_days_to_close": 16.4,
        },
        "rejection_rate": {
            "title": "Auditor Evidence Rejection Rate",
            "series": [{"month": r["month"], "month_key": r["month_key"], "rate_pct": r["rate_pct"], "rejections": r["rejections"], "submitted": r["submitted"]} for r in series],
            "_series_full": series,
            "top_reasons": rejection_reasons,
            "latest_rate_pct": series[-1]["rate_pct"],
        },
        "sla_compliance": {
            "title": "Remediation SLA Compliance",
            "series": [{"month": r["month"], "month_key": r["month_key"], "on_time_pct": r["on_time_pct"], "breaches": r["breaches"]} for r in series],
            "framework_wise": sla_framework,
            "latest_on_time_pct": series[-1]["on_time_pct"],
            "total_breaches": sum(r["breaches"] for r in series[-3:]),
        },
        "top_risk_applications": top_apps,
    }

    return {
        "kpis": [
            {"label": "Audit Readiness", "value": f"{audit_readiness}%", "tone": "primary", "drill": "audit_readiness", "tooltip": "Approved controls with active evidence."},
            {"label": "Open Audit Findings", "value": open_findings_count, "tone": "danger", "drill": "open_findings", "tooltip": "Unresolved observations and evidence gaps."},
            {"label": "High-Risk Controls", "value": len(high_risk_controls), "tone": "warning", "drill": "high_risk_controls", "tooltip": "Critical/High controls with aging remediation."},
            {"label": "Evidence Freshness", "value": f"{100 - stale_pct:.0f}%", "tone": "success", "drill": "evidence_freshness", "tooltip": "Evidences refreshed within 60 days."},
        ],
        "intel": intel,
        "top_risk_applications": top_apps,
        "control_effectiveness": control_effectiveness,
        "framework_effectiveness_rows": fw_effectiveness_rows,
        "repeat_failures": repeat_failures,
        "open_findings": open_findings,
        "high_risk_controls": high_risk_controls,
        "audit_history": audit_history,
        "governance_extended": {
            "audit_readiness_pct": audit_readiness,
            "open_findings": open_findings_count,
            "stale_evidence_pct": stale_pct,
            "top_risky_controls": high_risk_controls,
        },
        "role": role,
    }


def drill_risk_register(metric: str, item_id: str = "", role: str = "owner") -> dict[str, Any]:
    data = build_risk_register_demo(role)
    risks = data["rows"]
    if metric == "total":
        return {"type": "list", "title": f"All Enterprise Risks ({len(risks)})", "rows": risks}
    if metric == "high_open":
        rows = data["high_open"]
        return {"type": "list", "title": f"Open High/Critical Risks ({len(rows)})", "rows": rows}
    if metric == "escalated":
        rows = [r for r in risks if r["status"] == "Escalated"]
        return {"type": "list", "title": f"Escalated Risks ({len(rows)})", "rows": rows}
    if metric == "aging":
        return {"type": "list", "title": "Risk Aging Distribution", "rows": data["aging_trend"]}
    if metric == "category" and item_id:
        rows = [r for r in risks if r["category"] == item_id or r["category"].startswith(item_id)]
        if not rows:
            rows = [r for r in risks if item_id in r["category"]]
        return {"type": "list", "title": f"{item_id} ({len(rows)})", "rows": rows}
    if metric == "aging_bucket" and item_id:
        parts = item_id.split("-")
        lo, hi = int(parts[0]), int(parts[1])
        rows = [r for r in risks if lo <= r["aging_days"] <= hi]
        return {"type": "list", "title": f"Aging {lo}–{hi}d ({len(rows)})", "rows": rows}
    if metric == "bu" and item_id:
        rows = [r for r in risks if r["business_unit"] == item_id]
        return {"type": "list", "title": f"{item_id} — Open Risks ({len(rows)})", "rows": rows}
    if metric == "audit":
        return {"type": "list", "title": f"Risk Audit History ({len(data['audit_history'])})", "rows": data["audit_history"]}
    if item_id and metric in ("risk", "", "detail"):
        row = next((r for r in risks if r["risk_id"] == item_id), None)
        if row:
            return {"type": "risk", "title": f"{row['risk_id']} — {row['title'][:50]}", "data": row}
    if item_id:
        row = next((r for r in risks if r["risk_id"] == item_id), risks[0])
        return {"type": "risk", "title": f"{row['risk_id']} — {row['title'][:50]}", "data": row}
    return {"type": "summary", "title": "Risk Register", "data": {"total": len(risks)}, "rows": risks[:20]}


def drill_governance_analytics(metric: str, item_id: str = "", role: str = "cio") -> dict[str, Any]:
    data = build_governance_analytics_demo(role)
    intel = data["intel"]
    if metric == "audit_readiness":
        return {"type": "list", "title": "Framework Effectiveness", "rows": data["framework_effectiveness_rows"]}
    if metric == "open_findings":
        rows = data["open_findings"]
        return {"type": "list", "title": f"Open Audit Findings ({len(rows)})", "rows": rows}
    if metric == "high_risk_controls":
        rows = data["high_risk_controls"]
        return {"type": "list", "title": f"High-Risk Controls ({len(rows)})", "rows": rows}
    if metric == "evidence_freshness":
        stale = intel["implementation_coverage"]["_series_full"][-1]
        return {"type": "list", "title": "Stale Evidence by Application", "rows": data["top_risk_applications"]}
    if metric == "coverage_month" and item_id:
        row = next((r for r in intel["implementation_coverage"]["_series_full"] if r["month_key"] == item_id or r["month"] == item_id), None)
        if row:
            return {"type": "list", "title": f"Coverage — {row['month']} ({row['coverage_pct']}%)", "rows": row.get("observation_records", [])[: row["opened"]]}
        return {"type": "list", "title": "Coverage detail", "rows": []}
    if metric == "observations_month" and item_id:
        row = next((r for r in intel["observations"]["_series_full"] if r["month_key"] == item_id), None)
        if row:
            recs = row.get("observation_records", [])
            return {"type": "list", "title": f"Observations — {row['month']} opened {row['opened']} ({len(recs)})", "rows": recs}
        return {"type": "list", "title": "Observations", "rows": []}
    if metric == "rejection_month" and item_id:
        row = next((r for r in intel["rejection_rate"]["_series_full"] if r["month_key"] == item_id), None)
        if row:
            recs = row.get("rejection_records", [])
            return {"type": "list", "title": f"Rejections — {row['month']} ({len(recs)})", "rows": recs}
        return {"type": "list", "title": "Rejections", "rows": []}
    if metric == "framework" and item_id:
        rows = [r for r in data["repeat_failures"] if r["framework"] == item_id]
        eff = next((r for r in data["framework_effectiveness_rows"] if r["framework"] == item_id), {})
        return {"type": "framework", "title": f"{item_id} — {eff.get('effectiveness_pct', '—')}% effective", "data": eff, "rows": rows}
    if metric == "rejection_reason" and item_id:
        reason = next((r for r in intel["rejection_rate"]["top_reasons"] if r["reason"] == item_id), None)
        if reason:
            return {"type": "list", "title": f"{item_id} ({reason['count']})", "rows": reason.get("records", [])}
        return {"type": "list", "title": item_id, "rows": []}
    if metric == "application" and item_id:
        row = next((a for a in data["top_risk_applications"] if a["application"] == item_id), data["top_risk_applications"][0])
        return {"type": "application", "title": f"{item_id} — Risk Posture", "data": row}
    if metric == "repeat_failures":
        return {"type": "list", "title": f"Repeat Failures ({len(data['repeat_failures'])})", "rows": data["repeat_failures"]}
    if metric == "audit":
        return {"type": "list", "title": f"Governance Audit History ({len(data['audit_history'])})", "rows": data["audit_history"]}
    return {"type": "summary", "title": "Governance Analytics", "data": data["governance_extended"]}
