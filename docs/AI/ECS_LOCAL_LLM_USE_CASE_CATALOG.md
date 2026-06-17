# ECS Local LLM Use Case Catalog (Phase 4)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

28 use cases. Each runs on **local Ollama** (`qwen3:8b` + `nomic-embed-text` → pgvector) — no cloud.
**Status** = current implementation today (Det = deterministic, Heur = heuristic search, RAG = already
local-LLM). **ROI** is a qualitative banking estimate (time saved / risk reduced), not a measured figure.

Persona keys map to real ECS roles (see `app/auth/roles.py`, persona matrix). Frameworks are from the
15-entry catalog (`framework_catalog.py:740-756`); applications from `ecs_state.BANKING_APPLICATIONS`.

---

| # | Use case | Status | Persona | Application | Framework | ROI |
|---|---|---|---|---|---|---|
| 1 | Evidence Classification | Det→LLM | Application Owner | All | All | High (auto-tag, less manual triage) |
| 2 | Evidence Summarization | Det→LLM | Auditor | All | All | High (faster review) |
| 3 | Evidence Deduplication | Det→Embed | Application Owner | All | All | Medium (storage + review savings) |
| 4 | Evidence Quality Review | Det→LLM | Auditor | All | All | High (consistency) |
| 5 | Audit Observation Analysis | Det→LLM | Auditor | All | PCI DSS, ISO27001 | High |
| 6 | Control Gap Detection | Det→LLM | Compliance | All | All | High (audit prep) |
| 7 | Framework Mapping | Det→LLM | Compliance | All | All | High (onboarding speed) |
| 8 | Cross-Framework Correlation | Det→LLM | Compliance | All | PCI DSS↔ISO27001↔SOC2 | High (evidence reuse) |
| 9 | Audit Readiness Assessment | Det→LLM | Audit Lead | All | All | High |
| 10 | Risk Summarization | Det→LLM | Risk/Security | All | RBI Cyber Security, VAPT | Medium-High |
| 11 | Executive Dashboard Narratives | Det→LLM | CIO/Executive | Enterprise | All | Medium (board comms) |
| 12 | RCA Generation | Det→LLM | Operations | All | ITPP, ITDRM | Medium-High |
| 13 | Compliance Exception Analysis | Det→LLM | Compliance | All | All | Medium |
| 14 | Policy Summarization | Embed+LLM | Governance | All | ISG, ISO27001 | Medium |
| 15 | SOP Summarization | Embed+LLM | Operations | All | ITPP | Medium |
| 16 | Evidence Recommendation | Embed | Application Owner | All | All | High (collection guidance) |
| 17 | Similar Evidence Discovery | Heur→Embed | Application Owner | All | All | High (reuse) |
| 18 | Natural Language Search | Heur→Embed | All | All | All | High (findability) |
| 19 | Control Recommendation | Det→LLM | Control Owner | All | All | Medium |
| 20 | Audit Copilot | RAG | Auditor | All | All | High |
| 21 | Operations Copilot | Det→RAG | Operations | All | ITPP, ITDRM | Medium-High |
| 22 | Governance Copilot | RAG | Governance | All | All | High |
| 23 | Integration Troubleshooting Assistant | Det→LLM | Operations | API Gateway, all | — | Medium |
| 24 | Connector Failure Analysis | Det→LLM | Operations | All | — | Medium |
| 25 | Knowledge Base Assistant | RAG | All | All | All | High |
| 26 | Rejection-Reason Drafting | Det→LLM | Auditor | All | All | Medium (consistency) |
| 27 | Evidence Sufficiency Narrative | Det→LLM | Auditor | All | All | Medium-High |
| 28 | Onboarding Gap Narrative | Det→LLM | Operations/App Owner | New apps | All | Medium |

---

## Detailed cards

### 1. Evidence Classification
- **Business value:** Auto-categorize incoming evidence (type, control area), reducing manual triage.
- **Input:** Evidence title/content (`evidence.title`, `.content`), source system.
- **Output:** Category + suggested control mapping + confidence.
- **Persona:** Application Owner · **App:** all · **Framework:** all · **ROI:** High.
- **Code anchor:** evidence stored via repository/ingestion (`ecs_platform/ingestion.py`); today metadata is rule/mock-driven.

### 2. Evidence Summarization
- **Value:** One-paragraph summary so auditors review faster.
- **Input:** Evidence content. **Output:** Concise summary + key facts.
- **Persona:** Auditor · all · all · **ROI:** High.
- **Anchor:** RAG generate path `rag.py:649` (local provider).

### 3. Evidence Deduplication
- **Value:** Detect near-duplicate evidence to cut storage/review.
- **Input:** Embeddings of evidence chunks. **Output:** Duplicate clusters.
- **Persona:** Application Owner · all · all · **ROI:** Medium.
- **Anchor:** `provider.embed()` + pgvector cosine (`pgvector_store.py:97`).

### 4. Evidence Quality Review
- **Value:** Flag low-quality/insufficient evidence consistently.
- **Input:** Evidence + control requirement. **Output:** Quality score + gaps.
- **Persona:** Auditor · all · all · **ROI:** High.
- **Anchor:** complements `SUFFICIENCY_ENGINE` (deterministic today, `.env.example:128-157`).

### 5. Audit Observation Analysis
- **Value:** Cluster/triage observations; suggest disposition.
- **Input:** Observation text + history. **Output:** Theme + recommended action.
- **Persona:** Auditor · all · PCI DSS/ISO27001 · **ROI:** High.

### 6. Control Gap Detection
- **Value:** Identify controls lacking sufficient evidence.
- **Input:** Control catalog + evidence map. **Output:** Gap list + rationale.
- **Persona:** Compliance · all · all · **ROI:** High.
- **Anchor:** completeness engine + framework catalog.

### 7. Framework Mapping
- **Value:** Suggest control→framework mappings during onboarding.
- **Input:** Control description. **Output:** Mapped framework controls.
- **Persona:** Compliance · all · all · **ROI:** High.
- **Anchor:** `framework_catalog.py`, onboarding engine.

### 8. Cross-Framework Correlation
- **Value:** Reuse one evidence item across overlapping frameworks.
- **Input:** Control crosswalk + evidence. **Output:** Reuse opportunities.
- **Persona:** Compliance · all · PCI DSS↔ISO27001↔SOC2 · **ROI:** High.
- **Anchor:** `control_framework_crosswalk` (used in `rag.py:482`).

### 9. Audit Readiness Assessment
- **Value:** Narrative readiness score per app/framework before an audit.
- **Input:** Coverage + evidence freshness. **Output:** Readiness summary.
- **Persona:** Audit Lead · all · all · **ROI:** High.
- **Anchor:** audit-prep engines, `gov_audit_readiness.html`.

### 10. Risk Summarization
- **Value:** Summarize top risks for leadership.
- **Input:** Risk register rows. **Output:** Prioritized narrative.
- **Persona:** Risk/Security Officer · all · RBI Cyber Security/VAPT · **ROI:** Medium-High.

### 11. Executive Dashboard Narratives
- **Value:** Auto-generate board-ready commentary on KPIs.
- **Input:** Dashboard metrics. **Output:** Plain-language narrative.
- **Persona:** CIO/Executive · Enterprise · all · **ROI:** Medium.

### 12. RCA Generation
- **Value:** Draft root-cause analysis from incident/problem data.
- **Input:** Problem record + signals. **Output:** RCA draft.
- **Persona:** Operations · all · ITPP/ITDRM · **ROI:** Medium-High.

### 13. Compliance Exception Analysis
- **Value:** Analyze exception requests; flag risky/expiring ones.
- **Input:** Exception records. **Output:** Risk note + recommendation.
- **Persona:** Compliance · all · all · **ROI:** Medium.
- **Anchor:** exception engines (`exception_state_engine.py`).

### 14. Policy Summarization
- **Value:** Summarize long policies into actionable points.
- **Input:** Policy doc (embedded). **Output:** Summary + obligations.
- **Persona:** Governance · all · ISG/ISO27001 · **ROI:** Medium.

### 15. SOP Summarization
- **Value:** Condense SOPs for operators.
- **Input:** SOP doc. **Output:** Step summary.
- **Persona:** Operations · all · ITPP · **ROI:** Medium.

### 16. Evidence Recommendation
- **Value:** Recommend what evidence to collect for a control.
- **Input:** Control + existing evidence. **Output:** Suggested artifacts.
- **Persona:** Application Owner · all · all · **ROI:** High.

### 17. Similar Evidence Discovery
- **Value:** Find semantically similar evidence for reuse (today heuristic).
- **Input:** Query/evidence. **Output:** Ranked similar items.
- **Persona:** Application Owner · all · all · **ROI:** High.
- **Anchor:** upgrade `search_module.py:119-137` + `reuse.py` to embeddings.

### 18. Natural Language Search
- **Value:** Ask in plain English across evidence/controls.
- **Input:** NL query. **Output:** Ranked grounded results.
- **Persona:** All · all · all · **ROI:** High.
- **Anchor:** RAG retrieval (`rag.py:442-463`), today heuristic in governance search.

### 19. Control Recommendation
- **Value:** Suggest additional controls for a risk/app.
- **Input:** App profile + framework. **Output:** Recommended controls.
- **Persona:** Control Owner · all · all · **ROI:** Medium.

### 20. Audit Copilot
- **Value:** Conversational audit assistant grounded in evidence.
- **Input:** Auditor questions. **Output:** Grounded answers + citations.
- **Persona:** Auditor · all · all · **ROI:** High.
- **Anchor:** `/api/platform/assistant` (RAG, local).

### 21. Operations Copilot
- **Value:** Answer ops questions (scheduler, integrations).
- **Input:** Ops questions. **Output:** Grounded ops answers.
- **Persona:** Operations · all · ITPP/ITDRM · **ROI:** Medium-High.
- **Anchor:** `/mvp/ai-ops-assistant` (keyword today → local RAG).

### 22. Governance Copilot
- **Value:** Governance Q&A over posture/compliance data.
- **Input:** Governance questions. **Output:** Grounded answers.
- **Persona:** Governance · all · all · **ROI:** High.
- **Anchor:** `governance_qa()` deterministic fallback + RAG.

### 23. Integration Troubleshooting Assistant
- **Value:** Diagnose connector/integration issues.
- **Input:** Connector status/logs. **Output:** Likely cause + fix.
- **Persona:** Operations · API Gateway/all · — · **ROI:** Medium.
- **Anchor:** integrations hub (`integrations_module.py`).

### 24. Connector Failure Analysis
- **Value:** Explain why a scan/connector run failed.
- **Input:** Connector error output. **Output:** Cause + remediation.
- **Persona:** Operations · all · — · **ROI:** Medium.
- **Anchor:** scan connectors (`query_connectors.py`).

### 25. Knowledge Base Assistant
- **Value:** Org-wide KB Q&A grounded in repository.
- **Input:** Questions. **Output:** Grounded answers + sources.
- **Persona:** All · all · all · **ROI:** High.
- **Anchor:** RAG pipeline.

### 26. Rejection-Reason Drafting
- **Value:** Draft consistent, complete evidence-rejection reasons.
- **Input:** Evidence + gap. **Output:** Reason text.
- **Persona:** Auditor · all · all · **ROI:** Medium.
- **Anchor:** evidence approval flow (`evidence_approval_engine.py`).

### 27. Evidence Sufficiency Narrative
- **Value:** Explain why evidence is/ isn't sufficient.
- **Input:** Evidence + control. **Output:** Narrative + missing items.
- **Persona:** Auditor · all · all · **ROI:** Medium-High.

### 28. Onboarding Gap Narrative
- **Value:** Summarize gaps surfaced by the onboarding simulator.
- **Input:** Onboarding result. **Output:** Gap narrative + next steps.
- **Persona:** Operations/App Owner · new apps · all · **ROI:** Medium.
- **Anchor:** `onboarding_engine.py`, `/api/onboarding/simulate`.

---

## Summary

| Status today | Count | Local-LLM path |
|---|---|---|
| Already local RAG | 4 (UC 20,22,25 + assistant) | none needed |
| Heuristic → embeddings upgrade | 3 (UC 17,18 + search) | reuse `provider.embed()` + pgvector |
| Deterministic → local-LLM enhancement | 21 | reuse `provider.generate()` |

All 28 use cases are achievable **entirely on local LLM** with the existing provider + pgvector; none
require cloud AI.
