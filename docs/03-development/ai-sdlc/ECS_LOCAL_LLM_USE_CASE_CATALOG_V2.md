# ECS Local LLM Use Case Catalog V2

**Type:** Use-case documentation (expansion of [ECS_LOCAL_LLM_USE_CASE_CATALOG.md](ECS_LOCAL_LLM_USE_CASE_CATALOG.md) from 28 → **104** use cases). **No code changed.** **Grounding:** `ecs_platform/rag.py`, `provider.py`, AI SDLC/operations/governance engines, route registrars. All run on **local Ollama** (`qwen3:8b` + `nomic-embed-text` → pgvector). ROI/benefit is a **qualitative banking estimate**.

**Each use case below carries:** Business Problem · Inputs · Processing Flow · Outputs · Personas · Screens · APIs · Data Sources · Expected Benefits. Domains share a common **processing flow** (the ECS RAG pipeline), summarized once in §0 and referenced per card.

---

## 0. Shared processing flow (the ECS RAG pipeline)

Most cards follow this grounded pipeline (`rag.py:599-656`):

> **Query → RBAC scope filter (`_rbac_filter`) → Retrieval (pgvector semantic, repository fallback `_retrieve`) → Enrichment (reuse + framework crosswalk `_enrich`) → Governance facts (`_governance_facts`) → Grounding gate (refuse if no evidence) → `provider.generate()` with `SYSTEM_PROMPT` → cited answer.**

Embedding/index flow (`rag.py:259-384`): repository + governance docs → `chunk_text` (1000/150) → `provider.embed` → pgvector upsert (incremental, content-hash dedup). Common **APIs:** `/api/platform/assistant`, `/mvp/ai-assistant`, `/mvp/ai-ops-assistant`, AI-SDLC `/api/ai-sdlc/*`. Common **Data Sources:** `evidence`, `evidence_reviews`, `control_catalog`, `control_framework_crosswalk`, `applications`, `evidence_lineage`, `audit_log`, pgvector `evidence_embeddings`.

---

## 1. Master catalog (104 use cases)

| # | Use Case | Domain | Persona | Primary Screen | Benefit |
|---|---|---|---|---|---|
| 1 | Audit Copilot Q&A | Audit | Auditor | `/mvp/ai-assistant` | Faster audit answers |
| 2 | Audit readiness narrative | Audit | Audit Lead | `/mvp/audit-prep` | Readiness story |
| 3 | Observation clustering | Audit | Auditor | `/mvp/audit-prep` | Triage speed |
| 4 | Observation disposition suggestion | Audit | Auditor | `/mvp/audit-prep` | Consistent calls |
| 5 | Mock-audit findings draft | Audit | Auditor | `/mvp/workflow/mock-audit` | Pre-audit prep |
| 6 | Audit-pack summary | Audit | Auditor/CIO | `/mvp/reports` | Board-ready packs |
| 7 | Rejection-reason drafting | Audit | Auditor | `/evidence/review` | Consistency |
| 8 | Evidence sufficiency narrative | Audit | Auditor | `/evidence/review` | Defensible calls |
| 9 | Auditor question pre-answering | Audit | Auditor | `/mvp/ai-assistant` | Fewer follow-ups |
| 10 | Audit timeline reconstruction | Audit | Auditor | `/mvp/audit-prep` | Faster fieldwork |
| 11 | Evidence classification/auto-tag | Evidence | App Owner | `/mvp/upload` | Less triage |
| 12 | Evidence summarization | Evidence | Auditor | `/evidence/review` | Faster review |
| 13 | Evidence quality scoring | Evidence | Auditor | `/mvp/evidence-health` | Quality control |
| 14 | Evidence deduplication | Evidence | App Owner | `/mvp/evidence-explorer` | Storage/review savings |
| 15 | Similar-evidence discovery | Evidence | App Owner | `/mvp/reuse` | Reuse |
| 16 | Evidence recommendation | Evidence | App Owner | `/mvp/completeness` | Collection guidance |
| 17 | Evidence freshness narrative | Evidence | Governance | `/mvp/lifecycle` | Decay awareness |
| 18 | Evidence lineage explanation | Evidence | Auditor | `/mvp/evidence-explorer` | Traceability |
| 19 | Bulk-upload auto-mapping assist | Evidence | App Owner | `/mvp/upload` | Faster onboarding |
| 20 | Evidence anomaly detection | Evidence | Governance | `/mvp/evidence-health` | Catch outliers |
| 21 | Evidence-to-control mapping | Evidence | Compliance | `/mvp/completeness` | Coverage |
| 22 | Control → framework mapping | Framework | Compliance | `/mvp/framework-loader` | Onboarding speed |
| 23 | Cross-framework correlation | Framework | Compliance | `/mvp/reuse` | Reuse intelligence |
| 24 | Framework onboarding gap narrative | Framework | FW Owner | `/mvp/framework-admin` | Faster activation |
| 25 | Control gap detection | Framework | Compliance | `/mvp/completeness` | Audit prep |
| 26 | Regulatory crosswalk explanation | Framework | Compliance | `/mvp/regulatory` | Normalize regs |
| 27 | Control description normalization | Framework | FW Owner | `/mvp/framework-admin` | Catalog quality |
| 28 | New-regulation impact summary | Framework | Compliance | `/mvp/regulatory` | Change readiness |
| 29 | Framework coverage commentary | Framework | Compliance | `/framework/{name}` | Posture clarity |
| 30 | Control overlap detection | Framework | Compliance | `/mvp/reuse` | De-duplicate effort |
| 31 | Framework maturity narrative | Framework | Compliance | `/mvp/enterprise` | Maturity story |
| 32 | Governance Copilot | Governance | Gov Lead | `/mvp/ai-assistant` | Governance Q&A |
| 33 | Completeness gap narrative | Governance | Compliance | `/mvp/completeness` | Close gaps |
| 34 | Policy summarization | Governance | Governance | `/mvp/ai-assistant` | Digest policy |
| 35 | SOP summarization | Governance | Operations | `/mvp/ai-ops-assistant` | Operator speed |
| 36 | Governance data-quality explanation | Governance | Admin | `/mvp/governance-quality` | Self-heal data |
| 37 | Exception (TD) risk analysis | Governance | Compliance | `/mvp/exceptions` | TD risk control |
| 38 | Lifecycle-stage explanation | Governance | Compliance | `/mvp/lifecycle` | Process clarity |
| 39 | Attestation-readiness narrative | Governance | Governance | `/mvp/audit-prep` | Attestation prep |
| 40 | Exception governance CAB summary | Governance | Compliance | `/mvp/exception-governance` | Faster CAB |
| 41 | Governance analytics commentary | Governance | CIO | `/mvp/governance-analytics` | Trend insight |
| 42 | Risk summarization for leadership | Risk | Risk/Security | `/mvp/risk-register` | Exec brief |
| 43 | Risk prioritization narrative | Risk | Governance/Risk | `/mvp/risk-register` | Focus effort |
| 44 | VAPT findings summary | Risk | Security | `/dashboard/cio` | Security posture |
| 45 | Risk trajectory commentary | Risk | Risk | `/mvp/trends` | Forecast story |
| 46 | Compensating-control suggestion | Risk | Compliance/Risk | `/mvp/exceptions` | Mitigation |
| 47 | Heatmap hotspot explanation | Risk | CIO | `/mvp/heatmaps` | Spot hotspots |
| 48 | Correlation chain narrative | Risk | Admin | `/mvp/correlation` | Root cause |
| 49 | Third-party risk note | Risk | Risk | `/mvp/risk-register` | Vendor risk |
| 50 | Executive dashboard narrative | Executive | CIO | `/dashboard/cio` | Board comms |
| 51 | Board-pack commentary | Executive | CIO | `/mvp/reports` | Board comms |
| 52 | ROI storyboard narrative | Executive | CIO | `/mvp/roi` | Value story |
| 53 | Pan-India regional summary | Executive | Vertical Head | `/mvp/pan-india` | Regional view |
| 54 | Enterprise posture brief | Executive | CIO | `/mvp/enterprise` | Org posture |
| 55 | Trend interpretation commentary | Executive | CIO | `/mvp/trends` | Trajectory |
| 56 | Stakeholder Q&A prep | Executive | CIO | `/mvp/ai-assistant` | Meeting prep |
| 57 | KPI exception narrative | Executive | CIO | `/dashboard/cio` | Alert context |
| 58 | Operations Copilot | Operations | Ops Owner | `/mvp/ai-ops-assistant` | Ops Q&A |
| 59 | Integration troubleshooting assistant | Operations | Ops Owner | `/mvp/integration-health` | Faster fixes |
| 60 | Connector failure analysis | Operations | Ops Owner | `/mvp/integrations-hub` | Root cause |
| 61 | Scheduler run explanation | Operations | Ops Owner | `/mvp/scheduler` | Run clarity |
| 62 | RCA generation | Operations | Operations | `/mvp/ai-ops-assistant` | Incident speed |
| 63 | Collection-coverage narrative | Operations | Ops Owner | `/mvp/scheduler` | Coverage story |
| 64 | AI-Ops investigation summary | Operations | Ops Owner | `/mvp/ai-ops-assistant` | Faster triage |
| 65 | Onboarding gap narrative | Operations | Ops/App Owner | `/mvp/onboarding` | Onboarding speed |
| 66 | Predefined-query explanation | Operations | Ops Owner | `/mvp/predefined-queries` | Query clarity |
| 67 | Stage-gate readiness narrative | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/control-tower` | Gate clarity |
| 68 | Requirements artifact drafting | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/requirements` | Faster docs |
| 69 | Design/threat-model summary | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/design` | Risk surfacing |
| 70 | Development evidence summary | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/development` | Gate evidence |
| 71 | Test-evidence summary | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/testing` | QA story |
| 72 | Findings remediation suggestion | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/findings` | Faster fixes |
| 73 | Go-live gate explanation | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/golive` | Release confidence |
| 74 | Controlled-document generation | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/evidence` | Doc automation |
| 75 | AI SDLC report commentary | AI SDLC | AI SDLC Owner | `/mvp/ai-sdlc/reports` | Reporting |
| 76 | AI governance posture narrative | AI SDLC | AI Gov Owner | `/mvp/ai-governance` | AI risk story |
| 77 | AI registry entry summary | AI SDLC | AI Gov Owner | `/mvp/ai-registry` | Model inventory |
| 78 | Prompt-audit narrative | AI SDLC | AI Gov Owner | `/mvp/ai-governance` | Oversight |
| 79 | Knowledge-base assistant | Knowledge | All | `/mvp/ai-assistant` | Org Q&A |
| 80 | Document Q&A with citations | Knowledge | All | `/mvp/ai-assistant` | Grounded answers |
| 81 | Onboarding knowledge assistant | Knowledge | New joiner | `/mvp/ai-assistant` | Self-serve learning |
| 82 | Glossary / KPI explainer | Knowledge | All | dashboards | KPI literacy |
| 83 | Runbook assistant | Knowledge | Operator | `/mvp/ai-ops-assistant` | Faster ops |
| 84 | Best-practice recommendation | Knowledge | Compliance | `/mvp/ai-assistant` | Quality uplift |
| 85 | AI registry knowledge lookup | Knowledge | AI Gov Owner | `/mvp/ai-registry` | Asset lookup |
| 86 | Control-library knowledge lookup | Knowledge | Compliance | `/mvp/predefined-queries` | Control lookup |
| 87 | Natural-language evidence search | Search | All | `/mvp/search` | Findability |
| 88 | Semantic similarity search | Search | All | `/mvp/search` | Reuse discovery |
| 89 | Faceted retrieval (app/fw/status) | Search | Auditor | `/mvp/search` | Targeted search |
| 90 | Cross-system evidence lookup | Search | Admin | `/mvp/evidence-explorer` | Unified search |
| 91 | Control-to-evidence search | Search | Compliance | `/mvp/completeness` | Coverage check |
| 92 | Citation-grounded answer search | Search | Auditor | `/mvp/ai-assistant` | Trustable answers |
| 93 | Source-system filtered search | Search | Admin | `/mvp/evidence-explorer` | Connector triage |
| 94 | Audit-pack narrative generation | Reporting | Auditor | `/mvp/reports` | Pack quality |
| 95 | Report executive summary | Reporting | CIO/Compliance | `/mvp/reports` | Exec digest |
| 96 | AI SDLC report narrative | Reporting | AI SDLC Owner | `/mvp/ai-sdlc/reports` | Reporting |
| 97 | Comparison/gap report narrative | Reporting | Heads | `/mvp/comparison` | Benchmarking |
| 98 | Regulator-ready report phrasing | Reporting | Compliance | `/mvp/reports` | Regulator comms |
| 99 | Scheduled report digest | Reporting | CIO | `/mvp/reports` | Recurring comms |
| 100 | Coverage report commentary | Reporting | Compliance | `/mvp/platform/control-coverage` | Coverage story |
| 101 | Evidence reuse report narrative | Reporting | Compliance | `/mvp/platform/evidence-reuse` | Reuse value |
| 102 | Multi-framework rollup narrative | Reporting | Compliance | `/mvp/platform/framework-coverage` | Portfolio view |
| 103 | Health-check digest | Operations | Ops Owner | `/api/platform/health` | Ops awareness |
| 104 | Anomaly/alert explanation | Risk | CIO/Risk | `/dashboard/cio` | Alert context |

---

## 2. Detailed cards (representative, one+ per domain)

### UC-1 · Audit Copilot Q&A
- **Business Problem:** Auditors spend hours hunting evidence across systems.
- **Inputs:** NL question; role/user; optional app/framework filter.
- **Processing Flow:** §0 RAG pipeline; refuses if no grounded evidence.
- **Outputs:** Cited answer (`[E#]`), evidence UIDs, source systems, timestamps, framework refs.
- **Personas:** Auditor, Audit Lead. **Screens:** `/mvp/ai-assistant`. **APIs:** `/api/platform/assistant`.
- **Data Sources:** evidence, reviews, crosswalk, governance facts. **Benefits:** Faster, defensible audit answers.

### UC-11 · Evidence Classification
- **Business Problem:** Incoming evidence is untyped; manual triage is slow.
- **Inputs:** `evidence.title/content`, source system.
- **Processing Flow:** embed + `provider.generate` to suggest type + control mapping + confidence.
- **Outputs:** category, suggested control, confidence. **Personas:** App Owner. **Screens:** `/mvp/upload`. **APIs:** ingestion. **Data:** evidence. **Benefits:** Less manual triage, better coverage.

### UC-23 · Cross-Framework Correlation
- **Business Problem:** Same control re-evidenced per framework wastes effort.
- **Inputs:** control crosswalk + evidence map. **Processing Flow:** `_enrich` adds `CONTROL_CROSSWALK` framework refs; LLM narrates reuse.
- **Outputs:** reuse opportunities + mapped requirements. **Personas:** Compliance. **Screens:** `/mvp/reuse`. **APIs:** assistant + governance. **Data:** `control_framework_crosswalk`. **Benefits:** Collect once, satisfy many.

### UC-33 · Completeness Gap Narrative
- **Business Problem:** Hard to know what's missing before audit.
- **Inputs:** control catalog + evidence map + penalties. **Processing Flow:** completeness engine facts → LLM narrative.
- **Outputs:** gap list + rationale + next steps. **Personas:** Compliance. **Screens:** `/mvp/completeness`. **APIs:** governance. **Data:** controls, evidence map. **Benefits:** Targeted remediation.

### UC-42 · Risk Summarization
- **Business Problem:** Leadership needs a concise risk picture. **Inputs:** risk register rows.
- **Processing Flow:** retrieve risk facts → LLM prioritized narrative. **Outputs:** top-risk brief. **Personas:** Risk/Security. **Screens:** `/mvp/risk-register`. **APIs:** grc-demo. **Data:** risk register. **Benefits:** Faster exec decisions.

### UC-50 · Executive Dashboard Narrative
- **Business Problem:** KPIs lack plain-language context. **Inputs:** dashboard metrics (`executive_summary`).
- **Processing Flow:** governance facts → LLM commentary. **Outputs:** board-ready narrative. **Personas:** CIO. **Screens:** `/dashboard/cio`. **APIs:** assistant. **Data:** governance metrics. **Benefits:** Better board comms. (Non-sensitive → Hybrid OK.)

### UC-58 · Operations Copilot
- **Business Problem:** Ops staff context-switch across scheduler/integrations. **Inputs:** ops questions.
- **Processing Flow:** `ai_ops_assistant_engine` (keyword today) → local RAG. **Outputs:** grounded ops answers. **Personas:** Ops Owner. **Screens:** `/mvp/ai-ops-assistant`. **APIs:** `/mvp/ai-ops-assistant/summary/{mode}`. **Data:** connector health, scheduler. **Benefits:** Faster operations.

### UC-67 · Stage-Gate Readiness Narrative
- **Business Problem:** AI delivery gates need evidence-backed go/no-go. **Inputs:** stage coverage (fw/ctrl/evidence).
- **Processing Flow:** `ai_sdlc_governance` facts → LLM readiness narrative. **Outputs:** gate readiness + blockers. **Personas:** AI SDLC Owner. **Screens:** `/mvp/ai-sdlc/control-tower`. **APIs:** `/api/ai-sdlc/control-tower/*`. **Data:** AI SDLC store. **Benefits:** Confident gating.

### UC-79 · Knowledge-Base Assistant
- **Business Problem:** Tribal knowledge; slow self-serve. **Inputs:** any NL question.
- **Processing Flow:** §0 RAG over evidence + governance docs. **Outputs:** grounded answer + sources. **Personas:** All. **Screens:** `/mvp/ai-assistant`. **APIs:** `/api/platform/assistant`. **Data:** full indexed corpus. **Benefits:** Self-service knowledge.

### UC-87 · Natural-Language Evidence Search
- **Business Problem:** Keyword search misses semantically related evidence. **Inputs:** NL query.
- **Processing Flow:** `provider.embed(query)` → pgvector `store.search` (RBAC + filters) → ranked results. **Outputs:** ranked grounded results. **Personas:** All. **Screens:** `/mvp/search`. **APIs:** assistant retrieval. **Data:** `evidence_embeddings`. **Benefits:** Higher findability + reuse.

### UC-94 · Audit-Pack Narrative Generation
- **Business Problem:** Audit packs need consistent narrative framing. **Inputs:** pack data + coverage facts.
- **Processing Flow:** governance facts → LLM narrative sections. **Outputs:** narrative-augmented report. **Personas:** Auditor. **Screens:** `/mvp/reports`. **APIs:** reporting + assistant. **Data:** evidence, coverage. **Benefits:** Regulator-ready packs faster.

---

## 3. Implementation status (today vs local-LLM upgrade)

| Status | Examples | Local-LLM path |
|---|---|---|
| Already local RAG | UC 1, 32, 79, 80, 92 (assistant) | none needed |
| Heuristic → embeddings | UC 14, 15, 87, 88 (search/reuse) | `provider.embed` + pgvector |
| Deterministic → local-LLM | most narrative/summary UCs | `provider.generate` |

**All 104 use cases are achievable entirely on local LLM** with the existing provider + pgvector. None require cloud.

**Cross-links:** [Coverage Matrix](ECS_LLM_USE_CASE_COVERAGE_MATRIX.md) · [Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) · [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) · [Functional Requirements](ECS_AI_FUNCTIONAL_REQUIREMENTS.md) · [Original 28-UC catalog](ECS_LOCAL_LLM_USE_CASE_CATALOG.md)
