"""Executive analytics — banking BU, regional, trends granularity, heatmaps, regulatory traceability, correlation graph."""

from __future__ import annotations

import hashlib

from app import ecs_state
from app.demo_metrics import BUSINESS_UNITS, ENTERPRISE_MONTHLY_TRENDS
from app.framework_catalog import FRAMEWORK_CATALOG
from app.governance_intelligence import build_extended_trends, parse_analytics_filters, _seed

CORE_BANKING_UNITS = ["Retail Banking", "Corporate Banking", "Wealth Management", "Digital Channels"]
REGIONS = ["North", "South", "East", "West", "Central"]
APPLICATIONS = ecs_state.BANKING_APPLICATIONS + ["Wealth Portal"]
FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())


def _h(key: str, lo: int, hi: int) -> int:
    return _seed(key, lo, hi)


def build_banking_bu_analytics(role: str = "owner") -> list[dict]:
    """Retail / Corporate / Wealth / Digital — compliance, readiness, gaps, observations, risk."""
    stats = ecs_state.build_evidence_analytics()
    live_pct = stats.get("overall_compliance_pct", 78)
    rows = []
    for bu in BUSINESS_UNITS:
        if bu["unit"] not in CORE_BANKING_UNITS:
            continue
        u = bu["unit"]
        obs = bu["open_gaps"] + _h(u + "obs", 3, 14)
        readiness = round(min(99, bu["compliance_pct"] + _h(u + "rdy", -2, 4)), 1)
        risk_score = round(max(1, min(10, (100 - bu["compliance_pct"]) / 8 + _h(u + "rs", 0, 3))), 1)
        rows.append({
            "unit": u,
            "compliance_pct": bu["compliance_pct"],
            "audit_readiness": readiness,
            "open_gaps": bu["open_gaps"],
            "observations": obs,
            "risk_score": risk_score,
            "risk": bu["risk"],
            "framework": "Enterprise-wide",
            "application": u,
            "owner": bu.get("owner", "R. Mehta (App Owner)"),
            "status": "Monitoring" if bu["risk"] != "High" else "At Risk",
            "live_delta": round(live_pct - bu["compliance_pct"], 1),
        })
    return rows


def build_bu_chart_series(bu_rows: list[dict]) -> dict:
    """Multi-metric chart payloads for executive BU dashboard."""
    return {
        "compliance": [{"label": r["unit"].replace(" Banking", "").replace(" Management", "").replace(" Channels", ""), "value": r["compliance_pct"], "tone": "green" if r["compliance_pct"] >= 85 else "orange", "tooltip": f"{r['unit']}: {r['compliance_pct']}% compliance"} for r in bu_rows],
        "readiness": [{"label": r["unit"][:8], "value": r["audit_readiness"], "tone": "teal", "tooltip": f"Audit readiness {r['audit_readiness']}%"} for r in bu_rows],
        "gaps": [{"label": r["unit"][:8], "value": r["open_gaps"], "tone": "orange", "tooltip": f"{r['open_gaps']} open gaps"} for r in bu_rows],
        "observations": [{"label": r["unit"][:8], "value": r["observations"], "tone": "red", "tooltip": f"{r['observations']} open observations"} for r in bu_rows],
        "risk_score": [{"label": r["unit"][:8], "value": r["risk_score"], "tone": "navy", "tooltip": f"Risk score {r['risk_score']}/10"} for r in bu_rows],
    }


def enhance_pan_india_regions(regions: list[dict], framework_matrix: list[dict]) -> list[dict]:
    """Add PCI readiness, critical observations, framework posture summary."""
    out = []
    for r in regions:
        zone = r.get("region") or r.get("zone")
        pci_rows = [m for m in framework_matrix if m["region"] == zone and m["framework"] == "PCI DSS"]
        pci = pci_rows[0]["readiness_pct"] if pci_rows else round(r.get("score", 80) - 2, 1)
        fw_avg = round(sum(m["readiness_pct"] for m in framework_matrix if m["region"] == zone) / max(len([m for m in framework_matrix if m["region"] == zone]), 1), 1)
        critical = max(1, r.get("observations_open", 0) // 5 + r.get("failed_controls", 0))
        out.append({
            **r,
            "zone": zone,
            "pci_readiness": pci,
            "framework_posture": fw_avg,
            "critical_observations": critical,
            "audit_score": r.get("audit_readiness_pct", r.get("score", 80)),
        })
    return out


def build_granularity_trends(filters: dict | None = None) -> dict:
    """Daily / weekly / monthly / quarterly trend bundles."""
    f = parse_analytics_filters()
    if filters:
        f.update({k: v for k, v in filters.items() if v})
    mult = 1.0
    fw = f.get("framework", "Enterprise-wide")
    ext = build_extended_trends(f)

    daily_labels = [f"D{i}" for i in range(1, 15)]
    weekly_labels = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"]
    monthly_labels = [row["month"].split()[0][:3] for row in ENTERPRISE_MONTHLY_TRENDS]
    quarterly_labels = ["Q1", "Q2", "Q3", "Q4"]

    def series(labels, prefix, lo, hi, suffix="", tone="blue"):
        return [{"label": lb, "value": max(1, int(_h(f"{fw}-{prefix}-{lb}", lo, hi) * mult)), "tone": tone, "suffix": suffix} for lb in labels]

    return {
        "daily": {
            "observations": series(daily_labels, "d-obs", 1, 8, "", "blue"),
            "compliance": [{"label": lb, "value": min(99, round(72 + _h(f"{fw}-{lb}-c", 0, 12) * mult, 1)), "tone": "green", "suffix": "%"} for lb in daily_labels],
            "failed_evidence": series(daily_labels, "d-fail", 0, 5, "", "red"),
            "risk_escalation": series(daily_labels, "d-esc", 0, 3, "", "orange"),
            "evidence_aging": series(daily_labels, "d-age", 2, 12, "", "slate"),
            "remediation": series(daily_labels, "d-rem", 1, 6, "", "teal"),
        },
        "weekly": {
            "observations": ext["weekly_control_growth"],
            "compliance": [{"label": w["label"], "value": min(99, round(74 + _h(fw + w["label"], 0, 10), 1)), "tone": "green", "suffix": "%"} for w in ext["weekly_control_growth"]],
            "failed_evidence": ext["failed_controls_trend"][: len(weekly_labels)] or series(weekly_labels, "w-fail", 1, 8, "", "red"),
            "risk_escalation": series(weekly_labels, "w-esc", 0, 4, "", "orange"),
            "evidence_aging": ext["stale_evidence_trend"][: len(weekly_labels)] or series(weekly_labels, "w-age", 3, 15, "", "slate"),
            "remediation": ext["remediation_closure_velocity"][: len(weekly_labels)] or series(weekly_labels, "w-rem", 2, 10, "", "teal"),
        },
        "monthly": {
            "observations": [{"label": row["month"].split()[0][:3], "value": row["opened"], "tone": "blue"} for row in ENTERPRISE_MONTHLY_TRENDS],
            "compliance": [{"label": row["month"].split()[0][:3], "value": row["compliance"], "tone": "green", "suffix": "%"} for row in ENTERPRISE_MONTHLY_TRENDS],
            "failed_evidence": ext["failed_controls_trend"],
            "risk_escalation": [{"label": m["label"], "value": max(0, _h(fw + m["label"] + "esc", 0, 5)), "tone": "orange"} for m in ext["failed_controls_trend"]],
            "evidence_aging": ext["stale_evidence_trend"],
            "remediation": ext["remediation_closure_velocity"],
        },
        "quarterly": {
            "observations": [{"label": q, "value": _h(fw + q + "obs", 12, 48), "tone": "blue"} for q in quarterly_labels],
            "compliance": ext["quarterly_audit_readiness"],
            "failed_evidence": [{"label": q, "value": _h(fw + q + "fail", 2, 12), "tone": "red"} for q in quarterly_labels],
            "risk_escalation": [{"label": q, "value": _h(fw + q + "esc", 1, 6), "tone": "orange"} for q in quarterly_labels],
            "evidence_aging": [{"label": q, "value": _h(fw + q + "stale", 8, 28), "tone": "slate"} for q in quarterly_labels],
            "remediation": [{"label": q, "value": _h(fw + q + "rem", 10, 35), "tone": "teal"} for q in quarterly_labels],
        },
    }


def _heat_tone(score: float) -> str:
    if score >= 85:
        return "green"
    if score >= 75:
        return "amber"
    if score >= 65:
        return "red"
    return "dark-red"


def build_audit_prep_heatmaps(filters: dict | None = None) -> dict:
    """Framework × application readiness matrix + stale indicators."""
    from app.audit_prep_data import build_audit_prep_view

    view = build_audit_prep_view("cio", filters or {})
    fw_rows = view.get("readiness_by_framework", [])
    app_rows = view.get("readiness_by_application", [])
    matrix = []
    for fw in fw_rows[:8]:
        for app in app_rows[:8]:
            score = round((fw["readiness_pct"] + app["readiness_pct"]) / 2 + _h(f"{fw['framework']}-{app['application']}", -5, 5), 1)
            stale = _h(f"stale-{fw['framework']}-{app['application']}", 0, 6)
            matrix.append({
                "framework": fw["framework"],
                "application": app["application"],
                "readiness_pct": score,
                "stale_count": stale,
                "tone": _heat_tone(score),
                "owner": app.get("owner", "—"),
                "gaps": fw.get("gap_count", 0) + (1 if score < 75 else 0),
            })
    upcoming = view.get("upcoming_audits", [])[:6]
    return {
        "framework_rows": fw_rows,
        "application_rows": app_rows,
        "matrix": matrix,
        "upcoming_audits": upcoming,
        "stale_total": view.get("evidence_freshness", {}).get("stale_count", 0),
        "weighted_readiness": view.get("weighted_readiness_pct", 0),
    }


def build_period_heatmaps(period: str = "month") -> dict:
    """Month / quarter / year executive heatmap cells."""
    stats = ecs_state.build_evidence_analytics()
    base_compliance = stats.get("overall_compliance_pct", 78)
    cells = []
    if period == "month":
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    elif period == "quarter":
        labels = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026"]
    else:
        labels = ["2022", "2023", "2024", "2025", "2026"]

    for i, lb in enumerate(labels):
        compliance = min(99, round(base_compliance + _h(lb, -8, 6), 1))
        evidence_vol = _h(lb + "ev", 120, 420)
        obs_density = _h(lb + "obs", 8, 42)
        risk_conc = round(max(1, (100 - compliance) / 10 + _h(lb + "risk", 0, 3)), 1)
        cells.append({
            "label": lb,
            "period": period,
            "compliance_score": compliance,
            "evidence_volume": evidence_vol,
            "observation_density": obs_density,
            "risk_concentration": risk_conc,
            "tone": _heat_tone(compliance),
        })
    return {"period": period, "cells": cells, "legend": [
        {"tone": "green", "label": "≥85% — Compliant"},
        {"tone": "amber", "label": "75–84% — Watch"},
        {"tone": "red", "label": "65–74% — At Risk"},
        {"tone": "dark-red", "label": "<65% — Critical"},
    ]}


def build_regulatory_traceability() -> dict:
    """Control lineage, shared evidence, framework overlap."""
    from app.enterprise_grc import build_regulatory_mapping

    base = build_regulatory_mapping("compliance_head")
    mappings = base["mappings"]
    lineage = []
    overlap = []
    for i, m in enumerate(mappings):
        src = m["frameworks"][0]
        for tgt in m["frameworks"][1:3]:
            cov = max(60, m["coverage_pct"] - _h(src + tgt + m["control_theme"], 0, 15))
            lineage.append({
                "source_framework": src,
                "target_framework": tgt,
                "control_theme": m["control_theme"],
                "reused_evidence": m["shared_evidence"],
                "reused_controls": _h(m["control_theme"], 2, 12),
                "coverage_pct": cov,
                "gap_pct": 100 - cov,
                "status": "Mapped" if cov >= 80 else "Gap",
            })
        overlap.append({
            "theme": m["control_theme"],
            "frameworks": m["frameworks"],
            "coverage_pct": m["coverage_pct"],
            "shared_evidence": m["shared_evidence"],
        })
    trace_nodes = []
    for i, ln in enumerate(lineage[:12]):
        trace_nodes.append({"id": f"N{i}", "label": ln["control_theme"][:20], "framework": ln["source_framework"], "type": "control"})
        trace_nodes.append({"id": f"E{i}", "label": ln["reused_evidence"][:18], "framework": ln["target_framework"], "type": "evidence"})
    return {
        **base,
        "lineage": lineage,
        "overlap": overlap,
        "trace_graph": {"nodes": trace_nodes, "edges": [{"from": f"N{i}", "to": f"E{i}", "label": "reuses"} for i in range(min(12, len(lineage)))]},
        "coverage_chart": [{"label": o["theme"][:14], "value": o["coverage_pct"], "tone": "green" if o["coverage_pct"] >= 85 else "orange"} for o in overlap],
    }


def build_correlation_graph(role: str = "owner") -> dict:
    """Dependency graph nodes/edges for cross-tool correlation."""
    from app.correlation_engine import CORRELATION_CHAINS

    tools = ["Jira", "ServiceNow", "Prisma", "ECS", "CMDB", "VAPT", "AppSec", "Tripwire", "SharePoint"]
    nodes = []
    edges = []
    node_details = {}
    idx = 0
    for chain in CORRELATION_CHAINS:
        root_id = f"node-{chain['chain_id']}"
        sev = chain["severity"]
        nodes.append({"id": root_id, "label": chain["source_tool"], "tool": chain["source_tool"], "severity": sev, "type": "source", "chain_id": chain["chain_id"]})
        node_details[root_id] = {
            "title": chain["title"],
            "linked_observations": [f"OBS-{chain['chain_id']}-001"],
            "linked_incidents": [chain["source_record"]],
            "linked_evidence": [l["record"] for l in chain["links"] if l["tool"] == "ECS"][:3],
            "impacted_applications": [chain["application"]],
            "remediation_workflow": [l["record"] for l in chain["links"] if l["tool"] == "Jira"][:2] or ["Remediation in progress"],
            "severity": sev,
            "status": chain["status"],
        }
        prev = root_id
        for link in chain["links"]:
            idx += 1
            nid = f"node-{chain['chain_id']}-{idx}"
            nodes.append({"id": nid, "label": link["tool"], "tool": link["tool"], "severity": sev, "type": "link", "record": link["record"][:40]})
            edges.append({"from": prev, "to": nid, "label": link["status"][:12]})
            node_details[nid] = {
                "title": link["record"],
                "linked_observations": [],
                "linked_incidents": [link["record"]] if link["tool"] in ("ServiceNow", "Jira") else [],
                "linked_evidence": [link["record"]] if link["tool"] == "ECS" else [],
                "impacted_applications": [chain["application"]],
                "remediation_workflow": [link["status"]],
                "severity": sev,
                "status": link["status"],
            }
            prev = nid
    return {
        "nodes": nodes,
        "edges": edges,
        "node_details": node_details,
        "tools": tools,
        "chains": CORRELATION_CHAINS,
    }
