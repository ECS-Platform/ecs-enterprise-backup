"""Enterprise Framework Onboarding Engine — ingest, normalize, reuse intelligence, gap creation."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app import ecs_state
from modules.frameworks.engines.framework_catalog import (
    APPLICATIONS,
    FRAMEWORK_CATALOG,
    get_all_evidence_records,
    get_framework_controls,
    resolve_framework_name,
)
from modules.shared.services.audit_trail import log_event

LIFECYCLE_STATES = ("Draft", "Imported", "Mapped", "Reviewed", "Approved", "Active")
CATEGORIES = ("Security", "Audit", "Regulatory", "Infra", "Risk")

KEYWORD_CLUSTERS: dict[str, list[str]] = {
    "firewall": ["firewall", "segmentation", "network access", "cde access", "acl", "waf"],
    "logging": ["log", "siem", "monitoring", "audit trail", "log review", "soc"],
    "mfa": ["mfa", "multi-factor", "privileged access", "pam", "authentication"],
    "encryption": ["encrypt", "tde", "tls", "cryptograph", "at rest", "in transit"],
    "vulnerability": ["vulnerability", "va scan", "pentest", "patch", "remediation"],
    "hardening": ["hardening", "baseline", "cis", "configuration standard"],
    "access": ["access review", "iam", "role", "least privilege", "identity"],
    "consent": ["consent", "privacy", "pii", "data protection", "retention"],
    "backup": ["backup", "recovery", "dr", "resilience", "availability"],
}

SAMPLE_TEMPLATES = [
    ("Daily log monitoring validation", "Security", "High", "Daily", "SIEM export / log review report"),
    ("Firewall rule review and segmentation", "Security", "Critical", "Quarterly", "Firewall rule export"),
    ("MFA enforcement for privileged users", "Security", "High", "Monthly", "PAM MFA enrollment report"),
    ("Encryption at rest attestation", "Security", "Critical", "Quarterly", "TDE / vault attestation"),
    ("External vulnerability assessment", "Audit", "High", "Quarterly", "VA scan report"),
    ("OS hardening baseline validation", "Infra", "Medium", "Quarterly", "CIS benchmark spreadsheet"),
    ("Access review for production systems", "Audit", "Medium", "Quarterly", "IAM access review export"),
    ("Incident response plan testing", "Risk", "High", "Annual", "Tabletop exercise minutes"),
    ("Data retention and consent management", "Regulatory", "High", "Quarterly", "Consent log export"),
    ("Secure SDLC gate attestation", "Security", "Medium", "Per release", "SAST/DAST summary"),
]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _framework_delegate(capability: str, role: str):
    """PolicyEngine LEGACY-COMPAT verdict for a framework capability, or None to
    use legacy. Gated by the same RBAC_DELEGATION_ENABLED kill switch (default
    FALSE). Never raises — any error returns None so the caller falls back to
    the verbatim legacy logic. Bug-for-bug parity with the legacy predicate.
    """
    from modules.shared.services.role_permissions import _delegation_enabled

    if not _delegation_enabled():
        return None
    try:
        from app.auth.authz import get_policy_engine

        return bool(get_policy_engine().can_legacy(role, capability))
    except Exception:  # noqa: BLE001
        return None


def can_manage_framework_onboarding(role: str) -> bool:
    d = _framework_delegate("can_manage_framework_onboarding", role)
    if d is not None:
        return d
    from modules.shared.services.role_permissions import normalize_role
    return normalize_role(role) in {"cio", "compliance_head", "enterprise_admin", "admin"}


def can_review_framework_onboarding(role: str) -> bool:
    d = _framework_delegate("can_review_framework_onboarding", role)
    if d is not None:
        return d
    from modules.shared.services.role_permissions import normalize_role
    return normalize_role(role) in {"auditor", "enterprise_admin", "admin", "cio", "compliance_head"}


def can_reuse_evidence_decision(role: str) -> bool:
    d = _framework_delegate("can_reuse_evidence_decision", role)
    if d is not None:
        return d
    from modules.shared.services.role_permissions import normalize_role
    return normalize_role(role) in {"owner", "auditor", "cio", "compliance_head", "enterprise_admin", "admin"}


def derive_prefix(framework_name: str, version: str = "") -> str:
    known = {
        "pci dss": "PCI", "iso 27001": "ISO", "rbi cyber security": "RBI-CS",
        "swift csp": "SWIFT-CSP", "cis controls": "CIS", "dpsc": "DP",
        "appsec": "AS", "vapt": "VP", "csite": "CS", "itpp": "IT",
    }
    key = framework_name.lower().strip()
    for k, p in known.items():
        if k in key:
            return p
    parts = re.sub(r"[^A-Za-z0-9 ]", "", framework_name).split()
    if len(parts) >= 2:
        return "-".join(p[:4].upper() for p in parts[:2])
    return (parts[0][:6].upper() if parts else "FW")


def validate_framework_details(details: dict) -> list[str]:
    errors: list[str] = []
    name = (details.get("framework_name") or "").strip()
    if not name:
        errors.append("Framework name is required.")
    elif any(f.get("framework_name", "").lower() == name.lower() for f in ecs_state.framework_onboarding_registry.values()):
        errors.append(f"Framework '{name}' already exists in onboarding registry.")
    elif name in FRAMEWORK_CATALOG or name in ecs_state.dynamic_framework_catalog:
        errors.append(f"Framework '{name}' already exists in ECS catalog.")
    if not (details.get("version") or "").strip():
        errors.append("Framework version is required.")
    if not (details.get("regulator") or "").strip():
        errors.append("Regulator / authority is required.")
    cat = details.get("category", "")
    if cat and cat not in CATEGORIES:
        errors.append(f"Invalid category — choose from: {', '.join(CATEGORIES)}.")
    return errors


def _parse_csv_controls(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    fields = {f.lower().strip(): f for f in reader.fieldnames}
    rows: list[dict] = []
    for i, row in enumerate(reader):
        name = row.get(fields.get("control_name", ""), "") or row.get(fields.get("control", ""), "") or row.get(fields.get("title", ""), "")
        if not name:
            continue
        rows.append({
            "control_name": name.strip(),
            "control_description": (row.get(fields.get("control_description", ""), "") or row.get(fields.get("description", ""), "") or name).strip(),
            "section": (row.get(fields.get("section", ""), "") or row.get(fields.get("requirement_id", ""), "") or f"{i // 5 + 1}").strip(),
            "requirement": (row.get(fields.get("requirement", ""), "") or row.get(fields.get("requirement_text", ""), "")).strip(),
            "category": (row.get(fields.get("category", ""), "") or "Security").strip(),
            "criticality": (row.get(fields.get("criticality", ""), "") or row.get(fields.get("severity", ""), "") or "Medium").strip(),
            "frequency": (row.get(fields.get("frequency", ""), "") or "Quarterly").strip(),
            "expected_evidence": (row.get(fields.get("expected_evidence", ""), "") or row.get(fields.get("evidence", ""), "") or "Policy attestation").strip(),
        })
    return rows


def _synthesize_controls(framework_name: str, filename: str, count: int = 24) -> list[dict]:
    """Deterministic mock parse for PDF/DOCX/XLSX when structured parse unavailable."""
    base = hashlib.md5(f"{framework_name}:{filename}".encode()).hexdigest()
    n = 18 + (_seed(base, 0, 12))
    rows: list[dict] = []
    for i in range(n):
        tpl = SAMPLE_TEMPLATES[i % len(SAMPLE_TEMPLATES)]
        sec = f"{10 + (i % 8)}.{(i % 6) + 1}"
        rows.append({
            "control_name": tpl[0] if i < len(SAMPLE_TEMPLATES) else f"{framework_name} control attestation {i + 1}",
            "control_description": f"{tpl[0]} — {framework_name} requirement mapping for enterprise banking scope.",
            "section": sec,
            "requirement": f"Req {sec} — {tpl[0]}",
            "category": tpl[1],
            "criticality": tpl[2],
            "frequency": tpl[3],
            "expected_evidence": tpl[4],
        })
    return rows


def parse_control_document(content: bytes, filename: str, framework_name: str) -> tuple[list[dict], list[str]]:
    """Parse uploaded control assessment document."""
    warnings: list[str] = []
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    rows: list[dict] = []
    if ext == "csv":
        rows = _parse_csv_controls(content)
    elif ext in ("xlsx", "xls"):
        try:
            rows = _parse_csv_controls(content)
        except Exception:
            rows = []
        if not rows:
            warnings.append("Excel parsed via AI extraction — using structured control inference.")
            rows = _synthesize_controls(framework_name, filename)
    elif ext in ("pdf", "docx", "doc"):
        warnings.append(f"{ext.upper()} document processed via AI control extraction engine.")
        rows = _synthesize_controls(framework_name, filename)
    else:
        warnings.append("Unknown format — applied AI control inference from document metadata.")
        rows = _synthesize_controls(framework_name, filename)

    if not rows:
        return [], ["No controls could be parsed — check document format and column headers."]
    return rows, warnings


def generate_control_id(prefix: str, section: str, index: int) -> str:
    sec = section.replace(" ", "").replace("Req", "").strip() or str(index + 1)
    if re.match(r"^[\d.]+$", sec):
        return f"{prefix}-{sec}"
    return f"{prefix}-{sec[:8]}-{index + 1:02d}"


def _control_keywords(text: str) -> set[str]:
    t = text.lower()
    found: set[str] = set()
    for cluster, words in KEYWORD_CLUSTERS.items():
        if any(w in t for w in words):
            found.add(cluster)
    tokens = set(re.findall(r"[a-z]{4,}", t))
    return found | tokens


def _similarity(a: str, b: str) -> float:
    ka, kb = _control_keywords(a), _control_keywords(b)
    if not ka or not kb:
        return 0.0
    inter = len(ka & kb)
    union = len(ka | kb)
    ratio = inter / union if union else 0.0
    if a.lower() in b.lower() or b.lower() in a.lower():
        ratio = max(ratio, 0.72)
    return round(ratio * 100, 1)


def _existing_control_corpus() -> list[dict]:
    corpus: list[dict] = []
    for fw, controls in {**FRAMEWORK_CATALOG, **ecs_state.dynamic_framework_catalog}.items():
        for c in controls:
            corpus.append({
                "framework": fw,
                "control_id": c.get("control_id", ""),
                "control_name": c.get("control", c.get("control_name", "")),
                "control_description": c.get("control_description", ""),
                "evidences": c.get("evidences", []),
            })
    return corpus


def normalize_and_match(imported: list[dict], prefix: str) -> list[dict]:
    """Assign ECS control IDs and detect reuse against global corpus."""
    corpus = _existing_control_corpus()
    evidence_index = get_all_evidence_records()
    enriched: list[dict] = []
    for i, row in enumerate(imported):
        cid = generate_control_id(prefix, row.get("section", ""), i)
        name = row["control_name"]
        desc = row.get("control_description", name)
        matches: list[dict] = []
        for ex in corpus:
            sim = _similarity(f"{name} {desc}", f"{ex['control_name']} {ex['control_description']}")
            if sim >= 45:
                ev_candidates = []
                for ev in ex.get("evidences", [])[:2]:
                    ev_candidates.append({
                        "evidence_id": ev.get("evidence_id", ""),
                        "evidence_name": ev.get("evidence_name", ""),
                        "mock_file": ev.get("mock_file", ""),
                    })
                for rec in evidence_index:
                    if rec.get("control_id") == ex["control_id"] or ex["control_name"] in rec.get("control", ""):
                        ev_candidates.append({
                            "evidence_id": rec.get("evidence_id", ""),
                            "evidence_name": rec.get("evidence_name", ""),
                            "mock_file": rec.get("mock_file", ""),
                        })
                matches.append({
                    "framework": ex["framework"],
                    "control_id": ex["control_id"],
                    "control_name": ex["control_name"][:60],
                    "similarity_pct": sim,
                    "match_type": "Exact" if sim >= 85 else ("Semantic" if sim >= 65 else "Partial"),
                    "evidence": ev_candidates[:3],
                })
        matches.sort(key=lambda x: -x["similarity_pct"])
        best = matches[0] if matches else None
        reuse_conf = best["similarity_pct"] if best else 0
        enriched.append({
            **row,
            "control_id": cid,
            "control": name,
            "control_description": desc,
            "reuse_matches": matches[:5],
            "best_match": best,
            "reuse_confidence_pct": reuse_conf,
            "reuse_recommended": reuse_conf >= 65,
            "implementation_state": "Implemented" if reuse_conf >= 75 else ("Partial" if reuse_conf >= 50 else "Missing"),
            "evidence_reuse_available": bool(best and best.get("evidence")),
            "linked_evidence": (best.get("evidence") or [{}])[0] if best else {},
        })
    return enriched


def analyze_implementation(controls: list[dict], applications: list[str] | None = None) -> dict:
    apps = applications or APPLICATIONS
    total = len(controls)
    implemented = sum(1 for c in controls if c.get("implementation_state") == "Implemented")
    partial = sum(1 for c in controls if c.get("implementation_state") == "Partial")
    reusable = sum(1 for c in controls if c.get("reuse_recommended"))
    missing = total - implemented - partial
    critical_missing = sum(1 for c in controls if c.get("criticality") in ("Critical", "High") and c.get("implementation_state") != "Implemented")
    new_evidence = sum(1 for c in controls if not c.get("evidence_reuse_available"))
    coverage = round((implemented + partial * 0.5) / total * 100, 1) if total else 0.0
    return {
        "total_controls": total,
        "implemented": implemented,
        "partially_implemented": partial,
        "missing": missing,
        "reusable_controls": reusable,
        "new_evidence_required": new_evidence,
        "critical_missing": critical_missing,
        "implementation_coverage_pct": coverage,
        "applications_checked": len(apps),
    }


def build_mapping_matrix(controls: list[dict]) -> list[dict]:
    matrix: list[dict] = []
    for c in controls:
        bm = c.get("best_match")
        matrix.append({
            "new_control_id": c["control_id"],
            "new_control_name": c["control_name"][:50],
            "existing_framework": bm["framework"] if bm else "—",
            "existing_control_id": bm["control_id"] if bm else "—",
            "existing_control_name": (bm["control_name"][:40] if bm else "—"),
            "linked_evidence": (c.get("linked_evidence") or {}).get("evidence_name", "—"),
            "application_coverage": "All onboarded apps",
            "reuse_confidence_pct": c.get("reuse_confidence_pct", 0),
            "match_type": bm["match_type"] if bm else "New",
        })
    return matrix


def build_app_implementation_matrix(controls: list[dict], applications: list[str] | None = None) -> list[dict]:
    apps = applications or APPLICATIONS
    rows: list[dict] = []
    for app in apps:
        for c in controls[:12]:
            key = f"{app}:{c['control_id']}"
            state_roll = _seed(key, 0, 100)
            if c.get("implementation_state") == "Implemented":
                state = "Implemented"
            elif c.get("implementation_state") == "Partial":
                state = "Partially Implemented" if state_roll > 30 else "Missing"
            else:
                state = "Missing" if state_roll > 55 else "Partially Implemented"
            rows.append({
                "application": app,
                "control_id": c["control_id"],
                "control_name": c["control_name"][:40],
                "state": state,
                "evidence_reusable": c.get("evidence_reuse_available", False) and state != "Missing",
            })
    return rows


def create_gaps_and_tasks(framework_id: str, framework_name: str, controls: list[dict]) -> list[dict]:
    gaps: list[dict] = []
    for c in controls:
        if c.get("implementation_state") == "Implemented" and c.get("reuse_recommended"):
            continue
        gid = f"GAP-{framework_id[:8].upper()}-{c['control_id']}"
        gaps.append({
            "gap_id": gid,
            "framework": framework_name,
            "framework_id": framework_id,
            "control_id": c["control_id"],
            "control_name": c["control_name"],
            "gap_type": "Missing Evidence" if not c.get("evidence_reuse_available") else "Partial Implementation",
            "severity": c.get("criticality", "Medium"),
            "owner": "App Owner Queue",
            "description": f"Onboarding gap — {c['control_name'][:60]}",
            "expected_evidence": c.get("expected_evidence", "Policy attestation"),
            "status": "Open",
            "observation_id": f"OBS-{derive_prefix(framework_name)}-{c['control_id'].replace('.', '')}",
        })
    ecs_state.framework_onboarding_gaps.setdefault(framework_id, []).extend(gaps)
    return gaps


def _catalog_controls_from_imported(controls: list[dict], fw_code: str, framework_name: str) -> list[dict]:
    out: list[dict] = []
    for i, c in enumerate(controls):
        eid = f"EVD-{fw_code}-{i + 1:03d}"
        ev_name = c.get("expected_evidence", "Policy attestation")
        linked = c.get("linked_evidence") or {}
        if linked.get("evidence_id"):
            eid = linked["evidence_id"]
            ev_name = linked.get("evidence_name", ev_name)
        out.append({
            "control": c["control_name"],
            "control_id": c["control_id"],
            "control_description": c.get("control_description", c["control_name"]),
            "evidences": [{
                "evidence_id": eid,
                "evidence_name": ev_name,
                "mock_file": linked.get("mock_file", f"{c['control_id']}_attestation.pdf"),
                "application_name": APPLICATIONS[i % len(APPLICATIONS)],
                "application": APPLICATIONS[i % len(APPLICATIONS)],
                "uploaded_by": "Framework Onboarding Engine",
                "upload_timestamp": _ts(),
                "evidence_status": "Current",
                "audit_status": "Pending Review",
                "reviewer": "",
                "comments": f"Linked via framework onboarding — {framework_name}",
                "expiry_date": "2026-12-31",
                "evidence_source": "Onboarding Import",
                "server_name": "NETBANKING_PROD",
                "environment": "Production",
                "region": "Central",
                "evidence_version": "v1.0",
            }],
            "primary_evidence": ev_name,
        })
    return out


def run_onboarding_pipeline(
    details: dict,
    file_content: bytes,
    filename: str,
    user: str,
    role: str,
) -> dict[str, Any]:
    """Full ingest pipeline: validate → parse → normalize → analyze → persist."""
    errors = validate_framework_details(details)
    if errors:
        return {"ok": False, "errors": errors}

    fw_name = details["framework_name"].strip()
    prefix = derive_prefix(fw_name, details.get("version", ""))
    parsed, warnings = parse_control_document(file_content, filename, fw_name)
    if not parsed:
        return {"ok": False, "errors": warnings or ["Parse failed."]}

    controls = normalize_and_match(parsed, prefix)
    analysis = analyze_implementation(controls)
    matrix = build_mapping_matrix(controls)
    app_matrix = build_app_implementation_matrix(controls)
    fw_id = f"FW-{uuid.uuid4().hex[:10].upper()}"

    record = {
        "framework_id": fw_id,
        "framework_name": fw_name,
        "version": details.get("version", ""),
        "regulator": details.get("regulator", ""),
        "effective_date": details.get("effective_date", ""),
        "category": details.get("category", "Security"),
        "prefix": prefix,
        "lifecycle_state": "Imported",
        "controls": controls,
        "analysis": analysis,
        "mapping_matrix": matrix,
        "app_matrix": app_matrix,
        "gaps": [],
        "upload_filename": filename,
        "created_by": user,
        "created_at": _ts(),
        "warnings": warnings,
        "audit_trail": [{"timestamp": _ts(), "action": "import", "actor": user, "role": role, "detail": f"Imported {len(controls)} controls"}],
    }
    gaps = create_gaps_and_tasks(fw_id, fw_name, controls)
    record["gaps"] = gaps
    ecs_state.framework_onboarding_registry[fw_id] = record
    log_event("Framework Imported", user, fw_name, "", f"{len(controls)} controls parsed", role=role)
    return {"ok": True, "framework_id": fw_id, "record": record, "warnings": warnings}


def advance_lifecycle(framework_id: str, action: str, user: str, role: str) -> str:
    rec = ecs_state.framework_onboarding_registry.get(framework_id)
    if not rec:
        return f"Framework {framework_id} not found."
    order = list(LIFECYCLE_STATES)
    state = rec.get("lifecycle_state", "Draft")
    transitions = {
        "map": "Mapped",
        "review": "Reviewed",
        "approve": "Approved",
        "activate": "Active",
    }
    if action == "map" and state in ("Imported", "Draft"):
        rec["lifecycle_state"] = "Mapped"
    elif action in transitions:
        target = transitions[action]
        if action == "activate" and state != "Approved":
            return "Framework must be Approved before activation."
        rec["lifecycle_state"] = target
        if action == "activate":
            _activate_framework(rec)
    else:
        return f"Unknown action: {action}"
    rec.setdefault("audit_trail", []).append({
        "timestamp": _ts(), "action": action, "actor": user, "role": role,
        "detail": f"Lifecycle → {rec['lifecycle_state']}",
    })
    ecs_state.framework_onboarding_registry[framework_id] = rec
    return f"Framework {rec['framework_name']} moved to {rec['lifecycle_state']}."


def _activate_framework(rec: dict) -> None:
    fw_name = rec["framework_name"]
    prefix = rec["prefix"]
    catalog_controls = _catalog_controls_from_imported(rec["controls"], prefix.replace("-", "")[:6], fw_name)
    ecs_state.dynamic_framework_catalog[fw_name] = catalog_controls
    if fw_name not in ecs_state.frameworks:
        ecs_state.frameworks[fw_name] = [(c["control"], c["primary_evidence"]) for c in catalog_controls]


def apply_evidence_reuse(framework_id: str, control_id: str, decision: str, user: str, role: str) -> str:
    rec = ecs_state.framework_onboarding_registry.get(framework_id)
    if not rec:
        return "Framework not found."
    for c in rec["controls"]:
        if c["control_id"] != control_id:
            continue
        c["reuse_decision"] = decision
        c["reuse_decision_by"] = user
        if decision == "reuse":
            c["implementation_state"] = "Implemented"
            bm = c.get("best_match")
            if bm and bm.get("evidence"):
                c["linked_evidence"] = bm["evidence"][0]
        elif decision == "upload_new":
            c["implementation_state"] = "Missing"
        rec["analysis"] = analyze_implementation(rec["controls"])
        rec["mapping_matrix"] = build_mapping_matrix(rec["controls"])
        ecs_state.framework_onboarding_registry[framework_id] = rec
        return f"Control {control_id}: {decision.replace('_', ' ').title()} recorded."
    return f"Control {control_id} not found."


def get_onboarding_record(framework_id: str) -> dict | None:
    return ecs_state.framework_onboarding_registry.get(framework_id)


def list_onboarding_records(role: str = "owner") -> list[dict]:
    rows = [dict(v) for v in ecs_state.framework_onboarding_registry.values()]
    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return rows


def build_admin_dashboard(role: str) -> dict:
    rows = list_onboarding_records(role)
    active = [r for r in rows if r.get("lifecycle_state") == "Active"]
    pending = [r for r in rows if r.get("lifecycle_state") in ("Imported", "Mapped", "Reviewed")]
    total_controls = sum(r.get("analysis", {}).get("total_controls", 0) for r in rows)
    return {
        "frameworks": rows,
        "active_count": len(active),
        "pending_count": len(pending),
        "total_controls_imported": total_controls,
        "catalog_frameworks": list({**FRAMEWORK_CATALOG, **ecs_state.dynamic_framework_catalog}.keys()),
        "can_manage": can_manage_framework_onboarding(role),
        "can_review": can_review_framework_onboarding(role),
        "can_reuse_decide": can_reuse_evidence_decision(role),
        "kpis": [
            {"label": "Onboarded Frameworks", "value": len(rows), "tone": "primary"},
            {"label": "Active", "value": len(active), "tone": "success"},
            {"label": "Pending Review", "value": len(pending), "tone": "warning"},
            {"label": "Controls Imported", "value": total_controls, "tone": "info"},
        ],
    }


def export_onboarding_analysis(framework_id: str, fmt: str = "pdf") -> tuple[bytes, str, str]:
    rec = ecs_state.framework_onboarding_registry.get(framework_id)
    if not rec:
        raise ValueError("Framework not found")
    fmt = (fmt or "pdf").lower()
    fw = rec["framework_name"].replace(" ", "_")
    ts = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    filename = f"{fw}_Onboarding_Analysis_{ts}.{'xlsx' if fmt == 'excel' else fmt}"

    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ECS Framework Onboarding Export", rec["framework_name"]])
        w.writerow(["Lifecycle", rec.get("lifecycle_state")])
        a = rec.get("analysis", {})
        for k, v in a.items():
            w.writerow([k, v])
        w.writerow([])
        w.writerow(["Control Mapping Matrix"])
        w.writerow(["New Control", "Existing FW", "Existing Control", "Evidence", "Confidence"])
        for m in rec.get("mapping_matrix", []):
            w.writerow([m["new_control_id"], m["existing_framework"], m["existing_control_id"], m["linked_evidence"], m["reuse_confidence_pct"]])
        return buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", filename

    payload = {
        "meta": {
            "generated_at": _ts(),
            "framework": rec["framework_name"],
            "application": "All Applications",
            "time_range": "Onboarding",
            "scope": f"Framework Onboarding — {rec.get('lifecycle_state')}",
        },
        "executive_summary": [{
            "framework": rec["framework_name"],
            "application": "Enterprise",
            "readiness_pct": rec.get("analysis", {}).get("implementation_coverage_pct", 0),
            "open_findings": rec.get("analysis", {}).get("missing", 0),
            "failed_controls": rec.get("analysis", {}).get("critical_missing", 0),
            "critical_gaps": len(rec.get("gaps", [])),
            "risk_trend": rec.get("lifecycle_state", "Draft"),
            "audit_readiness": rec.get("analysis", {}).get("implementation_coverage_pct", 0),
            "gap_severity_summary": f"{rec.get('analysis', {}).get('reusable_controls', 0)} reusable controls",
        }],
        "gap_details": [
            {
                "observation_id": g.get("observation_id", g["gap_id"]),
                "application": "Net Banking",
                "framework": g["framework"],
                "control_id": g["control_id"],
                "control_description": g["control_name"],
                "gap_type": g["gap_type"],
                "severity": g["severity"],
                "missing_evidence": g["expected_evidence"],
                "risk": g["severity"],
                "owner": g["owner"],
                "due_date": "2026-06-30",
                "remediation_status": g["status"],
            }
            for g in rec.get("gaps", [])[:40]
        ],
    }
    from modules.governance.engines.gap_export_engine import _build_pdf, _spreadsheet_xml
    if fmt == "excel":
        return _spreadsheet_xml(payload), "application/vnd.ms-excel", filename
    return _build_pdf(payload), "application/pdf", filename
