"""Enterprise AI workload profiles for the ECS benchmark.

These profiles describe *realistic* enterprise audit / compliance workloads for
Neev capacity planning. Each profile is just data: a realistic question, the
retrieval breadth (``top_k``), and size/intent classifiers. They are consumed by
``enterprise_runner`` which routes them through the EXISTING RAG pipeline
(``ecs_platform.rag.answer``) — nothing here reimplements ECS logic.

Design intent
-------------
* Prompt size is driven by the *content* of realistic audit instructions, never
  by padding or repeated text.
* Retrieved-context volume is driven by ``top_k`` (the real retrieval lever).
* Response length is driven by realistic instruction wording (e.g. "in one
  sentence" vs "exhaustive, control-by-control") — ECS governs ``max_output_tokens``
  via ``config/llm.yaml``; the benchmark does not force artificial limits.
* Maximum-token scenarios combine the widest realistic retrieval with the most
  detailed realistic assessment to reveal worst-case production token usage.

The application / framework / source vocabulary mirrors the existing benchmark
dataset (``scripts/generate_benchmark_dataset.py``) so profiles retrieve real
evidence on the benchmark workstation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Retrieval breadth presets (documents requested from the retriever).
TOP_K_SMALL = 3
TOP_K_MEDIUM = 5
TOP_K_LARGE = 8
TOP_K_MAX = 40  # maximum realistic retrieved context (worst-case sizing)


@dataclass(frozen=True)
class WorkloadProfile:
    """One realistic enterprise AI workload scenario."""

    key: str
    name: str
    category: str            # framework | baseline | evidence | size_matrix | stress | risk
    prompt_class: str        # small | medium | large
    response_intent: str     # small | normal | large | maximum
    top_k: int
    question: str
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# 1) Prompt-size x response-size matrix (6 scenarios)
# --------------------------------------------------------------------------- #
_SIZE_MATRIX: list[WorkloadProfile] = [
    WorkloadProfile(
        key="sp_sr",
        name="Small Prompt -> Small Response",
        category="size_matrix",
        prompt_class="small",
        response_intent="small",
        top_k=TOP_K_SMALL,
        question="State the current PCI DSS readiness status for Payments Gateway in one sentence with one citation.",
        description="Cheapest realistic call: short ask, short grounded verdict.",
    ),
    WorkloadProfile(
        key="sp_lr",
        name="Small Prompt -> Large Response",
        category="size_matrix",
        prompt_class="small",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question="Provide a complete, control-by-control PCI DSS readiness assessment for Payments Gateway, citing ECS evidence for each control.",
        description="Short instruction that legitimately elicits a long, detailed answer.",
    ),
    WorkloadProfile(
        key="mp_mr",
        name="Medium Prompt -> Medium Response",
        category="size_matrix",
        prompt_class="medium",
        response_intent="normal",
        top_k=TOP_K_MEDIUM,
        question=(
            "For Mobile Banking, summarize SOC2 and PCI DSS evidence coverage, list the "
            "top three open gaps, and recommend the next remediation step for each, with citations."
        ),
        description="Typical analyst workload.",
    ),
    WorkloadProfile(
        key="mp_lr",
        name="Medium Prompt -> Large Response",
        category="size_matrix",
        prompt_class="medium",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question=(
            "For Corporate Banking, produce a detailed audit-readiness report covering access control, "
            "change management, vulnerability management and incident response: for each control area "
            "describe current evidence, gaps, risk rating and remediation, citing ECS evidence."
        ),
        description="Detailed single-application audit package.",
    ),
    WorkloadProfile(
        key="lp_sr",
        name="Large Prompt -> Small Response",
        category="size_matrix",
        prompt_class="large",
        response_intent="small",
        top_k=TOP_K_MEDIUM,
        question=(
            "Acting as the lead IT auditor for HDFC Bank, consider the following scope: applications "
            "Mobile Banking, Payments Gateway and Loan Origination; frameworks PCI DSS, RBI Cyber Security "
            "Framework, SOC2 and ISO 27001; control families access control, change management, "
            "vulnerability management, incident response and backup/DR; evidence sources Jira, Jenkins, "
            "SonarQube, ServiceNow, CMDB, Confluence and GitHub. Weigh evidence freshness, citation "
            "coverage and rejected-evidence ratios. After fully evaluating the above, respond with only a "
            "single overall audit-readiness verdict (Ready / Conditional / Not Ready) and a one-line justification."
        ),
        description="Heavy context-laden instruction, deliberately terse output (tests input-heavy cost).",
    ),
    WorkloadProfile(
        key="lp_lr",
        name="Large Prompt -> Large Response",
        category="size_matrix",
        prompt_class="large",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question=(
            "Acting as the lead IT auditor for HDFC Bank, assess audit readiness across applications "
            "Mobile Banking, Payments Gateway, Loan Origination, Corporate Banking and Treasury Ops "
            "against PCI DSS, RBI Cyber Security Framework, SOC2 and ISO 27001. For every application and "
            "control family (access control, change management, vulnerability management, incident response, "
            "backup/DR) provide current evidence, gaps, risk rating, remediation owner and target, and cite "
            "ECS evidence for each finding. Conclude with a per-framework readiness scorecard."
        ),
        description="Large input and large output (balanced worst case).",
    ),
]

# --------------------------------------------------------------------------- #
# 2) Retrieved-context stress (2 scenarios) — maximum realistic context
# --------------------------------------------------------------------------- #
_CONTEXT_STRESS: list[WorkloadProfile] = [
    WorkloadProfile(
        key="maxctx_normal",
        name="Maximum Retrieved Context -> Normal Answer",
        category="stress",
        prompt_class="medium",
        response_intent="normal",
        top_k=TOP_K_MAX,
        question=(
            "Using all available evidence across every application and framework, summarize the overall "
            "enterprise compliance posture in a concise executive paragraph with key citations."
        ),
        description="Widest retrieval, concise answer (isolates input/context token cost).",
    ),
    WorkloadProfile(
        key="maxctx_max",
        name="Maximum Retrieved Context -> Maximum Detailed Assessment",
        category="stress",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Using all available evidence across every application, framework and evidence source, produce "
            "an exhaustive enterprise compliance assessment: for each framework (PCI DSS, RBI Cyber Security "
            "Framework, SOC2, ISO 27001, AI-SDLC) and each application, enumerate every control with its "
            "evidence, freshness, gaps, risk rating, remediation plan, owner and target date, and cite ECS "
            "evidence for each item. Finish with an enterprise-wide risk register and a prioritized remediation roadmap."
        ),
        description="Worst-case realistic token consumption for infrastructure sizing.",
    ),
]

# --------------------------------------------------------------------------- #
# 3) Named enterprise workloads (12 scenarios)
# --------------------------------------------------------------------------- #
_ENTERPRISE: list[WorkloadProfile] = [
    WorkloadProfile(
        key="multidoc_audit",
        name="Large Multi-document Audit",
        category="evidence",
        prompt_class="large",
        response_intent="large",
        top_k=TOP_K_MAX,
        question=(
            "Perform a multi-document audit for Loan Origination: correlate Jira change records, Jenkins build "
            "evidence, SonarQube quality findings, ServiceNow incidents and CMDB configuration items into a "
            "single timeline, identify control breaks, and cite each supporting ECS evidence record."
        ),
        description="Cross-source correlation over many documents.",
    ),
    WorkloadProfile(
        key="complete_compliance",
        name="Complete Compliance Assessment",
        category="framework",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Produce a complete compliance assessment for the enterprise covering PCI DSS, RBI Cyber Security "
            "Framework, SOC2 and ISO 27001: per framework, list every applicable control, its evidence status, "
            "gaps, risk and remediation, with citations, and a consolidated compliance scorecard."
        ),
        description="Full multi-framework compliance pass.",
    ),
    WorkloadProfile(
        key="enterprise_risk",
        name="Enterprise Risk Assessment",
        category="risk",
        prompt_class="large",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question=(
            "Generate an enterprise risk assessment: identify the top risks across all applications based on "
            "rejected evidence, stale evidence, open vulnerabilities and incident history; rate each by "
            "likelihood and impact; and recommend mitigations with citations."
        ),
        description="Risk-centric reasoning across evidence.",
    ),
    WorkloadProfile(
        key="cmdb_analysis",
        name="CMDB Evidence Analysis",
        category="evidence",
        prompt_class="medium",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question=(
            "Analyze CMDB evidence across applications: assess configuration-item completeness, ownership and "
            "relationships, flag missing or stale CIs, and map them to affected controls, citing ECS evidence."
        ),
        description="CMDB-focused configuration assurance.",
    ),
    WorkloadProfile(
        key="servicenow_correlation",
        name="ServiceNow Evidence Correlation",
        category="evidence",
        prompt_class="medium",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question=(
            "Correlate ServiceNow change and incident evidence with control outcomes for Payments Gateway and "
            "Corporate Banking: identify unauthorized or failed changes, link incidents to root-cause controls, "
            "and cite supporting ECS evidence."
        ),
        description="ITSM correlation workload.",
    ),
    WorkloadProfile(
        key="rbi_csite",
        name="RBI C-SITE Assessment",
        category="framework",
        prompt_class="medium",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question="Provide an RBI C-SITE (Cyber Security) readiness assessment across all applications with control-level evidence, gaps and remediation, citing ECS evidence.",
        description="RBI Cyber Security Framework readiness.",
    ),
    WorkloadProfile(
        key="pci_dss",
        name="PCI DSS Assessment",
        category="framework",
        prompt_class="medium",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question="Provide a PCI DSS readiness assessment for the cardholder-data environment applications, with requirement-level evidence, gaps and remediation, citing ECS evidence.",
        description="PCI DSS readiness.",
    ),
    WorkloadProfile(
        key="windows_baseline",
        name="Windows Baseline Assessment",
        category="baseline",
        prompt_class="medium",
        response_intent="normal",
        top_k=TOP_K_MEDIUM,
        question="Assess Windows server hardening baseline compliance: evaluate patch level, account policy, audit logging and service hardening evidence, list deviations and remediation, citing ECS evidence.",
        description="OS baseline (Windows).",
    ),
    WorkloadProfile(
        key="linux_baseline",
        name="Linux Baseline Assessment",
        category="baseline",
        prompt_class="medium",
        response_intent="normal",
        top_k=TOP_K_MEDIUM,
        question="Assess Linux server hardening baseline compliance: evaluate patching, SSH and account policy, file integrity and logging evidence, list deviations and remediation, citing ECS evidence.",
        description="OS baseline (Linux).",
    ),
    WorkloadProfile(
        key="db_baseline",
        name="Database Baseline Assessment",
        category="baseline",
        prompt_class="medium",
        response_intent="normal",
        top_k=TOP_K_MEDIUM,
        question="Assess database security baseline compliance: evaluate encryption at rest and in transit, privileged access, auditing and backup evidence, list deviations and remediation, citing ECS evidence.",
        description="Database baseline.",
    ),
    WorkloadProfile(
        key="middleware_baseline",
        name="Middleware Baseline Assessment",
        category="baseline",
        prompt_class="medium",
        response_intent="normal",
        top_k=TOP_K_MEDIUM,
        question="Assess middleware (application/web server) baseline compliance: evaluate TLS configuration, version currency, hardening and access-control evidence, list deviations and remediation, citing ECS evidence.",
        description="Middleware baseline.",
    ),
    WorkloadProfile(
        key="backup_dr",
        name="Backup & DR Assessment",
        category="baseline",
        prompt_class="medium",
        response_intent="large",
        top_k=TOP_K_LARGE,
        question="Assess backup and disaster-recovery readiness across critical applications: evaluate backup success, restore testing, RPO/RTO adherence and DR drill evidence, list gaps and remediation, citing ECS evidence.",
        description="Resilience / DR assurance.",
    ),
]


def default_profiles() -> list[WorkloadProfile]:
    """Full enterprise workload catalog (20 realistic scenarios)."""
    return [*_SIZE_MATRIX, *_CONTEXT_STRESS, *_ENTERPRISE]


def profiles_by_keys(keys: list[str]) -> list[WorkloadProfile]:
    """Subset of the catalog by profile key, preserving catalog order."""
    wanted = set(keys)
    return [p for p in default_profiles() if p.key in wanted]


def catalog_index() -> dict[str, WorkloadProfile]:
    return {p.key: p for p in default_profiles()}
