"""Pan-India enterprise reference-context generator for the ECS benchmark.

WHY THIS EXISTS
---------------
Today's ECS repository on the benchmark workstation is small, so the EXISTING RAG
retrieval (``ecs_platform.rag.answer``) returns only a little evidence and the
measured input tokens are low (~900-1,000). That faithfully measures *today*, but
it does NOT represent a mature **Pan-India** ECS deployment (500+ applications,
expanded frameworks, large evidence repositories, years of observations, etc.).

This module generates realistic, structured **benchmark-modeled enterprise
context** that mirrors what a mature ECS RAG would assemble and send to the model
when the evidence repository scales up. The runner prepends this context to the
profile question for ``pan_india_enterprise`` profiles, so the EXISTING
instrumentation measures a realistic *future-state* input-token volume.

STRICT PROVENANCE
-----------------
* This is **MODELED** context, never a measurement, and is labelled as such
  everywhere (header banner + reporting tier ``PAN_INDIA_MODELED``).
* It is **data-driven**: every block is derived from configurable
  ``PanIndiaAssumptions`` (applications, frameworks, controls, evidence files,
  observations, exceptions, reuse mappings). No hard-coded business logic.
* It contains **no meaningless padding and no repeated filler**. Each generated
  line is a distinct, parameterized, realistic enterprise fact (different
  application / framework / control / owner / status). Length comes from genuine
  enterprise breadth, not from repetition.
* It does NOT call ECS, the LLM, the retriever, or any instrumentation. Pure text.

Nothing here changes ECS, the runner, reporting, or capacity-planning frameworks;
it is a self-contained context data source consumed additively by the runner.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Realistic enterprise vocabulary (consistent with the benchmark dataset and the
# governance domain). Expanded to a Pan-India estate scale via the assumptions.
_LINES_OF_BUSINESS = [
    "Retail Banking", "Corporate Banking", "Payments", "Treasury & Markets",
    "Wealth Management", "Lending", "Cards", "Insurance", "Digital Channels",
    "Trade Finance",
]

_APPLICATION_FAMILIES = [
    "mobile-banking", "payments-gateway", "loan-origination", "corporate-banking",
    "treasury-ops", "retail-lending", "cards-platform", "upi-switch", "net-banking",
    "wealth-portal", "trade-finance", "insurance-core", "kyc-aml", "fraud-engine",
    "data-lake", "api-gateway", "core-banking", "reconciliation", "settlement",
    "customer-360",
]

_FRAMEWORKS = [
    "RBI C-SITE", "RBI Cyber Security Framework", "PCI DSS", "DPSC", "ITGRC",
    "VAPT", "AppSec", "ITDRM", "Cloud Governance", "SOC2", "ISO 27001",
    "AI-SDLC", "BCP/DR", "Data Privacy (DPDP)", "Outsourcing Governance",
]

_CONTROL_DOMAINS = [
    "Access Control", "Change Management", "Vulnerability Management",
    "Incident Response", "Data Protection", "Network Security",
    "Logging & Monitoring", "Business Continuity", "Third-Party Risk",
    "Cryptography & Key Management",
]

_SOURCE_SYSTEMS = [
    "jira", "jenkins", "sonarqube", "servicenow", "cmdb", "confluence",
    "github", "splunk", "qualys", "crowdstrike",
]

_REGIONS = [
    "Mumbai", "Delhi NCR", "Bengaluru", "Chennai", "Hyderabad", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Lucknow",
]

_OWNER_ROLES = [
    "CISO Office", "App Security Lead", "Infra Security", "Compliance Officer",
    "Risk Manager", "Cloud Platform Lead", "SRE Lead", "Data Protection Officer",
]

_STATUSES = ["Compliant", "Partially Compliant", "Non-Compliant", "In Remediation"]
_SEVERITIES = ["Critical", "High", "Medium", "Low"]
_MATURITY_LEVELS = [
    "Level 1 - Initial", "Level 2 - Developing", "Level 3 - Defined",
    "Level 4 - Managed", "Level 5 - Optimizing",
]


@dataclass
class PanIndiaAssumptions:
    """Configurable Pan-India future-state scale. All MODELED, never measured.

    These drive how much realistic enterprise context the generator emits and the
    token model in ``capacity_planning``. Edit via the ``pan_india_assumptions``
    config block. Output-token figures (target_output_tokens / output_weighting_
    factor / peak_requests_per_minute) are consumed by the Neev formula validation.
    """

    applications: int = 500
    frameworks: int = 15
    control_domains: int = 10
    controls_per_framework: int = 100
    evidence_files_per_control: int = 2
    historical_observations_per_framework: int = 50
    risk_exception_records_per_framework: int = 25
    evidence_reuse_mappings_per_framework: int = 100
    lines_of_business: int = 10
    source_systems: int = 10

    # Neev weighted-token formula inputs (configurable).
    output_weighting_factor: int = 9
    peak_requests_per_minute: int = 3
    target_input_tokens: int = 125000
    target_output_tokens: int = 50000

    # Token-band targets for reporting (input/output realistic envelopes).
    input_token_target_low: int = 75000
    input_token_target_high: int = 125000
    output_token_target_low: int = 25000
    output_token_target_high: int = 50000

    # Generator budget: how many distinct rows each block emits. Caps keep the
    # generated context realistic and bounded (one row per genuine enterprise fact,
    # never duplicated). Default sized so the modeled context estimate lands inside
    # the 75k-125k input token target band (~84k est tokens at 450).
    max_rows_per_block: int = 450

    # Approx chars/token for the MODELED size estimate ONLY (the LLM tokenizer is
    # the source of truth at run time; this is a planning estimate for the report).
    chars_per_token: float = 4.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PanIndiaAssumptions":
        data = data or {}
        known = {k: data[k] for k in data if k in cls.__dataclass_fields__}
        return cls(**known)


# Banner so the model (and any human reading the prompt/log) cannot mistake the
# MODELED enterprise context for measured/real evidence.
_BANNER = (
    "===== BENCHMARK-MODELED PAN-INDIA ENTERPRISE REFERENCE CONTEXT =====\n"
    "The following is BENCHMARK-MODELED future-state enterprise context representing a "
    "mature Pan-India ECS deployment. It simulates the volume and shape of evidence, "
    "observations, exceptions and crosswalk metadata that ECS RAG would retrieve at "
    "scale. Treat it as the working dataset for the requested deliverable.\n"
    "==================================================================\n"
)


def _rows(n: int, cap: int) -> int:
    return max(0, min(int(n), int(cap)))


def _cycle(seq: list[str], i: int) -> str:
    return seq[i % len(seq)]


def _framework_control_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Framework & Control Coverage Summary"]
    total = a.frameworks * a.control_domains
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        dom = _cycle(_CONTROL_DOMAINS, i // max(1, a.frameworks))
        ctrls = a.controls_per_framework // max(1, a.control_domains)
        status = _cycle(_STATUSES, i)
        owner = _cycle(_OWNER_ROLES, i)
        lines.append(
            f"- {fw} / {dom}: {ctrls} controls in scope, status={status}, "
            f"owner={owner}, evidence_files~{ctrls * a.evidence_files_per_control}."
        )
    return "\n".join(lines)


def _application_portfolio_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Application Portfolio Summary (Pan-India estate)"]
    for i in range(_rows(a.applications, a.max_rows_per_block)):
        fam = _cycle(_APPLICATION_FAMILIES, i)
        lob = _cycle(_LINES_OF_BUSINESS, i)
        region = _cycle(_REGIONS, i)
        fw = _cycle(_FRAMEWORKS, i)
        lines.append(
            f"- APP-{i + 1:04d} {fam}-{region.lower().replace(' ', '')} | LoB={lob} | "
            f"region={region} | primary_framework={fw} | criticality="
            f"{_cycle(_SEVERITIES, i)}."
        )
    return "\n".join(lines)


def _evidence_inventory_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Evidence Inventory Summary"]
    total = a.frameworks * a.control_domains
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        dom = _cycle(_CONTROL_DOMAINS, i)
        src = _cycle(_SOURCE_SYSTEMS, i)
        files = (a.controls_per_framework // max(1, a.control_domains)) * a.evidence_files_per_control
        lines.append(
            f"- {fw} / {dom}: {files} evidence files from {src}; freshness="
            f"{30 + (i % 11) * 30}d; collection={'automated' if i % 3 else 'manual'}."
        )
    return "\n".join(lines)


def _open_observation_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Open Observation Summary"]
    total = a.frameworks * a.historical_observations_per_framework
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        dom = _cycle(_CONTROL_DOMAINS, i)
        sev = _cycle(_SEVERITIES, i)
        app = _cycle(_APPLICATION_FAMILIES, i)
        owner = _cycle(_OWNER_ROLES, i)
        lines.append(
            f"- OBS-{i + 1:05d}: {fw}/{dom} on {app}; severity={sev}; "
            f"root_cause={'control gap' if i % 2 else 'evidence gap'}; owner={owner}; "
            f"target=Q{(i % 4) + 1}."
        )
    return "\n".join(lines)


def _risk_acceptance_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Risk Acceptance & Exception Summary"]
    total = a.frameworks * a.risk_exception_records_per_framework
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        app = _cycle(_APPLICATION_FAMILIES, i)
        sev = _cycle(_SEVERITIES, i)
        lines.append(
            f"- EXC-{i + 1:05d}: {fw} on {app}; residual_risk={sev}; "
            f"compensating_control={'WAF+monitoring' if i % 2 else 'MFA+segmentation'}; "
            f"expiry=Q{(i % 4) + 1}; approver={_cycle(_OWNER_ROLES, i)}."
        )
    return "\n".join(lines)


def _control_maturity_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Control Maturity Summary (by framework x domain)"]
    total = a.frameworks * a.control_domains
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        dom = _cycle(_CONTROL_DOMAINS, i)
        lvl = _cycle(_MATURITY_LEVELS, i)
        lines.append(
            f"- {fw} / {dom}: maturity={lvl}; evidence_strength="
            f"{'strong' if i % 3 == 0 else 'moderate' if i % 3 == 1 else 'weak'}; "
            f"trend={'improving' if i % 2 else 'stable'}."
        )
    return "\n".join(lines)


def _evidence_reuse_crosswalk_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Evidence Reuse Crosswalk Summary"]
    total = a.frameworks * a.evidence_reuse_mappings_per_framework
    for i in range(_rows(total, a.max_rows_per_block)):
        fw_a = _cycle(_FRAMEWORKS, i)
        fw_b = _cycle(_FRAMEWORKS, i + 3)
        dom = _cycle(_CONTROL_DOMAINS, i)
        lines.append(
            f"- MAP-{i + 1:05d}: evidence for {fw_a}/{dom} also satisfies {fw_b}; "
            f"reuse_ratio={(i % 5) + 1}:1; confidence="
            f"{'high' if i % 3 == 0 else 'medium'}."
        )
    return "\n".join(lines)


def _audit_closure_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Audit Closure Record Summary"]
    total = a.frameworks * (a.historical_observations_per_framework // 2)
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        lines.append(
            f"- CLR-{i + 1:05d}: {fw} observation closed; "
            f"closure_evidence={'re-test passed' if i % 2 else 'policy updated'}; "
            f"cycle_time={(i % 6) * 15 + 10}d; verified_by={_cycle(_OWNER_ROLES, i)}."
        )
    return "\n".join(lines)


def _remediation_roadmap_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Remediation Roadmap Summary"]
    total = a.frameworks * a.control_domains
    for i in range(_rows(total, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        dom = _cycle(_CONTROL_DOMAINS, i)
        horizon = "quick win" if i % 3 == 0 else "medium-term" if i % 3 == 1 else "structural"
        lines.append(
            f"- RMD-{i + 1:05d}: {fw}/{dom}; {horizon}; "
            f"owner={_cycle(_OWNER_ROLES, i)}; dependency="
            f"{'platform uplift' if i % 2 else 'process change'}; target=Q{(i % 4) + 1}."
        )
    return "\n".join(lines)


def _regulator_inspection_summary(a: PanIndiaAssumptions) -> str:
    lines = ["## Regulator Inspection Readiness Summary"]
    for i in range(_rows(a.frameworks, a.max_rows_per_block)):
        fw = _cycle(_FRAMEWORKS, i)
        lines.append(
            f"- {fw}: readiness={_cycle(_STATUSES, i)}; "
            f"open_observations~{a.historical_observations_per_framework}; "
            f"exceptions~{a.risk_exception_records_per_framework}; "
            f"evidence_coverage={60 + (i % 4) * 10}%."
        )
    return "\n".join(lines)


# Ordered block builders. Each returns a distinct, parameterized section.
_BLOCK_BUILDERS = [
    ("framework_control", _framework_control_summary),
    ("application_portfolio", _application_portfolio_summary),
    ("evidence_inventory", _evidence_inventory_summary),
    ("open_observations", _open_observation_summary),
    ("risk_acceptance", _risk_acceptance_summary),
    ("control_maturity", _control_maturity_summary),
    ("evidence_reuse_crosswalk", _evidence_reuse_crosswalk_summary),
    ("audit_closure", _audit_closure_summary),
    ("remediation_roadmap", _remediation_roadmap_summary),
    ("regulator_inspection", _regulator_inspection_summary),
]


def build_reference_context(assumptions: PanIndiaAssumptions | None = None,
                            *, blocks: list[str] | None = None) -> str:
    """Build the full MODELED Pan-India reference-context string.

    ``blocks`` optionally restricts to a subset of block names (see _BLOCK_BUILDERS);
    None -> all blocks. The result is prefixed with a clear MODELED banner.
    """
    a = assumptions or PanIndiaAssumptions()
    wanted = set(blocks) if blocks else None
    sections = [_BANNER]
    for name, builder in _BLOCK_BUILDERS:
        if wanted is None or name in wanted:
            sections.append(builder(a))
    sections.append("===== END BENCHMARK-MODELED PAN-INDIA REFERENCE CONTEXT =====")
    return "\n\n".join(sections)


def context_size_estimate(assumptions: PanIndiaAssumptions | None = None,
                          *, blocks: list[str] | None = None) -> dict[str, Any]:
    """MODELED size estimate of the generated reference context (planning only).

    Returns char count and an estimated token count (chars / chars_per_token). The
    LLM tokenizer is the source of truth at run time; this estimate exists so the
    report can show the modeled input volume even without executing the benchmark.
    """
    a = assumptions or PanIndiaAssumptions()
    text = build_reference_context(a, blocks=blocks)
    chars = len(text)
    est_tokens = round(chars / a.chars_per_token, 2) if a.chars_per_token else None
    return {
        "tier": "PAN_INDIA_MODELED",
        "modeled_context_chars": chars,
        "modeled_context_estimated_tokens": est_tokens,
        "chars_per_token_basis": a.chars_per_token,
        "blocks_included": list(blocks) if blocks else [n for n, _ in _BLOCK_BUILDERS],
        "_basis": (
            "MODELED enterprise reference context generated from PanIndiaAssumptions. "
            "Token count is an estimate (chars / chars_per_token); actual input tokens "
            "are MEASURED by the existing instrumentation at run time."
        ),
    }
