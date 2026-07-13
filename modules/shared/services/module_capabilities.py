"""Specialized business views for each ECS MVP module (not generic workflow queues)."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from modules.governance.engines.analytics_module import (
    application_comparison,
    audit_preparation_checklist,
    completeness_report,
    compliance_trends,
    enterprise_dashboard,
    lifecycle_timeline,
)
from modules.executive_overview.engines.demo_metrics import REUSE_METRICS, onboarding_progress, BUSINESS_UNITS
from modules.governance.engines.governance_mock_data import (
    OWNERS,
    audit_prep_enrichment,
    comparison_enrichment,
    completeness_enrichment,
    health_enrichment,
    lifecycle_enrichment,
    search_defaults,
)
from modules.operations.engines.evidence_repository import get_health_dashboard
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records
from modules.operations.engines.integrations_module import get_integration_dashboard
from modules.executive_overview.engines.reporting_module import list_reports
from modules.operations.engines.scheduler_module import get_scheduler_dashboard
from modules.governance.engines.search_module import build_search_discovery
from modules.governance.engines.workflow_module import aging_days_from

MODULE_PURPOSES = {
    "scheduler": "Evidence Collection Engine — collects and refreshes evidence from integrated enterprise platforms (ServiceNow, GitHub, Jenkins, SonarQube, and more).",
    "upload": "Mass onboarding and batch import of evidence artefacts with validation, deduplication, and framework auto-mapping.",
    "evidence_health": "Risk and quality scoring — stale, expired, incomplete, and low-confidence evidence governance.",
    "search": "Enterprise evidence discovery with semantic filters, reuse mapping, and cross-framework search.",
    "completeness": "Coverage gap analysis — controls without evidence, partial compliance, and audit readiness.",
    "reuse": "Cross-framework evidence reuse engine — map once, satisfy multiple controls, reduce duplicate uploads.",
    "lifecycle": "Evidence lifecycle governance — draft through active, expiring, archived, and retired states.",
    "comparison": "Application compliance posture comparison — maturity variance, control gaps, and risk heatmaps.",
    "integrations": "External system connectors — SIEM, ticketing, GRC, and ingestion pipeline health.",
    "enterprise": "Organization-wide governance KPIs, framework maturity, business-unit risk, and compliance posture.",
    "pan_india": "Regional and branch-level compliance visibility with zone risk and SLA breach tracking.",
    "reports": "Audit-ready export center — regulator packs, scheduled reports, and export history.",
    "audit_prep": "Audit readiness cockpit — upcoming audits, missing controls, and mock-audit preparation.",
    "trends": "Historical compliance analytics — control implementation coverage, observation closure, auditor rejection, remediation SLA, and evidence aging.",
    "onboarding": "Application onboarding workflow — framework assignment, ownership, and registration stages.",
    "framework_admin": "Framework administration — ingest new compliance frameworks, control normalization, reuse intelligence, and activation.",
    "risk_register": "Enterprise risk governance — inherent/residual risk, treatment, regulatory impact, and risk aging.",
    "exceptions_td": "Technical debt and exception workflow — compensating controls, TD expiry, renewal, and approval.",
    "cmdb": "CMDB and asset inventory — applications, servers, cloud assets, ownership, and compliance mapping.",
    "regulatory_mapping": "Cross-framework regulatory normalization — shared controls, evidence reuse, and coverage matrix.",
    "executive_heatmaps": "CIO/MD executive visibility — framework, application, BU, regional, and SLA heatmaps.",
    "integrations_hub": "Enterprise integration orchestration — ServiceNow, Jira, Prisma, Tripwire, SonarQube, and more.",
    "correlation": "Cross-tool governance correlation — incident-to-remediation-to-control failure chains.",
    "governance_analytics": "Enterprise governance intelligence — audit readiness, rejection patterns, remediation SLA, evidence freshness, and application risk posture.",
    "evidence_approval": "Evidence approval analytics — approved, rejected, pending validation, stale evidence, quality scorecards, and reviewer workload.",
    "exception_governance": "Exception governance dashboard — TD lifecycle, approval persistence, expiring exceptions, and CAB pending queue.",
    "ai_ops_assistant": "ECS AI Ops Assistant — banking governance copilot for incidents, audit, compliance, frameworks, evidence, and operations drilldowns.",
    "predefined_queries": "Predefined Queries — centralized catalog of control queries from the ECS Query Driven Control Library across all frameworks.",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _analytics_filters_key(analytics_filters: dict | None) -> str:
    if not analytics_filters:
        return ""
    import json
    return json.dumps(analytics_filters, sort_keys=True, default=str)


def get_module_capability(module: str, role: str = "owner", analytics_filters: dict | None = None) -> dict:
    filters_key = _analytics_filters_key(analytics_filters)
    cached = _MODULE_CAPABILITY_CACHE.get((module, role, filters_key))
    if cached is not None:
        return cached
    view = _build_module_capability(module, role, analytics_filters)
    _MODULE_CAPABILITY_CACHE[(module, role, filters_key)] = view
    return view


_MODULE_CAPABILITY_CACHE: dict[tuple[str, str, str], dict] = {}


def invalidate_module_capability_cache(module: str | None = None) -> None:
    if module is None:
        _MODULE_CAPABILITY_CACHE.clear()
        return
    for key in list(_MODULE_CAPABILITY_CACHE):
        if key[0] == module:
            del _MODULE_CAPABILITY_CACHE[key]


def _build_module_capability(module: str, role: str, analytics_filters: dict | None) -> dict:
    builders = {
        "scheduler": _scheduler_view,
        "upload": _upload_view,
        "evidence_health": _health_view,
        "search": _search_view,
        "completeness": _completeness_view,
        "reuse": _reuse_view,
        "lifecycle": _lifecycle_view,
        "comparison": _comparison_view,
        "integrations": _integrations_view,
        "enterprise": _enterprise_view,
        "pan_india": _pan_india_view,
        "reports": _reports_view,
        "audit_prep": _audit_prep_view,
        "trends": _trends_view,
        "onboarding": _onboarding_view,
        "framework_admin": _framework_admin_view,
        "risk_register": _risk_register_view,
        "exceptions_td": _exceptions_view,
        "cmdb": _cmdb_view,
        "regulatory_mapping": _regulatory_view,
        "executive_heatmaps": _heatmaps_view,
        "integrations_hub": _integrations_hub_view,
        "correlation": _correlation_view,
        "governance_analytics": _governance_analytics_view,
        "evidence_approval": _evidence_approval_view,
        "exception_governance": _exception_governance_view,
        "ai_ops_assistant": _ai_ops_assistant_view,
        "predefined_queries": _predefined_queries_view,
    }
    fn = builders.get(module)
    if not fn:
        return {"purpose": "", "kpis": [], "rows": [], "role": role}
    if module in ("trends", "governance_analytics", "audit_prep"):
        view = fn(role, analytics_filters)
    else:
        view = fn(role)
    view["purpose"] = MODULE_PURPOSES.get(module, "")
    view["module"] = module
    view["role"] = role
    return view


def _scheduler_view(role: str) -> dict:
    from modules.operations.engines.operations_mock_data import build_operations_dataset
    from modules.operations.engines.scheduler_intelligence import build_scheduler_intelligence
    from modules.operations.engines.scheduler_module import get_scheduler_dashboard, is_scheduler_paused
    from modules.shared.services.execution_engine_registry import evidence_collection_engine

    ops = build_operations_dataset("scheduler", role)
    dash = get_scheduler_dashboard()
    intel = build_scheduler_intelligence(paused=is_scheduler_paused())
    jobs = ops["records"]["jobs"]
    failed_jobs = ops["records"]["failures"]
    failed = [j for j in jobs if j.get("status") in ("Failed", "Partial", "Delayed")]
    ys = intel["yesterday_summary"]
    ys = {
        **ys,
        "applications_scanned": len(ops["records"]["application_scans"]),
        "evidence_collected": sum(s["evidence_collected"] for s in ops["records"]["application_scans"]),
        "controls_auto_validated": sum(j["controls_validated"] for j in jobs),
        "failed_collections": len(failed),
    }
    return {
        "kpis": [
            {"label": "Apps Scanned", "value": len(ops["records"]["application_scans"]), "tone": "primary"},
            {"label": "Evidence Collected", "value": sum(s["evidence_collected"] for s in ops["records"]["application_scans"][:50]), "tone": "success"},
            {"label": "Auto-Validated", "value": sum(j["controls_validated"] for j in jobs[:50]), "tone": "info"},
            {"label": "Failed Collections", "value": len(failed), "tone": "danger"},
        ],
        "operations_dataset": ops,
        "scheduler_health": {
            "status": "Paused" if intel["paused"] else "Operational",
            "uptime_pct": dash["status"]["success_rate_pct"],
            "healthy_jobs": len(jobs) - len(failed),
            "total_jobs": len(jobs),
            "live_status": intel["live_status"],
        },
        "rows": jobs[:20],
        "failed_jobs": failed[:30],
        "execution_history": intel["run_history"],
        "yesterday_summary": ys,
        "cron_timeline": ops["records"]["cron_runs"][:12],
        "application_scans": ops["records"]["application_scans"],
        "scheduler_failures": failed_jobs[:30],
        "upcoming_plan": intel["upcoming_plan"],
        "compliance_impact": intel["compliance_impact"],
        "integration_health": intel["integration_health"],
        "paused": intel["paused"],
        "execution_engine": evidence_collection_engine(paused=intel["paused"], dashboard=dash),
        "actions": _actions_for(role, scheduler=True),
    }


def _upload_view(role: str) -> dict:
    from modules.operations.engines.operations_mock_data import build_operations_dataset
    from modules.governance.engines.operational_mock_data import MOCK_UPLOAD_SAMPLES

    ops = build_operations_dataset("upload", role)
    uploads = ops["records"]["uploads"]
    batch_list = ops["records"]["batches"]
    return {
        "kpis": [
            {"label": "Active Batches", "value": len(batch_list), "tone": "primary"},
            {"label": "Files Ingested", "value": len(uploads), "tone": "success"},
            {"label": "Duplicates Flagged", "value": sum(1 for u in uploads if u["status"] == "Rejected"), "tone": "warning"},
            {"label": "Ingestion Errors", "value": sum(u.get("error_count", 0) for u in uploads), "tone": "danger"},
        ],
        "operations_dataset": ops,
        "rows": batch_list,
        "tracker_rows": uploads,
        "recent_uploads": uploads[:10],
        "mock_samples": MOCK_UPLOAD_SAMPLES,
        "actions": _actions_for(role, upload=True),
    }


def _health_view(role: str) -> dict:
    from modules.governance.engines.evidence_health_engine import build_evidence_health_view
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    view = build_evidence_health_view(role)
    view["standard_dataset"] = build_standard_dataset("evidence_health", role)
    view["actions"] = _actions_for(role, health=True)
    view["integrity"] = get_health_dashboard()
    return view


def _search_view(role: str) -> dict:
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    discovery = build_search_discovery()
    defaults = search_defaults()
    results = discovery["results"] or defaults["default_results"]
    semantic = discovery["semantic_matches"] or defaults["default_results"][:12]
    std = build_standard_dataset("search", role)
    return {
        "kpis": [
            {"label": "Indexed Artefacts", "value": discovery["total_indexed"], "tone": "primary"},
            {"label": "Frameworks Mapped", "value": len(FRAMEWORK_CATALOG), "tone": "info"},
            {"label": "Reuse Suggestions", "value": len(discovery["reuse_suggestions"]), "tone": "success"},
            {"label": "Search Results", "value": len(results), "tone": "secondary"},
        ],
        "rows": results,
        "discovery": discovery,
        "framework_filters": discovery["framework_filters"],
        "default_results": defaults["default_results"],
        "control_lookup": defaults["control_lookup"],
        "findings": defaults["findings"],
        "semantic_matches": semantic,
        "reuse_suggestions": discovery["reuse_suggestions"],
        "standard_dataset": std,
        "actions": _actions_for(role, search=True),
    }


def _completeness_view(role: str) -> dict:
    from modules.governance.engines.governance_completeness_engine import build_completeness_dashboard, build_completeness_dataset

    dash = build_completeness_dashboard(role=role)
    dataset = build_completeness_dataset(role)
    return {
        "kpis": dash["kpis"],
        "completeness_dataset": dataset,
        "completeness_pct": dash.get("completeness_pct"),
        "detail_rows": dash["detail_rows"],
        "framework_summaries": dash["framework_summaries"],
        "framework_rows": dash["framework_summaries"],
        "application_readiness": dash["detail_rows"],
        "control_rows": dash["detail_rows"],
        "rows": dash["gap_rows"],
        "missing_evidence_rows": dash["missing_evidence_rows"],
        "upload_kpis": dash["upload_kpis"],
        "incomplete": [r for r in dash["detail_rows"] if r["readiness_pct"] < 80],
        "actions": _actions_for(role, completeness=True),
    }


def _reuse_view(role: str) -> dict:
    from modules.executive_overview.engines.enterprise_mock_service import build_reuse_mappings
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    reuse_data = build_reuse_mappings(120)
    std = build_standard_dataset("reuse", role)
    candidates = reuse_data["rows"]
    pending = reuse_data["pending_rows"]
    fw_breakdown: dict[str, dict] = {}
    for r in candidates:
        fw = r["source_framework"]
        bucket = fw_breakdown.setdefault(fw, {"framework": fw, "reuse_groups": 0, "controls_linked": 0, "pending": 0, "approved": 0})
        bucket["reuse_groups"] += 1
        bucket["controls_linked"] += r.get("controls_linked", 1)
        if r.get("status") == "Approved":
            bucket["approved"] += 1
        else:
            bucket["pending"] += 1
    return {
        "kpis": [
            {"label": "Reuse Groups", "value": len(candidates), "tone": "primary"},
            {"label": "Mapped Controls", "value": sum(c["controls_linked"] for c in candidates), "tone": "success"},
            {"label": "Pending Approval", "value": len(pending), "tone": "warning"},
            {"label": "Hours Saved", "value": REUSE_METRICS["top_saving_hours"], "tone": "teal"},
        ],
        "rows": candidates,
        "pending_rows": pending,
        "candidates": reuse_data["candidates"],
        "workbench": reuse_data["workbench"],
        "framework_breakdown": list(fw_breakdown.values()),
        "standard_dataset": std,
        "actions": _actions_for(role, reuse=True),
    }


def _lifecycle_view(role: str) -> dict:
    from modules.governance.engines.governance_lifecycle_engine import build_lifecycle_dashboard, build_lifecycle_dataset

    dash = build_lifecycle_dashboard(role=role)
    dataset = build_lifecycle_dataset(role)
    return {
        "kpis": dash["kpis"],
        "lifecycle_dataset": dataset,
        "controls": dash["controls"],
        "evidence_rows": dash["evidence"],
        "observations": dash["observations"],
        "remediations": dash["remediations"],
        "audits": dash["audits"],
        "exceptions": dash["exceptions"],
        "timelines": dash["timelines"],
        "charts": dash["charts"],
        "rows": dash["controls"],
        "actions": _actions_for(role, lifecycle=True),
    }


def _comparison_view(role: str) -> dict:
    from modules.governance.engines.comparison_engine import build_comparison_dashboard, build_comparison_dataset
    from modules.shared.services.role_filter_scope import apply_role_scope, apps_for_role

    dash = build_comparison_dashboard()
    dataset = build_comparison_dataset(role)
    readiness = apply_role_scope(dash["readiness_matrix"], role)
    allowed = apps_for_role(role)
    if allowed:
        pairs = [p for p in dash["comparison_pairs"] if p.get("app_a") in allowed or p.get("app_b") in allowed]
    else:
        pairs = dash["comparison_pairs"]
    if not pairs:
        pairs = dash["comparison_pairs"][:12]
    cards = apply_role_scope(dash["heatmap_cards"], role)
    if not cards:
        cards = dash["heatmap_cards"][:8]
    rankings = sorted(readiness, key=lambda r: -r["readiness_pct"])
    return {
        "kpis": dash["kpis"],
        "comparison_pairs": pairs,
        "heatmap_cards": cards,
        "readiness_matrix": readiness,
        "trends": dash["trends"],
        "comparison_dataset": dataset,
        "pair_rows": pairs,
        "rankings": rankings,
        "variance_rows": pairs,
        "heatmap": [{"application": c["application"], "framework": c["framework"], "pct": c["readiness_pct"], "tone": c["tone"]} for c in cards],
        "rows": rankings,
        "actions": _actions_for(role, comparison=True),
    }


def _integrations_view(role: str) -> dict:
    from modules.operations.engines.integration_health_engine import build_integration_health_dashboard
    from modules.operations.engines.integrations_module import get_integrations_hub_dashboard
    from modules.operations.engines.operations_mock_data import build_operations_dataset
    from modules.governance.engines.operational_mock_data import build_integration_sync_jobs

    ops = build_operations_dataset("integrations", role)
    dash = build_integration_health_dashboard()
    hub = get_integrations_hub_dashboard()
    rows = []
    for c in hub["connectors"]:
        rows.append({
            **c,
            "pipeline": c.get("name", "Connector"),
            "last_sync": c.get("last_sync", "2026-05-24 06:00 UTC"),
            "records_ingested": c.get("records_pulled", c.get("records", 128)),
            "api_health": "Healthy" if c.get("api_status", c["status"]) in ("Healthy", "Connected", "Synced") else "Degraded",
            "sync_status": c.get("sync_status", c["status"]),
        })
    event_logs = list(ops["records"]["events"])
    return {
        "kpis": dash["kpis"],
        "operations_dataset": ops,
        "health_rows": dash["health_rows"],
        "all_health_rows": dash["all_health_rows"],
        "connector_usage_bars": dash["connector_usage_bars"],
        "health_distribution": dash["health_distribution"],
        "framework_dependencies": dash["framework_dependencies"],
        "rows": rows,
        "sync_jobs": build_integration_sync_jobs(rows),
        "event_logs": event_logs,
        "grouped": hub.get("grouped", {}),
        "sync_issue_rows": hub.get("sync_issue_rows", []),
        "actions": _actions_for(role, integrations=True),
    }


def _enterprise_view(role: str) -> dict:
    from modules.executive_overview.engines.executive_analytics_engine import build_banking_bu_analytics, build_bu_chart_series
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    ent = enterprise_dashboard()
    stats = ecs_state.build_evidence_analytics()
    std = build_standard_dataset("enterprise", role)
    bu_analytics = build_banking_bu_analytics(role)
    rows = []
    for fw in stats["framework_stats"]:
        rows.append({
            "framework": fw["name"],
            "application": "All Applications",
            "maturity_pct": fw["compliance_pct"],
            "approved": fw["approved"],
            "total": fw["total"],
            "risk": "High" if fw["compliance_pct"] < 70 else ("Medium" if fw["compliance_pct"] < 85 else "Low"),
            "open_items": fw["pending"] + fw["submitted"] + fw["rejected"],
            "owner": OWNERS[hash(fw["name"]) % len(OWNERS)],
            "status": "Monitoring",
        })
    return {
        "kpis": [
            {"label": "Enterprise Compliance", "value": f"{ent['kpis']['enterprise_compliance_pct']}%", "tone": "success"},
            {"label": "National Score", "value": f"{ent['national_score']}%", "tone": "primary"},
            {"label": "Open Observations", "value": ent["kpis"]["open_observations"], "tone": "warning"},
            {"label": "Frameworks at Risk", "value": len([r for r in rows if r["risk"] == "High"]), "tone": "danger"},
        ],
        "rows": rows,
        "business_units": BUSINESS_UNITS,
        "banking_bu_analytics": bu_analytics,
        "bu_charts": build_bu_chart_series(bu_analytics),
        "enterprise": ent,
        "maturity_heatmap": [{"framework": r["framework"], "pct": r["maturity_pct"]} for r in rows],
        "standard_dataset": std,
        "actions": _actions_for(role, enterprise=True),
    }


def _pan_india_view(role: str) -> dict:
    from modules.executive_overview.engines.enterprise_mock_service import build_pan_india_posture
    from modules.executive_overview.engines.executive_analytics_engine import enhance_pan_india_regions
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    posture = build_pan_india_posture()
    std = build_standard_dataset("pan_india", role)
    enhanced = enhance_pan_india_regions(posture["regions"], posture["framework_matrix"])
    rows = []
    for r in enhanced:
        rows.append({
            **r,
            "zone": r["region"],
            "sla_breaches": r["sla_breaches"],
            "compliance_pct": r["score"],
            "risk_level": r["risk_level"],
        })
    return {
        "kpis": [
            {"label": "Regions", "value": len(rows), "tone": "primary"},
            {"label": "Branches", "value": sum(r["branches"] for r in rows), "tone": "info"},
            {"label": "Open Observations", "value": sum(r["observations_open"] for r in rows), "tone": "warning"},
            {"label": "SLA Breaches", "value": sum(r["sla_breaches"] for r in rows), "tone": "danger"},
        ],
        "rows": rows,
        "framework_matrix": posture["framework_matrix"],
        "zone_heatmap": [
            {"zone": r["zone"], "score": r["compliance_pct"], "risk": r["risk_level"], "pci": r.get("pci_readiness"), "critical_obs": r.get("critical_observations", 0)}
            for r in rows
        ],
        "standard_dataset": std,
        "actions": _actions_for(role, pan_india=True),
    }


def _reports_view(role: str) -> dict:
    from modules.executive_overview.engines.ecs_reports_engine import report_type_for_catalog_id
    from modules.executive_overview.engines.reports_analytics_engine import build_reports_overview
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    overview = build_reports_overview(role)
    std = build_standard_dataset("reports", role)
    rows = []
    for r in overview["catalog"]:
        rows.append({
            **r,
            "view_type": report_type_for_catalog_id(r["id"]),
            "generated_at": r.get("generated_at", "2026-05-20 14:00 UTC"),
            "format": r.get("format", "PDF"),
            "schedule": r.get("schedule", "On Demand"),
            "framework": r.get("framework", "Enterprise-wide"),
            "application": r.get("application", "All Applications"),
            "owner": r.get("owner", OWNERS[0]),
            "risk": r.get("risk", "Low"),
            "status": r.get("status", "Generated"),
        })
    return {
        "kpis": overview["kpis"],
        "rows": rows,
        "history_rows": overview["history_rows"],
        "observation_rows": overview["observation_rows"],
        "generated_records": overview["generated_records"],
        "scheduled_records": overview["scheduled_records"],
        "pending_records": overview["pending_records"],
        "failed_records": overview["failed_records"],
        "reports_overview": overview,
        "standard_dataset": std,
        "actions": _actions_for(role, reports=True),
    }


def _audit_prep_view(role: str, filters: dict | None = None) -> dict:
    from modules.governance.engines.audit_prep_data import build_audit_prep_view
    from modules.governance.engines.audit_schedule_engine import build_audit_operations
    from modules.executive_overview.engines.executive_analytics_engine import build_audit_prep_heatmaps
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    view = build_audit_prep_view(role, filters)
    view["standard_dataset"] = build_standard_dataset("audit_prep", role, filters)
    view["audit_heatmaps"] = build_audit_prep_heatmaps(filters)
    view["actions"] = _actions_for(role, audit_prep=True)

    # Dynamic audit operations — replaces the legacy static upcoming-audits list
    # so every framework (quarterly + yearly) is represented across the rolling
    # 12-month window.
    ops = build_audit_operations(role, filters)
    view["upcoming_audits"] = ops["upcoming_audits"]
    view["audit_calendar"] = ops["calendar"]
    view["audit_pipeline"] = ops["pipeline"]
    view["baselining_history"] = ops["baselining_history"]
    view["audit_kpi_drilldowns"] = ops["kpi_drilldowns"]
    view["audit_summary"] = ops["summary"]
    if view["upcoming_audits"]:
        nxt = next((a for a in view["upcoming_audits"] if a["days_remaining"] >= 0), view["upcoming_audits"][0])
        view["next_audit_countdown"] = {
            "framework": nxt["framework"],
            "application": nxt["application"],
            "auditor": nxt["auditor"],
            "days_remaining": nxt["days_remaining"],
            "readiness_pct": nxt["readiness_pct"],
            "blockers": nxt["blockers"],
            "audit_id": nxt["audit_id"],
        }
    return view


def _trends_view(role: str, filters: dict | None = None) -> dict:
    from modules.executive_overview.engines.executive_analytics_engine import build_granularity_trends
    from modules.governance.engines.governance_intelligence import build_trends_module_view

    view = build_trends_module_view(role, filters)
    view["granularity_trends"] = build_granularity_trends(filters)
    view["actions"] = _actions_for(role, trends=True)
    return view


def _onboarding_view(role: str) -> dict:
    from modules.operations.engines.onboarding_engine import (
        ALL_FRAMEWORKS,
        WORKFLOW_STEPS,
        build_application_onboarder_dashboard,
        recent_onboarding_suggestions,
    )
    from modules.operations.engines.operations_mock_data import build_operations_dataset
    from modules.governance.engines.operational_mock_data import build_onboarding_pipelines, build_post_onboarding_metrics, build_onboarding_challenges

    ops = build_operations_dataset("onboarding", role)
    onboard_rows = ops["records"]["applications"]
    rows = []
    for r in onboard_rows:
        rows.append({
            "application": r["application"],
            "stage": r["stage"],
            "status": r["status"],
            "progress_pct": r["progress_pct"],
            "frameworks_mapped": r["frameworks_mapped"],
            "owner": r["owner"],
            "framework": r["framework"],
            "risk": r["risk"],
            "pending_tasks": r["controls_missing"],
            "pipeline_id": r.get("pipeline_id", ""),
            "controls_discovered": r.get("controls_discovered", 0),
            "controls_implemented": r.get("controls_implemented", 0),
            "controls_missing": r.get("controls_missing", 0),
            "readiness_pct": r.get("readiness_pct", r.get("progress_pct", 0)),
        })
    post_metrics = build_post_onboarding_metrics(rows[:20])
    challenges = build_onboarding_challenges(rows[:20])
    accepting = [m for m in post_metrics if m.get("accepting_evidence")]
    suggestions = recent_onboarding_suggestions(ecs_state.onboarded_applications)
    return {
        "kpis": [
            {"label": "Applications", "value": len(rows), "tone": "primary"},
            {"label": "Accepting Evidence", "value": len(accepting), "tone": "success"},
            {"label": "Observation Closures", "value": sum(m["observation_closures_count"] for m in post_metrics), "tone": "info"},
            {"label": "Avg Compliance Adherence", "value": f"{round(sum(m['audit_compliance_adherence_pct'] for m in post_metrics) / max(len(post_metrics), 1), 1)}%", "tone": "primary"},
            {"label": "Failed / Stalled", "value": len(challenges), "tone": "danger"},
        ],
        "operations_dataset": ops,
        "rows": rows,
        "pipelines": build_onboarding_pipelines(rows[:30]),
        "post_onboarding_metrics": post_metrics,
        "onboarding_challenges": challenges,
        "stages": ["Initial Setup", "Framework Mapping", "Owner Assignment", "Registration Complete"],
        "onboarding_apps": suggestions,
        "onboarding_frameworks": ALL_FRAMEWORKS,
        "progress_steps": WORKFLOW_STEPS,
        "onboarder": build_application_onboarder_dashboard(),
        "business_units": [u["unit"] for u in BUSINESS_UNITS],
        "actions": _actions_for(role, onboarding=True),
    }


def _framework_admin_view(role: str) -> dict:
    from modules.frameworks.engines.framework_onboarding_engine import build_admin_dashboard

    dash = build_admin_dashboard(role)
    return {
        **dash,
        "rows": dash["frameworks"],
        "purpose": MODULE_PURPOSES["framework_admin"],
        "role": role,
        "actions": _actions_for(role, framework_admin=True),
    }


def _risk_register_view(role: str) -> dict:
    from modules.enterprise_grc.engines.grc_demo_service import build_risk_register_demo_view

    view = build_risk_register_demo_view(role)
    view["actions"] = _actions_for(role, risk=True)
    view["standard_dataset"] = {
        "module": "risk_register",
        "role": role,
        "records": {
            "risks": view["rows"],
            "top_risks": view["top_risks"],
            "bu_exposure": view["bu_exposure"],
        },
    }
    return view


def _exceptions_view(role: str) -> dict:
    from modules.enterprise_grc.engines.enterprise_grc import build_exceptions_td
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    data = build_exceptions_td(role)
    std = build_standard_dataset("exceptions_td", role)
    return {**data, "standard_dataset": std, "actions": _actions_for(role, exception=True)}


def _cmdb_view(role: str) -> dict:
    from modules.enterprise_grc.engines.enterprise_grc import build_cmdb_inventory
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    data = build_cmdb_inventory(role)
    std = build_standard_dataset("cmdb", role)
    return {**data, "standard_dataset": std, "actions": _actions_for(role, cmdb=True)}


def _regulatory_view(role: str) -> dict:
    from modules.executive_overview.engines.executive_analytics_engine import build_regulatory_traceability
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    data = build_regulatory_traceability()
    std = build_standard_dataset("regulatory_mapping", role)
    rows = std["records"].get("mappings", data["mappings"])
    return {**data, "rows": rows, "standard_dataset": std, "actions": _actions_for(role, regulatory=True)}


def _heatmaps_view(role: str) -> dict:
    from modules.enterprise_grc.engines.enterprise_grc import build_executive_heatmaps
    from modules.executive_overview.engines.executive_analytics_engine import build_period_heatmaps
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    data = build_executive_heatmaps(role)
    std = build_standard_dataset("executive_heatmaps", role)
    rec = std["records"]
    if rec.get("application_heatmap"):
        data["application_heatmap"] = [{"name": r["application"], "score": r["score"], "risk": r["risk"]} for r in rec["application_heatmap"]]
    if rec.get("regional_heatmap"):
        data["regional_heatmap"] = [{"region": r["region"], "score": r["score"], "observations": r.get("observations", 0)} for r in rec["regional_heatmap"]]
    data["period_heatmaps"] = {
        "month": build_period_heatmaps("month"),
        "quarter": build_period_heatmaps("quarter"),
        "year": build_period_heatmaps("year"),
    }
    data["standard_dataset"] = std
    data["actions"] = _actions_for(role, heatmaps=True)
    return data


def _integrations_hub_view(role: str) -> dict:
    from modules.executive_overview.engines.integration_hub_executive_engine import build_integration_hub_executive_view
    view = build_integration_hub_executive_view(role)
    view["actions"] = _actions_for(role, hub=True)
    return view


def _correlation_view(role: str) -> dict:
    from modules.enterprise_grc.engines.correlation_engine import build_correlation_dashboard
    from modules.executive_overview.engines.executive_analytics_engine import build_correlation_graph
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    data = build_correlation_dashboard(role)
    graph = build_correlation_graph(role)
    std = build_standard_dataset("correlation", role)
    data["chains"] = std["records"].get("chains", data.get("chains", []))
    data["graph"] = graph
    data["node_details"] = graph["node_details"]
    data["standard_dataset"] = std
    data["actions"] = _actions_for(role, correlation=True)
    return data


def _exception_governance_view(role: str) -> dict:
    from modules.governance.engines.exception_state_engine import build_governance_dashboard
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    view = build_governance_dashboard(role)
    view["standard_dataset"] = build_standard_dataset("exception_governance", role)
    view["actions"] = _actions_for(role, exception=True)
    return view


def _evidence_approval_view(role: str) -> dict:
    from modules.governance.engines.evidence_approval_engine import build_evidence_approval_view
    from modules.shared.utils.standard_filter_engine import build_standard_dataset

    view = build_evidence_approval_view(role)
    view["standard_dataset"] = build_standard_dataset("evidence_approval", role)
    view["actions"] = _actions_for(role, evidence_approval=True)
    return view


def _governance_analytics_view(role: str, filters: dict | None = None) -> dict:
    from modules.enterprise_grc.engines.grc_demo_service import build_governance_analytics_demo_view

    view = build_governance_analytics_demo_view(role, filters)
    view["actions"] = _actions_for(role, gov_analytics=True)
    return view


def _ai_ops_assistant_view(role: str) -> dict:
    from modules.operations.engines.ai_ops_assistant_engine import build_assistant_view

    view = build_assistant_view(role, "cio@bank.com")
    view["actions"] = []
    view["rows"] = view.get("incident_rows", [])
    return view


def _predefined_queries_view(role: str) -> dict:
    from modules.operations.engines.predefined_queries_engine import get_predefined_queries_dashboard

    view = get_predefined_queries_dashboard(per_page=10)
    view["actions"] = []
    return view


def _actions_for(role: str, **flags) -> list[str]:
    """Return action keys allowed for role on this module type."""
    from modules.shared.services.role_permissions import filter_actions_for_role, is_auditor, is_executive_readonly

    r = role
    if flags.get("scheduler"):
        base = ["run_now", "pause", "resume", "retry", "change_frequency"] if r in ("owner", "auditor", "cio", "compliance_head") else ["run_now"]
        return filter_actions_for_role(r, base)
    if flags.get("upload"):
        return filter_actions_for_role(r, ["upload_batch", "validate", "reprocess", "approve_import", "reject_import"])
    if flags.get("health"):
        if is_auditor(r):
            return ["escalate_risk", "request_reupload", "assign_owner", "reassign", "approve", "reject"]
        if is_executive_readonly(r):
            return ["escalate_risk", "drill_down"]
        return ["replace", "extend", "escalate_risk", "request_upload"]
    if flags.get("search"):
        return ["open", "map_framework", "reuse", "compare"]
    if flags.get("completeness"):
        if is_auditor(r):
            return ["assign_gap", "request_owner", "request_reupload", "reassign", "escalate", "approve", "reject"]
        return filter_actions_for_role(r, ["assign_gap", "upload_missing", "request_owner"])
    if flags.get("reuse"):
        if is_auditor(r):
            return ["approve_reuse", "reject_reuse", "link", "compare"]
        return ["reuse_across", "link", "approve_reuse", "reject_reuse"]
    if flags.get("lifecycle"):
        if is_auditor(r):
            return ["assign_owner", "reassign", "escalate", "view_trail"]
        return filter_actions_for_role(r, ["renew", "archive", "retire", "extend_retention"])
    if flags.get("comparison"):
        return ["compare", "export_gap", "variance_report"]
    if flags.get("integrations"):
        return ["test_connection", "sync_now", "reconnect", "view_logs"]
    if flags.get("enterprise"):
        return ["drill_down", "view_gaps", "escalate_risk"] if r in ("cio", "vertical_head", "compliance_head") else ["drill_down"]
    if flags.get("pan_india"):
        return ["open_region", "escalate_zone", "export_regional"]
    if flags.get("reports"):
        return ["generate", "export_pdf", "export_excel", "schedule"]
    if flags.get("audit_prep"):
        if is_auditor(r):
            return ["assign_owner", "reassign", "escalate", "request_reupload", "mock_audit", "approve", "reject"]
        return filter_actions_for_role(r, ["close_gap", "upload_missing", "assign_owner", "mock_audit", "generate_package"])
    if flags.get("trends"):
        return ["export_chart", "drill_down"]
    if flags.get("onboarding"):
        return filter_actions_for_role(r, ["start", "assign_framework", "assign_owner", "complete_registration"])
    if flags.get("framework_admin"):
        if is_auditor(r):
            return ["review", "approve", "map", "export_pdf", "export_excel"]
        if r in ("cio", "compliance_head", "enterprise_admin", "admin"):
            return ["import", "map", "review", "approve", "activate", "export_pdf", "export_excel", "export_csv"]
        return ["reuse", "upload_new", "compare"]
    if flags.get("risk"):
        if is_auditor(r):
            return ["escalate_risk", "assign_owner", "reassign", "link_control", "link_observation"]
        return filter_actions_for_role(r, ["accept_risk", "escalate_risk", "mitigate_risk", "assign_owner", "request_exception", "link_control"])
    if flags.get("exception"):
        if is_auditor(r):
            return ["approve_exception", "reject_exception", "escalate_expired_td", "close_exception"]
        return ["approve_exception", "reject_exception", "extend_td", "escalate_expired_td", "renew_exception"]
    if flags.get("evidence_approval"):
        if is_auditor(r):
            return ["view_trail", "export_summary", "drill_down", "approve", "reject", "request_reupload", "assign_owner", "escalate"]
        if r == "owner":
            return ["view_trail", "resubmit", "drill_down"]
        return ["view_trail", "export_summary", "drill_down", "escalate_stale"]
    if flags.get("cmdb"):
        return ["open_asset", "view_controls", "view_risks", "view_evidence"]
    if flags.get("regulatory"):
        return ["reuse_evidence", "link_control", "map_framework", "export_mapping"]
    if flags.get("heatmaps"):
        return ["drill_down", "escalate_risk", "view_exception", "approve_closure"]
    if flags.get("hub"):
        return ["sync_now", "test_connection", "view_logs", "retry_failed_sync"]
    if flags.get("correlation"):
        if is_auditor(r):
            return ["view_chain", "escalate", "assign_owner", "link_control"]
        return ["view_chain", "escalate", "link_control"]
    if flags.get("gov_analytics"):
        return ["export_chart", "drill_down", "view_trends"]
    return []


def module_counter_rows(module: str, role: str) -> int:
    """Live row count for nav badge — derived from module capability, not workflow queue."""
    view = get_module_capability(module, role)
    rows = view.get("rows", [])
    if module == "completeness":
        return len(rows) + len(view.get("missing_evidence_rows", [])) + len(view.get("incomplete", []))
    if module == "comparison":
        return len(view.get("variance_rows", [])) + len([r for r in rows if r.get("risk") in ("High", "Critical", "Elevated")])
    if module == "search":
        return len(get_all_evidence_records())
    if module == "risk_register":
        return len([r for r in view.get("rows", []) if r.get("status") in ("Open", "Escalated")])
    if module == "exceptions_td":
        return len([r for r in view.get("rows", []) if r.get("status") in ("Submitted", "Under Review", "Draft")]) + len(view.get("expired", []))
    if module == "evidence_approval":
        return len(view.get("pending_rows", [])) + len(view.get("stale_rows", []))
    if module == "exception_governance":
        return len(view.get("pending_cab", [])) + len(view.get("expiring_month", []))
    if module == "cmdb":
        return len([r for r in view.get("rows", []) if r.get("risk_rating") in ("Critical", "High") or not r.get("monitoring_enabled")])
    if module == "integrations_hub":
        return sum(1 for r in view.get("rows", []) if r.get("sync_health") != "Healthy" or r.get("failed_syncs", 0) > 0)
    if module == "correlation":
        return len([c for c in view.get("chains", []) if c.get("status") == "Open"])
    if module == "ai_ops_assistant":
        return len(view.get("incident_rows", []))
    if module == "predefined_queries":
        return view.get("all_predefined_count", len(rows))
    return len(rows)
