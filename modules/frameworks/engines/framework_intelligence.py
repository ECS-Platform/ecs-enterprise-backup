"""Framework Control Intelligence & Evidence Reuse Engine.

Builds the executive analytics that power the Framework Loader page:

* Canonical control "themes" derived from every framework's controls
* Cross-framework overlap matrix (themes × frameworks)
* Reusable-evidence registry with per-application coverage
* App-by-app evidence scan results
* Reuse traceability tree (theme → frameworks → applications → reuse targets)
* Compact heatmap data + KPI roll-ups (controls reused, evidence reused,
  audit effort saved, readiness improvement)
* Drill-down records for any theme/control
"""

from __future__ import annotations

from typing import Any, Iterable

from app import ecs_state
from modules.frameworks.engines.framework_catalog import (
    FRAMEWORK_CATALOG,
    get_all_evidence_records,
    get_merged_framework_catalog,
)


# ---------------------------------------------------------------------------
# Canonical control themes — maps natural-language control names into
# normalized governance dimensions used for reuse matching.
# ---------------------------------------------------------------------------

CONTROL_THEMES: list[dict[str, Any]] = [
    {"key": "encryption_rest", "label": "Encryption at Rest", "category": "Cryptography",
     "keywords": ["encryption at rest", "tde", "transparent data", "data at rest", "key escrow",
                  "key management", "cryptographic key", "key custodian", "key ceremony",
                  "backup encryption", "biometric data", "database encryption"]},
    {"key": "encryption_transit", "label": "Encryption in Transit", "category": "Cryptography",
     "keywords": ["encryption in transit", "tls", "ssl", "https", "in transit",
                  "data in motion", "channel encryption", "mtls", "certificate"]},
    {"key": "mfa", "label": "MFA / Privileged Access", "category": "Identity",
     "keywords": ["mfa", "multi-factor", "multi factor", "two-factor", "privileged access",
                  "pam", "session recording", "session security"]},
    {"key": "access_review", "label": "Access Review & Recertification", "category": "Identity",
     "keywords": ["access review", "recertification", "iam", "least privilege",
                  "entitlement", "sod", "segregation of duties", "role-based",
                  "access restriction", "binding"]},
    {"key": "siem", "label": "SIEM / Log Monitoring", "category": "Detection",
     "keywords": ["siem", "log monitoring", "log review", "audit log", "audit trail",
                  "centralized log", "soc monitoring", "alert", "monitoring",
                  "detection", "anomaly", "edr"]},
    {"key": "incident_response", "label": "Incident Response & RCA", "category": "Detection",
     "keywords": ["incident response", "ir tabletop", "rca", "root cause",
                  "incident sla", "major incident", "p1", "p2", "soar", "playbook"]},
    {"key": "vulnerability", "label": "Vulnerability Mgmt / VAPT", "category": "Detection",
     "keywords": ["vulnerability", "va scan", "pen test", "penetration", "vapt",
                  "asv", "patch", "remediation", "red team", "container escape",
                  "fuzz", "logic flaw"]},
    {"key": "firewall", "label": "Firewall / Segmentation", "category": "Network",
     "keywords": ["firewall", "segmentation", "network segmentation", "dmz",
                  "ddos", "rate limit", "rate limiting", "waf"]},
    {"key": "hardening", "label": "Hardening & Baselines", "category": "Infrastructure",
     "keywords": ["hardening", "baseline", "cis", "configuration", "secure config",
                  "kernel", "sshd", "sysctl", "container host", "container runtime",
                  "drift", "security header", "ocsp"]},
    {"key": "backup_recovery", "label": "Backup, DR & Recovery", "category": "Resilience",
     "keywords": ["backup", "restore", "recovery", "dr plan", "dr drill", "dr site",
                  "rpo", "rto", "failover", "high availability", "ha", "resilien",
                  "continuity", "bcm", "bia"]},
    {"key": "change_management", "label": "Change & Release Management", "category": "Operations",
     "keywords": ["change advisory", "cab", "change control", "emergency change",
                  "release security", "post-implementation", "rollback",
                  "change testing", "uat signoff"]},
    {"key": "asset_inventory", "label": "Asset / CMDB Inventory", "category": "Operations",
     "keywords": ["cmdb", "asset", "inventory", "device inventory", "asset register",
                  "unused service", "decommiss"]},
    {"key": "third_party", "label": "Third-Party / Vendor Risk", "category": "Risk",
     "keywords": ["third-party", "third party", "tpsp", "vendor", "supplier",
                  "psp", "service provider", "vendor risk"]},
    {"key": "appsec", "label": "AppSec / Secure SDLC", "category": "Application Security",
     "keywords": ["sast", "dast", "sca", "secure code", "secure sdlc", "devsecops",
                  "secrets scan", "input validation", "session management",
                  "threat model", "sbom", "deserialization", "security champion",
                  "appsec"]},
    {"key": "data_privacy", "label": "Data Privacy & Retention", "category": "Privacy",
     "keywords": ["retention", "disposal", "data minimization", "consent", "privacy",
                  "cross-border", "dpa", "biometric data", "data masking",
                  "data protection"]},
    {"key": "fraud_payments", "label": "Fraud & Payments Integrity", "category": "Payments",
     "keywords": ["fraud", "aml", "screening", "tokenization", "settlement",
                  "transaction screening", "payment exception"]},
    {"key": "monitoring_availability", "label": "Availability & Capacity", "category": "Operations",
     "keywords": ["availability", "uptime", "capacity", "cpu utilization",
                  "storage forecast", "throughput", "load test"]},
    {"key": "training", "label": "Training & Awareness", "category": "Culture",
     "keywords": ["training", "awareness", "phishing simulation", "security champions"]},
]


_THEME_INDEX = {t["key"]: t for t in CONTROL_THEMES}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_frameworks() -> dict[str, list[dict]]:
    """Merged catalog (static + dynamically-onboarded)."""
    return get_merged_framework_catalog()


def _normalize(text: str | None) -> str:
    return (text or "").lower().strip()


def _theme_match_score(control_text: str, theme: dict) -> int:
    """Return number of keyword hits for a theme."""
    return sum(1 for kw in theme["keywords"] if kw in control_text)


def classify_control_themes(control: dict) -> list[str]:
    """Return the canonical theme keys that match this control (multi-tag)."""
    blob = " ".join(
        _normalize(str(control.get(k, "")))
        for k in ("control", "control_name", "control_description")
    )
    if not blob:
        return []
    matched: list[tuple[str, int]] = []
    for theme in CONTROL_THEMES:
        score = _theme_match_score(blob, theme)
        if score:
            matched.append((theme["key"], score))
    matched.sort(key=lambda kv: -kv[1])
    if matched:
        return [k for k, _ in matched[:3]]
    return ["asset_inventory"]


# ---------------------------------------------------------------------------
# Core index built once per request
# ---------------------------------------------------------------------------


def build_control_index() -> list[dict]:
    """Return a flat per-control index: framework, control id/name, themes, evidences."""
    out: list[dict] = []
    for fw, controls in _all_frameworks().items():
        for ctrl in controls:
            name = ctrl.get("control") or ctrl.get("control_name") or ""
            themes = classify_control_themes(ctrl)
            evidences = []
            for ev in ctrl.get("evidences", []) or []:
                evidences.append({
                    "evidence_id": ev.get("evidence_id", ""),
                    "evidence_name": ev.get("evidence_name", ""),
                    "application": ev.get("application") or ev.get("application_name") or "",
                    "audit_status": ev.get("audit_status", ""),
                    "evidence_status": ev.get("evidence_status", ""),
                    "mock_file": ev.get("mock_file", ""),
                    "source": ev.get("evidence_source", ""),
                })
            out.append({
                "framework": fw,
                "control_id": ctrl.get("control_id", ""),
                "control_name": name,
                "description": ctrl.get("control_description", ""),
                "themes": themes,
                "primary_theme": themes[0] if themes else "asset_inventory",
                "evidences": evidences,
                "applications": sorted({e["application"] for e in evidences if e["application"]}),
            })
    return out


# ---------------------------------------------------------------------------
# Overlap matrix
# ---------------------------------------------------------------------------


def build_overlap_matrix(
    index: list[dict] | None = None,
    framework_columns: list[str] | None = None,
) -> dict[str, Any]:
    index = index or build_control_index()
    frameworks = framework_columns or sorted({c["framework"] for c in index})
    rows: list[dict] = []
    for theme in CONTROL_THEMES:
        controls_by_fw: dict[str, list[dict]] = {fw: [] for fw in frameworks}
        for ctrl in index:
            if theme["key"] in ctrl["themes"] and ctrl["framework"] in controls_by_fw:
                controls_by_fw[ctrl["framework"]].append(ctrl)
        covered_count = sum(1 for fw in frameworks if controls_by_fw[fw])
        reusable = covered_count >= 2
        cells = [
            {
                "framework": fw,
                "present": bool(controls_by_fw[fw]),
                "count": len(controls_by_fw[fw]),
                "control_names": [c["control_name"] for c in controls_by_fw[fw][:3]],
            }
            for fw in frameworks
        ]
        if covered_count == 0:
            continue
        rows.append({
            "theme_key": theme["key"],
            "theme_label": theme["label"],
            "category": theme["category"],
            "frameworks_covered": covered_count,
            "frameworks_total": len(frameworks),
            "coverage_pct": round(covered_count / max(len(frameworks), 1) * 100, 1),
            "reusable": reusable,
            "cells": cells,
            "tone": ("tone-green" if covered_count >= 4 else
                     "tone-amber" if covered_count >= 2 else
                     "tone-red"),
        })
    rows.sort(key=lambda r: -r["frameworks_covered"])
    return {"frameworks": frameworks, "rows": rows}


# ---------------------------------------------------------------------------
# Evidence reuse engine
# ---------------------------------------------------------------------------


def build_evidence_reuse(
    index: list[dict] | None = None,
    focus_framework: str | None = None,
) -> dict[str, Any]:
    """KPIs for the Evidence Reuse Dashboard.

    Args:
        focus_framework: when provided, "new evidence required" measures the
            controls in this framework that lack any cross-framework matches.
    """
    index = index or build_control_index()
    matrix = build_overlap_matrix(index)
    # "Reusable" baseline: theme appears in ≥2 frameworks
    reusable_themes = [r for r in matrix["rows"] if r["reusable"]]
    reusable_theme_keys = {r["theme_key"] for r in reusable_themes}
    # "High reuse" themes: covered by ≥3 frameworks — drives audit effort %
    high_reuse_keys = {
        r["theme_key"] for r in matrix["rows"] if r["frameworks_covered"] >= 3
    }

    # Controls reused = controls outside the "source" framework for each theme.
    # For each theme, the framework with the most controls is treated as the
    # canonical source; controls in every other framework tagged with the same
    # theme count as reuse. This produces a believable headcount for the
    # demo (e.g. ~80–140 reuse mappings on a 10-framework catalog).
    theme_framework_index: dict[str, set[str]] = {}
    for c in index:
        for t in c["themes"]:
            theme_framework_index.setdefault(t, set()).add(c["framework"])
    theme_source_framework: dict[str, str] = {}
    for theme_key, fws in theme_framework_index.items():
        if not fws:
            continue
        ranked = sorted(
            fws,
            key=lambda fw: (
                -sum(1 for c in index if c["framework"] == fw and theme_key in c["themes"]),
                fw,
            ),
        )
        theme_source_framework[theme_key] = ranked[0]
    controls_reused = sum(
        1
        for c in index
        if c["primary_theme"] in reusable_theme_keys
        and theme_source_framework.get(c["primary_theme"]) != c["framework"]
    )

    # Reusable evidence = unique evidence files attached to high-reuse themes
    reusable_evidence_ids: set[str] = set()
    apps_with_reuse: set[str] = set()
    for c in index:
        if not any(t in high_reuse_keys for t in c["themes"]):
            continue
        for ev in c["evidences"]:
            if ev.get("evidence_id"):
                reusable_evidence_ids.add(ev["evidence_id"])
            if ev.get("application"):
                apps_with_reuse.add(ev["application"])

    # New evidence required (focus framework lens, or themes covered only once)
    if focus_framework:
        focus_controls = [c for c in index if c["framework"] == focus_framework]
        new_evidence_required = sum(
            1
            for c in focus_controls
            if not any(t in reusable_theme_keys for t in c["themes"])
        )
    else:
        new_evidence_required = sum(
            1 for r in matrix["rows"] if r["frameworks_covered"] == 1
        )

    total_controls = len(index)
    # Audit effort saved blends reused-control share with high-reuse coverage,
    # capped at 78% so the demo never claims absolute reuse.
    raw_saved = (controls_reused / max(total_controls, 1)) * 100
    audit_effort_saved_pct = round(min(raw_saved * 0.7, 78.0), 1) if total_controls else 0.0
    # Readiness improvement = % of frameworks where ≥40% of themes overlap
    framework_overlap_scores: dict[str, float] = {}
    for fw in matrix["frameworks"]:
        themes_in_fw = {t for c in index if c["framework"] == fw for t in c["themes"]}
        reusable_in_fw = themes_in_fw & reusable_theme_keys
        if themes_in_fw:
            framework_overlap_scores[fw] = round(
                len(reusable_in_fw) / len(themes_in_fw) * 100, 1
            )
    readiness_improvement_pct = (
        round(sum(framework_overlap_scores.values()) / len(framework_overlap_scores), 1)
        if framework_overlap_scores
        else 0.0
    )
    # Cap & normalize to "+X%" improvement narrative
    readiness_delta = min(round(readiness_improvement_pct / 3, 1), 38.0)

    return {
        "controls_reused": controls_reused,
        "reusable_evidence_found": len(reusable_evidence_ids),
        "new_evidence_required": new_evidence_required,
        "audit_effort_saved_pct": audit_effort_saved_pct,
        "readiness_improvement_pct": readiness_delta,
        "applications_covered": len(apps_with_reuse),
        "reusable_themes_count": len(reusable_themes),
        "total_themes": len(matrix["rows"]),
        "framework_overlap_scores": framework_overlap_scores,
    }


# ---------------------------------------------------------------------------
# Reuse traceability tree
# ---------------------------------------------------------------------------


def build_reuse_traceability(
    index: list[dict] | None = None,
    limit_themes: int = 6,
) -> list[dict]:
    index = index or build_control_index()
    rows: list[dict] = []
    for theme in CONTROL_THEMES:
        bucket = [c for c in index if theme["key"] in c["themes"]]
        if not bucket:
            continue
        primary_frameworks = sorted({c["framework"] for c in bucket})
        applications = sorted({a for c in bucket for a in c["applications"]})
        evidence_samples = []
        seen: set[str] = set()
        for c in bucket:
            for ev in c["evidences"]:
                eid = ev.get("evidence_id")
                if eid and eid not in seen:
                    seen.add(eid)
                    evidence_samples.append({
                        "evidence_id": eid,
                        "evidence_name": ev["evidence_name"],
                        "application": ev["application"],
                        "framework": c["framework"],
                    })
                if len(evidence_samples) >= 6:
                    break
            if len(evidence_samples) >= 6:
                break
        reusable_for = primary_frameworks[1:5] if len(primary_frameworks) > 1 else []
        rows.append({
            "theme_key": theme["key"],
            "theme_label": theme["label"],
            "category": theme["category"],
            "frameworks": primary_frameworks,
            "applications": applications,
            "evidence_samples": evidence_samples[:5],
            "reusable_for": reusable_for,
            "source_framework": primary_frameworks[0] if primary_frameworks else "",
            "reuse_confidence_pct": round(min(95, 55 + len(primary_frameworks) * 7), 1),
        })
    rows.sort(key=lambda r: -len(r["frameworks"]))
    return rows[:limit_themes]


# ---------------------------------------------------------------------------
# Application-by-application evidence scan
# ---------------------------------------------------------------------------


APPLICATION_SCAN_LIST: list[str] = [
    "Net Banking",
    "Mobile Banking",
    "Payments",
    "Treasury",
    "UPI",
    "Loan System",
    "API Gateway",
    "Wealth Portal",
]


def build_application_scan(
    index: list[dict] | None = None,
    applications: list[str] | None = None,
) -> list[dict]:
    index = index or build_control_index()
    apps = applications or APPLICATION_SCAN_LIST
    rows: list[dict] = []
    for app in apps:
        theme_hits: dict[str, int] = {}
        evidence_samples: list[dict] = []
        seen: set[str] = set()
        for c in index:
            relevant = [
                ev for ev in c["evidences"]
                if (ev.get("application") or "").lower() == app.lower()
            ]
            if not relevant:
                continue
            for t in c["themes"]:
                theme_hits[t] = theme_hits.get(t, 0) + 1
            for ev in relevant:
                eid = ev.get("evidence_id")
                if eid and eid not in seen:
                    seen.add(eid)
                    evidence_samples.append({
                        "evidence_id": eid,
                        "evidence_name": ev["evidence_name"],
                        "framework": c["framework"],
                        "theme_label": (
                            _THEME_INDEX.get(c["primary_theme"], {}).get("label", "—")
                        ),
                        "audit_status": ev.get("audit_status", ""),
                    })
        rows.append({
            "application": app,
            "evidence_count": sum(1 for _ in evidence_samples),
            "themes_covered": [
                {
                    "theme_key": k,
                    "theme_label": _THEME_INDEX.get(k, {}).get("label", k),
                    "count": v,
                }
                for k, v in sorted(theme_hits.items(), key=lambda kv: -kv[1])[:6]
            ],
            "evidence_samples": evidence_samples[:6],
            "scan_status": (
                "scanning" if not evidence_samples else "complete"
            ),
        })
    return rows


# ---------------------------------------------------------------------------
# Control heatmap (themes × tone)
# ---------------------------------------------------------------------------


def build_control_heatmap(matrix: dict[str, Any]) -> list[dict]:
    cells: list[dict] = []
    for row in matrix["rows"]:
        if row["frameworks_covered"] >= 4:
            tone = "tone-green"
            label = "High Reuse"
        elif row["frameworks_covered"] >= 2:
            tone = "tone-amber"
            label = "Partial Reuse"
        else:
            tone = "tone-red"
            label = "Needs New Evidence"
        cells.append({
            "theme_key": row["theme_key"],
            "theme_label": row["theme_label"],
            "category": row["category"],
            "tone": tone,
            "label": label,
            "frameworks_covered": row["frameworks_covered"],
            "frameworks_total": row["frameworks_total"],
            "coverage_pct": row["coverage_pct"],
        })
    return cells


# ---------------------------------------------------------------------------
# Public façade for the loader page
# ---------------------------------------------------------------------------


def build_intelligence_payload(focus_framework: str | None = None) -> dict[str, Any]:
    index = build_control_index()
    matrix = build_overlap_matrix(index)
    reuse = build_evidence_reuse(index, focus_framework)
    traceability = build_reuse_traceability(index)
    app_scan = build_application_scan(index)
    heatmap = build_control_heatmap(matrix)
    catalog_stats = {
        "frameworks_total": len(matrix["frameworks"]),
        "controls_total": len(index),
        "themes_total": len(matrix["rows"]),
        "applications_scanned": len(app_scan),
    }
    reuse_dashboard = [
        {"label": "Controls Reused", "value": reuse["controls_reused"], "tone": "primary", "hint": "Across mapped frameworks"},
        {"label": "Reusable Evidence Found", "value": reuse["reusable_evidence_found"], "tone": "success", "hint": "Unique evidence artefacts"},
        {"label": "New Evidence Required", "value": reuse["new_evidence_required"], "tone": "danger", "hint": "Themes without overlap"},
        {"label": "Audit Effort Saved", "value": f"{reuse['audit_effort_saved_pct']}%", "tone": "info", "hint": "Reused controls share"},
        {"label": "Readiness Improvement", "value": f"+{reuse['readiness_improvement_pct']}%", "tone": "warning", "hint": "Cross-framework lift"},
    ]
    return {
        "stats": catalog_stats,
        "overlap_matrix": matrix,
        "evidence_reuse": reuse,
        "evidence_reuse_dashboard": reuse_dashboard,
        "reuse_traceability": traceability,
        "application_scan": app_scan,
        "control_heatmap": heatmap,
        "themes": CONTROL_THEMES,
    }


# ---------------------------------------------------------------------------
# Drill-down API (single theme / control)
# ---------------------------------------------------------------------------


def drill_theme(theme_key: str) -> dict[str, Any]:
    theme = _THEME_INDEX.get(theme_key)
    if not theme:
        return {"ok": False, "error": f"Unknown theme {theme_key}"}
    index = build_control_index()
    matches = [c for c in index if theme_key in c["themes"]]
    frameworks = sorted({c["framework"] for c in matches})
    applications = sorted({a for c in matches for a in c["applications"]})
    evidence_records = []
    seen: set[str] = set()
    for c in matches:
        for ev in c["evidences"]:
            eid = ev.get("evidence_id", "")
            key = f"{c['framework']}::{eid}"
            if key in seen:
                continue
            seen.add(key)
            evidence_records.append({
                "framework": c["framework"],
                "control_id": c["control_id"],
                "control_name": c["control_name"],
                "evidence_id": eid,
                "evidence_name": ev["evidence_name"],
                "application": ev["application"],
                "audit_status": ev["audit_status"],
                "evidence_status": ev["evidence_status"],
                "source": ev["source"],
            })
    observations = []
    for c in matches[:10]:
        observations.append({
            "framework": c["framework"],
            "control_id": c["control_id"],
            "observation_id": f"OBS-{c['control_id'].replace('.', '').replace('-', '')[-6:]}",
            "status": ("Closed" if len(c["evidences"]) >= 2 else "Open"),
            "summary": (c["description"] or c["control_name"])[:160],
        })
    reuse_pct = round(min(95, 55 + len(frameworks) * 7), 1) if frameworks else 0.0
    return {
        "ok": True,
        "theme_key": theme_key,
        "theme_label": theme["label"],
        "category": theme["category"],
        "linked_frameworks": frameworks,
        "linked_applications": applications,
        "linked_controls": [
            {
                "framework": c["framework"],
                "control_id": c["control_id"],
                "control_name": c["control_name"],
            }
            for c in matches[:25]
        ],
        "linked_evidence": evidence_records[:40],
        "linked_observations": observations,
        "reuse_confidence_pct": reuse_pct,
        "audit_cycles": ["Q1 2026", "Q2 2026", "Q3 2026 (planned)"],
    }
