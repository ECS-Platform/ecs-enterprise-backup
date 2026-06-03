"""Trends module drilldowns — formula, contributors, and supporting records."""

from __future__ import annotations

from typing import Any

from modules.executive_overview.engines.demo_metrics import APPLICATION_COMPLIANCE_BASELINE
from modules.frameworks.engines.framework_catalog import get_all_evidence_records
from modules.governance.engines.governance_intelligence import parse_analytics_filters
from modules.governance.engines.trends_analytics_engine import (
    OBSERVATIONS_CLOSURE_LABEL,
    OBSERVATIONS_CLOSURE_TOOLTIP,
    PRIMARY_FRAMEWORKS,
    build_trends_tab_payload,
    enterprise_control_totals,
    framework_implementation_contributions,
    observations_period_series,
    quarterly_coverage_history,
    rejections_period_series,
    sla_period_series,
)
from modules.shared.services.role_filter_scope import apps_for_role
from modules.shared.utils.demo_data_standards import (
    BANKING_APPLICATIONS,
    BANKING_OWNERS,
    RISKS,
    STATUSES,
    ensure_drill_rows,
    pick,
    seed,
)


def _filters(filters: dict | None) -> dict:
    return filters or parse_analytics_filters()


def _period_obs_row(period_label: str, obs_series: list[dict[str, Any]]) -> dict[str, Any] | None:
    key = (period_label or "").strip().lower()
    for row in obs_series:
        label = (row.get("label") or row.get("month", "") or "").strip().lower()
        month = (row.get("month") or "").strip().lower()
        if key in (label, month.split()[0][:3].lower() if month else ""):
            return row
        if label and key and (key.startswith(label) or label.startswith(key)):
            return row
    return obs_series[-1] if obs_series else None


def _scoped_apps(filters: dict) -> list[str]:
    app = filters.get("application", "All Applications")
    if app and app != "All Applications":
        return [app]
    return list(APPLICATION_COMPLIANCE_BASELINE.keys()) or BANKING_APPLICATIONS


def _generate_observation_drill_rows(
    *,
    period_label: str,
    series_key: str,
    count: int,
    filters: dict,
    role: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Mock observation records whose row count matches the chart bar value exactly."""
    apps = _scoped_apps(filters)
    allowed = apps_for_role(role)
    if allowed is not None:
        apps = [a for a in apps if a in allowed] or list(allowed)
    fw_filter = filters.get("framework", "Enterprise-wide")
    frameworks = [fw_filter] if fw_filter != "Enterprise-wide" else PRIMARY_FRAMEWORKS
    month_num = {"nov": 11, "dec": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6}.get(
        (period_label or "")[:3].lower(), 3
    )
    year = 2025 if month_num >= 11 else 2026
    rows: list[dict[str, Any]] = []
    for i in range(max(0, count)):
        s = seed("obs-drill", period_label, series_key, i, fw_filter)
        app = pick(s, apps)
        fw = pick(s >> 2, frameworks)
        obs_id = f"OBS-{fw[:3].upper()}-{period_label[:3].upper()}-{i + 1:04d}"
        owner = pick(s >> 4, BANKING_OWNERS)
        status = "Closed" if series_key == "closed" else pick(s >> 6, ["Open", "In Remediation", "Submitted"])
        day = (i % 27) + 1
        date_str = f"{year}-{month_num:02d}-{day:02d}"
        if series_key == "closed":
            rows.append({
                "observation_id": obs_id,
                "application": app,
                "closure_date": date_str,
                "owner": owner,
                "status": status,
            })
        else:
            rows.append({
                "observation_id": obs_id,
                "application": app,
                "framework": fw,
                "severity": pick(s >> 8, RISKS),
                "owner": owner,
                "status": status,
                "opened_date": date_str,
            })
    if series_key == "closed":
        columns = ["observation_id", "application", "closure_date", "owner", "status"]
    else:
        columns = ["observation_id", "application", "framework", "severity", "owner", "status", "opened_date"]
    return rows[:count], columns


def drill_observations_chart_bar(
    period_label: str,
    series_key: str,
    *,
    role: str = "cio",
    filters: dict | None = None,
    count: int = 0,
) -> dict[str, Any]:
    f = _filters(filters)
    obs_series = observations_period_series(f)
    period_row = _period_obs_row(period_label, obs_series)
    if not period_row:
        return {"ok": False, "error": "Unknown period", "rows": [], "columns": []}

    key = (series_key or "").lower()
    if key not in ("opened", "closed"):
        key = "opened"
    bar_count = int(period_row.get(key, 0) or 0)
    if count and count != bar_count:
        bar_count = int(count)

    rows, columns = _generate_observation_drill_rows(
        period_label=period_label or period_row.get("label", ""),
        series_key=key,
        count=bar_count,
        filters=f,
        role=role,
    )
    label = period_row.get("label") or period_label
    title = f"{label} — {'Opened' if key == 'opened' else 'Closed'} Observations ({bar_count})"
    narrative = (
        f"{bar_count} {'opened' if key == 'opened' else 'closed'} audit observations in {label}. "
        f"{OBSERVATIONS_CLOSURE_LABEL}: {round(period_row.get('closure_rate_pct', 0), 1)}% for this period."
    )
    return {
        "ok": True,
        "title": title,
        "metric_trace": {
            "metric_name": title,
            "display_value": str(bar_count),
            "calculation_formula": {
                "numerator_label": "Closed" if key == "closed" else "Opened",
                "denominator_label": "Period total",
                "formula_text": f"{bar_count} records in {label}",
                "result": str(bar_count),
                "narrative": narrative,
            },
            "justification": OBSERVATIONS_CLOSURE_TOOLTIP if key == "closed" else narrative,
        },
        "detail": {"period": label, "series": key, "count": bar_count, "period_row": period_row},
        "rows": rows,
        "columns": columns,
        "trace_count": bar_count,
        "row_count": len(rows),
    }


def _supporting_rows(
    *,
    metric: str,
    filters: dict,
    count: int = 25,
    application: str = "",
    framework: str = "",
) -> list[dict[str, Any]]:
    records = get_all_evidence_records()
    rows = []
    for i, rec in enumerate(records[: max(count, 12)]):
        app = rec.get("application") or pick(seed(metric, i, "a"), ["Net Banking", "Mobile Banking", "Payments"])
        fw = rec.get("framework") or pick(seed(metric, i, "f"), PRIMARY_FRAMEWORKS)
        if application and app != application:
            continue
        if framework and fw != framework:
            continue
        rows.append({
            "application": app,
            "framework": fw,
            "control": rec.get("control") or rec.get("control_id") or f"CTRL-{i + 1:04d}",
            "evidence": rec.get("evidence_name") or rec.get("filename") or f"EVD-{i + 1:04d}",
            "observation": f"OBS-{fw[:3].upper()}-{i + 1:04d}",
            "owner": rec.get("uploaded_by") or pick(seed(metric, i, "o"), BANKING_OWNERS),
            "status": rec.get("audit_status") or rec.get("evidence_status") or "Approved",
        })
    if not rows:
        for i in range(min(count, 12)):
            rows.append({
                "application": application or pick(seed(metric, i), ["Net Banking", "Mobile Banking"]),
                "framework": framework or pick(seed(metric, i, "fw"), PRIMARY_FRAMEWORKS),
                "control": f"CTRL-{i + 1:04d}",
                "evidence": f"EVD-{i + 1:04d}",
                "observation": f"OBS-{i + 1:04d}",
                "owner": pick(seed(metric, i, "own"), BANKING_OWNERS),
                "status": "Approved",
            })
    return ensure_drill_rows(rows, max(count, 25), metric=metric)


def _metric_trace(
    *,
    title: str,
    implemented: int,
    total: int,
    result: str,
    narrative: str,
    filters: dict,
    historical: list[dict] | None = None,
) -> dict[str, Any]:
    fw_contrib = framework_implementation_contributions(filters)
    apps = list({r["application"] for r in _supporting_rows(metric=title, filters=filters, count=8)})
    return {
        "metric_name": title,
        "display_value": result,
        "calculation_formula": {
            "implemented_controls": implemented,
            "applicable_controls": total,
            "numerator_label": "Implemented Controls" if "Rejection" not in title and "SLA" not in title else "Numerator",
            "denominator_label": "Total Controls" if "Coverage" in title else "Denominator",
            "formula_text": narrative.split(".")[0] if narrative else f"{implemented} / {total}",
            "result": result,
            "narrative": narrative,
        },
        "contributing_applications": apps[:8],
        "contributing_frameworks": [r["framework"] for r in fw_contrib[:6]],
        "framework_contributions": fw_contrib,
        "historical_trend": historical or [],
        "contributing_controls": [f"CTRL-{fw[:3].upper()}-{i + 1:03d}" for i, fw in enumerate(PRIMARY_FRAMEWORKS)],
        "contributing_evidence": [
            {
                "evidence_id": r.get("evidence", f"EVD-{i + 1:04d}"),
                "owner": r.get("owner", "—"),
                "status": r.get("status", "Approved"),
                "upload_date": "2026-05-22",
                "application": r.get("application", "Net Banking"),
                "framework": r.get("framework", PRIMARY_FRAMEWORKS[0]),
            }
            for i, r in enumerate(_supporting_rows(metric=title, filters=filters, count=6))
        ],
        "related_observations": [
            {
                "observation_id": r.get("observation", f"OBS-{i + 1:04d}"),
                "severity": pick(seed(title, i), ["Critical", "High", "Medium"]),
                "application": r.get("application", "Net Banking"),
                "framework": r.get("framework", PRIMARY_FRAMEWORKS[0]),
                "status": pick(seed(title, i, "st"), ["Open", "Closed", "In Remediation"]),
            }
            for i, r in enumerate(_supporting_rows(metric=title, filters=filters, count=5))
        ],
        "justification": narrative,
        "quarterly_history": quarterly_coverage_history(filters),
    }


def drill_trends_kpi(metric: str, role: str = "cio", filters: dict | None = None, count: int = 0) -> dict[str, Any]:
    f = _filters(filters)
    payload = build_trends_tab_payload(f)
    m = (metric or "").lower().replace("-", "_").replace(" ", "_")
    totals = payload["control_totals"]

    if "implementation" in m or "coverage" in m:
        hist = [
            {
                "month": q["quarter"],
                "value_pct": q["coverage_pct"],
                "controls_covered": q["implemented_controls"],
                "evidence_approved": int(q["implemented_controls"] * 0.82),
            }
            for q in payload["quarterly_coverage"]
        ]
        trace = _metric_trace(
            title="Implementation Coverage",
            implemented=totals["implemented_controls"],
            total=totals["total_controls"],
            result=f"{totals['coverage_pct']}%",
            narrative=(
                f"Implementation Coverage = {totals['implemented_controls']:,} implemented controls ÷ "
                f"{totals['total_controls']:,} total applicable controls × 100. "
                f"Framework contribution: {', '.join(PRIMARY_FRAMEWORKS)}."
            ),
            filters=f,
            historical=hist,
        )
        trace["calculation_formula"]["numerator_label"] = "Implemented Controls"
        trace["calculation_formula"]["denominator_label"] = "Total Controls"
        trace["calculation_formula"]["formula_text"] = (
            f"Coverage = {totals['implemented_controls']:,} / {totals['total_controls']:,} × 100"
        )
        return {
            "ok": True,
            "title": "Implementation Coverage",
            "metric_trace": trace,
            "detail": totals,
            "rows": _supporting_rows(metric=m, filters=f, count=count or 25),
            "columns": ["application", "framework", "control", "evidence", "observation", "owner", "status"],
            "sections": {"framework_contribution": payload["framework_contributions"]},
        }

    if "observation" in m:
        obs = payload["observations_series"]
        latest = obs[-1] if obs else {}
        opened = sum(s["opened"] for s in obs)
        closed = sum(s["closed"] for s in obs)
        net = closed - opened
        trace = _metric_trace(
            title="Observations Net",
            implemented=closed,
            total=opened,
            result=str(latest.get("net", net)),
            narrative=(
                f"Net Observations = Closed ({closed}) − Opened ({opened}) = {net}. "
                f"{OBSERVATIONS_CLOSURE_LABEL} {payload['closure_rate_pct']}% across {len(obs)} periods."
            ),
            filters=f,
            historical=[
                {"month": s["label"], "value_pct": s["closure_rate_pct"], "controls_covered": s["closed"], "evidence_approved": s["opened"]}
                for s in obs
            ],
        )
        trace["calculation_formula"]["numerator_label"] = "Closed Observations"
        trace["calculation_formula"]["denominator_label"] = "Opened Observations"
        return {
            "ok": True,
            "title": "Observations Net",
            "metric_trace": trace,
            "detail": {"closure_rate_pct": payload["closure_rate_pct"], "latest": latest},
            "rows": _supporting_rows(metric=m, filters=f, count=count or 25),
            "columns": ["application", "framework", "observation", "control", "owner", "status"],
            "sections": {"period_breakdown": obs},
        }

    if "reject" in m:
        rej = payload["rejections_series"]
        latest = rej[-1] if rej else {}
        submitted = latest.get("submitted", 167)
        rejected = latest.get("rejected", 7)
        rate = latest.get("rate_pct", round(rejected * 100 / max(submitted, 1), 1))
        trace = _metric_trace(
            title="Auditor Rejection Rate",
            implemented=rejected,
            total=submitted,
            result=f"{rate}%",
            narrative=f"Rejection Rate = {rejected} rejected ÷ {submitted} submitted × 100 = {rate}%.",
            filters=f,
            historical=[
                {"month": s["label"], "value_pct": s["rate_pct"], "controls_covered": s["rejected"], "evidence_approved": s["submitted"]}
                for s in rej
            ],
        )
        trace["calculation_formula"]["numerator_label"] = "Evidence Rejected"
        trace["calculation_formula"]["denominator_label"] = "Evidence Submitted"
        trace["top_rejection_reasons"] = payload["rejection_reasons"]
        return {
            "ok": True,
            "title": "Auditor Evidence Rejection Rate",
            "metric_trace": trace,
            "detail": latest,
            "rows": _supporting_rows(metric=m, filters=f, count=count or 25),
            "columns": ["application", "framework", "evidence", "control", "owner", "status"],
            "sections": {"top_rejection_reasons": payload["rejection_reasons"], "period_breakdown": rej},
        }

    if "sla" in m or "remediation" in m:
        sla = payload["sla_series"]
        latest = sla[-1] if sla else {}
        on_time = latest.get("on_time_pct", 91)
        breached = latest.get("breached", 8)
        near = latest.get("near_breach", 4)
        within = on_time
        trace = _metric_trace(
            title="Remediation SLA Compliance",
            implemented=within,
            total=100,
            result=f"{on_time}%",
            narrative=(
                f"SLA Compliance = {within}% within SLA · {near} near breach · {breached} breached. "
                f"Based on remediation queue across onboarded applications."
            ),
            filters=f,
            historical=[
                {"month": s["label"], "value_pct": s["on_time_pct"], "controls_covered": s["within_sla_pct"], "evidence_approved": s["breached"]}
                for s in sla
            ],
        )
        trace["calculation_formula"]["numerator_label"] = "Within SLA"
        trace["calculation_formula"]["denominator_label"] = "Total Remediation Tasks"
        return {
            "ok": True,
            "title": "Remediation SLA Compliance",
            "metric_trace": trace,
            "detail": latest,
            "rows": _supporting_rows(metric=m, filters=f, count=count or 25),
            "columns": ["application", "framework", "control", "observation", "owner", "status"],
            "sections": {"sla_violators": payload["sla_violators"], "period_breakdown": sla},
        }

    totals = enterprise_control_totals(f)
    return drill_trends_kpi("implementation_coverage", role, f, count)


def drill_trends_chart(
    chart: str,
    element: str,
    *,
    role: str = "cio",
    filters: dict | None = None,
    count: int = 0,
) -> dict[str, Any]:
    f = _filters(filters)
    chart_l = (chart or "").lower()
    element_l = (element or "").lower()

    if "|" in (element or ""):
        period_part, series_part = element.split("|", 1)
        if "observation" in chart_l or series_part.lower() in ("opened", "closed", "net"):
            return drill_observations_chart_bar(
                period_part.strip(),
                series_part.strip(),
                role=role,
                filters=f,
                count=count,
            )

    if "observation" in chart_l and element_l in ("opened", "closed"):
        obs = observations_period_series(f)
        latest = obs[-1] if obs else {}
        return drill_observations_chart_bar(
            latest.get("label", ""),
            element_l,
            role=role,
            filters=f,
            count=count,
        )

    metric_map = {
        "coverage": {
            "implemented": "implementation_coverage",
            "missing": "implementation_coverage",
            "pending": "implementation_coverage",
        },
        "observations": {
            "opened": "observations_net",
            "closed": "observations_net",
            "net": "observations_net",
        },
        "rejections": {
            "submitted": "auditor_rejection_rate",
            "rejected": "auditor_rejection_rate",
            "rate": "auditor_rejection_rate",
        },
        "sla": {
            "within": "remediation_sla_compliance",
            "near": "remediation_sla_compliance",
            "breached": "remediation_sla_compliance",
        },
    }
    for key, elements in metric_map.items():
        if key in chart_l or key in element_l:
            for el_key, metric in elements.items():
                if el_key in element_l or el_key in chart_l:
                    if key == "observations" and el_key in ("opened", "closed"):
                        obs = observations_period_series(f)
                        latest = obs[-1] if obs else {}
                        return drill_observations_chart_bar(
                            latest.get("label", ""),
                            el_key,
                            role=role,
                            filters=f,
                            count=count or int(latest.get(el_key, 0)),
                        )
                    body = drill_trends_kpi(metric, role, f, count)
                    body["title"] = f"{chart} — {element}"
                    body.setdefault("detail", {})["period"] = element
                    return body

    if "aging" in chart_l or "stale" in chart_l or "remediation" in chart_l:
        body = drill_trends_kpi("remediation_sla_compliance", role, f, count)
        body["title"] = f"{chart} — {element}"
        return body

    if "compliance" in chart_l:
        return drill_trends_kpi("implementation_coverage", role, f, count)

    return drill_trends_kpi(element or chart or "implementation_coverage", role, f, count)
