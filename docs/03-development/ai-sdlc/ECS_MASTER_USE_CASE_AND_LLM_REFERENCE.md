# ECS Master Use Case & LLM Reference

**Type:** Definitive ECS use-case repository (150+) with integration + LLM analysis. **Mode:** Documentation only. No code/UI/DB changes. No commits.
**Grounding:** `config/llm.yaml`, `config/integrations.yaml`, `config/environments/_base.yaml`, `ecs_platform/llm_engine/*`, `ecs_platform/rag.py`, `ecs_platform/connectors/*`, `modules/operations/engines/*connector*.py`, and existing ECS docs.
**Reuses (not duplicated):** [Master Use Case Catalog](../../01-product/product/ECS_MASTER_USE_CASE_CATALOG.md) (IDs reused & extended), [AI Use Case Catalog V2](ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md), [LLM Use Case Coverage Matrix](ECS_LLM_USE_CASE_COVERAGE_MATRIX.md), [Local vs Cloud Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md), [AI Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md).

> **Companion docs:** [LLM Use Case Priority Matrix](ECS_LLM_USE_CASE_PRIORITY_MATRIX.md) · [LLM Implementation Roadmap](ECS_LLM_IMPLEMENTATION_ROADMAP.md).
> **Marking:** Items not directly evidenced in code are flagged **[Inferred/Target]**. ROI figures are **[Inferred/Target — validate]** (see ROI note).

---

## 1. How to read this reference

Each use case carries the full 18-field schema below. To keep 150+ entries usable, ECS documents them in **two layers**:
- **§4 Worked exemplars** — fully-expanded entries (all 18 fields + Integration block + LLM block) for representative use cases per category.
- **§5 Category coverage tables** — every use case (150+) as a structured row carrying the core schema fields (ID · Name · Business Problem · Personas · Module · Trigger · KPIs · Reports · Integration Y/N+Type · LLM Y/N+Role · Local model · Mode · Phase). Where a field is identical to its category default (declared at the top of each category), it is inherited rather than repeated.

**Schema (per use case):** 1 ID · 2 Name · 3 Business Problem · 4 Business Objective · 5 Personas · 6 ECS Module · 7 Trigger Event · 8 Preconditions · 9 Workflow · 10 Inputs · 11 Outputs · 12 KPIs · 13 Reports Generated · 14 Audit Impact · 15 Compliance Impact · 16 Executive Impact · 17 Business Value · 18 ROI.
**Integration block:** Required Y/N · Type · Purpose · Data Retrieved · Evidence Generated · Authentication · Scheduling · Frequency · Failure Handling · Security Controls · YAML Dependency · UAT Dependency · Production Dependency.
**LLM block:** Required Y/N · Role · Prompt Input · Context Sources · RAG Usage · Vector Search · Embedding Usage · Expected Output · Confidence · Human Validation · Local model · RAM · Cloud option · Recommended Mode.

---

## 2. Global LLM & integration architecture (applies to all use cases)

**LLM stack (verified `config/llm.yaml`):** provider-pluggable — `ollama` (default, local) | `gemini` | `openai` | `azure_openai` | `claude`. Default model **`qwen3:8b`**; embeddings **`nomic-embed-text`** (dim 768); `temperature 0.1`; `max_output_tokens 2048`. Ollama reached via `host.docker.internal:11434`.
**RAG (verified):** `top_k 8`, `max_context_chunks 12`, **`require_citations: true`**, **`refuse_without_evidence: true`** → no answer without grounded evidence (anti-hallucination). Retrieval = pgvector similarity over `nomic-embed-text` embeddings (`ecs_vectors`).
**RBAC-before-AI (verified):** role scoping (`app/auth/*`, `config/rbac.yaml`) filters context **before** the model call → no cross-tenant/role data leakage.
**Connectors (verified):** SaaS/enterprise via `ecs_platform/connectors/*` (factory `_REGISTRY`: gitea, github, sonarqube, jenkins, jira, confluence, figma, servicenow, teams, sharepoint, prisma, azure_devops), config in `config/integrations.yaml` (`enabled:false` by default). Predefined-query execution via `modules/operations/engines/*` — **PostgreSQL/Linux/SonarQube/Trivy/Gitleaks implemented**; generic remote DB/SSH/API are `NotImplementedError` (see [Remote Connector Expansion Plan](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md)).

**Local model sizing defaults [Inferred/Target]:**
| Model | RAM (approx) | Use |
|---|---|---|
| Qwen3:4B | 4–6 GB | light classification/tagging, short summaries |
| **Qwen3:8B** (ECS default) | 8–12 GB | RAG Q&A, summarization, drafting (banking sweet spot) |
| Qwen3:14B | 16–24 GB | complex reasoning, control mapping, multi-doc synthesis |
| Gemma 2 (9B) | 8–12 GB | alternative general model |
| nomic-embed-text | 1–2 GB | all embeddings (always local) |

---

## 3. Recommended-mode rationale (banking)

ECS is **local-first** by design (data sovereignty, RBI/PCI data residency, air-gap capability, zero per-token cost). Default recommendation per use-case class:
- **LOCAL ONLY** — anything touching evidence content, control text, observations, classification, RAG Q&A (sensitive data must not leave the bank). Qwen3:8B + nomic-embed-text.
- **HYBRID** — heavy synthesis / board-grade narrative / very long-context where a cloud model materially improves quality **and** inputs can be de-identified or are non-sensitive aggregates.
- **CLOUD ONLY** — effectively none for sensitive paths; reserved for optional non-sensitive aggregate polish where policy permits.

> **Cloud providers in ECS:** code-complete (Gemini/OpenAI/Azure OpenAI/Claude) but not default-active; enabling requires API keys + data-residency sign-off. "Neve" in the prompt is treated as the bank's sanctioned cloud-LLM option (provider-agnostic slot).

---

## 4. Worked exemplars (full 18-field schema)

### UC-A01 — Prove audit readiness fast
1. **ID** UC-A01 · 2. **Name** Audit readiness scoring · 3. **Problem** Audit prep is a reactive fire-drill; teams can't quickly prove readiness. · 4. **Objective** On-demand, defensible readiness score. · 5. **Personas** Auditor, Audit Manager, Compliance, CIO. · 6. **Module** Audit Preparation. · 7. **Trigger** Audit announced / periodic review. · 8. **Preconditions** Frameworks loaded; evidence mapped. · 9. **Workflow** Select scope → compute (control coverage + evidence completeness + validation health) → readiness score + gap list → drill to evidence. · 10. **Inputs** Framework scope, controls, evidence, validation status. · 11. **Outputs** Readiness score (0–100), gap list, drilldowns. · 12. **KPIs** Audit Readiness Score, Control Coverage %, Evidence Completeness %, Validation Health. · 13. **Reports** Audit readiness report, gap report. · 14. **Audit** Pre-audit confidence; fewer findings. · 15. **Compliance** Demonstrable posture per framework. · 16. **Executive** Board-credible readiness number. · 17. **Value** Days→hours of prep. · 18. **ROI** [Inferred/Target] high — avoided audit overruns.
- **Integration:** **NO** (uses ECS-resident evidence/controls).
- **LLM:** **Optional (Hybrid value-add)** — Role: Audit Readiness Assessment/Summary. Prompt: "Summarize readiness + top gaps for <framework>." Context: readiness KPIs + gap list (RBAC-scoped). RAG: yes (cite evidence/control records). Vector/Embedding: yes. Output: narrative + prioritized gaps. Confidence: Medium-High. Human validation: **Yes** (auditor sign-off). Local: Qwen3:8B (8–12 GB). Cloud: optional for board narrative. **Mode: LOCAL ONLY** (sensitive).

### UC-E10 — Semantic evidence search
1. **ID** UC-E10 · 2. **Name** Semantic evidence retrieval · 3. **Problem** Keyword search misses relevant evidence phrased differently. · 4. **Objective** Find evidence by meaning, grounded + cited. · 5. **Personas** Auditor, Compliance, Application Owner. · 6. **Module** AI Assistant / Search. · 7. **Trigger** User question / evidence hunt. · 8. **Preconditions** Content indexed into pgvector. · 9. **Workflow** Query → embed (nomic-embed-text) → pgvector top_k → RBAC filter → cited answer or refusal. · 10. **Inputs** Natural-language query, role scope. · 11. **Outputs** Ranked evidence + citations. · 12. **KPIs** Retrieval relevance [Target], answer-with-citation rate. · 13. **Reports** N/A (interactive). · 14. **Audit** Faster defensible answers. · 15. **Compliance** Evidence-backed claims. · 16. **Executive** Analyst productivity. · 17. **Value** Find-fast; minutes saved per query. · 18. **ROI** [Inferred/Target] medium-high (volume).
- **Integration:** **NO**.
- **LLM:** **YES** — Role: Chatbot/RAG retrieval. Prompt: user question. Context: pgvector chunks (`top_k 8`, `max 12`). RAG: **yes (core)**; `require_citations`, `refuse_without_evidence`. Vector/Embedding: **yes (core)**. Output: cited answer or explicit refusal. Confidence: Medium-High (grounded). Human validation: advisory. Local: Qwen3:8B + nomic-embed-text. **Mode: LOCAL ONLY**.

### UC-F04 — OS baselining at scale
1. **ID** UC-F04 · 2. **Name** Linux OS baselining via predefined queries · 3. **Problem** Manual host hardening checks don't scale and aren't objective. · 4. **Objective** Automated, evidence-generating control tests. · 5. **Personas** Operations, Compliance, Auditor. · 6. **Module** Predefined Queries. · 7. **Trigger** Scheduled / on-demand control run. · 8. **Preconditions** Target reachable; control flagged live-executable; allow-listed command. · 9. **Workflow** Control → LinuxConnector (`docker exec` / [Target] SSH) → parse → pass/fail → evidence → control/framework map → dashboard. · 10. **Inputs** Control id, target, command (`LINUX_CONTROL_COMMANDS`). · 11. **Outputs** Pass/fail + extracted values + evidence row. · 12. **KPIs** Control coverage, query pass rate. · 13. **Reports** Baseline compliance report. · 14. **Audit** Objective, repeatable evidence. · 15. **Compliance** OS baseline framework posture. · 16. **Executive** Hardening assurance. · 17. **Value** Eliminates manual checks. · 18. **ROI** [Inferred/Target] high (scale).
- **Integration:** **YES** — Type: **Linux**. Purpose: run hardening checks. Data: command stdout (sshd_config, sysctl, etc.). Evidence: pass/fail + raw output. Auth: container exec (demo) / SSH key [Target prod]. Scheduling: Scheduler. Frequency: per policy (e.g., daily/weekly). Failure: structured (timeout/connection) — no crash. Security: read-only commands, allow-list. YAML: `predefined_query_targets.linux` / `os_servers`. UAT: ubuntu-demo or UAT hosts. Prod: SSHConnector + real hosts ([Remote Connector Plan](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md)).
- **LLM:** **Optional** — Role: Summarize baseline failures / remediation guidance. RAG: yes (cite results). **Mode: LOCAL ONLY**. Human validation: Yes for remediation.

### UC-AI04 — Draft observation / rejection reason
1. **ID** UC-AI04 · 2. **Name** Observation & rejection drafting · 3. **Problem** Reviewers write inconsistent, slow rejection/observation text. · 4. **Objective** Consistent, evidence-cited drafts. · 5. **Personas** Reviewer, Auditor, Compliance. · 6. **Module** Evidence Review / AI Assistant. · 7. **Trigger** Reviewer requests draft on a finding. · 8. **Preconditions** Evidence + control context available. · 9. **Workflow** Context (control + evidence gap) → LLM draft → reviewer edits → persisted observation (durable when `OBSERVATIONS_DURABLE_ENABLED`). · 10. **Inputs** Control, evidence, gap detail. · 11. **Outputs** Draft observation/rejection text. · 12. **KPIs** Reviewer throughput, time-to-decision. · 13. **Reports** Observation register. · 14. **Audit** Consistent, defensible findings. · 15. **Compliance** Clear remediation asks. · 16. **Executive** Faster closure cycles. · 17. **Value** Minutes saved per review. · 18. **ROI** [Inferred/Target] medium-high (volume).
- **Integration:** **NO**.
- **LLM:** **YES** — Role: Observation Drafting/Summarization. Prompt: control+gap context. Context: RBAC-scoped evidence. RAG: yes. Vector/Embedding: yes. Output: draft text. Confidence: Medium. Human validation: **Yes (mandatory)**. Local: Qwen3:8B. **Mode: LOCAL ONLY** (sensitive findings).

### UC-X02 — Board-ready executive summary
1. **ID** UC-X02 · 2. **Name** Executive/board summary generation · 3. **Problem** Synthesizing enterprise posture into a board narrative is slow. · 4. **Objective** Auto-draft an evidence-grounded executive summary. · 5. **Personas** CIO, CISO, Executive. · 6. **Module** Executive Summary / AI Assistant. · 7. **Trigger** Board cycle / on-demand. · 8. **Preconditions** Enterprise KPIs computed. · 9. **Workflow** Aggregate KPIs → LLM narrative → exec edits → export. · 10. **Inputs** Enterprise KPIs, trends, risks. · 11. **Outputs** Narrative summary. · 12. **KPIs** Compliance %, readiness, risk posture, ROI. · 13. **Reports** Executive summary report. · 14. **Audit** Governance narrative. · 15. **Compliance** Posture articulation. · 16. **Executive** Board-ready in minutes. · 17. **Value** Hours saved per cycle. · 18. **ROI** [Inferred/Target] medium.
- **Integration:** **NO**.
- **LLM:** **YES** — Role: Executive Summary. Context: **aggregate** KPIs (low sensitivity). RAG: yes. Output: narrative. Confidence: Medium. Human validation: **Yes**. Local: Qwen3:8B/14B. Cloud: **Hybrid candidate** (aggregates de-identified; cloud polish acceptable per policy). **Mode: HYBRID**.

### UC-I03 — ServiceNow change/CAB evidence
1. **ID** UC-I03 · 2. **Name** ServiceNow change & CAB evidence ingestion · 3. **Problem** Change-control evidence lives in ServiceNow, disconnected from GRC. · 4. **Objective** Auto-ingest change/CAB records as evidence. · 5. **Personas** Compliance, Auditor, Ops. · 6. **Module** Connector Framework / Integrations. · 7. **Trigger** Scheduled sync. · 8. **Preconditions** Connector enabled + credentials. · 9. **Workflow** ServiceNowConnector pull → normalize → evidence → control/framework map → repository. · 10. **Inputs** SNOW change/CAB records. · 11. **Outputs** Evidence rows + mappings. · 12. **KPIs** Connector health, evidence freshness. · 13. **Reports** Change-control evidence report. · 14. **Audit** Change governance trail. · 15. **Compliance** ITPP/change-mgmt controls. · 16. **Executive** Control automation. · 17. **Value** Eliminates manual export. · 18. **ROI** [Inferred/Target] medium-high.
- **Integration:** **YES** — Type: **ServiceNow**. Purpose: change/CAB evidence. Data: change requests, approvals, CAB minutes. Evidence: normalized change records. Auth: OAuth2/Basic (`*_env` secrets). Scheduling: Scheduler. Frequency: daily [default]. Failure: retry + structured error; connector health flag. Security: least-privilege API user, TLS. YAML: `config/integrations.yaml` (`servicenow`). UAT: sandbox tenant. Prod: prod tenant + vault creds.
- **LLM:** **Optional** — Role: summarize change risk. **Mode: LOCAL ONLY**. Human validation: advisory.

### UC-O01 — Automated evidence collection (scheduler)
1. **ID** UC-O01 · 2. **Name** Scheduled evidence collection · 3. **Problem** Manual evidence gathering is slow and lapses. · 4. **Objective** Continuous automated collection. · 5. **Personas** Operations, Admin, Compliance. · 6. **Module** Scheduler. · 7. **Trigger** Schedule fires. · 8. **Preconditions** Connectors enabled; schedules defined. · 9. **Workflow** Scheduler → connector pulls / query runs → evidence → repository → freshness KPIs. · 10. **Inputs** Schedules, connector configs. · 11. **Outputs** Fresh evidence, run history. · 12. **KPIs** Evidence freshness, sync success rate. · 13. **Reports** Sync run audit. · 14. **Audit** Continuous evidence. · 15. **Compliance** Always-ready posture. · 16. **Executive** Operational efficiency. · 17. **Value** Removes manual cadence. · 18. **ROI** [Inferred/Target] high.
- **Integration:** **YES** — Type: **multiple** (any enabled connector / query connector). See per-connector blocks. Scheduling: core. Failure: retry/alert (see [Scheduler Reference](../operations/ECS_SCHEDULER_REFERENCE.md)).
- **LLM:** **NO**.

---

## 5. Category coverage tables (all use cases)

**Legend:** Integ = integration required (type) · LLM = LLM role (—=none) · Mode = recommended (L=Local only, H=Hybrid, C=Cloud) · Local = recommended local model (Q4=Qwen3:4B, Q8=Qwen3:8B, Q14=Qwen3:14B) · HV = human validation. Reports/Audit/Compliance/Exec impact inherit category defaults unless noted. Full schema for representative rows in §4.

### Cat 1–5. Evidence Management / Reuse / Versioning / Classification / Search
*Default module: Evidence Repository · Personas: Application Owner, Reviewer, Auditor, Compliance · Reports: evidence/approval/health reports.*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-E01 | Centralize evidence | Scattered evidence | Upload/sync | Evidence count, completeness | Opt (any) | — | — | L | — |
| UC-E02 | Bulk import | Mass onboarding slow | Bulk upload | Import success % | No | Classification (opt) | Q4 | L | Y |
| UC-E03 | Validate sufficiency | Weak evidence accepted | On submit | Sufficiency score | No | Classification | Q8 | L | Y |
| UC-E04 | Approve/reject + reason | Inconsistent decisions | Review | Approval rate | No | Observation drafting | Q8 | L | Y |
| UC-E05 | Resubmit rejected | Slow remediation | On reject | Rework cycle time | No | — | — | L | — |
| UC-E06 | Detect expiring evidence | Stale evidence | Schedule | Expiry count, freshness | No | — | — | L | — |
| UC-E07 | Evidence lineage | No traceability | Drilldown | Lineage completeness | No | — | — | L | — |
| UC-E08 | Cross-framework reuse | Duplicate collection | Map | Reuse multiplier | No | Evidence reuse | Q8 | L | Y |
| UC-E09 | Cross-tool correlation | Siloed signals | Correlate | Correlation groups | Opt (multi) | Summarization | Q8 | L | adv |
| UC-E10 | Semantic search | Keyword misses | Query | Relevance [T] | No | RAG retrieval | Q8 | L | adv |
| UC-E11 | Faceted search | Hard discovery | Filter | Result precision | No | — | — | L | — |
| UC-E12 | Evidence health scoring | Decay unseen | Schedule | Health score | No | — | — | L | — |
| UC-E13 | Auto-classify evidence [T] | Manual tagging | On upload | Classification accuracy [T] | No | Classification | Q4/Q8 | L | Y |
| UC-E14 | Evidence versioning | No version trail | Resubmit | Version depth | No | — | — | L | — |
| UC-E15 | Evidence archival/retention | Retention risk | Policy | Retention compliance | No | — | — | L | — |

### Cat 6–8. Framework Assessment / Readiness / Mapping
*Default module: Framework Assessment · Personas: Compliance, Framework Owner, Auditor, CIO · Reports: framework compliance report.*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-F01 | Onboard framework | Slow regulation adoption | Load library | Controls loaded | No | Framework guidance | Q8 | L | Y |
| UC-F02 | PCI DSS posture | Payment compliance | Assess | PCI KPIs | Opt | Summarization | Q8 | L | Y |
| UC-F03 | DPSC self-assessment | RBI alignment | Workbook | DPSC coverage | No | Framework guidance | Q8 | L | Y |
| UC-F06 | Framework readiness | Unknown readiness | Compute | Readiness score | No | Audit readiness | Q8 | L | Y |
| UC-F10 | Control→regulation mapping | Coverage unclear | Map | Theme coverage | No | Control mapping | Q14 | H | Y |
| UC-F11 | Compare maturity | Investment focus | Compare | Maturity bars | No | Summarization | Q8 | L | adv |
| UC-F12 | Reuse multiplier | Duplicate effort | Crosswalk | Reuse % | No | Evidence reuse | Q8 | L | Y |

### Cat 9–11. Control Library / Reuse / Mapping
*Default module: Control Library · Personas: Compliance, Framework Owner, Control Owner, Auditor · Reports: control coverage/effectiveness.*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-C01 | Maintain control library | No baseline | Admin | Control count (305) | No | — | — | L | — |
| UC-C02 | Assign ownership | No accountability | Assign | Ownership % | No | — | — | L | — |
| UC-C03 | Assess maturity | Unknown maturity | Assess | Maturity dist | No | Risk assessment | Q8 | L | Y |
| UC-C04 | Validate coverage | Hidden gaps | Compute | Coverage % | No | — | — | L | — |
| UC-C05 | Test control via query | Manual testing | Run query | Pass rate | **Yes** (PG/Linux/etc.) | Summarization (opt) | Q8 | L | adv |
| UC-C06 | Cross-framework control reuse | Duplicate controls | Crosswalk | Shared controls | No | Control mapping | Q14 | H | Y |
| UC-C10 | Control effectiveness | False assurance | Compute | Effectiveness | No | Risk assessment | Q8 | L | Y |
| UC-C11 | Close control | Open backlog | Remediate | Closure rate | No | — | — | L | — |

### Cat 12–15. Observation Management / Closure / Risk Acceptance / RAF
*Default module: Governance / Risk / Exceptions · Personas: Compliance, Risk, Auditor, ISG · Reports: observation/risk register. See [Observation Plan](../../01-product/use-cases/ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md), [RAF Plan](../../01-product/use-cases/ECS_RAF_IMPLEMENTATION_PLAN.md).*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-OB01 | Raise observation | Gaps untracked | On gap | Open observations | No | Observation drafting | Q8 | L | Y |
| UC-OB02 | Track to closure | Findings linger | Lifecycle | Closure rate, aging | No | Summarization | Q8 | L | adv |
| UC-OB03 | Durable observation persistence | Lost on restart | Flag on | Persistence integrity | No | — | — | L | — |
| UC-OB04 | Auto-close on control closure | Manual cleanup | Control closed | Auto-close count | No | — | — | L | — |
| UC-C07 | Raise control exception | Risk untracked | On gap | Open exceptions | No | Observation drafting | Q8 | L | Y |
| UC-C08 | Govern exceptions/TD | Uncontrolled risk | CAB | Exception lifecycle | No | Risk assessment | Q8 | L | Y |
| UC-C09 | Compensating controls | Pragmatic gaps | On exception | Compensating count | No | Recommendation | Q8 | L | Y |
| UC-RAF01 | Risk acceptance (via exception) [current] | No formal RAF | Accept risk | Accepted risks | No | Risk assessment | Q8 | L | Y |
| UC-RAF02 | First-class RAF + ISG approval [Target] | No time-boxed RAF | Submit RAF | RAF status, expiry | No | Risk assessment | Q8 | L | Y |
| UC-RAF03 | Risk acceptance lifecycle [Target] | No renewal control | Expiry | Expiring RAFs | No | Recommendation | Q8 | L | Y |

### Cat 16–18. Executive / Audit / Governance Reporting
*Default module: Reports / Executive Summary / Governance Analytics · Personas: CIO, CISO, Auditor, Compliance, Heads · Reports: as named.*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-X01 | CIO single-pane posture | No unified view | Open dashboard | Enterprise KPIs | No | Executive summary | Q8 | H | Y |
| UC-X02 | Board-ready summary | Slow synthesis | Board cycle | Posture KPIs | No | Executive summary | Q8/Q14 | H | Y |
| UC-X03 | Quantify ROI | No value story | Compute | Annual value | No | Summarization | Q8 | H | Y |
| UC-RP01 | Audit reports | Manual report build | Scope | Coverage | No | Summarization | Q8 | L | Y |
| UC-RP06 | Executive summary report | Board prep | Export | Posture | No | Executive summary | Q8 | H | Y |
| UC-RP09 | Risk report | Governance need | Export | Risk KPIs | No | Risk assessment | Q8 | L | Y |
| UC-G01 | Governance analytics | Weak oversight | Open | Governance metrics | No | Summarization | Q8 | L | adv |
| UC-G05 | Exception governance/CAB | Uncontrolled risk | CAB | Exception approvals | No | Risk assessment | Q8 | L | Y |
| UC-G11 | AI governance operating model | Irresponsible AI | Lifecycle | AI compliance score | No | Risk assessment | Q8 | L | Y |

### Cat 19–21. Application Inventory / Onboarding / CMDB
*Default module: Application Inventory / Onboarding / CMDB · Personas: Ops, Admin, Compliance · Reports: inventory/onboarding. See [Onboarding Guide](../operations/ECS_APPLICATION_ONBOARDING_GUIDE.md).*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-O04 | Onboard application | Coverage gaps | New app | Apps onboarded | Opt | Recommendation | Q8 | L | Y |
| UC-W01 | Application onboarding workflow | Inconsistent onboarding | New app | Onboarding completeness | Opt | Framework guidance | Q8 | L | Y |
| UC-G06 | CMDB/asset governance | Unknown assets | Register | Asset inventory | Opt (CMDB) | — | — | L | — |
| UC-AP01 | Tech identification | Unknown stack | Onboard | Tech tagged | No | Classification | Q8 | L | Y |
| UC-AP02 | Framework identification | Wrong scope | Onboard | Frameworks mapped | No | Framework guidance | Q8 | L | Y |

### Cat 22–23. Scheduler Execution / Predefined Query Execution
*Default module: Scheduler / Predefined Queries · Personas: Ops, Admin, Compliance · Reports: sync run audit, baseline report. See [Predefined Query Architecture](../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md).*

| ID | Name | Business Problem | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|---|
| UC-O01 | Scheduled evidence collection | Manual cadence | Schedule | Freshness, success rate | Yes (multi) | — | — | L | — |
| UC-O06 | Scheduler failure handling | Silent failures | Failure | Failure/retry count | Yes | — | — | L | — |
| UC-O11 | Sync run audit | No accountability | Run | Run history | Yes | — | — | L | — |
| UC-O03 | Query-driven controls | Manual checks | Run query | Pass rate | **Yes** | Summarization (opt) | Q8 | L | adv |
| UC-PQ01 | Predefined query execution | No objective test | Run | Evidence generated | **Yes** | — | — | L | — |
| UC-PQ02 | Remote target execution [Target] | No remote evidence | Run | Remote pass rate | **Yes** (remote) | — | — | L | — |

### Cat 24–29. Baselining (Linux / Windows / PostgreSQL / Aurora MySQL / Yugabyte / Nginx)
*Default module: Predefined Queries · Personas: Ops, Compliance, Auditor · Reports: baseline compliance report. Integration = the target technology. LLM = optional remediation summary (Local, HV=Y).*

| ID | Name | Integration (type) | Status | KPIs | Mode |
|---|---|---|---|---|---|
| UC-BL01 | Linux baselining | **Linux** (docker exec; SSH [Target]) | ✅ Implemented (demo) | Pass rate | L |
| UC-BL02 | Windows baselining | **Windows** (WinRM) [Target] | ❌ To build | Pass rate | L |
| UC-BL03 | PostgreSQL baselining | **PostgreSQL** (psycopg2) | ✅ Implemented | Pass rate | L |
| UC-BL04 | Aurora MySQL baselining | **MySQL** driver [Target] | ❌ To build | Pass rate | L |
| UC-BL05 | Yugabyte baselining | **PostgreSQL-wire** (psycopg2-compatible) [Inferred] | ⚠ Likely via PG connector — validate | Pass rate | L |
| UC-BL06 | Nginx baselining | **Linux/SSH** (config inspection) [Target] | ⚠ via Linux connector | Pass rate | L |
| UC-BL07 | Oracle baselining | **Oracle** driver [Target] | ❌ To build | Pass rate | L |
| UC-BL08 | SQL Server baselining | **SQL Server** (pyodbc) [Target] | ❌ To build | Pass rate | L |
| UC-BL09 | Trivy image scan | **Trivy** (subprocess) | ✅ Implemented | CVE count | L |
| UC-BL10 | Gitleaks secret scan | **Gitleaks** (subprocess) | ✅ Implemented | Secrets found | L |
| UC-BL11 | SonarQube quality gate | **SonarQube** (API) | ✅ Implemented | Issues/coverage | L |

### Cat 30–35. Frameworks (PCI DSS / DPSC / ITPP / ITDRM / VAPT / AppSec)
*Default module: Framework Assessment · Personas: Compliance, Risk, AppSec, Auditor · Reports: framework compliance report. See [Framework Coverage Audit](../../01-product/product/ECS_FRAMEWORK_COVERAGE_AUDIT.md).*

| ID | Name | Trigger | KPIs | Integ | LLM | Local | Mode | HV |
|---|---|---|---|---|---|---|---|---|
| UC-FW-PCI | PCI DSS compliance | Assess | PCI posture | Opt (scans) | Summarization | Q8 | L | Y |
| UC-FW-DPSC | DPSC self-assessment | Workbook | DPSC coverage | No | Framework guidance | Q8 | L | Y |
| UC-FW-ITPP | ITPP policy adherence | Assess | Adherence % | Opt (Confluence) | Framework guidance | Q8 | L | Y |
| UC-FW-ITDRM | ITDRM resilience | Attest | DR readiness | Opt | Summarization | Q8 | L | Y |
| UC-FW-VAPT | VAPT remediation tracking | Findings | Open VAPT | Opt (scanners) | Risk assessment | Q8 | L | Y |
| UC-FW-APPSEC | AppSec gates | Scan | Quality gate | **Yes** (Sonar/Trivy/Gitleaks) | Summarization | Q8 | L | adv |
| UC-FW-CSITE | C-SITE assessment | Assess | C-SITE posture | No | Framework guidance | Q8 | L | Y |
| UC-FW-ISG | ISG self-assessment | Attest | ISG score | No | Framework guidance | Q8 | L | Y |

### Cat 36. Connector Framework
*Default module: Connector Framework / Integrations · Personas: Admin, Ops, Integration Architect · Reports: integration health. See [Integrations](../connectors/_legacy_INTEGRATIONS_index.md).*

| ID | Name | Integration (type) | Data Retrieved | Auth | Mode |
|---|---|---|---|---|---|
| UC-I01 | Jira delivery evidence | **Jira** | issues, sprints, links | PAT/OAuth2 | L |
| UC-I02 | Confluence policy evidence | **Confluence** | pages, policies | PAT/OAuth2 | L |
| UC-I03 | ServiceNow change/CAB | **ServiceNow** | change/CAB records | OAuth2/Basic | L |
| UC-I04 | Prisma cloud findings | **Prisma Cloud** | cloud posture findings | API key | L |
| UC-I05 | SharePoint evidence files | **SharePoint** (Graph) | documents | Azure AD app | L |
| UC-I06 | Teams approval evidence | **Microsoft Teams** (Graph) | messages/approvals | Azure AD app | L |
| UC-I07 | Azure DevOps SDLC | **Azure DevOps** | PRs, pipelines | PAT | L |
| UC-I08 | GitHub SCM evidence | **GitHub** | PRs, branches | PAT/App | L |
| UC-I09 | Jenkins build/test | **Jenkins** | builds, tests | token | L |
| UC-I10 | No-code tenant onboarding | **any** (config) | n/a | env/vault | L |
| UC-I11 | Gitea SCM evidence | **Gitea** | repos, PRs | token | L |
| UC-I12 | Figma design evidence | **Figma** | design files | token | L |
| UC-I13 | Connector health monitoring | **all** | sync status | n/a | L |

*Integration block defaults for Cat 36: Evidence = normalized records → repository; Scheduling = Scheduler; Frequency = daily [default]; Failure = retry + health flag + structured error; Security = least-privilege API user + TLS + secrets via `*_env`/vault; YAML = `config/integrations.yaml`; UAT = sandbox tenant; Prod = prod tenant + vault. LLM = optional summarization (Local, advisory).*

### Cat 37–40. AI Assistant / Audit Copilot / Governance Copilot / Executive Copilot
*Default module: AI Assistant · Personas: per copilot · LLM: YES (core) · RAG/Vector/Embedding: yes · Mode: LOCAL ONLY (sensitive) except exec aggregates (Hybrid).*

| ID | Name | LLM Role | Persona | Context | Confidence | HV | Local | Mode |
|---|---|---|---|---|---|---|---|---|
| UC-AI01 | Citation-grounded Q&A | Chatbot/RAG | All | evidence/controls | Med-High | adv | Q8 | L |
| UC-AI02 | Refuse without evidence | Guardrail | All | n/a | High | — | Q8 | L |
| UC-AI03 | Semantic retrieval | RAG retrieval | Auditor | pgvector | Med-High | adv | Q8 | L |
| UC-AI06 | Summarize framework posture | Summarization | Compliance | framework KPIs | Med | Y | Q8 | L |
| UC-AI07 | RBAC-scoped AI | Access control | All | role scope | High | — | Q8 | L |
| UC-AI08 | Local-first private AI | Infra/privacy | Bank | on-host | High | — | Q8 | L |
| UC-CP01 | Audit Copilot | Audit readiness + Q&A | Auditor/Audit Mgr | evidence/controls | Med-High | Y | Q8/Q14 | L |
| UC-CP02 | Governance Copilot | Recommendation + guidance | Governance/Compliance | governance data | Med | Y | Q8 | L |
| UC-CP03 | Executive Copilot | Executive summary | CIO/CISO | aggregate KPIs | Med | Y | Q8/Q14 | H |
| UC-CP04 | Ops Governance Copilot | Recommendation | Ops/Admin | ops/connector data | Med | adv | Q8 | L |
| UC-AI09 | AI-SDLC stage gating | Risk assessment | AI SDLC | stage evidence | Med | Y | Q8 | L |
| UC-AI10 | AI governance posture | Risk assessment | AI Gov | 6 AI dims | Med | Y | Q8 | L |
| UC-AI11 | Hybrid cloud fallback [Target] | Scale offload | Bank | de-identified | Med | Y | n/a | H |

### Additional cross-domain use cases (reused from Master Catalog)
The remaining IDs from the [Master Use Case Catalog](../../01-product/product/ECS_MASTER_USE_CASE_CATALOG.md) are incorporated by reference and inherit the LLM/Integration/Mode defaults of their category above: **Audit** UC-A02–A12, **Evidence** (covered), **Risk** UC-R01–R11, **Compliance** UC-K01–K11, **Governance** UC-G02–G10, **Executive** UC-X04–X11, **Operations** UC-O02/O05/O07–O10, **Reporting** UC-RP02–RP08/RP10, **Search** UC-S01–S08, **Workflow** UC-W02–W10.

**Total catalogued: 150+ use cases** (≈40 detailed/exemplar rows above + the full reused catalog by reference).

---

## 6. Local LLM analysis (summary)
- **Recommended default:** **Qwen3:8B** (ECS default) for RAG Q&A, summarization, drafting, framework guidance — banking sweet spot of quality vs. RAM.
- **Qwen3:4B:** lightweight classification/tagging (UC-E02/E13, UC-AP01) on constrained hosts.
- **Qwen3:14B / Gemma2-9B:** complex reasoning — control mapping (UC-F10/C06), board narrative (UC-X02), multi-doc synthesis — where RAM (16–24 GB) permits.
- **Embeddings:** **nomic-embed-text** (always local, dim 768) for all vector search.
- **Performance [Inferred/Target]:** interactive Q&A acceptable on 8B with `keep_alive` resident; batch classification favors 4B; reserve 14B for offline/async synthesis. Validate with [AI Performance Benchmark](../../04-testing/benchmarks/ECS_AI_PERFORMANCE_BENCHMARK.md).

## 7. Cloud LLM analysis (summary)
- **Providers (code-complete, off by default):** Gemini, OpenAI, Azure OpenAI, Claude — treated as the bank's sanctioned **"Neve"** cloud slot (provider-agnostic).
- **Benefits:** stronger long-context synthesis, polish for board narrative, burst scale.
- **Trade-offs:** per-token cost, **data residency / sovereignty risk** (PCI/RBI), network dependency, vendor lock-in. **Not permitted for sensitive evidence content.**
- **Use only for:** non-sensitive aggregates / de-identified executive narrative, with policy sign-off.

## 8. Hybrid AI analysis (recommendation)
- **LOCAL ONLY** — all evidence/control/observation/classification/search/copilot paths (the vast majority). Data never leaves the bank.
- **HYBRID** — executive/board narrative (UC-X02, UC-CP03), heavy control-mapping synthesis (UC-F10/C06), optional cloud-quality boost on de-identified aggregates; local remains the fallback.
- **CLOUD ONLY** — none for sensitive data.

**Final recommendation:** **LOCAL FIRST**, with an optional **HYBRID** tier for non-sensitive executive synthesis — grounded in ECS's local-first architecture (`provider: ollama`, qwen3:8b, pgvector, RBAC-before-AI, `refuse_without_evidence`) and banking data-residency requirements. See [LLM Implementation Roadmap](ECS_LLM_IMPLEMENTATION_ROADMAP.md) for sequencing.

## ROI note
ROI grounded in `config/roi.yaml` (`roi/workbook.py`): hours-saved × rate + reuse savings. A documented **rate-basis discrepancy** exists (`cost_per_hour: 1500` vs ₹1,000/hr tables — see [documentation audit](../../executive/documentation_audit.md)); per-use-case ROI is **[Inferred/Target — validate]**.

## Cross-references
- [LLM Use Case Priority Matrix](ECS_LLM_USE_CASE_PRIORITY_MATRIX.md) · [LLM Implementation Roadmap](ECS_LLM_IMPLEMENTATION_ROADMAP.md) · [AI Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) · [Local vs Cloud Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) · [AI Use Case Catalog V2](ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md) · [Master Use Case Catalog](../../01-product/product/ECS_MASTER_USE_CASE_CATALOG.md) · [Master KPI Dictionary](../../01-product/product/ECS_MASTER_KPI_DICTIONARY.md)
