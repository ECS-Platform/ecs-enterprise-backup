"""Realistic ECS prompt factory for the Neev validation benchmark.

WHY THIS EXISTS
---------------
The Neev capacity-planning assumption (125,000 input / 50,000 output tokens per
request, 9x output weighting, 3 RPM) is a *planning assumption*. This factory
builds realistic ECS assessment prompts so the benchmark can MEASURE the real
token shape of an ECS request and test — objectively — whether that assumption is
realistic, conservative, over-tokenized, or under-estimated.

CORE PRINCIPLE
--------------
The benchmark does NOT measure the size of the evidence repository. It measures
the FINAL prompt sent to the LLM *after retrieval and prompt construction*:

    application metadata + framework/control catalog + RETRIEVED evidence
    summaries + observation history + VAPT findings + baseline status + risk
    exceptions + audit comments + remediation status + executive instruction.

Repository size (200 / 300 / 500 / 600 applications) affects retrieval METADATA
and scenario scale, but never dumps all application evidence into the prompt —
only the retrieved context enters the prompt (``evidence_files_per_framework``).

PROVENANCE / GUARDRAILS
-----------------------
* Synthetic but realistic banking / audit content. No lorem ipsum, no meaningless
  repeated filler, no artificial token inflation. Every line is a distinct,
  parameterized enterprise fact (different app / framework / control / finding).
* Pure standard library and self-contained, so the dry-run path (prompt build +
  token estimate + reports) runs on an 8 GB workstation WITHOUT Docker / Ollama /
  Postgres / yaml. The real ECS system prompt is reused when importable; otherwise
  a representative copy is used and the source is recorded for transparency.
* Mirrors the EXISTING ECS prompt shape (``ecs_platform.llm_engine.prompt_builder``):
  numbered, citable evidence blocks ``[E1] source=... type=... app=... uid=...``.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Any

# Representative copy of the ECS system prompt (ecs_platform.llm_engine.prompt_builder
# .SYSTEM_PROMPT). The real one is reused at run time when importable; this copy keeps
# the dry-run path dependency-free and the input-token shape representative.
_BUNDLED_SYSTEM_PROMPT = (
    "You are the ECS Evidence Assistant for an enterprise GRC (governance, risk, "
    "and compliance) platform. You answer questions strictly using the evidence "
    "context provided. Rules:\n"
    "1. Use ONLY the supplied evidence and ECS governance facts. Never invent facts, "
    "controls, systems, applications, or evidence ids.\n"
    "2. Every factual claim must cite its evidence id like [E1], [E3].\n"
    "3. If the supplied context does not contain the answer, reply with EXACTLY this "
    "sentence and nothing else: \"No evidence found in ECS repository.\"\n"
    "4. Be concise and audit-ready. Prefer specifics (counts, owners, statuses, dates).\n"
    "5. Do not include chain-of-thought or <think> sections; output only the final answer.\n"
)


def load_system_prompt() -> tuple[str, str]:
    """Return ``(system_prompt, source)``. Reuse the REAL ECS system prompt when it
    imports cleanly (full-run on the 16 GB box); otherwise fall back to the bundled
    representative copy (dry-run on an 8 GB box). The source is recorded in reports so
    any difference in system-prompt chars is transparent."""
    try:
        from ecs_platform.llm_engine.prompt_builder import SYSTEM_PROMPT  # type: ignore
        if SYSTEM_PROMPT:
            return SYSTEM_PROMPT, "ecs_platform.llm_engine.prompt_builder.SYSTEM_PROMPT"
    except Exception:  # noqa: BLE001 - dependency-free fallback for dry-run
        pass
    return _BUNDLED_SYSTEM_PROMPT, "bundled_representative_copy"


# --------------------------------------------------------------------------- #
# Realistic banking / audit vocabulary (parameterized, never repeated filler).
# --------------------------------------------------------------------------- #
_APP_FAMILIES = [
    "upi-switch", "payments-gateway", "core-banking", "net-banking", "mobile-banking",
    "loan-origination", "cards-platform", "treasury-ops", "trade-finance", "kyc-aml",
    "fraud-engine", "reconciliation", "settlement", "wealth-portal", "customer-360",
]
_LOBS = ["Payments", "Retail Banking", "Corporate Banking", "Lending", "Cards",
         "Treasury & Markets", "Wealth Management", "Trade Finance", "Insurance"]
_REGIONS = ["Mumbai", "Delhi NCR", "Bengaluru", "Chennai", "Hyderabad", "Pune",
            "Kolkata", "Ahmedabad"]
_CRITICALITY = ["Critical", "High", "Medium"]
_OWNERS = ["CISO Office", "App Security Lead", "Infra Security", "Compliance Officer",
           "Risk Manager", "Cloud Platform Lead", "SRE Lead", "Data Protection Officer"]
_FRAMEWORKS = [
    "RBI Cyber Security Framework", "RBI C-SITE", "PCI DSS 4.0", "DPSC",
    "ISO 27001:2022", "SOC 2 Type II", "NIST CSF", "Data Privacy (DPDP Act)",
    "Cloud Security Baseline", "Application Security (AppSec)",
]
_CONTROL_DOMAINS = [
    "Access Control", "Change Management", "Vulnerability Management",
    "Incident Response", "Data Protection", "Network Security",
    "Logging & Monitoring", "Business Continuity", "Third-Party Risk",
    "Cryptography & Key Management",
]
_CONTROL_INTENTS = [
    "Enforce MFA for all privileged access to production banking systems with quarterly recertification",
    "Require CAB approval and segregation of duties for all production changes",
    "Remediate critical vulnerabilities within 15 days per the risk-based SLA",
    "Maintain a tested incident response runbook with 24x7 escalation",
    "Encrypt cardholder and PII data at rest (AES-256) and in transit (TLS 1.2+)",
    "Segment the cardholder data environment from the corporate network",
    "Centralize security logs with 12-month retention and tamper protection",
    "Validate DR failover for tier-1 applications at least semi-annually",
    "Assess outsourced service providers annually against the security baseline",
    "Manage cryptographic keys in an HSM with documented rotation",
]
_SOURCE_SYSTEMS = ["splunk", "qualys", "servicenow", "jira", "github", "sonarqube",
                   "crowdstrike", "cmdb", "confluence", "jenkins"]
_OBJECT_TYPES = ["access-review", "scan-report", "change-record", "incident",
                 "config-baseline", "policy", "pentest-report", "dr-test", "audit-note"]
_STATUSES = ["Compliant", "Partially Compliant", "Non-Compliant", "In Remediation"]
_SEVERITIES = ["Critical", "High", "Medium", "Low"]

# Sentence fragments used to compose realistic, distinct evidence excerpts. Combined
# with per-item parameters (app/framework/control/index) so no two lines are identical.
_EVIDENCE_FACTS = [
    "Privileged access review covered {n} admin accounts; {k} flagged for stale entitlements with remediation tickets raised.",
    "MFA enforced on {pct}% of administrative logins; {k} break-glass accounts pending hardware-token rollout.",
    "Vulnerability scan returned {n} findings ({k} high/critical); mean time-to-remediate tracked against the {sla}-day SLA.",
    "Change records show {n} production changes this quarter; {k} emergency changes pending retrospective CAB approval.",
    "Encryption posture validated: TLS {tls} on external endpoints, AES-256 at rest; {k} legacy endpoints on the migration backlog.",
    "Log pipeline ingesting {n} GB/day with {months}-month retention; tamper-evident storage confirmed for in-scope sources.",
    "DR failover test completed with RTO {rto}h / RPO {rpo}h; {k} tier-1 dependencies require runbook updates.",
    "Network segmentation verified between the cardholder data environment and corporate zones; {k} firewall exceptions under review.",
    "Third-party assessment of {n} providers complete; {k} flagged for overdue SOC 2 reports.",
    "Key management audit confirms HSM-backed rotation every {months} months; {k} service keys outside the rotation policy.",
]


@dataclass
class PromptSpec:
    """Drives one realistic ECS assessment prompt. All counts are scenario-derived;
    repository_apps is METADATA only (it scales retrieval realism, never the dump)."""

    repository_apps: int = 1
    apps_selected: int = 1
    frameworks: int = 3
    controls_per_framework: int = 20
    evidence_files_per_framework: int = 2
    pages_per_file: int = 2
    words_per_page: int = 500
    output_style: str = "short readiness summary"
    output_mode: str = "summarized"           # summarized | framework_report | consolidated
    # Retrieved-context sizing (what actually enters the prompt). Defaults model a
    # realistic retrieved chunk/summary, NOT the full source document.
    evidence_excerpt_words: int = 90
    control_desc_words: int = 18
    # Auxiliary realistic context volumes (derived from scale; see from_scenario()).
    observation_count: int = 9
    vapt_count: int = 6
    baseline_count: int = 3
    exception_count: int = 6
    audit_comment_count: int = 5
    remediation_count: int = 6

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    """ESTIMATED token count for the dry-run / pre-call path (chars / chars_per_token).

    This is a planning ESTIMATE only. The LLM tokenizer (provider ``prompt_eval_count``)
    is the source of truth for MEASURED input tokens at run time."""
    if not text or not chars_per_token:
        return 0
    return int(round(len(text) / float(chars_per_token)))


def _pick(rng: random.Random, seq: list[str]) -> str:
    return seq[rng.randrange(len(seq))]


def _cycle(seq: list[str], i: int) -> str:
    return seq[i % len(seq)]


def _words(text: str) -> int:
    return len(text.split())


def _pad_to_words(base: str, target_words: int, rng: random.Random) -> str:
    """Extend a realistic excerpt to ~target_words by appending further DISTINCT,
    parameterized audit facts (never repeated filler). Each appended clause carries
    new numbers/owners so length comes from genuine breadth, not duplication."""
    out = [base]
    have = _words(base)
    i = 0
    while have < target_words:
        i += 1
        clause = (
            f"Cross-reference {i}: control owner {_pick(rng, _OWNERS)} confirms "
            f"{_pick(rng, _STATUSES).lower()} status with {rng.randint(2, 40)} supporting "
            f"artifacts; last verified {2024 + rng.randint(0, 2)}-Q{rng.randint(1, 4)}, "
            f"residual risk {_pick(rng, _SEVERITIES).lower()}."
        )
        out.append(clause)
        have += _words(clause)
    return " ".join(out)


def _evidence_excerpt(rng: random.Random, idx: int, target_words: int) -> str:
    tmpl = _cycle(_EVIDENCE_FACTS, idx)
    base = tmpl.format(
        n=rng.randint(20, 480), k=rng.randint(1, 25), pct=rng.randint(88, 100),
        sla=_pick(rng, ["7", "15", "30"]), tls=_pick(rng, ["1.2", "1.3"]),
        months=rng.choice([6, 12, 18]), rto=rng.choice([2, 4, 8]),
        rpo=rng.choice([1, 2, 4]),
    )
    return _pad_to_words(base, target_words, rng)


# --------------------------------------------------------------------------- #
# Section builders. Each returns (text, item_count).
# --------------------------------------------------------------------------- #
def _application_metadata(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Application Scope (selected for this assessment)"]
    for i in range(max(1, spec.apps_selected)):
        fam = _cycle(_APP_FAMILIES, i)
        region = _pick(rng, _REGIONS)
        lines.append(
            f"- {fam}-{region.lower().replace(' ', '')} (APP-{1000 + i*7:04d}) | "
            f"LoB={_pick(rng, _LOBS)} | region={region} | "
            f"criticality={_pick(rng, _CRITICALITY)} | hosting=GCP ap-south-1 | "
            f"data_classification={_pick(rng, ['Confidential', 'Restricted', 'Internal'])} | "
            f"owner={_pick(rng, _OWNERS)} | last_pentest={2025 + (i % 2)}-{(i % 12) + 1:02d}-12"
        )
    lines.append(
        f"(Repository scope: {spec.repository_apps} applications onboarded in ECS; "
        f"only the {spec.apps_selected} selected application(s) and their retrieved "
        f"evidence enter this prompt.)"
    )
    return "\n".join(lines), max(1, spec.apps_selected)


def _framework_catalog(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Frameworks in Scope"]
    for i in range(spec.frameworks):
        fw = _cycle(_FRAMEWORKS, i)
        lines.append(f"- {fw}: {spec.controls_per_framework} controls in scope; "
                     f"primary owner {_pick(rng, _OWNERS)}.")
    return "\n".join(lines), spec.frameworks


def _control_descriptions(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Control Catalog & Current Status"]
    count = 0
    for f in range(spec.frameworks):
        fw = _cycle(_FRAMEWORKS, f)
        for c in range(spec.controls_per_framework):
            dom = _cycle(_CONTROL_DOMAINS, c)
            intent = _cycle(_CONTROL_INTENTS, c)
            cid = f"{fw.split()[0].upper()}-{dom[:2].upper()}-{c + 1:02d}"
            lines.append(
                f"- {cid} ({dom}): {intent}. Status={_pick(rng, _STATUSES)}; "
                f"owner={_pick(rng, _OWNERS)}; evidence_refs={rng.randint(1, 6)}."
            )
            count += 1
    return "\n".join(lines), count


def _retrieved_evidence(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    """Numbered, citable evidence blocks mirroring the ECS prompt shape. Count =
    frameworks x evidence_files_per_framework (retrieved chunks for the selected
    scope) — NOT the whole repository."""
    lines = ["## Retrieved Evidence Context"]
    idx = 0
    total = spec.frameworks * spec.evidence_files_per_framework
    for n in range(total):
        idx += 1
        app = _cycle(_APP_FAMILIES, n % max(1, spec.apps_selected))
        header = (
            f"[E{idx}] source={_cycle(_SOURCE_SYSTEMS, n)} "
            f"type={_cycle(_OBJECT_TYPES, n)} app={app} "
            f"uid=EV-{100000 + n*13:06d}"
        )
        lines.append(f"{header}\n{_evidence_excerpt(rng, n, spec.evidence_excerpt_words)}")
    return "\n\n".join(lines), total


def _observation_history(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Observation History"]
    for i in range(spec.observation_count):
        fw = _cycle(_FRAMEWORKS, i)
        lines.append(
            f"- OBS-{i + 1:05d}: {_cycle(_CONTROL_DOMAINS, i)} gap on "
            f"{_cycle(_APP_FAMILIES, i)} ({fw}); severity={_pick(rng, _SEVERITIES)}; "
            f"opened {2025}-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}; "
            f"root_cause={'control gap' if i % 2 else 'evidence gap'}; "
            f"status={_pick(rng, _STATUSES)}; target=Q{(i % 4) + 1}."
        )
    return "\n".join(lines), spec.observation_count


def _vapt_findings(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## VAPT Findings"]
    for i in range(spec.vapt_count):
        lines.append(
            f"- VAPT-2026-{i + 1:03d}: {_pick(rng, ['SQL injection', 'broken access control', 'SSRF', 'insecure deserialization', 'weak TLS config'])} "
            f"on {_cycle(_APP_FAMILIES, i)}; CVSS {rng.randint(40, 95) / 10:.1f} "
            f"({_pick(rng, _SEVERITIES)}); exploitability={_pick(rng, ['confirmed', 'theoretical'])}; "
            f"compensating_control={_pick(rng, ['WAF rule', 'network ACL', 'rate limiting'])}; "
            f"fix_target=Q{(i % 4) + 1}."
        )
    return "\n".join(lines), spec.vapt_count


def _baseline_status(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Baseline / Hardening Status"]
    for i in range(spec.baseline_count):
        std = _pick(rng, ["CIS Linux L1", "CIS Windows L1", "DB CIS Benchmark", "K8s CIS"])
        lines.append(
            f"- {std} for {_cycle(_APP_FAMILIES, i)} fleet: {rng.randint(78, 99)}% compliant "
            f"across {rng.randint(40, 600)} hosts; {rng.randint(2, 50)} hosts on drift; "
            f"top gap={_pick(rng, ['auditd config', 'kernel hardening', 'password policy', 'TLS ciphers'])}."
        )
    return "\n".join(lines), spec.baseline_count


def _risk_exceptions(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Risk Acceptance & Exceptions"]
    for i in range(spec.exception_count):
        lines.append(
            f"- EXC-{i + 1:05d}: accepted residual risk on {_cycle(_APP_FAMILIES, i)} "
            f"({_cycle(_FRAMEWORKS, i)}); residual={_pick(rng, _SEVERITIES)}; "
            f"compensating={_pick(rng, ['HSTS+cert pinning', 'MFA+segmentation', 'WAF+monitoring'])}; "
            f"approver={_pick(rng, _OWNERS)}; expiry=Q{(i % 4) + 1}."
        )
    return "\n".join(lines), spec.exception_count


def _audit_comments(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Auditor Comments"]
    for i in range(spec.audit_comment_count):
        lines.append(
            f"- {_pick(rng, ['Internal Audit', 'RBI Inspection', 'External Auditor'])} comment on "
            f"{_cycle(_FRAMEWORKS, i)}: {_pick(rng, ['evidence older than 12 months; request refresh', 'sampling gap on privileged access; expand scope', 'remediation evidence incomplete; provide closure artifacts', 'control narrative lacks owner sign-off'])}."
        )
    return "\n".join(lines), spec.audit_comment_count


def _remediation_status(rng: random.Random, spec: PromptSpec) -> tuple[str, int]:
    lines = ["## Remediation Status"]
    for i in range(spec.remediation_count):
        lines.append(
            f"- RMD-{i + 1:05d}: {_pick(rng, ['centralized secrets management', 'TLS 1.3 migration', 'privileged access hardening', 'log retention uplift', 'DR runbook refresh'])} "
            f"for {_cycle(_APP_FAMILIES, i)}; {rng.randint(10, 95)}% complete; "
            f"dependency={_pick(rng, ['platform uplift', 'vendor patch', 'process change'])}; "
            f"target=Q{(i % 4) + 1}."
        )
    return "\n".join(lines), spec.remediation_count


def _executive_instruction(spec: PromptSpec) -> tuple[str, int]:
    if spec.output_mode == "summarized":
        body = (
            "Produce a summarized audit readiness assessment. For EACH framework, keep the "
            "summary to ~200-300 characters and include: readiness status, the top control "
            "gaps, key open observations, and remediation recommendations. Conclude with a "
            "concise executive summary and a final readiness conclusion. Cite evidence ids "
            "like [E1] for every factual claim."
        )
    elif spec.output_mode == "framework_report":
        body = (
            "Produce a framework-wise readiness report. For EACH framework provide: readiness "
            "status, top control gaps, open observations, VAPT-driven risks, and prioritized "
            "remediation recommendations. End with an executive summary and a final readiness "
            "conclusion. Cite evidence ids like [E1] for every factual claim."
        )
    else:  # consolidated
        body = (
            "Produce a consolidated audit readiness report across all selected applications and "
            "frameworks. Provide a per-framework readiness status, top control gaps, open "
            "observations, risk exceptions, and remediation recommendations, then a single "
            "consolidated executive summary and final enterprise readiness conclusion. Cite "
            "evidence ids like [E1] for every factual claim."
        )
    text = f"## Executive Instruction\n{body}\nOutput style requested: {spec.output_style}."
    return text, 1


_SECTION_BUILDERS = [
    ("application_metadata", _application_metadata),
    ("framework_catalog", _framework_catalog),
    ("control_descriptions", _control_descriptions),
    ("retrieved_evidence", _retrieved_evidence),
    ("observation_history", _observation_history),
    ("vapt_findings", _vapt_findings),
    ("baseline_status", _baseline_status),
    ("risk_exceptions", _risk_exceptions),
    ("audit_comments", _audit_comments),
    ("remediation_status", _remediation_status),
    ("executive_instruction", lambda rng, spec: _executive_instruction(spec)),
]


def build_prompt(spec: PromptSpec, *, seed: int = 1234,
                 chars_per_token: float = 4.0) -> dict[str, Any]:
    """Build one realistic ECS assessment prompt and its composition breakdown.

    Returns a dict with ``system_prompt``, ``user_prompt``, ``system_prompt_source``,
    per-section ``composition`` (chars / estimated tokens / item counts), and the
    aggregate prompt-size metrics. Deterministic for a given ``seed``."""
    rng = random.Random(seed)
    system_prompt, system_source = load_system_prompt()

    sections: list[dict[str, Any]] = []
    body_parts: list[str] = []
    for name, builder in _SECTION_BUILDERS:
        text, items = builder(rng, spec)  # type: ignore[misc]
        body_parts.append(text)
        sections.append({
            "section": name,
            "items": int(items),
            "chars": len(text),
            "estimated_tokens": estimate_tokens(text, chars_per_token),
        })

    user_prompt = "\n\n".join(body_parts)
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    return {
        "system_prompt": system_prompt,
        "system_prompt_source": system_source,
        "user_prompt": user_prompt,
        "composition": sections,
        # Source-document scale (METADATA only — informs reviewers; not all of this
        # enters the prompt, only the retrieved excerpts above do).
        "source_pages_per_file": spec.pages_per_file,
        "source_words_per_page": spec.words_per_page,
        "retrieved_evidence_blocks": spec.frameworks * spec.evidence_files_per_framework,
        # MEASURED prompt-size metrics (exact, no model needed).
        "system_prompt_chars": len(system_prompt),
        "user_prompt_chars": len(user_prompt),
        "prompt_chars": len(full_prompt),
        "prompt_bytes": len(full_prompt.encode("utf-8")),
        # ESTIMATED input tokens (planning estimate; replaced by MEASURED at run time).
        "estimated_input_tokens": estimate_tokens(full_prompt, chars_per_token),
        "chars_per_token_basis": chars_per_token,
    }
