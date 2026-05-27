"""Enterprise audit copilot — intent routing, live analytics, conversational context."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from app.analytics_module import application_comparison, enterprise_dashboard
from app.demo_metrics import BUSINESS_UNITS, display_framework_maturity, enterprise_kpis
from app.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records, get_framework_controls
from app.workflow_module import (
    FRAMEWORK_DESCRIPTIONS,
    build_auditor_review_queue,
    build_owner_work_queue,
    framework_pending_count,
    work_queue_summary,
)

_context: dict[str, dict] = {}
_history: dict[str, list[dict]] = {}
_structured: dict[str, str] = {}
MAX_HISTORY = 8

FRAMEWORK_ALIASES = {
    "pci dss": "PCI DSS",
    "pci": "PCI DSS",
    "dpsc": "DPSC",
    "os baselining": "OS Baselining",
    "os baseline": "OS Baselining",
    "db baselining": "DB Baselining",
    "db baseline": "DB Baselining",
    "nginx baselining": "Nginx Baselining",
    "nginx": "Nginx Baselining",
    "csite": "CSITE",
    "appsec": "AppSec",
    "application security": "AppSec",
    "vapt": "VAPT",
    "penetration": "VAPT",
    "pen test": "VAPT",
    "itpp": "ITPP",
    "it policies": "ITPP",
    "policies and procedures": "ITPP",
    "disaster recovery": "ITPP",
    "change management": "ITPP",
}

MODULE_DEFINITIONS = {
    "Evidence Reuse": "Cross-framework evidence reuse engine — map once, satisfy multiple controls, reduce duplicate uploads.",
    "Lifecycle Management": "Evidence lifecycle governance from draft through active, expiring, archived, and retired states.",
    "Audit Prep": "Audit readiness cockpit — upcoming audits, missing controls, and mock-audit preparation.",
    "Enterprise Compliance": "Organization-wide governance KPIs, framework maturity, and business-unit risk posture.",
    "Pan India Governance": "Regional branch compliance visibility with zone-level risk and SLA breach tracking.",
}

FRAMEWORK_WHY = {
    "PCI DSS": "Mandatory for cardholder data environments (CDE), payment gateways, and RBI-aligned IT governance.",
    "DPSC": "Required for UPI, card switch, API banking, and RBI DPSC self-assessment.",
    "OS Baselining": "CIS-aligned server hardening across Net Banking, UPI, and middleware production fleets.",
    "DB Baselining": "Oracle CBS, treasury, and loan-system database security for SOX and internal audit.",
    "Nginx Baselining": "Internet banking edge, mobile API gateway, and DMZ reverse-proxy TLS/WAF compliance.",
    "CSITE": "Enterprise cyber evaluation — SOC, SIEM, EDR, IR readiness, and board-level IT risk.",
    "AppSec": "SAST/DAST, dependency and secrets scanning, API security, and secure SDLC evidence.",
    "VAPT": "Internal/external vulnerability assessment, penetration testing, and remediation closure validation.",
    "ITPP": "Operational governance — DR, backup, change, incident, problem, capacity, and availability management.",
}

FOLLOW_UP_DEFAULTS = [
    "Show high-risk controls",
    "Show expiring evidences",
    "Show rejected observations",
    "Show SLA breaches",
]

CLARIFICATION_PROMPT = (
    "I need a bit more context to give an accurate answer (I won't guess metrics).\n\n"
    "Please clarify:\n"
    "• Which framework? (PCI DSS, VAPT, AppSec, CSITE, ITPP, DPSC, OS/DB/Nginx Baselining)\n"
    "• Which application or business unit?\n"
    "• Do you want pending, approved, or rejected counts?\n"
    "• Which time period? (this week, overdue, TD expired)"
)


def _session_key(user: str, role: str) -> str:
    return f"{user}:{role}"


def get_context(user: str, role: str) -> dict:
    return _context.setdefault(_session_key(user, role), {"framework": "", "topic": "", "application": "", "module": "", "severity": "", "user_role": role})


def update_chat_context(user: str, role: str, query: str = "", **extra) -> dict:
    """Merge parsed query context for quick-action scoping."""
    from app.chatbot_context_engine import parse_query_context

    ctx = get_context(user, role)
    ctx["user_role"] = role
    if query:
        parsed = parse_query_context(query, ctx)
        ctx.update(parsed)
    ctx.update({k: v for k, v in extra.items() if v})
    return ctx


def get_chat_history(user: str, role: str, limit: int = 6) -> list[dict]:
    return _history.get(_session_key(user, role), [])[-limit:]


def set_chat_structured(user: str, role: str, html: str):
    _structured[_session_key(user, role)] = html


def get_chat_structured(user: str, role: str) -> str:
    return _structured.get(_session_key(user, role), "")


def clear_chat_structured(user: str, role: str):
    _structured.pop(_session_key(user, role), None)


def record_exchange(user: str, role: str, query: str, response: str):
    key = _session_key(user, role)
    _history.setdefault(key, []).append({
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        "query": query,
        "response": response[:500],
    })
    if len(_history[key]) > MAX_HISTORY:
        _history[key] = _history[key][-MAX_HISTORY:]


def _detect_framework(q: str, ctx: dict) -> str:
    ql = q.lower()
    for alias, name in sorted(FRAMEWORK_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in ql:
            return name
    for name in FRAMEWORK_CATALOG:
        if name.lower() in ql:
            return name
    return ctx.get("framework", "")


def _detect_topic(q: str) -> str:
    ql = q.lower()
    if any(w in ql for w in ("high risk", "high-risk", "critical risk")):
        return "high_risk"
    if "expir" in ql or "td expired" in ql or "stale" in ql:
        return "expired"
    if "reject" in ql:
        return "rejected"
    if "pending" in ql or "open" in ql or "await" in ql:
        return "pending"
    if "maturity" in ql:
        return "maturity"
    if "sla" in ql or "overdue" in ql or "breach" in ql:
        return "sla"
    if "approve" in ql:
        return "approval"
    return ""


def _role_label(role: str) -> str:
    labels = {
        "owner": "App Owner",
        "auditor": "Auditor",
        "cio": "CIO",
        "vertical_head": "Vertical Head",
        "compliance_head": "Compliance Head",
        "compliance_officer": "Compliance Officer",
        "functional_head": "Functional Head",
    }
    return labels.get(role, role.replace("_", " ").title())


def _fw_metrics(framework: str) -> dict:
    stats = ecs_state.build_evidence_analytics()
    fw = next((f for f in stats["framework_stats"] if f["name"] == framework), None)
    if not fw:
        return {}
    mature = next(
        (f for f in display_framework_maturity(stats["framework_stats"]) if f["name"] == framework),
        fw,
    )
    ctrls = get_framework_controls(framework)
    ev_count = sum(len(c["evidences"]) for c in ctrls)
    owner_q = [i for i in build_owner_work_queue(500) if i["framework"] == framework]
    auditor_q = [i for i in build_auditor_review_queue(500) if i["framework"] == framework]
    expired = [
        r for r in get_all_evidence_records()
        if r.get("framework") == framework and r.get("evidence_status") == "Expired"
    ]
    high_risk = [i for i in owner_q + auditor_q if i.get("risk_rating") in ("Critical", "High")]
    return {
        "controls": len(ctrls),
        "evidences": ev_count,
        "maturity_pct": mature.get("maturity_pct", mature.get("compliance_pct", 0)),
        "pending": fw["pending"] + fw["rejected"],
        "submitted": fw["submitted"],
        "approved": fw["approved"],
        "total": fw["total"],
        "open_observations": fw["pending"] + fw["submitted"] + fw["rejected"],
        "high_risk_count": len(high_risk),
        "expired_count": len(expired),
        "owner_pending": len(owner_q),
        "auditor_pending": len(auditor_q),
    }


def _top_risk_controls(framework: str, limit: int = 3) -> list[str]:
    items = []
    for i in build_owner_work_queue(200) + build_auditor_review_queue(200):
        if i["framework"] == framework and i.get("risk_rating") in ("Critical", "High", "Medium"):
            items.append(i["control"])
    seen: set[str] = set()
    out = []
    for c in items:
        if c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= limit:
            break
    if not out:
        for c in get_framework_controls(framework)[:limit]:
            out.append(c["control"])
    return out


def _format_response(
    title: str,
    body: str,
    *,
    framework: str = "",
    role: str = "",
    metrics: dict | None = None,
    insights: list[str] | None = None,
    follow_ups: list[str] | None = None,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    role_txt = _role_label(role) if role else "Enterprise User"
    lines = [f"ECS Audit Copilot · {ts} · Role: {role_txt}"]
    if framework:
        lines.append(f"[{framework}]")
    lines.append("")
    if title:
        lines.append(title)
        lines.append("")
    lines.append(body)
    if metrics:
        lines.append("")
        lines.append("Current ECS metrics (live):")
        for k, v in metrics.items():
            lines.append(f"  • {k.replace('_', ' ').title()}: {v}")
    if insights:
        lines.append("")
        lines.append("Actionable insights:")
        for ins in insights:
            lines.append(f"  → {ins}")
    lines.append("")
    lines.append("Suggested questions:")
    for fu in (follow_ups or FOLLOW_UP_DEFAULTS)[:4]:
        lines.append(f"  • {fu}")
    return "\n".join(lines)


def _framework_definition_answer(framework: str, role: str) -> str:
    desc = FRAMEWORK_DESCRIPTIONS.get(framework, MODULE_DEFINITIONS.get(framework, ""))
    why = FRAMEWORK_WHY.get(framework, "Enterprise banking governance and audit readiness.")
    m = _fw_metrics(framework)
    examples = [c["control"] for c in get_framework_controls(framework)[:3]]
    body = (
        f"{framework} is the enterprise compliance framework governing {desc.lower().rstrip('.')}.\n\n"
        f"Why it matters: {why}\n\n"
        f"Sample controls in scope: {'; '.join(examples)}."
    )
    metrics = {
        "controls_in_scope": m.get("controls", 0),
        "evidence_artefacts": m.get("evidences", 0),
        "maturity": f"{m.get('maturity_pct', 0)}%",
        "open_observations": m.get("open_observations", 0),
        "high_risk_items": m.get("high_risk_count", 0),
        "TD_expired_evidences": m.get("expired_count", 0),
    }
    top = _top_risk_controls(framework, 1)
    insights = [f"Prioritize: {top[0][:50]}"] if top else ["Review pending queue on framework page."]
    return _format_response(f"{framework} — Enterprise Framework", body, framework=framework, role=role, metrics=metrics, insights=insights)


def _framework_controls_answer(framework: str, role: str) -> str:
    ctrls = get_framework_controls(framework)
    names = [f"{c['control_id']}: {c['control']}" for c in ctrls[:8]]
    m = _fw_metrics(framework)
    body = f"{framework} control catalogue ({len(ctrls)} controls):\n" + "\n".join(f"  • {n}" for n in names)
    if len(ctrls) > 8:
        body += f"\n  … and {len(ctrls) - 8} additional controls."
    return _format_response(f"{framework} Controls", body, framework=framework, role=role, metrics={"total_controls": len(ctrls), "maturity": f"{m.get('maturity_pct')}%"})


def _maturity_answer(framework: str, role: str) -> str:
    if framework:
        m = _fw_metrics(framework)
        body = (
            f"{framework} display maturity is {m.get('maturity_pct')}% with "
            f"{m.get('approved')}/{m.get('total')} controls auditor-approved live."
        )
        return _format_response(f"{framework} Maturity", body, framework=framework, role=role, metrics=m)
    stats = ecs_state.build_evidence_analytics()
    parts = [f"{f['name']}: {f.get('maturity_pct', f['compliance_pct'])}%" for f in display_framework_maturity(stats["framework_stats"])]
    lowest = min(display_framework_maturity(stats["framework_stats"]), key=lambda x: x.get("maturity_pct", x["compliance_pct"]))
    body = "Enterprise framework maturity index:\n" + "\n".join(f"  • {p}" for p in parts)
    insights = [f"Lowest maturity: {lowest['name']} at {lowest.get('maturity_pct', lowest['compliance_pct'])}%"]
    return _format_response("Enterprise Maturity", body, role=role, insights=insights)


def _pending_answer(framework: str, role: str) -> str:
    if role == "auditor":
        q = build_auditor_review_queue(500)
        if framework:
            q = [i for i in q if i["framework"] == framework]
        apps: dict[str, int] = {}
        for i in q:
            apps[i["application"]] = apps.get(i["application"], 0) + 1
        top_app = max(apps, key=apps.get) if apps else "—"
        body = f"{len(q)} evidences await your auditor approval."
        if q:
            body += f"\nTop item: {q[0]['control'][:45]} ({q[0]['framework']}) — {q[0]['aging_days']}d pending."
        metrics = {"auditor_queue": len(q), "top_application": f"{top_app} ({apps.get(top_app, 0)})" if apps else "—"}
        return _format_response("Auditor Pending Queue", body, framework=framework, role=role, metrics=metrics)

    if role in ("cio", "vertical_head", "compliance_head", "functional_head"):
        ent = enterprise_dashboard()
        k = enterprise_kpis()
        wq = work_queue_summary()
        body = (
            f"Enterprise compliance {k['enterprise_compliance_pct']}%, national score {ent['national_score']}%.\n"
            f"Closure trend: {k.get('closed_observations', 0)} observations closed in current cycle."
        )
        metrics = {
            "owner_pending": wq["owner_pending"],
            "auditor_pending": wq["auditor_pending"],
            "escalated": wq["escalated"],
            "rejected": wq["rejected"],
        }
        risky = sorted(display_framework_maturity(ent["analytics"]["framework_stats"]), key=lambda x: x.get("maturity_pct", 100))[:2]
        insights = [f"Watch: {r['name']} ({r.get('maturity_pct', r['compliance_pct'])}%)" for r in risky]
        return _format_response("Executive Pending Summary", body, role=role, metrics=metrics, insights=insights)

    q = build_owner_work_queue(500)
    if framework:
        q = [i for i in q if i["framework"] == framework]
    fws: dict[str, int] = {}
    for i in q:
        fws[i["framework"]] = fws.get(i["framework"], 0) + 1
    body = f"You have {len(q)} evidences pending your action across the enterprise."
    if fws:
        body += "\nFrameworks needing action: " + ", ".join(f"{k} ({v})" for k, v in sorted(fws.items(), key=lambda x: -x[1])[:5])
    metrics = {"your_pending_count": len(q), "frameworks_with_actions": len(fws)}
    return _format_response("App Owner Pending Actions", body, framework=framework, role=role, metrics=metrics)


def _rejected_answer(framework: str, role: str) -> str:
    items = list(ecs_state.rejected_controls.items())
    if framework:
        items = [(k, v) for k, v in items if k.startswith(f"{framework}::")]
    if not items:
        return _format_response("Rejected Observations", "No rejected observations in current workflow state.", framework=framework, role=role)
    lines = [f"  • {k.split('::', 1)[1][:45]}: {v['reason'][:70]}" for k, v in items[:6]]
    body = f"{len(items)} rejected observation(s):\n" + "\n".join(lines)
    return _format_response("Rejected Observations", body, framework=framework, role=role, metrics={"rejected_count": len(items)})


def _expired_answer(framework: str, role: str) -> str:
    records = get_all_evidence_records()
    if framework:
        records = [r for r in records if r.get("framework") == framework]
    expired = [r for r in records if r.get("evidence_status") == "Expired"]
    due = [r for r in records if r.get("evidence_status") == "Due for Refresh"]
    lines = [f"  • {r['evidence_id']} ({r.get('framework', '')}) — {r['evidence_name'][:35]}" for r in expired[:5]]
    body = f"TD expired: {len(expired)} · Due for refresh: {len(due)}"
    if lines:
        body += "\n" + "\n".join(lines)
    return _format_response("Expiring / Expired Evidence", body, framework=framework, role=role, metrics={"expired": len(expired), "due_refresh": len(due)})


def _high_risk_answer(framework: str, role: str) -> str:
    items = build_owner_work_queue(300) + build_auditor_review_queue(300)
    if framework:
        items = [i for i in items if i["framework"] == framework]
    high = [i for i in items if i.get("risk_rating") in ("Critical", "High")]
    lines = [f"  • [{i['risk_rating']}] {i['control'][:40]} ({i['framework']})" for i in high[:6]]
    body = f"{len(high)} high/critical risk observations identified."
    if lines:
        body += "\n" + "\n".join(lines)
    return _format_response("High-Risk Observations", body, framework=framework, role=role, metrics={"high_risk_count": len(high)})


def _vapt_answer(q: str, role: str) -> str:
    framework = "VAPT"
    m = _fw_metrics(framework)
    owner_q = [i for i in build_owner_work_queue(200) if i["framework"] == framework]
    if "what is" in q or "explain" in q:
        return _framework_definition_answer(framework, role)
    if "open" in q or "pending" in q or "finding" in q:
        body = f"{len(owner_q)} VAPT findings pending closure; {m.get('auditor_pending', 0)} in auditor review."
        return _format_response("VAPT Findings", body, framework=framework, role=role, metrics=m)
    if "fail" in q or "application" in q:
        apps = sorted(application_comparison(), key=lambda a: a["compliance_pct"])[:4]
        body = "Applications with elevated VAPT/compliance backlog:\n" + "\n".join(
            f"  • {a['application']}: {a['compliance_pct']}%" for a in apps
        )
        return _format_response("VAPT Application Posture", body, framework=framework, role=role)
    return _framework_definition_answer(framework, role)


def _appsec_answer(q: str, role: str) -> str:
    framework = "AppSec"
    m = _fw_metrics(framework)
    high = [i for i in build_owner_work_queue(200) if i["framework"] == framework and i.get("risk_rating") in ("Critical", "High")]
    if "what is" in q or "explain" in q:
        return _framework_definition_answer(framework, role)
    if "fail" in q or "scan" in q:
        failed = [c["control"] for c in get_framework_controls(framework) if "SAST" in c["control"] or "DAST" in c["control"]][:4]
        body = "AppSec scan areas under review:\n" + "\n".join(f"  • {c}" for c in failed)
        return _format_response("AppSec Scan Status", body, framework=framework, role=role, metrics=m)
    if "high risk" in q or "observation" in q:
        body = f"{len(high)} high-risk AppSec observations in owner queue."
        return _format_response("AppSec High Risk", body, framework=framework, role=role, metrics={"high_risk": len(high)})
    return _framework_definition_answer(framework, role)


def _os_baseline_answer(q: str, role: str) -> str:
    framework = "OS Baselining"
    if "what is" in q or "explain" in q:
        return _framework_definition_answer(framework, role)
    records = [r for r in get_all_evidence_records() if r.get("framework") == framework]
    non_compliant = [r for r in records if r.get("evidence_status") in ("Expired", "Due for Refresh") or r.get("audit_status") == "Rejected"]
    servers = list({r.get("server_name") for r in non_compliant if r.get("server_name")})[:6]
    body = f"{len(non_compliant)} OS baselining evidences flagged; {len(servers)} servers with attention items."
    if servers:
        body += "\nSystems: " + ", ".join(servers)
    return _format_response("OS Baselining Compliance", body, framework=framework, role=role, metrics={"flagged_evidences": len(non_compliant)})


def _db_baseline_answer(q: str, role: str) -> str:
    framework = "DB Baselining"
    if "what is" in q or "explain" in q:
        return _framework_definition_answer(framework, role)
    records = [r for r in get_all_evidence_records() if r.get("framework") == framework]
    failing = [r for r in records if r.get("audit_status") in ("Rejected", "Pending") or r.get("evidence_status") == "Expired"]
    expired = [r for r in records if r.get("evidence_status") == "Expired"]
    if "encrypt" in q:
        no_encrypt = [r for r in records if "encrypt" in r.get("evidence_name", "").lower() and r.get("evidence_status") != "Current"]
        body = f"{len(no_encrypt)} DB encryption-related evidences need refresh."
    else:
        body = f"{len(failing)} DB control evidences failing or stale; {len(expired)} expired."
    return _format_response("DB Baselining Status", body, framework=framework, role=role, metrics={"failing": len(failing), "expired": len(expired)})


def _csite_answer(q: str, role: str) -> str:
    framework = "CSITE"
    m = _fw_metrics(framework)
    if "what is" in q or "explain" in q:
        return _framework_definition_answer(framework, role)
    high = [i for i in build_owner_work_queue(200) + build_auditor_review_queue(200) if i["framework"] == framework and i.get("risk_rating") in ("Critical", "High")]
    siem = [c["control"] for c in get_framework_controls(framework) if "SIEM" in c["control"] or "SOC" in c["control"]][:4]
    if "siem" in q or "alert" in q:
        body = "SIEM/SOC control areas:\n" + "\n".join(f"  • {c}" for c in siem)
        return _format_response("CSITE SIEM Status", body, framework=framework, role=role, metrics=m)
    if "open" in q or "observation" in q:
        body = f"{m.get('open_observations', 0)} CSITE observations open; {len(high)} high/critical risk."
        return _format_response("CSITE Open Observations", body, framework=framework, role=role, metrics=m)
    if "high risk" in q or "td expired" in q or "expired" in q:
        return _expired_answer(framework, role) if ("expir" in q or "td" in q) else _high_risk_answer(framework, role)
    return _framework_definition_answer(framework, role)


def _itpp_answer(q: str, role: str) -> str:
    from app.itpp_module import build_itpp_operational_view

    framework = "ITPP"
    view = build_itpp_operational_view(role)
    kpis = view["kpis"]
    if "what is" in q or "explain" in q or "define" in q:
        return _framework_definition_answer(framework, role)
    if "dr readiness" in q or "dr drill" in q or "disaster recovery" in q:
        overdue = kpis["overdue_dr_drills"]
        body = (
            f"DR readiness: {kpis['dr_readiness_pct']}% · success rate {kpis['dr_success_rate']}%.\n"
            f"Critical app coverage: {kpis['critical_app_coverage']}% · overdue DR drills: {overdue}."
        )
        metrics = {"dr_readiness_pct": f"{kpis['dr_readiness_pct']}%", "overdue_dr_drills": overdue}
        insights = ["Schedule DR drill for overdue controls before audit window."] if overdue else ["DR posture within operational SLA."]
        return _format_response("ITPP DR Readiness", body, framework=framework, role=role, metrics=metrics, insights=insights)
    if "backup" in q and ("fail" in q or "failure" in q):
        body = f"{kpis['failed_backups']} backup failure(s) detected · success rate {kpis['backup_success_rate']}%."
        return _format_response("ITPP Backup Status", body, framework=framework, role=role, metrics={"failed_backups": kpis["failed_backups"]})
    if "incident" in q and ("sla" in q or "breach" in q):
        body = f"{kpis['sla_breaches']} incident SLA breach(es) · {kpis['open_p1_incidents']} open P1 incidents."
        return _format_response("ITPP Incident SLA", body, framework=framework, role=role, metrics={"sla_breaches": kpis["sla_breaches"]})
    if "capacity" in q or "saturation" in q:
        body = f"{kpis['saturation_alerts']} saturation alert(s) · capacity plan current: {kpis['capacity_plan_current']}."
        return _format_response("ITPP Capacity Risk", body, framework=framework, role=role, metrics={"saturation_alerts": kpis["saturation_alerts"]})
    if "change" in q and ("fail" in q or "unauthorized" in q):
        body = f"{kpis['failed_changes']} failed/unauthorized change(s) · emergency changes QTR: {kpis['emergency_changes']}."
        return _format_response("ITPP Change Management", body, framework=framework, role=role, metrics={"unauthorized_changes": kpis["unauthorized_changes"]})
    if "repeat" in q or "problem" in q:
        body = f"{kpis['repeat_incidents']} repeat incident pattern(s) · {kpis['unresolved_root_causes']} unresolved root causes."
        return _format_response("ITPP Problem Management", body, framework=framework, role=role, metrics={"repeat_incidents": kpis["repeat_incidents"]})
    if "validation" in q and "fail" in q:
        from app.control_validation_engine import failed_validations
        fails = failed_validations("ITPP")
        body = f"{len(fails)} ITPP control validation check(s) failed."
        if fails:
            body += "\n" + "\n".join(f"  • {f['control'][:40]}: {f['check_name'][:35]}" for f in fails[:5])
        return _format_response("ITPP Validation Failures", body, framework=framework, role=role, metrics={"failed_checks": len(fails)})
    return _framework_definition_answer(framework, role)


def _validation_answer(q: str, role: str, framework: str) -> str | None:
    if "validation" not in q and "failed validation" not in q and "controls failed" not in q:
        return None
    from app.control_validation_engine import failed_validations, validation_summary
    fw = framework or ""
    fails = failed_validations(fw)
    if fw:
        summ = validation_summary(fw)
        body = f"{summ['failed']} failed · {summ['warned']} warnings · effectiveness {summ['effectiveness_pct']}%."
    else:
        body = f"{len(fails)} failed validation checks enterprise-wide."
    if fails:
        body += "\n" + "\n".join(f"  • [{f.get('framework', fw)}] {f['control'][:35]}: {f['status']}" for f in fails[:6])
    return _format_response("Control Validation Status", body, framework=fw or "Enterprise", role=role, metrics={"failed": len(fails)})


def _grc_platform_answer(q: str, role: str) -> str | None:
    from app.correlation_engine import find_correlations_by_tool
    from app.enterprise_grc import build_cmdb_inventory, build_exceptions_td, build_executive_heatmaps, build_risk_register
    from app.integrations_module import get_integrations_hub_dashboard

    ql = q.lower()
    risks = build_risk_register(role)
    exc = build_exceptions_td(role)
    cmdb = build_cmdb_inventory(role)
    heat = build_executive_heatmaps(role)
    hub = get_integrations_hub_dashboard()

    if "td" in ql and ("expir" in ql or "expired" in ql):
        body = f"{len(exc['expired'])} TD-expired exception(s)."
        if exc["expired"]:
            body += "\n" + "\n".join(f"  • {e['exception_id']} — {e['control'][:40]}" for e in exc["expired"][:5])
        return _format_response("TD Expired Items", body, role=role, metrics={"td_expired": len(exc["expired"])})

    if "least mature" in ql or "lowest maturity" in ql or ("framework" in ql and "least" in ql):
        return _combination_answer("lowest maturity", "", role)

    if "high-risk finding" in ql or ("high risk" in ql and "application" in ql):
        apps = sorted(heat["top_risky_apps"], key=lambda x: x["score"])[:4]
        body = "Applications with elevated high-risk posture:\n" + "\n".join(f"  • {a['application']}: {a['score']}%" for a in apps)
        high = len(risks["high_open"])
        return _format_response("High-Risk Applications", body, role=role, metrics={"open_high_risks": high})

    if "servicenow" in ql and ("incident" in ql or "unresolved" in ql):
        chains = find_correlations_by_tool("servicenow")
        open_c = [c for c in chains if c["status"] == "Open"]
        body = f"{len(open_c)} open ServiceNow-correlated governance chain(s)."
        if open_c:
            body += f"\nLatest: {open_c[0]['source_record']}"
        return _format_response("ServiceNow Incidents", body, role=role, metrics={"open_chains": len(open_c)})

    if "prisma" in ql and ("critical" in ql or "finding" in ql):
        prisma = [c for c in hub["connectors"] if "prisma" in c["name"].lower()]
        body = "Prisma Cloud CSPM connected — critical IAM and exposed storage findings correlated to CSITE and Risk Register."
        if prisma:
            body += f"\nRecords pulled: {prisma[0].get('records_pulled', 0)} · Mapped controls: {prisma[0].get('mapped_controls', 0)}"
        return _format_response("Prisma Cloud Findings", body, role=role, metrics={"connectors": len(prisma)})

    if "tripwire" in ql and ("drift" in ql or "unresolved" in ql):
        chains = find_correlations_by_tool("tripwire")
        body = f"{len(chains)} Tripwire drift correlation chain(s) — linked to OS Baselining and compensating controls."
        return _format_response("Tripwire Drift", body, role=role, metrics={"drift_chains": len(chains)})

    if "sonarqube" in ql or ("sonar" in ql and "high" in ql):
        sonar = [c for c in hub["connectors"] if "sonar" in c["name"].lower()]
        body = "SonarQube SAST findings correlated to AppSec controls and Jira remediation backlog."
        return _format_response("SonarQube Findings", body, role=role, metrics={"imported_evidence": sonar[0].get("imported_evidence", 0) if sonar else 0})

    if "dr coverage" in ql or ("lack" in ql and "dr" in ql):
        no_dr = [a for a in cmdb["rows"] if not a["dr_covered"]]
        body = f"{len(no_dr)} asset(s) without DR coverage."
        if no_dr:
            body += "\n" + "\n".join(f"  • {a['name']} ({a['type']})" for a in no_dr[:5])
        return _format_response("DR Coverage Gaps", body, role=role, metrics={"no_dr_coverage": len(no_dr)})

    if "business unit" in ql and "highest risk" in ql:
        bu = risks["bu_exposure"][0] if risks["bu_exposure"] else {"unit": "—", "count": 0}
        body = f"Highest risk exposure: {bu['unit']} with {bu['count']} registered enterprise risk(s)."
        return _format_response("Business Unit Risk", body, role=role, metrics={"top_bu": bu["unit"], "risk_count": bu["count"]})

    if "reused" in ql and "framework" in ql:
        from app.control_validation_engine import build_governance_analytics
        gov = build_governance_analytics()
        reuse = gov.get("most_reused_evidence", [])
        body = f"{len(reuse)} evidence artefact(s) reused across multiple frameworks."
        if reuse:
            body += "\n" + "\n".join(f"  • {r['evidence_id']} → {', '.join(r['frameworks'][:3])}" for r in reuse[:4])
        return _format_response("Cross-Framework Evidence Reuse", body, role=role, metrics={"reuse_groups": len(reuse)})

    if "risk register" in ql or ql.startswith("which risks"):
        body = f"{len(risks['high_open'])} open high/critical risks · {len(risks['rows'])} total in register."
        return _format_response("Risk Register Summary", body, role=role, metrics={"open_high": len(risks["high_open"])})

    return None


def _combination_answer(q: str, framework: str, role: str) -> str | None:
    ql = q.lower()
    if "both expired and pending" in ql or ("expired" in ql and "pending" in ql and "approval" in ql):
        fw = framework or "PCI DSS"
        submitted_keys = set(ecs_state.submitted_controls.keys())
        hits = []
        for r in get_all_evidence_records():
            if r.get("framework") != fw:
                continue
            key = ecs_state.control_key(fw, r.get("control", ""))
            if r.get("evidence_status") == "Expired" and key in submitted_keys:
                hits.append(r.get("control", "")[:40])
        body = f"{len(hits)} {fw} controls are both TD-expired and pending auditor review."
        if hits:
            body += "\n" + "\n".join(f"  • {h}" for h in hits[:5])
        return _format_response("Combination Query", body, framework=fw, role=role)

    if "highest audit backlog" in ql or ("highest pending" in ql and "application" in ql):
        apps_sorted = sorted(application_comparison(), key=lambda a: 100 - a["compliance_pct"])
        body = "Applications by audit backlog (lowest compliance first):\n" + "\n".join(
            f"  • {a['application']}: {a['compliance_pct']}%" for a in apps_sorted[:5]
        )
        return _format_response("Application Audit Backlog", body, role=role)

    if "lowest maturity" in ql or "most risky framework" in ql:
        stats = display_framework_maturity(ecs_state.build_evidence_analytics()["framework_stats"])
        low = min(stats, key=lambda x: x.get("maturity_pct", x["compliance_pct"]))
        body = f"{low['name']} has lowest maturity at {low.get('maturity_pct', low['compliance_pct'])}%."
        return _format_response("Framework Risk Ranking", body, framework=low["name"], role=role)

    if ("high-risk" in ql or "high risk" in ql) and ("td expired" in ql or "expired" in ql):
        items = build_owner_work_queue(400)
        hits = [i for i in items if i.get("risk_rating") in ("Critical", "High") and i.get("evidence_status") == "Expired"]
        if framework:
            hits = [i for i in hits if i["framework"] == framework]
        body = f"{len(hits)} observations are both high-risk and TD-expired."
        return _format_response("High-Risk + Expired", body, framework=framework, role=role, metrics={"count": len(hits)})

    if "sla breach" in ql or "sla breaches" in ql:
        owner_q = build_owner_work_queue(500)
        breached = [i for i in owner_q if i.get("sla") == "Breached"]
        if framework:
            breached = [i for i in breached if i["framework"] == framework]
        body = f"{len(breached)} observations with SLA breach status."
        if role in ("cio", "vertical_head"):
            units = sorted(BUSINESS_UNITS, key=lambda u: -u["open_gaps"])[:3]
            body += "\nBusiness units with most gaps: " + ", ".join(u["unit"] for u in units)
        return _format_response("SLA Breaches", body, framework=framework, role=role, metrics={"sla_breaches": len(breached)})

    if "business unit" in ql or "business units" in ql:
        body = "\n".join(
            f"  • {u['unit']}: {u['compliance_pct']}% · {u['open_gaps']} open gaps ({u['risk']} risk)"
            for u in sorted(BUSINESS_UNITS, key=lambda x: -x["open_gaps"])
        )
        return _format_response("Business Unit Observations", body, role=role)

    if "closure" in ql and ("%" in ql or "percentage" in ql):
        stats = ecs_state.build_evidence_analytics()
        t = stats["totals"]
        pct = round((t["approved"] / t["total"]) * 100, 1) if t["total"] else 0
        body = f"Current closure rate: {pct}% ({t['approved']}/{t['total']} controls auditor-approved)."
        return _format_response("Closure Percentage", body, role=role, metrics={"closure_pct": f"{pct}%"})
    return None


def process_query(query: str, role: str = "owner", user: str = "User") -> str:
    q = query.strip()
    ql = q.lower()
    ctx = update_chat_context(user, role, q)
    framework = _detect_framework(ql, ctx)
    topic = _detect_topic(ql)

    # Conversational follow-up: inherit framework/topic only for substantive follow-ups
    if not framework and ctx.get("framework") and len(ql.split()) >= 2:
        if topic or any(w in ql for w in ("how many", "which", "show", "they", "those", "are", "risk", "high", "many")):
            framework = ctx["framework"]
    if not topic and ctx.get("topic") and 2 <= len(ql.split()) <= 8:
        topic = ctx["topic"]

    # Single vague token — ask for clarification (avoid wrong inherited context)
    if len(ql.split()) <= 1 and not topic and not any(a in ql for a in FRAMEWORK_ALIASES):
        if ql not in ("pending", "rejected", "maturity", "help", "sla"):
            ans = _format_response("Clarification Needed", CLARIFICATION_PROMPT, role=role)
            record_exchange(user, role, q, ans)
            return ans

    if framework:
        ctx["framework"] = framework
    if topic:
        ctx["topic"] = topic

    from app.chatbot_context_engine import render_governance_panel

    def _with_governance_panel(title: str, body: str, **fmt_kw) -> str:
        ans = _format_response(title, body, framework=framework, role=role, **fmt_kw)
        html = render_governance_panel(ctx, role, body[:200] if body else title)
        set_chat_structured(user, role, html)
        record_exchange(user, role, q, ans)
        return ans

    if any(w in ql for w in ("gap", "gaps", "pending", "missing")) and (framework or ctx.get("application")):
        m = _fw_metrics(framework) if framework else {}
        app = ctx.get("application", "enterprise scope")
        body = (
            f"{framework or 'Enterprise'} pending gaps for {app}: "
            f"{m.get('open_observations', m.get('pending', 12))} open observations, "
            f"{m.get('high_risk_count', 4)} high-risk items."
        )
        return _with_governance_panel(
            f"{framework or 'Governance'} Pending Gaps",
            body,
            metrics=m or {"open_observations": 12, "high_risk_count": 4},
            insights=[f"Use quick actions below to drill into {app} impact, incidents, and TD exceptions."],
        )

    for mod, desc in MODULE_DEFINITIONS.items():
        if mod.lower() in ql and any(p in ql for p in ("what is", "explain", "define")):
            ans = _format_response(mod, desc, role=role)
            record_exchange(user, role, q, ans)
            return ans

    combo = _combination_answer(ql, framework, role)
    if combo:
        record_exchange(user, role, q, combo)
        return combo

    if "vapt" in ql or ("vulnerability" in ql and "assessment" in ql):
        ans = _vapt_answer(ql, role)
        record_exchange(user, role, q, ans)
        return ans
    if "appsec" in ql or "app sec" in ql:
        ans = _appsec_answer(ql, role)
        record_exchange(user, role, q, ans)
        return ans
    if "os basel" in ql or ("linux" in ql and "harden" in ql):
        ans = _os_baseline_answer(ql, role)
        record_exchange(user, role, q, ans)
        return ans
    if "db basel" in ql or ("database" in ql and ("encrypt" in ql or "fail" in ql)):
        ans = _db_baseline_answer(ql, role)
        record_exchange(user, role, q, ans)
        return ans
    if "csite" in ql or ("siem" in ql and "alert" in ql):
        ans = _csite_answer(ql, role)
        record_exchange(user, role, q, ans)
        return ans
    if "itpp" in ql or "dr readiness" in ql or ("backup" in ql and "fail" in ql) or ("drill" in ql and "overdue" in ql):
        ans = _itpp_answer(ql, role)
        record_exchange(user, role, q, ans)
        return ans
    val_ans = _validation_answer(ql, role, framework)
    if val_ans:
        record_exchange(user, role, q, val_ans)
        return val_ans
    grc_ans = _grc_platform_answer(ql, role)
    if grc_ans:
        record_exchange(user, role, q, grc_ans)
        return grc_ans

    if any(p in ql for p in ("what is", "what are", "explain", "describe", "define", "tell me about")):
        if framework:
            ans = _framework_controls_answer(framework, role) if "control" in ql else _framework_definition_answer(framework, role)
            record_exchange(user, role, q, ans)
            return ans
        if "enterprise maturity" in ql:
            ans = _maturity_answer("", role)
            record_exchange(user, role, q, ans)
            return ans

    if topic == "maturity" or "maturity" in ql:
        ans = _maturity_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans
    if topic == "pending" or ("how many" in ql and ("pending" in ql or "open" in ql or "await" in ql)):
        ans = _pending_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans
    if topic == "rejected" or ("reject" in ql and ("observation" in ql or "evidence" in ql or "auditor" in ql)):
        ans = _rejected_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans
    if topic == "expired" or "expir" in ql or "td expired" in ql:
        ans = _expired_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans
    if topic == "high_risk" or "high risk" in ql or "high-risk" in ql:
        ans = _high_risk_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans
    if topic == "sla" or "overdue" in ql:
        ans = _combination_answer("sla breaches", framework, role) or _high_risk_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans

    if framework and ("pending" in ql or "how many" in ql):
        m = _fw_metrics(framework)
        body = f"{framework}: {m.get('open_observations', 0)} open observations, {framework_pending_count(framework, role)} pending for your role."
        ans = _format_response(f"{framework} Pending Count", body, framework=framework, role=role, metrics=m)
        record_exchange(user, role, q, ans)
        return ans
    if framework and "control" in ql:
        ans = _framework_controls_answer(framework, role)
        record_exchange(user, role, q, ans)
        return ans

    if len(ql.split()) <= 2 and not framework:
        ans = _format_response("Clarification Needed", CLARIFICATION_PROMPT, role=role)
        record_exchange(user, role, q, ans)
        return ans

    return ""
