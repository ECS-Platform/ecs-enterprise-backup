"""Framework Loader service — executive presentation layer.

Builds the dashboard payload, kicks off the onboarding pipeline, and adapts
``framework_onboarding_engine`` output to the compact KPI/heatmap UI used
by the new Framework Loader page.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

from app import ecs_state
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG
from modules.frameworks.engines.framework_onboarding_engine import (
    advance_lifecycle,
    derive_prefix,
    list_onboarding_records,
    run_onboarding_pipeline,
)


FRAMEWORK_TYPES: list[str] = [
    "Pre-Assessment",
    "Regulatory",
    "Security Baseline",
    "Internal Governance",
    "Audit Assessment",
    "Vendor Assessment",
    "Compliance Mapping",
]

# UI framework_type → engine-expected category (engine accepts Security/Audit/Regulatory/Infra/Risk)
_TYPE_TO_CATEGORY: dict[str, str] = {
    "Pre-Assessment": "Audit",
    "Regulatory": "Regulatory",
    "Security Baseline": "Security",
    "Internal Governance": "Risk",
    "Audit Assessment": "Audit",
    "Vendor Assessment": "Risk",
    "Compliance Mapping": "Regulatory",
}

ONBOARDING_STAGES: list[str] = [
    "Document Uploaded",
    "Controls Parsed",
    "ECS IDs Generated",
    "Reusable Controls Matched",
    "Evidence Mapping Evaluated",
    "Auditor Review Pending",
    "Framework Activated",
]


# --------------------------------------------------------------------- helpers


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------- KPIs


def _aggregate_kpis(records: list[dict]) -> dict[str, Any]:
    total_loaded = len(records)
    total_controls = 0
    reusable = 0
    new_controls = 0
    cross_matches = 0
    pending = 0
    for rec in records:
        analysis = rec.get("analysis", {}) or {}
        total_controls += _safe_int(analysis.get("total_controls"))
        reusable += _safe_int(analysis.get("reusable_controls"))
        new_controls += _safe_int(analysis.get("missing"))
        for control in rec.get("controls", []) or []:
            cross_matches += len(control.get("reuse_matches", []) or [])
        if (rec.get("lifecycle_state") or "Imported") in (
            "Imported",
            "Mapped",
            "Reviewed",
        ):
            pending += 1
    return {
        "total_frameworks_loaded": total_loaded,
        "controls_parsed": total_controls,
        "reusable_controls_found": reusable,
        "new_controls_identified": new_controls,
        "cross_framework_matches": cross_matches,
        "pending_mapping_reviews": pending,
    }


def _ecs_control_id(framework_name: str, idx: int, fallback: str = "") -> str:
    prefix = derive_prefix(framework_name).replace("-", "")[:6].upper() or "FW"
    if fallback and fallback.startswith("ECS-"):
        return fallback
    return f"ECS-{prefix}-{idx + 1:03d}"


def _reusable_label(reuse_confidence: float) -> str:
    if reuse_confidence >= 75:
        return "Yes"
    if reuse_confidence >= 50:
        return "Partial"
    return "No"


def adapt_parsed_controls(record: dict) -> list[dict]:
    """Transform engine controls into the Framework Loader parsed-table rows."""
    framework_name = record.get("framework_name", "")
    out: list[dict] = []
    for idx, control in enumerate(record.get("controls", []) or []):
        best = control.get("best_match") or {}
        reuse = _safe_float(control.get("reuse_confidence_pct"))
        out.append(
            {
                "ecs_control_id": _ecs_control_id(
                    framework_name, idx, control.get("control_id", "")
                ),
                "uploaded_control": (control.get("control_name") or "")[:80],
                "control_description": (control.get("control_description") or "")[:120],
                "similar_existing_framework": best.get("framework") or "New Control",
                "match_pct": int(round(reuse)),
                "reusable": _reusable_label(reuse),
                "section": control.get("section", "—"),
                "criticality": control.get("criticality", "Medium"),
                "category": control.get("category", "Security"),
            }
        )
    return out


def _framework_overlap_heatmap(record: dict) -> list[dict]:
    counts: dict[str, dict[str, int]] = {}
    for control in record.get("controls", []) or []:
        for match in control.get("reuse_matches", []) or []:
            fw = match.get("framework", "")
            if not fw:
                continue
            tier = (
                "Strong"
                if match.get("similarity_pct", 0) >= 75
                else "Moderate"
                if match.get("similarity_pct", 0) >= 55
                else "Weak"
            )
            counts.setdefault(fw, {"Strong": 0, "Moderate": 0, "Weak": 0})
            counts[fw][tier] += 1
    cells: list[dict] = []
    for framework, buckets in sorted(counts.items(), key=lambda kv: -sum(kv[1].values())):
        total = sum(buckets.values()) or 0
        score = (buckets["Strong"] * 3 + buckets["Moderate"] * 2 + buckets["Weak"]) / max(
            total, 1
        )
        intensity = (
            "tone-green"
            if score >= 2.2
            else "tone-amber"
            if score >= 1.5
            else "tone-red"
        )
        cells.append(
            {
                "framework": framework,
                "strong": buckets["Strong"],
                "moderate": buckets["Moderate"],
                "weak": buckets["Weak"],
                "overlap_total": total,
                "intensity": intensity,
                "score": round(score, 2),
            }
        )
    return cells[:12]


def _readiness_breakdown(record: dict) -> list[dict]:
    analysis = record.get("analysis", {}) or {}
    total = max(_safe_int(analysis.get("total_controls")), 1)
    implemented = _safe_int(analysis.get("implemented"))
    partial = _safe_int(analysis.get("partially_implemented"))
    reusable = _safe_int(analysis.get("reusable_controls"))
    missing = _safe_int(analysis.get("missing"))
    new_evidence = _safe_int(analysis.get("new_evidence_required"))
    coverage = _safe_float(analysis.get("implementation_coverage_pct"))
    return [
        {
            "label": "Already Implemented",
            "value": implemented,
            "pct": round(implemented / total * 100, 1),
            "tone": "success",
        },
        {
            "label": "Partially Implemented",
            "value": partial,
            "pct": round(partial / total * 100, 1),
            "tone": "warning",
        },
        {
            "label": "Reusable From Other Frameworks",
            "value": reusable,
            "pct": round(reusable / total * 100, 1),
            "tone": "info",
        },
        {
            "label": "Net New Controls",
            "value": missing,
            "pct": round(missing / total * 100, 1),
            "tone": "danger",
        },
        {
            "label": "Need New Evidence",
            "value": new_evidence,
            "pct": round(new_evidence / total * 100, 1),
            "tone": "secondary",
        },
        {
            "label": "Implementation Readiness",
            "value": f"{coverage}%",
            "pct": coverage,
            "tone": "primary",
        },
    ]


def _audit_effort_saved(record: dict) -> dict[str, Any]:
    """Mock estimate — assume each reusable control saves ~6 audit-hours."""
    analysis = record.get("analysis", {}) or {}
    reusable = _safe_int(analysis.get("reusable_controls"))
    hours_saved = reusable * 6
    days_saved = round(hours_saved / 8, 1)
    return {
        "hours_saved": hours_saved,
        "days_saved": days_saved,
        "reusable_controls": reusable,
        "auditor_review_required": _safe_int(analysis.get("critical_missing")),
    }


def _implementation_callouts(record: dict) -> list[str]:
    analysis = record.get("analysis", {}) or {}
    total = max(_safe_int(analysis.get("total_controls")), 1)
    reusable = _safe_int(analysis.get("reusable_controls"))
    implemented = _safe_int(analysis.get("implemented"))
    overlap_map: dict[str, int] = {}
    for control in record.get("controls", []) or []:
        best = control.get("best_match") or {}
        fw = best.get("framework")
        if fw and best.get("similarity_pct", 0) >= 65:
            overlap_map[fw] = overlap_map.get(fw, 0) + 1
    top_fw = (
        max(overlap_map.items(), key=lambda kv: kv[1])[0]
        if overlap_map
        else "PCI DSS"
    )
    top_pct = (
        round(max(overlap_map.values()) / total * 100, 1) if overlap_map else 0.0
    )
    return [
        f"{top_pct}% reusable from {top_fw}",
        f"{round(implemented / total * 100, 1)}% already implemented across banking apps",
        f"{reusable} controls mapped automatically by reuse engine",
        f"{_safe_int(analysis.get('new_evidence_required'))} controls require new evidence",
        f"{_safe_int(analysis.get('critical_missing'))} critical gaps need auditor review",
    ]


def _workflow_stage_state(record: dict) -> list[dict]:
    lifecycle = (record.get("lifecycle_state") or "Imported").lower()
    order = {
        "draft": 0,
        "imported": 1,
        "mapped": 3,
        "reviewed": 5,
        "approved": 5,
        "active": 6,
    }
    reached = order.get(lifecycle, 1)
    stages: list[dict] = []
    for idx, label in enumerate(ONBOARDING_STAGES):
        state = (
            "complete"
            if idx < reached
            else "active"
            if idx == reached
            else "pending"
        )
        stages.append({"label": label, "state": state})
    return stages


def adapt_record_to_view(record: dict) -> dict[str, Any]:
    return {
        "framework_id": record.get("framework_id", ""),
        "framework_name": record.get("framework_name", ""),
        "framework_type": record.get("ui_type") or record.get("category", "Security Baseline"),
        "framework_owner": record.get("regulator") or record.get("created_by") or "Unassigned",
        "lifecycle_state": record.get("lifecycle_state", "Imported"),
        "created_at": record.get("created_at", _ts()),
        "upload_filename": record.get("upload_filename", ""),
        "warnings": record.get("warnings", []),
        "kpi_strip": _readiness_breakdown(record),
        "parsed_controls": adapt_parsed_controls(record),
        "mapping_matrix": record.get("mapping_matrix", []),
        "overlap_heatmap": _framework_overlap_heatmap(record),
        "implementation_callouts": _implementation_callouts(record),
        "audit_effort": _audit_effort_saved(record),
        "workflow_stages": _workflow_stage_state(record),
        "gaps_count": len(record.get("gaps", []) or []),
        "controls_count": len(record.get("controls", []) or []),
        "is_active": (record.get("lifecycle_state") == "Active"),
    }


def list_loader_records() -> list[dict]:
    rows: list[dict] = []
    for rec in list_onboarding_records():
        rows.append(
            {
                "framework_id": rec.get("framework_id"),
                "framework_name": rec.get("framework_name"),
                "framework_type": rec.get("ui_type") or rec.get("category", "Security Baseline"),
                "framework_owner": rec.get("regulator") or rec.get("created_by") or "Unassigned",
                "lifecycle_state": rec.get("lifecycle_state", "Imported"),
                "created_at": rec.get("created_at", ""),
                "controls_count": len(rec.get("controls", []) or []),
                "reusable_controls": _safe_int(
                    (rec.get("analysis") or {}).get("reusable_controls")
                ),
                "coverage_pct": _safe_float(
                    (rec.get("analysis") or {}).get("implementation_coverage_pct")
                ),
            }
        )
    return rows


def build_loader_dashboard(role: str, selected_framework_id: str = "") -> dict[str, Any]:
    from modules.frameworks.engines.framework_intelligence import build_intelligence_payload

    records = list_onboarding_records()
    kpis = _aggregate_kpis(records)
    selected = None
    if selected_framework_id:
        selected = next(
            (
                r
                for r in records
                if r.get("framework_id") == selected_framework_id
            ),
            None,
        )
    if not selected and records:
        selected = records[0]
    selected_view = adapt_record_to_view(selected) if selected else None
    intelligence = build_intelligence_payload(
        focus_framework=selected.get("framework_name") if selected else None,
    )
    return {
        "kpis": kpis,
        "framework_types": FRAMEWORK_TYPES,
        "existing_frameworks": sorted(list(FRAMEWORK_CATALOG.keys())),
        "loader_records": list_loader_records(),
        "selected": selected_view,
        "onboarding_stages": ONBOARDING_STAGES,
        "intelligence": intelligence,
        "kpi_cards": [
            {
                "label": "Total Frameworks Loaded",
                "value": kpis["total_frameworks_loaded"],
                "tone": "primary",
                "icon": "📚",
            },
            {
                "label": "Controls Parsed",
                "value": kpis["controls_parsed"],
                "tone": "info",
                "icon": "🧾",
            },
            {
                "label": "Reusable Controls",
                "value": kpis["reusable_controls_found"],
                "tone": "success",
                "icon": "♻️",
            },
            {
                "label": "Net New Controls",
                "value": kpis["new_controls_identified"],
                "tone": "warning",
                "icon": "✨",
            },
            {
                "label": "Cross-Framework Matches",
                "value": kpis["cross_framework_matches"],
                "tone": "secondary",
                "icon": "🔗",
            },
            {
                "label": "Pending Mapping Reviews",
                "value": kpis["pending_mapping_reviews"],
                "tone": "danger",
                "icon": "⏳",
            },
        ],
    }


# --------------------------------------------------------------- write actions


def submit_upload(
    framework_name: str,
    framework_type: str,
    framework_owner: str,
    filename: str,
    file_content: bytes,
    user: str,
    role: str,
) -> dict[str, Any]:
    """Drive a full pipeline run and return the loader-shaped view."""
    ui_type = framework_type if framework_type in FRAMEWORK_TYPES else "Security Baseline"
    details = {
        "framework_name": framework_name.strip(),
        "version": "1.0",
        "regulator": framework_owner.strip() or "ECS Internal",
        "effective_date": _ts().split(" ")[0],
        # Engine accepts only its strict category set — translate UI labels.
        "category": _TYPE_TO_CATEGORY.get(ui_type, "Security"),
        "ui_type": ui_type,
    }
    if not file_content:
        # Synthesize deterministic mock content so the pipeline always succeeds
        seed = hashlib.md5(
            f"{framework_name}:{framework_type}:{framework_owner}".encode()
        ).hexdigest()
        file_content = (
            "control_name,control_description,section,category,criticality\n"
            + "\n".join(
                f"{framework_name} mock control {i + 1},"
                f"{framework_name} requirement {i + 1} attestation for banking scope,"
                f"{(i // 4) + 1}.{(i % 4) + 1},Security,High"
                for i in range(18)
            )
        ).encode()
        if not filename:
            filename = f"{framework_name}-mock-{seed[:8]}.csv"
    result = run_onboarding_pipeline(details, file_content, filename or "upload.csv", user, role)
    if not result.get("ok"):
        return result
    record = result["record"]
    # Preserve the user-facing framework type so the loader table reflects it
    record["ui_type"] = details["ui_type"]
    ecs_state.framework_onboarding_registry[result["framework_id"]] = record
    return {
        "ok": True,
        "framework_id": result["framework_id"],
        "record": record,
        "view": adapt_record_to_view(record),
        "warnings": result.get("warnings", []),
    }


def activate_framework(framework_id: str, user: str, role: str) -> dict[str, Any]:
    """Drive lifecycle to Active, synthesizing intermediate transitions."""
    rec = ecs_state.framework_onboarding_registry.get(framework_id)
    if not rec:
        return {"ok": False, "message": f"Framework {framework_id} not found."}
    state = rec.get("lifecycle_state", "Imported")
    transitions = []
    if state in ("Imported", "Draft"):
        transitions.append("map")
    if state in ("Imported", "Draft", "Mapped"):
        transitions.append("review")
    if state in ("Imported", "Draft", "Mapped", "Reviewed"):
        transitions.append("approve")
    transitions.append("activate")
    messages = []
    for action in transitions:
        messages.append(advance_lifecycle(framework_id, action, user, role))
    rec = ecs_state.framework_onboarding_registry.get(framework_id, rec)
    return {
        "ok": True,
        "messages": messages,
        "framework_id": framework_id,
        "framework_name": rec.get("framework_name", ""),
        "lifecycle_state": rec.get("lifecycle_state", state),
        "view": adapt_record_to_view(rec),
    }
