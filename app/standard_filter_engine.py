"""Centralized standard-profile filter datasets for governance workspace modules."""

from __future__ import annotations

from app import ecs_state
from app.demo_metrics import BUSINESS_UNITS, REUSE_METRICS
from app.enterprise_mock_service import build_pan_india_posture, build_reuse_mappings
from app.governance_mock_data import health_enrichment, OWNERS
from app.analytics_module import enterprise_dashboard
from app.role_filter_scope import apply_role_scope, scope_reuse_for_role, scope_reports_for_role


def _match_row(r: dict, v: dict) -> bool:
    fw = v.get("framework") or ""
    app = v.get("application") or ""
    owner = v.get("owner") or ""
    risk = v.get("risk") or ""
    status = v.get("status") or ""
    region = v.get("region") or ""
    severity = v.get("severity") or ""
    if fw and not fw.startswith("All ") and r.get("framework") != fw:
        if fw not in str(r.get("framework_mapping", "")):
            return False
    if app and not app.startswith("All ") and r.get("application") != app:
        return False
    if owner and not owner.startswith("All ") and r.get("owner") != owner:
        return False
    if region and not region.startswith("All ") and r.get("region") not in (region, None, ""):
        if region not in str(r.get("region", r.get("zone", ""))):
            return False
    if risk and not risk.startswith("All "):
        rr = r.get("risk") or r.get("risk_level") or r.get("residual_risk") or ""
        if risk == "High":
            if rr not in ("High", "Critical"):
                return False
        elif rr != risk:
            return False
    if severity and not severity.startswith("All "):
        sev = r.get("severity") or r.get("residual_risk") or r.get("risk") or r.get("risk_level") or ""
        if severity == "High":
            if sev not in ("High", "Critical"):
                return False
        elif sev != severity:
            return False
    if status and not status.startswith("All "):
        candidates = [r.get("status"), r.get("health"), r.get("issue"), r.get("reuse_status")]
        hit = any(status.lower() in str(st).lower() for st in candidates if st)
        if not hit:
            return False
    return True


def filter_rows(rows: list[dict], v: dict) -> list[dict]:
    return [r for r in rows if _match_row(r, v)]


def build_standard_dataset(module: str, role: str = "owner", filters: dict | None = None) -> dict:
    builders = {
        "enterprise": _enterprise_dataset,
        "pan_india": _pan_india_dataset,
        "reuse": _reuse_dataset,
        "evidence_health": _health_dataset,
        "reports": _reports_dataset,
        "cmdb": _cmdb_dataset,
        "exceptions_td": _exceptions_dataset,
        "audit_prep": _audit_prep_dataset,
        "search": _search_dataset,
        "risk_register": _risk_register_dataset,
        "regulatory_mapping": _regulatory_dataset,
        "executive_heatmaps": _heatmaps_dataset,
        "correlation": _correlation_dataset,
        "evidence_approval": _evidence_approval_dataset,
        "exception_governance": _exception_governance_dataset,
    }
    fn = builders.get(module)
    if not fn:
        return {"module": module, "role": role, "records": {}}
    if module == "audit_prep":
        return fn(role, filters or {})
    return fn(role)


def _enterprise_dataset(role: str) -> dict:
    from app.executive_analytics_engine import build_banking_bu_analytics

    ent = enterprise_dashboard()
    stats = ecs_state.build_evidence_analytics()
    framework_rows = []
    for fw in stats["framework_stats"]:
        framework_rows.append({
            "framework": fw["name"],
            "application": "All Applications",
            "maturity_pct": fw["compliance_pct"],
            "approved": fw["approved"],
            "total": fw["total"],
            "open_items": fw["pending"] + fw["submitted"] + fw["rejected"],
            "risk": "High" if fw["compliance_pct"] < 70 else ("Medium" if fw["compliance_pct"] < 85 else "Low"),
            "owner": OWNERS[hash(fw["name"]) % len(OWNERS)],
            "status": "Monitoring",
        })
    bu_rows = []
    for bu in BUSINESS_UNITS:
        bu_rows.append({
            **bu,
            "unit": bu["unit"],
            "framework": "Enterprise-wide",
            "application": bu["unit"],
            "owner": OWNERS[hash(bu["unit"]) % len(OWNERS)],
            "status": "Active",
        })
    gap_rows = [r for r in framework_rows if r["open_items"] > 5]
    gap_rows = apply_role_scope(gap_rows, role)
    bu_rows = apply_role_scope(bu_rows, role) if role == "vertical_head" else bu_rows
    banking_bu = build_banking_bu_analytics(role)
    return {
        "module": "enterprise",
        "role": role,
        "records": {
            "frameworks": framework_rows,
            "business_units": bu_rows,
            "banking_bu": banking_bu,
            "gaps": gap_rows,
            "national_score": ent["national_score"],
            "open_observations": ent["kpis"]["open_observations"],
        },
    }


def _pan_india_dataset(role: str) -> dict:
    from app.executive_analytics_engine import enhance_pan_india_regions

    posture = build_pan_india_posture()
    enhanced = enhance_pan_india_regions(posture["regions"], posture["framework_matrix"])
    return {
        "module": "pan_india",
        "role": role,
        "records": {
            "regions": enhanced,
            "framework_matrix": posture["framework_matrix"],
            "zone_heatmap": [
                {"zone": r["region"], "score": r["score"], "risk": r["risk_level"], "pci": r.get("pci_readiness"), "critical_obs": r.get("critical_observations", 0)}
                for r in enhanced
            ],
        },
    }


def _reuse_dataset(role: str) -> dict:
    data = build_reuse_mappings(120)
    return {
        "module": "reuse",
        "role": role,
        "records": scope_reuse_for_role(data, role),
    }


def _health_dataset(role: str) -> dict:
    from app.evidence_health_engine import build_evidence_health_view

    view = build_evidence_health_view(role)
    return {
        "module": "evidence_health",
        "role": role,
        "records": {
            "queue": view["rows"],
            "framework_breakdown": view["framework_breakdown"],
            "application_breakdown": view["application_breakdown"],
            "rejection_trends": view["rejection_trends"],
            "stale_aging": view["stale_aging"],
            "categories": view["categories"],
        },
    }


def _reports_dataset(role: str) -> dict:
    from app.reporting_module import list_report_history, list_report_observation_rows, list_reports, list_scheduled_reports

    rows = []
    for r in list_reports():
        rows.append({
            **r,
            "framework": r.get("framework", "Enterprise-wide"),
            "application": r.get("application", "All Applications"),
            "owner": r.get("owner", OWNERS[0]),
            "risk": r.get("risk", "Low"),
            "status": r.get("status", "Generated"),
            "generated_at": r.get("generated_at", "2026-05-20 14:00 UTC"),
        })
    rows = scope_reports_for_role(rows, role)
    scheduled = scope_reports_for_role(list_scheduled_reports(), role)
    history = scope_reports_for_role(list_report_history(), role)
    observations = list_report_observation_rows(role)
    return {
        "module": "reports",
        "role": role,
        "records": {"reports": rows, "scheduled": scheduled, "history": history, "observations": observations},
    }


def _cmdb_dataset(role: str) -> dict:
    from app.enterprise_grc import build_cmdb_inventory

    data = build_cmdb_inventory(role)
    assets = []
    for r in data.get("rows", []):
        assets.append({
            **r,
            "framework": (r.get("frameworks_mapped") or ["ITPP"])[0],
            "application": r.get("name", "Net Banking"),
            "owner": r.get("owner", OWNERS[0]),
            "risk": r.get("risk_rating", "Medium"),
            "status": "Mapped" if r.get("monitoring_enabled") else "Unmonitored",
            "asset_name": r.get("name"),
            "hostname": r.get("name"),
        })
    assets = apply_role_scope(assets, role)
    return {"module": "cmdb", "role": role, "records": {"assets": assets}}


def _exceptions_dataset(role: str) -> dict:
    from app.exception_state_engine import get_all_exceptions

    rows = []
    for r in get_all_exceptions(role):
        rows.append({
            **r,
            "framework": r.get("framework", "PCI DSS"),
            "application": r.get("application", "Net Banking"),
            "owner": r.get("owner", OWNERS[0]),
            "risk": r.get("residual_risk", r.get("risk", "Medium")),
            "status": r.get("status", "Open"),
        })
    return {"module": "exceptions_td", "role": role, "records": {"exceptions": rows}}


def _audit_prep_dataset(role: str, filters: dict | None = None) -> dict:
    from app.audit_prep_data import build_audit_prep_view

    view = build_audit_prep_view(role, filters or {})
    gaps = view.get("actionable_gaps", view.get("rows", []))
    for g in gaps:
        g.setdefault("framework", g.get("framework", "PCI DSS"))
        g.setdefault("application", g.get("application", "Net Banking"))
        g.setdefault("owner", g.get("owner", OWNERS[0]))
        g.setdefault("risk", g.get("priority", "Medium"))
        g.setdefault("status", g.get("status", "Open"))
    audits = view.get("upcoming_audits", [])
    for a in audits:
        a.setdefault("owner", a.get("owner", OWNERS[0]))
        a.setdefault("risk", "High" if a.get("readiness_pct", 100) < 75 else "Medium")
        a.setdefault("status", "Scheduled")
    gaps = apply_role_scope(gaps, role)
    audits = apply_role_scope(audits, role)
    readiness_apps = apply_role_scope(view.get("readiness_by_application", []), role)
    return {
        "module": "audit_prep",
        "role": role,
        "records": {
            "gaps": gaps,
            "audits": audits,
            "requests": view.get("auditor_requests", []),
            "submissions": view.get("pending_submissions", []),
            "readiness_apps": readiness_apps,
            "weighted_readiness": view.get("weighted_readiness_pct", 0),
        },
    }


def _search_dataset(role: str) -> dict:
    from app.search_module import build_search_discovery
    from app.governance_mock_data import search_defaults

    discovery = build_search_discovery()
    defaults = search_defaults()
    results = discovery.get("results") or defaults.get("default_results", [])
    for r in results:
        r.setdefault("framework", r.get("framework", "PCI DSS"))
        r.setdefault("application", r.get("application", "Net Banking"))
        r.setdefault("owner", r.get("owner", OWNERS[0]))
        r.setdefault("risk", "Low")
        r.setdefault("status", r.get("status", "Approved"))
    results = apply_role_scope(results, role)
    controls = apply_role_scope(defaults.get("control_lookup", []), role)
    findings = apply_role_scope(defaults.get("findings", []), role)
    return {
        "module": "search",
        "role": role,
        "records": {
            "results": results,
            "controls": controls,
            "findings": findings,
            "total_indexed": discovery.get("total_indexed", len(results)),
        },
    }


def _risk_register_dataset(role: str) -> dict:
    from app.enterprise_grc import build_risk_register

    data = build_risk_register(role)
    rows = []
    for r in data.get("rows", []):
        rows.append({
            **r,
            "framework": r.get("linked_framework", "Enterprise-wide"),
            "risk": r.get("residual_risk", "Medium"),
        })
    rows = apply_role_scope(rows, role)
    return {
        "module": "risk_register",
        "role": role,
        "records": {
            "risks": rows,
            "top_risks": rows[:8],
            "bu_exposure": data.get("bu_exposure", []),
        },
    }


def _regulatory_dataset(role: str) -> dict:
    from app.enterprise_grc import build_regulatory_mapping

    data = build_regulatory_mapping(role)
    rows = []
    for m in data.get("mappings", []):
        for fw in m.get("frameworks", ["Enterprise-wide"])[:1]:
            rows.append({
                **m,
                "framework": fw,
                "application": "All Applications",
                "owner": OWNERS[hash(m["control_theme"]) % len(OWNERS)],
                "risk": "High" if m.get("coverage_pct", 100) < 80 else "Medium",
                "status": "Mapped" if m.get("coverage_pct", 0) >= 85 else "Gap",
            })
    return {"module": "regulatory_mapping", "role": role, "records": {"mappings": rows}}


def _heatmaps_dataset(role: str) -> dict:
    from app.enterprise_grc import build_executive_heatmaps

    data = build_executive_heatmaps(role)
    fw_rows = [{"name": h["name"], "framework": h["name"], "application": "All Applications", "score": h["score"], "risk": h.get("risk", "Medium"), "owner": OWNERS[0], "status": "Active"} for h in data.get("framework_heatmap", [])]
    app_rows = [{"name": h["name"], "framework": "Enterprise-wide", "application": h["name"], "score": h["score"], "risk": h.get("risk", "Medium"), "owner": OWNERS[hash(h["name"]) % len(OWNERS)], "status": "Active"} for h in data.get("application_heatmap", [])]
    app_rows = apply_role_scope(app_rows, role, app_key="application")
    reg_rows = [{"region": h["region"], "framework": "Enterprise-wide", "application": h["region"], "score": h["score"], "risk": "High" if h["score"] < 75 else "Medium", "observations": h.get("observations", 0), "owner": OWNERS[0], "status": "Monitoring"} for h in data.get("regional_heatmap", [])]
    return {
        "module": "executive_heatmaps",
        "role": role,
        "records": {
            "framework_heatmap": fw_rows,
            "application_heatmap": app_rows,
            "regional_heatmap": reg_rows,
            "business_unit_heatmap": data.get("business_unit_heatmap", []),
        },
    }


def _correlation_dataset(role: str) -> dict:
    from app.correlation_engine import build_correlation_dashboard

    data = build_correlation_dashboard(role)
    chains = []
    for c in data.get("chains", []):
        chains.append({
            **c,
            "framework": c.get("framework", "Enterprise-wide"),
            "application": c.get("application", "Net Banking"),
            "owner": OWNERS[hash(c["chain_id"]) % len(OWNERS)],
            "risk": c.get("severity", "Medium"),
            "status": c.get("status", "Open"),
        })
    chains = apply_role_scope(chains, role)
    return {"module": "correlation", "role": role, "records": {"chains": chains}}


def _evidence_approval_dataset(role: str) -> dict:
    from app.evidence_approval_engine import build_evidence_approval_view

    view = build_evidence_approval_view(role)
    return {
        "module": "evidence_approval",
        "role": role,
        "records": {
            "approved": view["approved_rows"],
            "rejected": view["rejected_rows"],
            "pending": view["pending_rows"],
            "stale": view["stale_rows"],
            "quality": view["quality_samples"],
            "framework_analytics": view["framework_analytics"],
            "application_analytics": view["application_analytics"],
            "approval_trend": view["approval_trend"],
            "rejection_trend": view["rejection_trend"],
            "audit_trail": view["audit_trail"],
        },
    }


def _exception_governance_dataset(role: str) -> dict:
    from app.exception_state_engine import build_governance_dashboard

    view = build_governance_dashboard(role)
    return {
        "module": "exception_governance",
        "role": role,
        "records": {
            "exceptions": view["rows"],
            "approved_recent": view["approved_recent"],
            "rejected_recent": view["rejected_recent"],
            "expiring_month": view["expiring_month"],
            "pending_cab": view["pending_cab"],
        },
    }


def aggregate_kpis(module: str, records: dict, filtered: dict) -> dict:
    if module == "enterprise":
        fw = filtered.get("frameworks", records.get("frameworks", []))
        at_risk = len([r for r in fw if r["risk"] == "High"])
        obs = records.get("open_observations", 0)
        if fw and len(fw) < len(records.get("frameworks", [])):
            obs = max(1, int(obs * len(fw) / max(len(records.get("frameworks", [])), 1)))
        return {
            "Enterprise Compliance": f"{round(sum(r['maturity_pct'] for r in fw) / max(len(fw), 1), 1)}%",
            "National Score": f"{records.get('national_score', 88)}%",
            "Open Observations": obs,
            "Frameworks at Risk": at_risk,
        }
    if module == "pan_india":
        reg = filtered.get("regions", records.get("regions", []))
        return {
            "Regions": len(reg),
            "Branches": sum(r["branches"] for r in reg),
            "Open Observations": sum(r["observations_open"] for r in reg),
            "SLA Breaches": sum(r["sla_breaches"] for r in reg),
        }
    if module == "reuse":
        rows = filtered.get("rows", records.get("rows", []))
        pending = [r for r in rows if r["status"] != "Approved"]
        return {
            "Reuse Groups": len(rows),
            "Mapped Controls": sum(r["controls_linked"] for r in rows),
            "Pending Approval": len(pending),
            "Hours Saved": REUSE_METRICS["top_saving_hours"],
        }
    if module == "evidence_health":
        q = filtered.get("queue", records.get("queue", []))
        stale = len([r for r in q if r.get("issue") == "Stale"])
        risky = len([r for r in q if r.get("risk") in ("Critical", "High")])
        expiring = len([r for r in q if r.get("issue") == "Expiring Soon"])
        rejected = len([r for r in q if r.get("issue") == "Rejected"])
        missing = len([r for r in q if r.get("validation_status") == "Not Submitted"])
        with_obs = len([r for r in q if r.get("observation_id")])
        revalidated = len([r for r in q if r.get("validation_status") == "Revalidation Required"])
        avg = round(sum(r["health_score"] for r in q[:50]) / max(len(q[:50]), 1), 1) if q else 0
        return {
            "Health Score": f"{avg}%",
            "Controls Missing Evidence": missing,
            "Evidence w/ Open Observations": with_obs,
            "High-Risk Failures": risky,
            "Expiring Evidence": expiring,
            "Rejected Evidence": rejected,
            "Revalidated Evidence": revalidated,
            "Stale Evidence": stale,
        }
    if module == "reports":
        rep = filtered.get("reports", records.get("reports", []))
        return {
            "Available Reports": len(rep),
            "Generated": len([r for r in rep if r.get("status") == "Generated"]),
            "Scheduled": len([r for r in rep if r.get("schedule") != "On-demand"]),
            "Pending": len([r for r in rep if r.get("status") != "Generated"]),
        }
    return {}
