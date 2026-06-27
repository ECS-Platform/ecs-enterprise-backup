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

from dataclasses import asdict, dataclass, field

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
    # When True, the runner prepends the BENCHMARK-MODELED Pan-India reference
    # context (pan_india_reference_context.build_reference_context) to the question
    # so the EXISTING instrumentation measures a realistic future-state input-token
    # volume. Default False -> behaviour unchanged for every existing profile.
    modeled_context: bool = False
    # Optional subset of modeled-context blocks (see pan_india_reference_context
    # _BLOCK_BUILDERS). Empty -> all blocks. Only used when modeled_context=True.
    modeled_context_blocks: tuple[str, ...] = field(default_factory=tuple)

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


# --------------------------------------------------------------------------- #
# 4) Worst-case enterprise workloads (14 scenarios) — maximum REALISTIC token use
# --------------------------------------------------------------------------- #
# These represent the heaviest plausible Pan-India HDFC governance workloads. They
# are NOT average production traffic; they exist to establish a realistic UPPER
# BOUND for LLM procurement / budgeting / infrastructure sizing. Every prompt is a
# genuine enterprise audit/governance instruction — large because the *scope* is
# large (every application x every framework x every control), never because of
# padding or repeated text. All run at TOP_K_MAX (widest realistic retrieval) and
# request maximum detailed output. They share the ``worst_case`` category and the
# ``response_intent="maximum"`` so reporting can isolate the worst-case envelope.
_WORST_CASE: list[WorkloadProfile] = [
    WorkloadProfile(
        key="wc_enterprise_compliance",
        name="Enterprise-wide Compliance Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Produce an enterprise-wide compliance assessment for the entire HDFC Bank application "
            "portfolio against PCI DSS, RBI Cyber Security Framework, RBI C-SITE, SOC2, ISO 27001 and "
            "AI-SDLC. For every application and every applicable control, state the control objective, "
            "current evidence with ECS citations, evidence freshness, compliance status, gap, risk rating, "
            "remediation action, owner and target date. Conclude with a per-framework readiness scorecard "
            "and an enterprise compliance index."
        ),
        description="Full portfolio x full framework set x control-by-control — primary worst case.",
    ),
    WorkloadProfile(
        key="wc_cross_framework_reuse",
        name="Cross-framework Evidence Reuse (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Across the full application portfolio, map every evidence record to all frameworks and controls "
            "it satisfies (PCI DSS, RBI CSF, RBI C-SITE, SOC2, ISO 27001, AI-SDLC), quantify reuse ratios per "
            "evidence item, identify single-points-of-failure evidence, and produce a complete cross-framework "
            "reuse matrix with citations and a remediation list for low-reuse obligations."
        ),
        description="Dense many-to-many reuse mapping over maximum retrieved evidence.",
    ),
    WorkloadProfile(
        key="wc_executive_audit_package",
        name="Executive Audit Package (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Assemble a complete executive audit package for the CISO and Audit Committee covering all "
            "applications and frameworks: executive summary, per-framework readiness, top enterprise risks, "
            "control-failure analysis, rejected/stale evidence analysis, remediation roadmap with owners and "
            "dates, and an appendix of cited ECS evidence for every material finding."
        ),
        description="Long-form executive deliverable with full evidence appendix.",
    ),
    WorkloadProfile(
        key="wc_board_reporting",
        name="Board Reporting Pack (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Generate a board-level technology governance and compliance report for HDFC Bank: enterprise "
            "compliance posture across all frameworks, material risks and trends, regulatory exposure, "
            "remediation status against prior commitments, and forward-looking risk outlook, each substantiated "
            "with cited ECS evidence and a clear executive narrative suitable for the Board."
        ),
        description="Board-grade narrative synthesis over the whole estate.",
    ),
    WorkloadProfile(
        key="wc_technology_risk",
        name="Technology Risk Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Perform an enterprise technology risk assessment across all applications: enumerate risks from open "
            "vulnerabilities, stale and rejected evidence, failed/unauthorized changes, incident history and "
            "control gaps; rate each by likelihood and impact; aggregate into a risk register with inherent and "
            "residual ratings; and recommend prioritized mitigations with owners, citing ECS evidence."
        ),
        description="Full-estate risk reasoning and register synthesis.",
    ),
    WorkloadProfile(
        key="wc_remediation_planning",
        name="Enterprise Remediation Planning (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Build an enterprise remediation plan covering every open gap across all applications and frameworks: "
            "for each gap describe root cause, affected controls and frameworks, remediation steps, dependencies, "
            "effort, owner, target date and verification evidence, then sequence everything into a prioritized "
            "multi-quarter roadmap with a critical-path summary, citing ECS evidence."
        ),
        description="Exhaustive gap-to-plan expansion across the estate.",
    ),
    WorkloadProfile(
        key="wc_cloud_governance",
        name="Cloud Governance Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Assess cloud governance across all cloud-hosted applications: evaluate identity and access, network "
            "controls, encryption, configuration baselines, logging/monitoring, backup/DR and regulatory data "
            "residency against PCI DSS, RBI CSF, ISO 27001 and SOC2; list deviations, risks and remediation per "
            "application with cited ECS evidence and a consolidated cloud posture scorecard."
        ),
        description="Cloud control-plane assessment across the portfolio.",
    ),
    WorkloadProfile(
        key="wc_data_governance",
        name="Data Governance Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Assess enterprise data governance: classify data across applications, evaluate encryption at rest and "
            "in transit, access control, retention, masking, lineage and DPSC/RBI data-localization obligations; "
            "identify gaps and risks per application and data domain; and provide remediation with cited ECS "
            "evidence and a data-governance maturity scorecard."
        ),
        description="Data-domain governance across the estate.",
    ),
    WorkloadProfile(
        key="wc_operational_resilience",
        name="Operational Resilience Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Assess operational resilience for all critical applications: evaluate backup success, restore testing, "
            "RPO/RTO adherence, DR drills, incident response maturity, change failure rate and single points of "
            "failure; map to RBI operational-resilience expectations; and provide per-application gaps, risks and "
            "remediation with cited ECS evidence and an enterprise resilience scorecard."
        ),
        description="Resilience/continuity across critical systems.",
    ),
    WorkloadProfile(
        key="wc_third_party_risk",
        name="Third-Party Risk Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Perform an enterprise third-party / vendor risk assessment: for every application with material "
            "third-party dependencies, evaluate due-diligence evidence, contractual controls, access, "
            "sub-processor risk, incident and SLA history against RBI outsourcing guidelines and ISO 27001; rate "
            "and prioritize risks; and recommend mitigations with cited ECS evidence."
        ),
        description="Vendor/outsourcing risk across the estate.",
    ),
    WorkloadProfile(
        key="wc_ai_governance",
        name="AI Governance Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Assess AI governance across all AI/ML use cases under the AI-SDLC framework: for each use case evaluate "
            "model risk, data provenance, bias/fairness, explainability, human oversight, security and lifecycle "
            "gate evidence; identify gaps and risks; and provide remediation and an AI-governance maturity "
            "scorecard with cited ECS evidence."
        ),
        description="AI/ML lifecycle governance across use cases.",
    ),
    WorkloadProfile(
        key="wc_portfolio_review",
        name="Portfolio-wide Compliance Review (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Conduct a portfolio-wide compliance review: for every application produce a one-page compliance "
            "profile (frameworks in scope, readiness, top gaps, top risks, remediation status) and then a "
            "portfolio rollup ranking applications by risk and readiness, all substantiated with cited ECS evidence."
        ),
        description="Per-application profiles plus portfolio rollup.",
    ),
    WorkloadProfile(
        key="wc_regulator_inspection",
        name="Large Regulator Inspection Response (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Prepare a comprehensive response to a large RBI regulatory inspection covering cyber security, IT "
            "governance, data localization, operational resilience and outsourcing: for each inspection area, "
            "provide the control narrative, supporting evidence with ECS citations, identified gaps, compensating "
            "controls and remediation commitments, formatted as a regulator-ready submission."
        ),
        description="Regulator-grade, evidence-backed inspection submission.",
    ),
    WorkloadProfile(
        key="wc_control_maturity",
        name="Enterprise Control Maturity Assessment (Worst Case)",
        category="worst_case",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Assess enterprise control maturity across all control families (access control, change management, "
            "vulnerability management, incident response, backup/DR, configuration management, data protection, "
            "logging/monitoring): for each family rate maturity on a defined scale with justification and cited "
            "ECS evidence, identify maturity gaps and improvement actions, and produce an enterprise maturity "
            "heatmap and roadmap."
        ),
        description="Maturity scoring across all control families.",
    ),
]

# --------------------------------------------------------------------------- #
# 5) True worst-case OUTPUT workloads (8 scenarios) — maximum REALISTIC output
# --------------------------------------------------------------------------- #
# Some worst-case profiles under-produced output tokens because the ask, while
# broad, did not explicitly require long-form, structured deliverables. These
# profiles target the MAXIMUM realistic OUTPUT envelope for token-budget approval:
# each is a genuine senior-management / audit / regulator / board deliverable
# whose length is justified by the governance use case (multi-section reports,
# control-level findings, registers, roadmaps) — NEVER by padding, repetition or
# "write as much as possible" phrasing. All run at TOP_K_MAX (widest realistic
# retrieval -> large input) and response_intent="maximum". They share the
# ``worst_case_output`` category so reporting can isolate the output envelope.
_WORST_CASE_OUTPUT: list[WorkloadProfile] = [
    WorkloadProfile(
        key="wco_regulator_inspection_pack",
        name="Full Regulator Inspection Response Pack (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Produce a complete RBI regulator-facing inspection response pack for HDFC Bank. Structure it "
            "as: (1) executive summary; (2) framework-by-framework findings for PCI DSS, RBI Cyber Security "
            "Framework, RBI C-SITE, SOC2, ISO 27001 and AI-SDLC, each as a table of control objective, "
            "current evidence with ECS citations, compliance status and gap; (3) control-failure analysis; "
            "(4) per-finding risk rating with justification; (5) a remediation plan with owners and target "
            "dates; (6) stated assumptions; and (7) audit caveats and evidence limitations. Provide "
            "control-level detail throughout and cite ECS evidence for every material finding."
        ),
        description="Regulator-ready multi-section submission with control-level tables and caveats.",
    ),
    WorkloadProfile(
        key="wco_board_audit_committee_pack",
        name="Board Audit Committee Pack (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Generate a board-ready audit committee compliance and technology-risk pack. Include: an "
            "executive summary; a compliance heatmap narrative across all frameworks; the top enterprise "
            "risks with likelihood/impact; systemic and recurring issues; overdue and stale evidence; a "
            "control-maturity overview by control family; recommended management actions with owners; and an "
            "explicit list of decision points requiring board direction. Use tables where appropriate and "
            "cite ECS evidence for each material point."
        ),
        description="Board-grade narrative + heatmap + risk + decisions, fully sectioned.",
    ),
    WorkloadProfile(
        key="wco_enterprise_remediation_roadmap",
        name="Enterprise Remediation Roadmap (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Convert every identified compliance and control gap across all applications and frameworks into "
            "a structured enterprise remediation roadmap. Organize it into quick wins, medium-term fixes and "
            "long-term structural changes; for each item give the affected controls and frameworks, root "
            "cause, remediation steps, control owner, dependencies, effort, target date, verification "
            "evidence and escalation triggers; then provide a sequenced multi-quarter plan with a "
            "critical-path summary. Cite ECS evidence for each gap."
        ),
        description="Exhaustive gap-to-roadmap expansion with owners, dependencies and timelines.",
    ),
    WorkloadProfile(
        key="wco_cross_framework_maturity_report",
        name="Cross-framework Control Maturity Report (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Produce a full control-maturity report across RBI C-SITE, PCI DSS, DPSC, ITGRC, VAPT, AppSec, "
            "ITDRM, cloud governance and the OS/database/middleware baselines. For each domain provide a "
            "maturity rating on a defined scale with justification, evidence strength, gaps, cross-framework "
            "reuse opportunities and control-by-control commentary, then a consolidated maturity heatmap and "
            "prioritized improvement plan. Cite ECS evidence throughout."
        ),
        description="Domain-by-domain maturity with control-level commentary and heatmap.",
    ),
    WorkloadProfile(
        key="wco_audit_observation_register",
        name="Full Audit Observation Register (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Generate a detailed enterprise audit observation register from the available evidence. For every "
            "observation provide: observation title, description, impacted framework(s), evidence source with "
            "ECS citation, root cause, severity, risk rating, recommendation, control owner, target date and "
            "closure criteria. Present the register as a structured table, group observations by framework and "
            "application, and finish with a summary of severity distribution and the most material themes."
        ),
        description="Long structured register: one fully-attributed row per observation.",
    ),
    WorkloadProfile(
        key="wco_evidence_reuse_efficiency_report",
        name="Executive Evidence Reuse & Efficiency Report (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Produce an executive evidence-reuse and efficiency report across all frameworks. Include a "
            "cross-framework crosswalk of which evidence satisfies which controls and frameworks; quantify "
            "reuse ratios and identify duplication; highlight coverage gaps and single-points-of-failure "
            "evidence; assess the risk of over-reliance on individual evidence items; and recommend "
            "automation and collection-efficiency opportunities. Use tables and cite ECS evidence."
        ),
        description="Reuse crosswalk + duplication + over-reliance risk + automation opportunities.",
    ),
    WorkloadProfile(
        key="wco_five_year_governance_narrative",
        name="Five-Year Enterprise Capacity & Governance Narrative (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Write a long-form executive narrative on HDFC Bank's five-year compliance evidence and "
            "governance outlook. Cover current posture and evidence base; projected evidence growth as "
            "applications and frameworks expand; control-maturity trajectory; governance and operating-model "
            "implications; key risks and dependencies over the horizon; and a year-by-year set of governance "
            "priorities. Ground the current-state sections in cited ECS evidence and clearly label "
            "forward-looking statements as assumptions."
        ),
        description="Long-form multi-year executive governance narrative, evidence-grounded.",
    ),
    WorkloadProfile(
        key="wco_ciso_technology_risk_briefing",
        name="CISO Technology Risk Briefing (Worst Case Output)",
        category="worst_case_output",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        question=(
            "Prepare a regulator-ready CISO technology-risk briefing for HDFC Bank. Include: enterprise "
            "control posture by control family; material evidence gaps; open risk themes with ratings; active "
            "exceptions and compensating controls; remediation sequencing with owners and timelines; and an "
            "overall assurance view. Provide control-level detail, use tables where appropriate, state "
            "assumptions and evidence caveats, and cite ECS evidence for each material point."
        ),
        description="CISO-grade assurance briefing: posture, gaps, exceptions, sequencing.",
    ),
]

# --------------------------------------------------------------------------- #
# 6) Pan-India enterprise workloads (8 scenarios) — FUTURE-STATE token sizing
# --------------------------------------------------------------------------- #
# These model a MATURE Pan-India ECS deployment for token-budget approval to
# Neev/Finance. Each carries ``modeled_context=True`` so the runner prepends the
# BENCHMARK-MODELED Pan-India reference context (a realistic, structured,
# configurable enterprise dataset — NOT padding/repetition) to the question. The
# combination of that modeled context + a genuine long-form governance ask drives
# realistic MAXIMUM input AND output token volumes, all MEASURED by the existing
# instrumentation. The modeled context is clearly separated from measured values
# in reporting (pan_india_capacity_validation). All run at TOP_K_MAX / large /
# maximum. Category ``pan_india_enterprise`` so the tier is selectable on its own.
_PAN_INDIA_ENTERPRISE: list[WorkloadProfile] = [
    WorkloadProfile(
        key="pie_regulator_pan_india_inspection",
        name="Regulator Pan-India Inspection Response (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, produce a complete RBI "
            "regulator-facing inspection response pack covering the full application estate and all "
            "in-scope frameworks. Provide: an executive summary; framework-by-framework findings as "
            "tables (control objective, evidence, status, gap); control-failure analysis; per-finding "
            "risk ratings with justification; a remediation plan with owners and target dates; stated "
            "assumptions; and audit caveats. Provide control-level detail across the estate."
        ),
        description="Estate-wide regulator submission over modeled Pan-India context.",
    ),
    WorkloadProfile(
        key="pie_board_enterprise_audit_pack",
        name="Board Enterprise Audit Pack (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, generate a board-ready compliance "
            "and technology-risk pack for the full Pan-India estate. Include: executive summary; "
            "compliance heatmap narrative across all frameworks and lines of business; top enterprise "
            "risks; systemic and recurring issues; overdue/stale evidence; control-maturity overview by "
            "domain; management actions with owners; and explicit board decision points. Use tables."
        ),
        description="Board pack spanning all LoBs/frameworks over modeled context.",
    ),
    WorkloadProfile(
        key="pie_pan_india_control_maturity",
        name="Pan-India Control Maturity Assessment (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, produce a full control-maturity "
            "assessment across every framework and control domain in the estate. For each "
            "framework/domain give a maturity rating with justification, evidence strength, gaps and "
            "cross-framework reuse opportunities, then a consolidated maturity heatmap and a prioritized, "
            "multi-quarter improvement plan with owners. Provide control-by-control commentary."
        ),
        description="Estate-wide maturity matrix + heatmap over modeled context.",
    ),
    WorkloadProfile(
        key="pie_enterprise_observation_register",
        name="Enterprise Observation Register (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, generate a detailed enterprise audit "
            "observation register for the full estate. For every observation provide: title, description, "
            "impacted framework(s) and application, evidence source, root cause, severity, risk rating, "
            "recommendation, control owner, target date and closure criteria. Present as a structured "
            "table grouped by framework and application, and close with severity distribution and the "
            "most material systemic themes."
        ),
        description="Long structured register across the modeled Pan-India estate.",
    ),
    WorkloadProfile(
        key="pie_framework_crosswalk_reuse",
        name="Framework Crosswalk & Evidence Reuse (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, produce an enterprise evidence-reuse "
            "and framework-crosswalk report. Include a cross-framework crosswalk of which evidence "
            "satisfies which controls/frameworks; quantify reuse ratios and duplication; identify coverage "
            "gaps and single-points-of-failure evidence; assess over-reliance risk; and recommend "
            "automation and collection-efficiency opportunities. Use tables throughout."
        ),
        description="Crosswalk + reuse + duplication analysis over modeled context.",
    ),
    WorkloadProfile(
        key="pie_risk_exception_governance",
        name="Risk & Exception Governance Review (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, produce an enterprise risk-acceptance "
            "and exception-governance review. Summarize all active exceptions and accepted risks by "
            "framework and application; assess residual risk and compensating controls; flag expiring or "
            "overdue exceptions; identify concentration and systemic risk; and recommend a governance and "
            "remediation-sequencing plan with owners, timelines and escalation triggers. Use tables."
        ),
        description="Exception/risk governance over the modeled Pan-India estate.",
    ),
    WorkloadProfile(
        key="pie_five_year_capacity_forecast",
        name="Five-Year Enterprise Capacity & Governance Narrative (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, write a long-form executive narrative "
            "on the bank's five-year Pan-India compliance, evidence and governance outlook. Cover current "
            "posture and evidence base; projected evidence/application/framework growth; control-maturity "
            "trajectory; governance and operating-model implications; key risks and dependencies; and a "
            "year-by-year set of governance priorities. Ground current-state sections in the reference "
            "context and clearly label forward-looking statements as assumptions."
        ),
        description="Long-form 5-year governance narrative grounded in modeled context.",
    ),
    WorkloadProfile(
        key="pie_ciso_operational_resilience",
        name="CISO Operational Resilience & Risk Briefing (Pan-India Enterprise)",
        category="pan_india_enterprise",
        prompt_class="large",
        response_intent="maximum",
        top_k=TOP_K_MAX,
        modeled_context=True,
        question=(
            "Using the Pan-India enterprise reference context above, prepare a regulator-ready CISO "
            "operational-resilience and technology-risk briefing for the full estate. Include: control "
            "posture by domain across all frameworks; material evidence gaps; open risk themes with "
            "ratings; active exceptions and compensating controls; BCP/DR and resilience posture; "
            "remediation sequencing with owners and timelines; and an overall assurance view. Provide "
            "control-level detail, use tables, and state assumptions and evidence caveats."
        ),
        description="CISO resilience/assurance briefing over the modeled estate.",
    ),
]


def default_profiles() -> list[WorkloadProfile]:
    """Default enterprise workload catalog (20 realistic scenarios).

    Backward compatible: the worst-case tier is intentionally NOT included here so
    existing runs/reports are unchanged. Use ``worst_case_profiles()`` or
    ``all_profiles()`` (or select ``category="worst_case"``) to include it.
    """
    return [*_SIZE_MATRIX, *_CONTEXT_STRESS, *_ENTERPRISE]


def worst_case_output_profiles() -> list[WorkloadProfile]:
    """True worst-case OUTPUT tier (8 maximum-realistic long-output scenarios).

    Additive: targets the maximum realistic OUTPUT-token envelope (board / audit /
    regulator deliverables). Category ``worst_case_output`` so it is selectable on
    its own (``--categories worst_case_output``).
    """
    return list(_WORST_CASE_OUTPUT)


def worst_case_profiles() -> list[WorkloadProfile]:
    """Worst-case enterprise workload tier (maximum-realistic scenarios).

    Includes BOTH the broad worst-case tier (``worst_case``) and the true
    worst-case OUTPUT tier (``worst_case_output``), so worst-case mode and
    ``all_profiles()`` pick up the long-output deliverables automatically.

    Backward compatible: the Pan-India future-state tier is intentionally NOT
    included here, so worst-case mode runs exactly as before. Select Pan-India via
    ``--categories pan_india_enterprise`` (resolved against ``all_profiles()``) or
    ``pan_india_enterprise_profiles()``.
    """
    return [*_WORST_CASE, *_WORST_CASE_OUTPUT]


def pan_india_enterprise_profiles() -> list[WorkloadProfile]:
    """Pan-India future-state tier (8 modeled-context enterprise scenarios).

    Additive: each profile carries ``modeled_context=True`` so the runner prepends
    the BENCHMARK-MODELED Pan-India reference context. Category
    ``pan_india_enterprise`` so it is selectable on its own
    (``--categories pan_india_enterprise``).
    """
    return list(_PAN_INDIA_ENTERPRISE)


def all_profiles() -> list[WorkloadProfile]:
    """Full catalog: default + worst-case tiers + Pan-India tier (50 scenarios)."""
    return [*default_profiles(), *worst_case_profiles(), *pan_india_enterprise_profiles()]


def profiles_by_keys(keys: list[str]) -> list[WorkloadProfile]:
    """Subset of the FULL catalog (default + worst-case + pan-india) by key."""
    wanted = set(keys)
    return [p for p in all_profiles() if p.key in wanted]


def catalog_index() -> dict[str, WorkloadProfile]:
    """Index of the FULL catalog (default + worst-case + pan-india) by profile key."""
    return {p.key: p for p in all_profiles()}
