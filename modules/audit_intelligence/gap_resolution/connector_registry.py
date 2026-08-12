"""Field -> connector candidate mapping for gap resolution.

Reuses the existing enterprise integration registry
(:mod:`modules.operations.integrations`) and its safe dry-run entry point
(:func:`modules.audit_intelligence.services.connector_workbench.dry_run`) —
no new connector logic, no live network calls. This module only adds the
mapping of "which missing evidence field could plausibly be supplied by
which connector(s)", which the completeness-detection path needs in order
to decide whether a gap has zero, one, or many candidate sources.
"""

from __future__ import annotations

from typing import Any

from modules.audit_intelligence.services import connector_workbench

#: Missing-evidence field id -> ordered list of connector names (from
#: modules.operations.integrations.ADAPTER_MODULES) that could plausibly
#: supply it. An empty list means no connector in the registry covers the
#: field at all. More than one entry means the field is ambiguous — the
#: deterministic path has no declared priority/tie-breaker among them.
FIELD_CONNECTOR_MAP: dict[str, list[str]] = {
    # Unambiguous — exactly one plausible source.
    "cmdb_asset_record": ["servicenow_cmdb"],
    "grc_control_mapping": ["archer"],
    "sast_scan_result": ["checkmarx"],
    "code_quality_report": ["sonarqube"],
    "file_integrity_report": ["tripwire"],
    "mailbox_retention_record": ["outlook_graph"],
    # Ambiguous — two or more plausible sources, no declared winner.
    "vuln_scan_report": [
        "nessus", "qualys", "aws_connector", "gcp_connector",
        "azure_connector", "prisma_cloud",
    ],
    "ci_build_evidence": ["github", "jenkins", "azure_devops"],
    "policy_document": ["sharepoint_graph", "confluence", "jira"],
    # No connector covers these at all (also absent from ADAPTER_MODULES).
    "backup_restore_test_log": [],
    "access_review_certification": [],
    "patch_compliance_matrix": [],
    "tde_attestation_report": [],
    "siem_use_case_export": [],
    "firewall_rule_export": [],
}


def candidates_for_field(field: str) -> list[str]:
    """Return the connector names that could plausibly supply `field`."""
    return list(FIELD_CONNECTOR_MAP.get(field, []))


def dry_run_fetch(connector_name: str) -> dict[str, Any]:
    """Config-only, no-network readiness check for one connector.

    Thin pass-through to the connector test workbench's `dry_run` — kept
    here so the gap-resolution code has a single import surface and so a
    future agent loop can swap in `parser_test` (mock-transport execution)
    without touching callers.
    """
    return connector_workbench.dry_run(connector_name)
