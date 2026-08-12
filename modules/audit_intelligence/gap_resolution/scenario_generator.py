"""Synthetic gap-scenario generator for completeness-detection baselining.

Produces ~24 deterministic scenarios across four tiers, built from the same
demo-data patterns already used by `missing_evidence_engine` (banking
applications, framework catalog, control-id prefixes) and the connector
names in `modules.operations.integrations.ADAPTER_MODULES` (via
`connector_registry`). No LLM, no network, no DB — pure synthetic fixture
generation so the baseline runner (and later the agent loop) has a stable,
version-controlled input.

Tiers:
  A — single missing field, one unambiguous connector source.
  B — wrong format / stale evidence: first fetch fails, retry with
      different params succeeds.
  C — missing field, multiple plausible connector sources, no clear winner.
  D — missing field, no connector has it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from modules.audit_intelligence.gap_resolution.connector_registry import candidates_for_field
from modules.shared.services.ecs_state import BANKING_APPLICATIONS

DEFAULT_FIXTURE_PATH = Path("data/fixtures/gap_scenarios.json")

# Single-source fields (used for tiers A and B — same field pool, different
# failure/retry behavior layered on top by each tier's builder).
_SINGLE_SOURCE_FIELDS = [
    "cmdb_asset_record",
    "grc_control_mapping",
    "sast_scan_result",
    "code_quality_report",
    "file_integrity_report",
    "mailbox_retention_record",
]

# Ambiguous fields (2+ candidate connectors, no declared winner) — cycled
# twice to produce 6 tier-C scenarios from 3 field types.
_AMBIGUOUS_FIELDS = [
    "vuln_scan_report",
    "ci_build_evidence",
    "policy_document",
]

# Fields with zero connector coverage.
_UNCOVERED_FIELDS = [
    "backup_restore_test_log",
    "access_review_certification",
    "patch_compliance_matrix",
    "tde_attestation_report",
    "siem_use_case_export",
    "firewall_rule_export",
]

_FRAMEWORKS = ["PCI DSS", "DPSC", "OS Baselining", "AppSec", "VAPT", "ITPP"]


def _seed_hash(key: str) -> str:
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _app(i: int) -> str:
    return BANKING_APPLICATIONS[i % len(BANKING_APPLICATIONS)]


def _framework(i: int) -> str:
    return _FRAMEWORKS[i % len(_FRAMEWORKS)]


def _control_id(tier: str, i: int) -> str:
    return f"{tier}GAP-{i + 1:03d}"


def _base_evidence(tier: str, i: int, field: str) -> dict[str, Any]:
    control_id = _control_id(tier, i)
    app = _app(i)
    framework = _framework(i)
    evidence_id = f"EVID-{_seed_hash(f'{tier}-{i}-{field}')}"
    return {
        "evidence_id": evidence_id,
        "control_id": control_id,
        "application": app,
        "framework": framework,
        "missing_field": field,
        "present_fields": {
            "control_id": control_id,
            "application": app,
            "framework": framework,
            "status": "collected",
        },
    }


def _tier_a_scenario(i: int) -> dict[str, Any]:
    field = _SINGLE_SOURCE_FIELDS[i]
    evidence = _base_evidence("A", i, field)
    candidates = candidates_for_field(field)
    return {
        "id": f"GAP-A-{i + 1:02d}",
        "tier": "A",
        "description": "Single missing field, one unambiguous connector source.",
        "evidence_id": evidence["evidence_id"],
        "evidence": evidence,
        "connector_candidates": candidates,
        "fetch_attempts": [
            {"attempt": 1, "connector": candidates[0], "params": {"mode": "dry-run"}, "result": "success"},
        ],
        "expected_outcome_category": "resolved",
    }


def _tier_b_scenario(i: int) -> dict[str, Any]:
    field = _SINGLE_SOURCE_FIELDS[i]
    evidence = _base_evidence("B", i, field)
    # Stale/wrong-format evidence is already present but fails validation.
    evidence["present_fields"][field] = {"value": "stale-or-wrong-format", "stale": True}
    candidates = candidates_for_field(field)
    connector = candidates[0]
    return {
        "id": f"GAP-B-{i + 1:02d}",
        "tier": "B",
        "description": "Wrong format / stale evidence: first fetch fails, retry with different params succeeds.",
        "evidence_id": evidence["evidence_id"],
        "evidence": evidence,
        "connector_candidates": candidates,
        "fetch_attempts": [
            {"attempt": 1, "connector": connector, "params": {"mode": "dry-run", "format": "legacy"},
             "result": "fail", "reason": "stale_or_wrong_format"},
            {"attempt": 2, "connector": connector, "params": {"mode": "dry-run", "format": "current"},
             "result": "success"},
        ],
        "expected_outcome_category": "resolved",
    }


def _tier_c_scenario(i: int) -> dict[str, Any]:
    field = _AMBIGUOUS_FIELDS[i % len(_AMBIGUOUS_FIELDS)]
    evidence = _base_evidence("C", i, field)
    candidates = candidates_for_field(field)
    return {
        "id": f"GAP-C-{i + 1:02d}",
        "tier": "C",
        "description": "Missing field, multiple plausible connector sources, no clear winner.",
        "evidence_id": evidence["evidence_id"],
        "evidence": evidence,
        "connector_candidates": candidates,
        "fetch_attempts": [],
        "expected_outcome_category": "escalated",
    }


def _tier_d_scenario(i: int) -> dict[str, Any]:
    field = _UNCOVERED_FIELDS[i]
    evidence = _base_evidence("D", i, field)
    return {
        "id": f"GAP-D-{i + 1:02d}",
        "tier": "D",
        "description": "Missing field, no connector has it.",
        "evidence_id": evidence["evidence_id"],
        "evidence": evidence,
        "connector_candidates": [],
        "fetch_attempts": [],
        "expected_outcome_category": "escalated",
    }


def generate_scenarios() -> list[dict[str, Any]]:
    """Build the full 24-scenario set (6 per tier), deterministic across runs."""
    scenarios: list[dict[str, Any]] = []
    for i in range(6):
        scenarios.append(_tier_a_scenario(i))
    for i in range(6):
        scenarios.append(_tier_b_scenario(i))
    for i in range(6):
        scenarios.append(_tier_c_scenario(i))
    for i in range(6):
        scenarios.append(_tier_d_scenario(i))
    return scenarios


def write_fixture(path: Path = DEFAULT_FIXTURE_PATH) -> Path:
    """Generate and persist the scenario fixture as JSON. Returns the path written."""
    scenarios = generate_scenarios()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(scenarios, fh, indent=2, ensure_ascii=True)
    return path


if __name__ == "__main__":
    out = write_fixture()
    print(f"Wrote {len(generate_scenarios())} scenarios to {out}")
