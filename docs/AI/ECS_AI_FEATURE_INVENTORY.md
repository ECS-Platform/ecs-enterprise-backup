# ECS AI Feature Inventory (Phase 2)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Method:** Code-grounded. Each feature is classified by how it actually computes today.

---

## Classification key

| Class | Meaning | Local-LLM impact |
|---|---|---|
| **LLM-RAG** | Genuinely calls the configured LLM provider (Ollama/cloud) over retrieved context | Runs locally on Ollama as-is |
| **Embeddings** | Generates vector embeddings → pgvector search | Runs locally on Ollama embeddings as-is |
| **Deterministic** | Rule/template/keyword/mock engine — *no model call* | Unaffected by provider; optionally LLM-upgradeable later |
| **Heuristic-search** | Keyword/overlap scoring labeled "semantic" | Optionally upgradeable to embeddings |

---

## 1. Feature Inventory (as requested + as found)

| AI capability | Class today | Where | Notes |
|---|---|---|---|
| **Chat Assistant (showcase)** `/mvp/chat` | Deterministic | `modules/shared/services/chatbot_engine.py:683-707`, `chatbot_enhanced.py:102-113` | Keyword/intent routing over `ecs_state`; no model call |
| **Knowledge / Platform RAG Assistant** `/api/platform/assistant`, `/mvp/ai-assistant` | **LLM-RAG** (+ deterministic fallback) | `ecs_platform/rag.py:642-653`; fallback `ecs_platform/governance.py:709-743` | Calls configured provider when set; else structured retrieval only |
| **Semantic / Vector / Similarity Search** | **Embeddings** (platform) **/ Heuristic** (governance module) | platform: `ecs_platform/rag.py:456-463`, `pgvector_store.py:97-101`; module: `search_module.py:119-137` | Two implementations — see Embedding Strategy doc |
| **Evidence Reuse Recommendations** | Deterministic / Heuristic | `modules/operations/engines/evidence_repository.py:104-105` ("simulate vector reuse"); `app/evidence_intel/reuse.py:8` ("NO-LLM") | No embeddings today; reuse via metadata |
| **Evidence Classification / Metadata Tagging** | Deterministic (mock) | governance/operations engines; AI SDLC mock | Tagged via rules/seeded metadata |
| **Evidence Summarization** | Deterministic / LLM-RAG (if assistant used) | `rag.py` answer path when provider configured | Summaries are templated unless RAG used |
| **Evidence Sufficiency Analysis** | Deterministic (flagged engine) | `.env.example:128-157` (`SUFFICIENCY_ENGINE_ENABLED`, explicitly NON-LLM) | Rule-based scoring |
| **Control Mapping / Framework Mapping** | Deterministic | `modules/frameworks/engines/framework_catalog.py`, onboarding engine | Catalog-driven mapping |
| **Audit Readiness** | Deterministic | `modules/governance/engines/audit_*`, `gov_audit_readiness.html` | Computed from state/metrics |
| **Compliance Gap Analysis** | Deterministic | completeness/comparison engines | Metric math |
| **Governance Recommendations** | Deterministic / LLM-RAG (assistant) | `governance.py:709-743` | Repository-aware keyword answers |
| **AI SDLC Recommendations** | Deterministic (mock) | `modules/ai_sdlc/engines/ai_sdlc_governance_mock.py` | Synthetic posture/recommendations |
| **Executive Summaries** | Deterministic / LLM-RAG (assistant) | `executive_overview` engines; RAG when invoked | Templated KPIs unless RAG used |
| **Risk Insights** | Deterministic (mock) | `enterprise_grc` engines, `grc_demo_service.py` | Computed risk scoring |
| **Report Generation** | Deterministic | `modules/executive_overview` reports, `ai_sdlc_reports_engine.py` | Template + data |
| **AI Governance Posture / Model Registry / Prompt Registry / AI Risk Monitoring** | Deterministic (mock) | `ai_sdlc_governance_mock.py:898-1567` | Display/demo data; no live model |

---

## 2. What actually exercises a local/remote LLM

Only **two** code paths invoke `provider.generate()` / `provider.embed()`:

1. **RAG answer generation** — `ecs_platform/rag.py:649` → `provider.generate(prompt, system=SYSTEM_PROMPT)`.
2. **Embedding/index + query** — `provider.embed()` via `rag.py` / `ingestion.py` / `pipeline.py` → pgvector.

Both run on the **configured provider**, which defaults to **local Ollama**. Therefore, switching ECS
to "local LLM" requires **no feature rewrites** — it is already the default for these paths.

A third class (`ResponseGenerator` in `ecs_platform/llm_engine/generator.py:54`) also calls
`provider.generate()` but has **no call sites** in app routes (exported, unused) — noted for cleanup.

---

## 3. Local-LLM readiness per feature (summary)

| Readiness | Features |
|---|---|
| **Already local-ready (provider-based)** | Platform RAG assistant, semantic/vector search (platform), embedding index |
| **Provider-agnostic (no change needed)** | All deterministic/mock features — they never call a model, so they work identically air-gapped |
| **Optional future LLM upgrade** | Evidence summarization, sufficiency, reuse recommendations, governance/executive narratives — could be routed through the local provider later (not in scope here) |

---

## 4. Phase 2 Conclusion

ECS's AI surface is **mostly deterministic** (safe for banking: explainable, reproducible), with a
**genuine LLM-RAG path that already defaults to local Ollama**. No feature depends on a *cloud* LLM.
This is an ideal posture for air-gapped/on-prem rollout: the deterministic features need nothing, and
the LLM features point at a local engine by default.
