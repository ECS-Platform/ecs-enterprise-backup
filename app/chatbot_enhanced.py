"""Additive natural-language audit query enhancements for ECS chatbot."""

from datetime import datetime, timezone

from app import ecs_state
from app.analytics_module import (
    application_comparison,
    audit_preparation_checklist,
    completeness_report,
    enterprise_dashboard,
)
from app.demo_metrics import REUSE_METRICS, enterprise_kpis
from app.evidence_repository import where_else_used
from app.workflow_module import (
    FRAMEWORK_DESCRIPTIONS,
    build_auditor_review_queue,
    build_owner_work_queue,
    framework_explanation,
    work_queue_summary,
)

from app.chatbot_engine import CLARIFICATION_PROMPT

FALLBACK = (
    "I couldn't match that query to live ECS data with confidence.\n\n" + CLARIFICATION_PROMPT
)

FRAMEWORK_WHY_IT_MATTERS = {
    "PCI DSS": "Mandatory for cardholder data environments (CDE), payment gateways, and RBI-aligned IT governance audits.",
    "DPSC": "Required for digital payment channels — UPI, card switch, API banking, and NPCI/RBI DPSC self-assessment.",
    "OS Baselining": "Ensures CIS-aligned server hardening across Net Banking, UPI, and middleware production fleets.",
    "DB Baselining": "Governs Oracle CBS, treasury, and loan-system database security for SOX and internal audit.",
    "Nginx Baselining": "Covers internet banking edge, mobile API gateway, and DMZ reverse-proxy TLS/WAF compliance.",
    "CSITE": "Enterprise cyber security evaluation — SOC integration, IR readiness, and board-level IT risk reporting.",
    "AppSec": "Required for secure SDLC, release gates, and application-layer audit across digital channels.",
    "VAPT": "Mandatory for external attack surface validation and RBI/PCI vulnerability closure evidence.",
    "ITPP": "Required for IT operational resilience — DR, backup, change, incident, and availability governance.",
}


def try_framework_definition(query: str) -> str | None:
    """Return framework explanation without inventing live metrics."""
    q = query.lower().strip()
    is_definition = any(
        p in q for p in ("what is", "explain", "what are", "describe", "tell me about", "define")
    )
    if not is_definition:
        return None

    from app.framework_catalog import get_framework_controls

    for name, desc in FRAMEWORK_DESCRIPTIONS.items():
        q_compact = q.replace(" ", "")
        name_compact = name.lower().replace(" ", "")
        if name.lower() in q or name_compact in q_compact:
            ctrls = get_framework_controls(name)
            ev_count = sum(len(c["evidences"]) for c in ctrls)
            ctrl_examples = [c["control"] for c in ctrls[:4]]
            ev_examples = [c["evidences"][0]["evidence_name"] for c in ctrls[:3]]
            file_examples = [c["evidences"][0].get("mock_file", "") for c in ctrls[:2]]
            why = FRAMEWORK_WHY_IT_MATTERS.get(name, "Required for enterprise banking governance and audit readiness.")
            body = (
                f"{name} — Enterprise Audit Framework\n\n"
                f"Overview: {desc}\n\n"
                f"Why it matters: {why}\n\n"
                f"ECS catalogue: {len(ctrls)} controls, {ev_count} evidence artefacts.\n"
                f"Sample controls: {'; '.join(ctrl_examples)}.\n"
                f"Sample evidence types: {'; '.join(ev_examples)}.\n"
                f"Example files: {', '.join(f for f in file_examples if f)}."
            )
            return format_chatbot_response(body, name)
    return None


def chatbot_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_chatbot_response(body: str, framework_hint: str = "") -> str:
    prefix = f"[ECS AI · {chatbot_timestamp()}]"
    if framework_hint:
        prefix += f" [{framework_hint}]"
    rec = _recommendation_snippet(body)
    if rec:
        return f"{prefix}\n{body}\n\nRecommendation: {rec}"
    return f"{prefix}\n{body}"


def _recommendation_snippet(body: str) -> str:
    b = body.lower()
    if "reject" in b:
        return "Prioritize resubmission for rejected controls within 5 business days."
    if "compliance" in b or "%" in body:
        return "Review top risk frameworks on the Enterprise dashboard before MD steering."
    if "pending" in b or "missing" in b:
        return "Assign App Owners to overdue PCI and DPSC observations this week."
    if "reuse" in b:
        return "Leverage mapped reuse groups to reduce duplicate uploads by ~34%."
    return ""


def try_enhanced_answer(query: str, role: str = "owner", user: str = "User") -> str | None:
    from app.operations_intelligence import try_operations_answer

    ops_answer = try_operations_answer(query, role=role, user=user)
    if ops_answer:
        return ops_answer

    from app.chatbot_engine import process_query

    engine_answer = process_query(query, role=role, user=user)
    if engine_answer:
        return engine_answer

    q = query.lower()
    fw_hint = ""
    for name in ecs_state.frameworks:
        if name.lower() in q:
            fw_hint = name
            break

    def fmt(body: str) -> str:
        return format_chatbot_response(body, fw_hint)

    if "where else" in q or "reuse" in q or ("used" in q and "evidence" in q):
        token = query.split()[-1] if len(query.split()) > 2 else ""
        body = where_else_used(token or "pci_mock")
        body += f" Reuse factor avg {REUSE_METRICS['avg_reuse_factor']}x across {REUSE_METRICS['total_reuse_groups']} groups."
        return fmt(body)

    if "pending audit" in q or ("pending" in q and "audit" in q):
        comp = completeness_report()
        return fmt(
            f"Pending audits: {comp['missing_count']} controls missing evidence, "
            f"{comp['incomplete_count']} incomplete submissions. "
            f"{comp['warnings']} total auditor warnings."
        )

    if "framework coverage" in q or "coverage" in q:
        stats = ecs_state.build_evidence_analytics()
        from app.demo_metrics import display_framework_maturity

        parts = [
            f"{f['name']} {f.get('maturity_pct', f['compliance_pct'])}%"
            for f in display_framework_maturity(stats["framework_stats"])
        ]
        return fmt("Framework coverage — " + " | ".join(parts))

    if "application" in q and ("health" in q or "audit" in q):
        apps = application_comparison()
        parts = [
            f"{a['application']}: {a['compliance_pct']}% ({a['risk']} risk) Owner: {a.get('owner', '—')}"
            for a in apps[:6]
        ]
        return fmt("Application audit health — " + " | ".join(parts))

    if "vertical" in q or "md" in q or "leadership" in q or "functional" in q:
        ent = enterprise_dashboard()
        k = ent["kpis"]
        return fmt(
            f"Leadership summary: national score {ent['national_score']}%, "
            f"enterprise compliance {k['enterprise_compliance_pct']}%, "
            f"{ent['completeness']['warnings']} open warnings, "
            f"{k['closed_observations']} closed observations."
        )

    if "audit prep" in q or "preparation" in q or "checklist" in q:
        prep = audit_preparation_checklist()
        return fmt(
            f"Audit preparation: {prep['ready_pct']}% ready, "
            f"{prep['missing_controls']} missing controls. "
            f"Top action: {prep['checklist'][0]['action'] if prep['checklist'] else 'None'}."
        )

    if "maturity" in q:
        stats = ecs_state.build_evidence_analytics()
        from app.demo_metrics import display_framework_maturity

        if "pci" in q:
            pci = next((f for f in display_framework_maturity(stats["framework_stats"]) if f["name"] == "PCI DSS"), None)
            if pci:
                return fmt(
                    f"PCI DSS maturity: {pci.get('maturity_pct', pci['compliance_pct'])}% display maturity, "
                    f"{pci['approved']}/{pci['total']} controls approved live, "
                    f"{pci['pending']} pending, {pci['submitted']} in auditor review."
                )
        parts = [f"{f['name']} {f.get('maturity_pct', f['compliance_pct'])}%" for f in display_framework_maturity(stats["framework_stats"])]
        return fmt("Framework maturity index — " + " | ".join(parts))

    if "trend" in q or "closure" in q:
        from app.analytics_module import compliance_trends

        t = compliance_trends()
        last = t["monthly"][-1]
        return fmt(
            f"Compliance trends: {last['month']} closed {last['closed']} observations, "
            f"opened {last['opened']}, maturity {last.get('compliance', 79)}%. "
            f"Avg closure {t['avg_days_to_close']} days."
        )

    if "scheduler" in q or "scheduled pull" in q:
        from app.scheduler_module import get_scheduler_dashboard

        s = get_scheduler_dashboard()["status"]
        return fmt(
            f"Scheduler: {s['last_pull_status']}, last pull {s['last_pull_at']}. "
            f"Completed {s['pulls_completed']} pulls, success rate {s['success_rate_pct']}%."
        )

    if "integration" in q or "sharepoint" in q or "servicenow" in q:
        from app.integrations_module import get_integration_dashboard

        conns = get_integration_dashboard()["connectors"]
        return fmt("Integrations — " + " | ".join(f"{c['name']}: {c['status']}" for c in conns))

    if "search" in q or "find evidence" in q:
        return fmt(
            "Use Evidence Search (/mvp/search) to query by framework, application, "
            "owner, or status globally."
        )

    if "hash" in q or "integrity" in q or "tamper" in q:
        return fmt(
            "Evidence Health: SHA-256 checksums, 98.7% valid integrity (demo), "
            "tamper simulation enabled."
        )

    if "compliance" in q and "officer" in q:
        k = enterprise_kpis()
        return fmt(f"Compliance Officer view: {k['enterprise_compliance_pct']}% enterprise, {k['open_observations']} open observations.")

    if "notification" in q or "activity" in q:
        from app.audit_trail import get_recent_activity

        acts = get_recent_activity(3)
        parts = [f"{a['action']} by {a['actor']}" for a in acts]
        return fmt("Recent activity — " + " | ".join(parts) if parts else "No recent activity.")

    if "expired" in q or "expiry" in q:
        from app.framework_catalog import get_all_evidence_records

        expired = [r for r in get_all_evidence_records() if r.get("evidence_status") == "Expired"][:6]
        due = [r for r in get_all_evidence_records() if r.get("evidence_status") == "Due for Refresh"][:4]
        parts = [f"{r['evidence_id']} ({r['framework']}) exp {r['expiry_date']}" for r in expired]
        return fmt(
            f"Expired evidences: {len(expired)} flagged. Due for refresh: {len(due)}. "
            + (" Samples: " + " | ".join(parts) if parts else " None critical this cycle.")
        )

    if "gap" in q or "compliance gap" in q:
        comp = completeness_report()
        return fmt(
            f"Compliance gaps: {comp['missing_count']} controls without submission, "
            f"{comp['incomplete_count']} in-flight/rejected. {comp['warnings']} total open items for remediation."
        )


    if "pending approval" in q or ("pending" in q and "approval" in q):
        wq = work_queue_summary()
        auditor_q = build_auditor_review_queue()
        return fmt(
            f"Pending approvals: {len(auditor_q)} items in auditor queue, "
            f"{wq['rejected']} rejected awaiting owner resubmission, "
            f"{wq['escalated']} escalated."
        )

    if ("app owner" in q or "my pending" in q or "my actions" in q) and (
        "pending" in q or "action" in q or "queue" in q or "task" in q
    ):
        owner_q = build_owner_work_queue()
        types: dict[str, int] = {}
        for item in owner_q:
            types[item["action_type"]] = types.get(item["action_type"], 0) + 1
        breakdown = " | ".join(f"{k}: {v}" for k, v in list(types.items())[:5])
        return fmt(
            f"App Owner work queue: {len(owner_q)} open items. Breakdown — {breakdown or 'none'}."
        )

    if "auditor queue" in q or ("auditor" in q and "review" in q):
        auditor_q = build_auditor_review_queue()
        if not auditor_q:
            return fmt("Auditor review queue is empty — no pending submissions.")
        sample = auditor_q[0]
        return fmt(
            f"Auditor queue: {len(auditor_q)} pending reviews. "
            f"Top item: {sample['control']} ({sample['framework']}) — "
            f"{sample['aging_days']} days pending, risk {sample['risk_rating']}."
        )

    if "cio" in q and ("summary" in q or "overview" in q or "executive" in q):
        ent = enterprise_dashboard()
        k = enterprise_kpis()
        wq = work_queue_summary()
        return fmt(
            f"CIO executive summary: enterprise compliance {k['enterprise_compliance_pct']}%, "
            f"national score {ent['national_score']}%, "
            f"{wq['auditor_pending']} pending auditor reviews, "
            f"{wq['owner_pending']} owner action items, "
            f"{k['closed_observations']} closed observations."
        )

    if "audit summary" in q or ("audit" in q and "summary" in q):
        stats = ecs_state.build_evidence_analytics()
        t = stats["totals"]
        return fmt(
            f"Audit summary: {t['approved']} closed, {t['submitted']} in review, "
            f"{t['rejected']} rejected, {t['pending']} pending submission. "
            f"Overall compliance {stats['overall_compliance_pct']}%."
        )

    if "application status" in q or ("application" in q and "status" in q):
        apps = application_comparison()
        parts = [f"{a['application']}: {a['compliance_pct']}% ({a['risk']})" for a in apps[:6]]
        return fmt("Application status — " + " | ".join(parts))

    if "aging" in q or "sla" in q:
        from app.demo_metrics import AUDIT_AGING_BUCKETS

        owner_q = build_owner_work_queue(limit=500)
        breached = sum(1 for i in owner_q if i.get("sla") == "Breached")
        buckets = " | ".join(f"{b['label']}: {b['count']}" for b in AUDIT_AGING_BUCKETS)
        return fmt(f"Aging observations: {breached} SLA breaches in active queue. Distribution — {buckets}.")

    if "framework health" in q or ("framework" in q and "health" in q):
        stats = ecs_state.build_evidence_analytics()
        from app.demo_metrics import display_framework_maturity

        parts = [
            f"{f['name']}: {f.get('maturity_pct', f['compliance_pct'])}% maturity, {f['pending']} pending"
            for f in display_framework_maturity(stats["framework_stats"])
        ]
        return fmt("Framework health — " + " | ".join(parts))

    if "enterprise risk" in q or "risk summary" in q:
        k = enterprise_kpis()
        wq = work_queue_summary()
        return fmt(
            f"Enterprise risk summary: compliance {k['enterprise_compliance_pct']}%, "
            f"{wq['escalated']} escalated, {wq['rejected']} rejected, "
            f"{wq['owner_pending']} owner actions, {wq['auditor_pending']} auditor reviews."
        )

    if "rejected" in q and "evidence" in q:
        rejected = list(ecs_state.rejected_controls.items())[:6]
        if not rejected:
            return fmt("No rejected evidences in the current workflow state.")
        parts = [f"{k.split('::')[1][:40]}: {v['reason'][:60]}" for k, v in rejected]
        return fmt(f"Rejected evidences ({len(ecs_state.rejected_controls)} total) — " + " | ".join(parts))

    if any(w in q for w in ("stale evidence", "failed evidence", "high-risk evidence", "high risk evidence")) or (
        "evidence" in q and any(w in q for w in ("stale", "failed", "reject", "expir", "health"))
    ):
        from app.chatbot_engine import set_chat_structured
        from app.chatbot_nav import evidence_health_link, mvp_url, link_html
        from app.evidence_health_engine import build_evidence_health_view

        view = build_evidence_health_view(role)
        rows = view["rows"]
        filter_issue = ""
        if "stale" in q:
            filter_issue, rows = "Stale", [r for r in rows if r["issue"] == "Stale"]
        elif "failed" in q or "fail" in q:
            filter_issue, rows = "Failed Validation", [r for r in rows if r["issue"] == "Failed Validation"]
        elif "reject" in q:
            filter_issue, rows = "Rejected", [r for r in rows if r["issue"] == "Rejected"]
        elif "expir" in q:
            filter_issue, rows = "Expired", [r for r in rows if r["issue"] in ("Expired", "Expiring Soon")]
        elif "high risk" in q or "high-risk" in q or "critical" in q:
            rows = [r for r in rows if r["risk"] in ("Critical", "High")]
        fw = fw_hint or (rows[0]["framework"] if rows else "")
        sample = rows[:5]
        parts = [
            f"{r['evidence_id']} — {r['control_id']} / {r['observation_id']}: {r['observation_summary'][:50]}"
            for r in sample
        ]
        body = f"Evidence Health: {len(rows)} matching records in your scope."
        if parts:
            body += " Samples — " + " | ".join(parts)
        link = evidence_health_link(role, user, filter_issue=filter_issue, framework=fw, label="Open Evidence Health (filtered)")
        html = (
            f'<div class="chart-card p-2 mb-2"><h6 class="chart-card-title mb-1">Evidence Health Intelligence</h6>'
            f'<p class="small mb-2">{body.replace("|", "<br>")}</p>{link}'
            f'<div class="mt-2">'
            + "".join(
                link_html(
                    r["evidence_id"],
                    mvp_url("evidence_health", role, user, framework=r["framework"], highlight=r["evidence_id"], filter_issue=filter_issue or r["issue"]),
                    "btn btn-outline-secondary btn-sm me-1 mb-1",
                )
                for r in sample
            )
            + "</div></div>"
        )
        set_chat_structured(user, role, html)
        return fmt(body + f" Open Evidence Health: /mvp/evidence-health?role={role}&filter_issue={filter_issue}")

    return None
