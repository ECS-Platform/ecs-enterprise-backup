"""Evidence discovery readiness (Phase 5.3).

Deterministically determines whether ECS can discover evidence from a source, by
comparing the evidence categories requested for collection against the categories
the connector type is known to support. No network calls, no LLM.

Score 0-100 = proportion of requested categories that are discoverable (or, when
nothing specific is requested, the breadth of the connector's known capability).
"""

from __future__ import annotations

from typing import Mapping

from app.connectivity.models import EvidenceDiscoveryReadiness, Outcome

# Built-in capability map (mirrors config/connectivity.yaml discovery_capabilities).
DEFAULT_DISCOVERY_CAPABILITIES: dict[str, list[str]] = {
    "jira": ["projects", "issues", "stories", "epics", "approvals", "comments", "workflow_states"],
    "github": ["repositories", "commits", "pull_requests", "review_approvals", "branch_protections", "releases"],
    "gitlab": ["repositories", "commits", "merge_requests", "approvals", "pipelines"],
    "azure_devops": ["repositories", "pull_requests", "pipelines", "releases"],
    "confluence": ["spaces", "pages", "attachments", "architecture_documents", "policies"],
    "sharepoint": ["policies", "documents", "evidence_files"],
    "servicenow": ["incidents", "change_requests", "problem_records", "cab_approvals"],
    "gitea": ["repositories", "commits", "pull_requests", "review_approvals", "branch_protections", "releases"],
    "sonarqube": ["quality_gates", "coverage", "vulnerabilities", "code_smells", "security_hotspots"],
    "jenkins": ["jobs", "builds", "test_results", "artifacts"],
    "teams": ["governance_channels", "approval_messages", "meeting_artifacts"],
    "figma": ["design_projects", "design_files", "design_reviews", "prototypes"],
    "prisma": ["cloud_findings", "compliance_violations", "risk_reports"],
}


def assess_discovery(connector_type: str, requested: list[str] | None = None, *,
                     capabilities: Mapping[str, list[str]] | None = None
                     ) -> EvidenceDiscoveryReadiness:
    """Assess evidence discovery readiness for a connector type. Never raises."""
    caps_map = dict(DEFAULT_DISCOVERY_CAPABILITIES)
    if capabilities:
        caps_map.update({k: list(v) for k, v in capabilities.items()})

    ctype = str(connector_type or "").strip().lower()
    supported = caps_map.get(ctype)

    if supported is None:
        return EvidenceDiscoveryReadiness(
            connector_type=ctype, outcome=Outcome.WARNING,
            supported_categories=[], requested_categories=list(requested or []),
            discoverable_categories=[], unsupported_categories=list(requested or []),
            score=0.0, detail=f"unknown connector type '{ctype}' -> no known discovery capability")

    requested = [str(r).strip().lower() for r in (requested or []) if str(r).strip()]
    supported_lower = [s.lower() for s in supported]

    if not requested:
        # Nothing requested -> readiness reflects breadth of capability (capped full).
        return EvidenceDiscoveryReadiness(
            connector_type=ctype, outcome=Outcome.PASS,
            supported_categories=list(supported), requested_categories=[],
            discoverable_categories=list(supported), unsupported_categories=[],
            score=100.0 if supported else 0.0,
            detail=f"{len(supported)} evidence categories discoverable")

    discoverable = [r for r in requested if r in supported_lower]
    unsupported = [r for r in requested if r not in supported_lower]
    total = len(requested) or 1
    score = round(100.0 * len(discoverable) / total, 1)

    if not unsupported:
        outcome = Outcome.PASS
        detail = "all requested evidence categories are discoverable"
    elif discoverable:
        outcome = Outcome.WARNING
        detail = "some requested categories not supported: " + ", ".join(unsupported)
    else:
        outcome = Outcome.FAIL
        detail = "no requested categories are discoverable"

    return EvidenceDiscoveryReadiness(
        connector_type=ctype, outcome=outcome, supported_categories=list(supported),
        requested_categories=requested, discoverable_categories=discoverable,
        unsupported_categories=unsupported, score=score, detail=detail)
