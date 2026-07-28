"""Static validation for phase1_chatbot_retrieval_catalogue.json (evaluation asset only)."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "benchmarks" / "config" / "phase1_chatbot_retrieval_catalogue.json"

ALLOWED_CONTROLS = {
    "PGX-001",
    "PGX-002",
    "PGX-008",
    "PCI-C01",
    "PCI-C02",
    "ITP-C01",
    "ITP-C02",
    "CC-AUDIT_LOGGING",
    "CC-IDENTITY_PRIVILEGED_ACCESS",
    "CC-ENCRYPTION_AT_REST",
    "CC-CERTIFICATE_MANAGEMENT",
    "MBSS-C-01",
    "MBSS-LOG-01",
    "MBSS-POL-LOGGING-01",
    "ZZ-9999",
}
PRESETS = {
    "latest_5_evidences",
    "latest_evidence_by_application",
    "evidence_by_framework",
    "evidence_by_scheduler_run",
    "duplicate_evidence_summary",
    "failed_evidence_collection",
    "evidence_pending_review",
    "recently_approved_evidence",
    "evidence_version_history",
    "expiring_evidence",
    "latest_open_observations",
    "high_risk_open_observations",
    "overdue_observations",
    "observations_by_application",
    "observations_by_framework",
    "rejected_evidence",
    "framework_collection_summary",
    "application_collection_summary",
    "control_without_evidence",
    "common_control_reuse",
    "pgvector_indexing_status",
}
INTENTS = {
    "latest_evidence",
    "pending_app_owner",
    "pending_auditor",
    "approved_evidence",
    "rejected_evidence",
    "missing_evidence",
    "duplicate_attempts",
    "date_range",
    "evidence_details",
    "control_approved",
}
APPS = {None, "Net Banking", "Mobile Banking", "Payments"}
FRAMEWORKS = {None, "PCI DSS", "ITPP"}
CONNECTORS = {None, "predefined_query", "common_controls", "sharepoint_graph"}
PATHS = {"deterministic", "preset", "rag", "no_evidence", "fallback"}


def main() -> int:
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    qs = data["questions"]
    required = set(data["required_category_coverage"])
    errors: list[str] = []

    ids = [q["id"] for q in qs]
    if len(ids) != len(set(ids)):
        errors.append("duplicate question ids")

    cat_counts: Counter[str] = Counter()
    for q in qs:
        for c in q["categories"]:
            cat_counts[c] += 1
    missing_req = required - set(cat_counts)
    if missing_req:
        errors.append(f"missing required categories: {sorted(missing_req)}")

    path_counts = Counter(q["expected_retrieval_path"] for q in qs)
    for path in path_counts:
        if path not in PATHS:
            errors.append(f"invalid path: {path}")

    invented_evd: list[tuple[str, str]] = []
    for q in qs:
        path = q["expected_retrieval_path"]
        qid = q["id"]
        if path == "preset":
            if not q.get("expected_preset_id"):
                errors.append(f"{qid}: preset without expected_preset_id")
            if not q["question"].startswith("@ceq:"):
                errors.append(f"{qid}: preset path but question is not @ceq:")
        if path == "deterministic" and not q.get("expected_deterministic_intent"):
            errors.append(f"{qid}: deterministic without intent")
        if path == "no_evidence" and not q.get("expect_no_evidence_or_refusal"):
            errors.append(f"{qid}: no_evidence path but expect_no_evidence_or_refusal is false")

        ctrl = q.get("expected_control_or_query")
        if ctrl and ctrl not in ALLOWED_CONTROLS:
            errors.append(f"{qid}: unexpected control/query {ctrl}")
        pid = q.get("expected_preset_id")
        if pid and pid not in PRESETS:
            errors.append(f"{qid}: unknown preset {pid}")
        intent = q.get("expected_deterministic_intent")
        if intent and intent not in INTENTS:
            errors.append(f"{qid}: unknown intent {intent}")
        if q.get("expected_application") not in APPS:
            errors.append(f"{qid}: unexpected application {q.get('expected_application')}")
        if q.get("expected_framework") not in FRAMEWORKS:
            errors.append(f"{qid}: unexpected framework {q.get('expected_framework')}")
        if q.get("expected_source_connector") not in CONNECTORS:
            errors.append(f"{qid}: unexpected connector {q.get('expected_source_connector')}")

        for m in re.findall(r"EVD-[A-Z0-9-]+", json.dumps(q)):
            if m == "EVD-99999":
                continue
            if m.startswith("EVD-#"):
                continue
            if re.fullmatch(r"EVD-\d{5}", m):
                invented_evd.append((qid, m))

    if invented_evd:
        errors.append(f"invented concrete EVD ids: {invented_evd}")

    print(f"TOTAL_QUESTIONS={len(qs)}")
    print("CATEGORY_COUNTS")
    for k in sorted(cat_counts):
        print(f"  {k}={cat_counts[k]}")
    print("PATH_COUNTS")
    for k in sorted(path_counts):
        print(f"  {k}={path_counts[k]}")
    print(f"REQUIRED_CATEGORIES_OK={not missing_req}")
    print(f"ERROR_COUNT={len(errors)}")
    for e in errors:
        print(f"ERROR: {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
