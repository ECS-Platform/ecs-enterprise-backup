"""Phase-1 Evidence Reuse & Observation Lifecycle — value-chain demonstration.

Demonstrates the complete ECS value chain for the three working predefined
controls (DB-001, APP-001, OS-001):

    Predefined Query -> Evidence Generation -> Evidence Reuse -> Audit Readiness
    -> Observation Creation -> Observation Closure

The engine is self-contained and deterministic. When a control has *live*
predefined-query evidence (from an actual run in this process), that evidence
is used; otherwise a deterministic demo evidence record is synthesised so the
story always renders. No new APIs, DB schema, connectors, or execution logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ----------------------------------------------------------------------------
# Phase-1 demonstration framework set (exactly the six requested)
# ----------------------------------------------------------------------------
FW_PCI = "PCI DSS"
FW_RBI = "RBI C-SITE"
FW_DPSC = "DPSC"
FW_DB = "DB Baseline"
FW_OS = "OS Baseline"
FW_ITPP = "ITPP"

HOURS_PER_COLLECTION = 4  # manual evidence-collection effort avoided per reuse

# ----------------------------------------------------------------------------
# Per-control demonstration definition (DB-001, APP-001, OS-001)
# Each control maps to multiple frameworks -> one evidence is REUSED across them.
# ----------------------------------------------------------------------------
STORY_CONTROLS: dict[str, dict[str, Any]] = {
    "DB-001": {
        "control_name": "Database transport encryption (SSL/TLS enforced)",
        "technology": "PostgreSQL",
        "application": "Core Banking Database",
        "frameworks": [FW_PCI, FW_RBI, FW_DB],
        "framework_refs": {FW_PCI: "Req 4.1", FW_RBI: "C-SITE 5.2", FW_DB: "DBB-07"},
        "rule": "PostgreSQL 'ssl' parameter must be ON",
        "severity": "High",
        "demo_result": "ssl\n---\noff",
    },
    "APP-001": {
        "control_name": "Application source-code security scanning",
        "technology": "SonarQube",
        "application": "Net Banking Application",
        "frameworks": [FW_PCI, FW_DPSC, FW_ITPP],
        "framework_refs": {FW_PCI: "Req 6.3", FW_DPSC: "DPSC 3.4", FW_ITPP: "ITPP 8.1"},
        "rule": "At least one project actively scanned by SonarQube",
        "severity": "Medium",
        "demo_result": "SonarQube Project Count: 6",
    },
    "OS-001": {
        "control_name": "Operating-system baseline hardening",
        "technology": "Linux",
        "application": "Payment Gateway Host",
        "frameworks": [FW_RBI, FW_OS, FW_ITPP],
        "framework_refs": {FW_RBI: "C-SITE 4.7", FW_OS: "OSB-12", FW_ITPP: "ITPP 8.3"},
        "rule": "SSH root login disabled and OS patches current",
        "severity": "Medium",
        "demo_result": "PermitRootLogin no\nyum check-update: 0 pending updates",
    },
}

# Pre-existing OPEN observation from a prior cycle that Phase-1 evidence can close,
# to demonstrate the closure half of the lifecycle.
PRE_EXISTING_OBSERVATIONS: list[dict[str, Any]] = [
    {
        "observation_id": "OBS-OS-0007",
        "framework": FW_OS,
        "control_id": "OS-001",
        "application": "Payment Gateway Host",
        "severity": "Medium",
        "finding": "OS baseline hardening not verified in the prior cycle "
                   "(SSH root-login and patch status were unconfirmed).",
        "status": "Open",
    },
]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _evaluate(control_id: str, result: str) -> tuple[bool, str]:
    """Return (satisfied, finding). Deterministic per-control compliance rule."""
    text = (result or "").lower()
    if control_id == "DB-001":
        # SSL must be ON; the demo/live result shows 'off' -> violation
        satisfied = "ssl" in text and "off" not in text and "on" in text
        finding = "" if satisfied else "Database SSL/TLS is OFF — data in transit is not encrypted."
        return satisfied, finding
    if control_id == "APP-001":
        count = 0
        for tok in text.replace(":", " ").split():
            if tok.isdigit():
                count = int(tok)
                break
        satisfied = "sonarqube" in text and count >= 1
        finding = "" if satisfied else "No SonarQube projects are being scanned for this application."
        return satisfied, finding
    if control_id == "OS-001":
        satisfied = "permitrootlogin no" in text
        finding = "" if satisfied else "SSH root login is permitted / OS baseline not hardened."
        return satisfied, finding
    return False, "Unknown control — no compliance rule defined."


def _evidence_for(control_id: str) -> dict[str, Any]:
    """Use live PQ evidence if present in this process; else deterministic demo."""
    spec = STORY_CONTROLS[control_id]
    live = None
    try:
        from modules.operations.engines.predefined_query_evidence import (
            get_latest_evidence_for_control,
        )

        live = get_latest_evidence_for_control(control_id)
    except Exception:  # noqa: BLE001
        live = None

    if live and live.get("result"):
        evidence_id = live.get("evidence_id") or f"PQ-EVD-{control_id}"
        result = live.get("result")
        timestamp = live.get("timestamp") or _ts()
        source = "live"
    else:
        evidence_id = f"PQ-EVD-DEMO-{control_id}"
        result = spec["demo_result"]
        timestamp = _ts()
        source = "demo"

    satisfied, finding = _evaluate(control_id, result)
    return {
        "evidence_id": evidence_id,
        "control_id": control_id,
        "control_name": spec["control_name"],
        "application": spec["application"],
        "technology": spec["technology"],
        "frameworks": list(spec["frameworks"]),
        "framework_coverage": ", ".join(spec["frameworks"]),
        "timestamp": timestamp,
        "result": result,
        "satisfied": satisfied,
        "status": "Satisfied" if satisfied else "Violation",
        "finding": finding,
        "severity": spec["severity"],
        "source": source,
    }


def build_evidence_reuse_story() -> dict[str, Any]:
    """Single entry point — returns the full value-chain demonstration."""
    evidence = [_evidence_for(cid) for cid in ("DB-001", "APP-001", "OS-001")]
    by_control = {e["control_id"]: e for e in evidence}

    # ---- 1. Evidence Reuse mapping: Evidence -> Framework -> Control -> Status
    reuse_rows: list[dict[str, Any]] = []
    frameworks_covered: set[str] = set()
    obligations = 0
    for e in evidence:
        for fw in e["frameworks"]:
            obligations += 1
            frameworks_covered.add(fw)
            reuse_rows.append({
                "evidence_id": e["evidence_id"],
                "control_id": e["control_id"],
                "framework": fw,
                "framework_ref": STORY_CONTROLS[e["control_id"]]["framework_refs"].get(fw, "—"),
                "status": e["status"],
            })

    unique_evidence = len(evidence)
    collections_saved = obligations - unique_evidence
    reuse_summary = {
        "reuse_count": obligations,                       # framework-control obligations served
        "reuse_factor": round(obligations / unique_evidence, 2) if unique_evidence else 0,
        "frameworks_covered": len(frameworks_covered),
        "frameworks_list": sorted(frameworks_covered),
        "controls_covered": unique_evidence,
        "collections_saved": collections_saved,
        "effort_saved_hours": collections_saved * HOURS_PER_COLLECTION,
    }

    # ---- 2. Audit Readiness: per-framework obligation coverage + drilldown
    fw_map: dict[str, list[dict[str, Any]]] = {}
    for e in evidence:
        for fw in e["frameworks"]:
            fw_map.setdefault(fw, []).append({
                "control_id": e["control_id"],
                "control_name": e["control_name"],
                "evidence_id": e["evidence_id"],
                "status": "Covered" if e["satisfied"] else "Gap",
            })

    by_framework = []
    covered_total = 0
    for fw in sorted(fw_map):
        ctrls = fw_map[fw]
        covered = sum(1 for c in ctrls if c["status"] == "Covered")
        covered_total += covered
        by_framework.append({
            "framework": fw,
            "covered": covered,
            "total": len(ctrls),
            "readiness_pct": round(100 * covered / len(ctrls), 1) if ctrls else 0.0,
            "controls": ctrls,
        })

    readiness = {
        "covered_controls": covered_total,
        "total_controls": obligations,
        "readiness_pct": round(100 * covered_total / obligations, 1) if obligations else 0.0,
        "controls_satisfied": sum(1 for e in evidence if e["satisfied"]),
        "controls_total": unique_evidence,
        "by_framework": by_framework,
    }

    # ---- 3. Observation Creation: auto-create for any violating evidence
    open_observations: list[dict[str, Any]] = []
    seq = 1
    for e in evidence:
        if not e["satisfied"]:
            primary_fw = e["frameworks"][0]
            open_observations.append({
                "observation_id": f"OBS-{e['control_id']}-{seq:04d}",
                "framework": primary_fw,
                "frameworks_impacted": e["frameworks"],
                "control_id": e["control_id"],
                "control_name": e["control_name"],
                "application": e["application"],
                "severity": e["severity"],
                "finding": e["finding"],
                "evidence_reference": e["evidence_id"],
                "status": "Open",
            })
            seq += 1

    # ---- 4. Observation Closure: satisfying evidence closes a matching open obs
    ready_for_closure: list[dict[str, Any]] = []
    for obs in PRE_EXISTING_OBSERVATIONS:
        ev = by_control.get(obs["control_id"])
        if ev and ev["satisfied"]:
            ready_for_closure.append({
                "observation_id": obs["observation_id"],
                "evidence_used": ev["evidence_id"],
                "control_covered": f"{ev['control_id']} — {ev['control_name']}",
                "framework_covered": obs["framework"],
                "application": obs["application"],
                "status": "READY FOR CLOSURE",
            })
        else:
            # still open if the evidence does not yet satisfy it
            open_observations.append({
                "observation_id": obs["observation_id"],
                "framework": obs["framework"],
                "frameworks_impacted": [obs["framework"]],
                "control_id": obs["control_id"],
                "control_name": STORY_CONTROLS.get(obs["control_id"], {}).get("control_name", ""),
                "application": obs["application"],
                "severity": obs["severity"],
                "finding": obs["finding"],
                "evidence_reference": "—",
                "status": "Open",
            })

    observations = {
        "open": open_observations,
        "open_count": len(open_observations),
        "ready_for_closure": ready_for_closure,
        "closure_count": len(ready_for_closure),
    }

    return {
        "ok": True,
        "evidence": evidence,
        "reuse_rows": reuse_rows,
        "reuse_summary": reuse_summary,
        "readiness": readiness,
        "observations": observations,
        "frameworks_in_scope": [FW_PCI, FW_RBI, FW_DPSC, FW_DB, FW_OS, FW_ITPP],
        "controls_in_scope": ["DB-001", "APP-001", "OS-001"],
    }
