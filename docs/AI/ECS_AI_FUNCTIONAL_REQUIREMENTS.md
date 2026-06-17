# ECS AI Functional Requirements

**Type:** Requirements documentation. **No code changed.** Each requirement is marked **[Implemented]** (traceable to code), **[Partial]**, or **[Inferred/Target]** (recommended, not shipped). Grounding in `ecs_platform/llm_engine/`, `rag.py`, `config/llm.yaml`, `config/vectorstore.yaml`, `app/auth/*`.

---

## 1. Functional Requirements (FR)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| FR-1 | Answer NL questions grounded in repository evidence | [Implemented] | `rag.answer()` |
| FR-2 | Return citations (evidence UID, source, timestamp, framework refs) | [Implemented] | `rag.py:621-628` |
| FR-3 | Refuse when no grounding evidence exists | [Implemented] | `rag.py:637-640`, `NO_EVIDENCE_MESSAGE` |
| FR-4 | Support 5 providers, config-selected | [Implemented] | `provider.py:230-246` |
| FR-5 | Default to local, keyless LLM (Ollama) | [Implemented] | `llm.yaml:7`, `provider.py:157-177` |
| FR-6 | Semantic retrieval over pgvector with repository fallback | [Implemented] | `rag.py:434-497` |
| FR-7 | Embed + index evidence + governance docs (incremental) | [Implemented] | `rag.reindex_evidence()` |
| FR-8 | Enrich answers with control reuse + framework crosswalk | [Implemented] | `rag.py:_enrich`, `CONTROL_CROSSWALK` |
| FR-9 | Inject computed governance facts (coverage, gaps, reuse) | [Implemented] | `rag.py:_governance_facts` |
| FR-10 | Deterministic fallback assistant when LLM unconfigured | [Implemented] | `rag.py:644-647`, governance Q&A |
| FR-11 | Operations / AI-Ops assistant | [Implemented] | `ai_ops_assistant_engine` |
| FR-12 | AI SDLC governance narratives/artifacts | [Implemented] | `ai_sdlc_*` engines |
| FR-13 | AI governance posture (6 dimensions) | [Implemented] | `ecs_ai_governance_drilldowns` |
| FR-14 | Per-request app/framework filters | [Implemented] | `rag.answer(application, framework)` |
| FR-15 | Strip model chain-of-thought from output | [Implemented] | `provider._strip_think`, SYSTEM_PROMPT rule 5 |
| FR-16 | Per-classification provider routing | [Inferred/Target] | single global provider today |
| FR-17 | Agentic multi-step remediation | [Inferred/Target] | maturity assessment target |

## 2. Non-Functional Requirements (NFR)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| NFR-1 | Importing AI modules never breaks the app (lazy SDKs, credential-optional) | [Implemented] | `provider.py:1-6` |
| NFR-2 | Graceful degradation when LLM/vector/DB down | [Implemented] | fallbacks in `rag.py` |
| NFR-3 | Keep local model resident (avoid cold start) | [Implemented] | `keep_alive=30m`, `warm()` |
| NFR-4 | Configurable timeout | [Implemented] | `request_timeout_sec=180` |
| NFR-5 | Provider switch without code change | [Implemented] | `ECS_LLM_PROVIDER` |
| NFR-6 | Vector provider switch (pgvector/chroma/milvus) | [Implemented] | `vectorstore.yaml:3` |
| NFR-7 | Idempotent, incremental indexing (content-hash dedup) | [Implemented] | `rag.py:342-345` |
| NFR-8 | Horizontal/remote LLM via `OLLAMA_URL` | [Implemented] | `provider.py:166` |
| NFR-9 | Health/readiness of AI stack | [Implemented] | `rag_status()`, `llm_connectivity()` |
| NFR-10 | Metrics/observability for AI calls | [Inferred/Target] | logging only today |

## 3. Security Requirements (SR)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| SR-1 | RBAC scope filter applied **before** model call | [Implemented] | `rag.py:_rbac_filter`, `_retrieve` |
| SR-2 | Restricted role with no assignments sees nothing | [Implemented] | `rag.py:472-474` |
| SR-3 | Local default keeps evidence on-prem (no egress) | [Implemented] | Ollama keyless |
| SR-4 | Keys via env/secret store, never hardcoded | [Implemented] | `resolve_secret`, `api_key_env` |
| SR-5 | Model sees only retrieved, scoped evidence | [Implemented] | grounded prompt assembly |
| SR-6 | Audit logging of governance actions | [Implemented] | `audit_log` (indexed into RAG) |
| SR-7 | PII redaction before prompt | [Inferred/Target] | not a runtime feature |
| SR-8 | Data-classification gate for cloud egress | [Inferred/Target] | policy/process today |
| SR-9 | Prompt-injection hardening (grounded-only) | [Partial] | grounding gate mitigates; no dedicated filter |

## 4. AI Requirements (AIR)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| AIR-1 | Grounded generation only (no free-form) | [Implemented] | SYSTEM_PROMPT rule 1 |
| AIR-2 | Mandatory citations per claim | [Implemented] | SYSTEM_PROMPT rule 2 |
| AIR-3 | Exact refusal sentence when ungrounded | [Implemented] | SYSTEM_PROMPT rule 3 |
| AIR-4 | Low temperature for deterministic outputs | [Implemented] | `temperature=0.1` |
| AIR-5 | Bounded output tokens | [Implemented] | `max_output_tokens=2048` |
| AIR-6 | Top-k retrieval + max context chunks | [Implemented] | `top_k=8`, `max_context_chunks=12` |
| AIR-7 | Embedding dim consistency | [Implemented] | `ECS_VECTOR_DIM=768` |
| AIR-8 | Model-agnostic embeddings (local nomic default) | [Implemented] | `embedding_model` |
| AIR-9 | Evaluation/guardrail harness | [Inferred/Target] | maturity target |

## 5. Performance Requirements (PR) — targets are **[estimate]**, no shipped benchmark

| ID | Requirement | Status |
|---|---|---|
| PR-1 | Warm model to avoid cold-start latency | [Implemented] (`warm()`, keep_alive) |
| PR-2 | Batch embedding (50/batch) | [Implemented] (`rag.py:348`) |
| PR-3 | Incremental reindex (skip unchanged) | [Implemented] |
| PR-4 | Configurable retrieval breadth | [Implemented] (`top_k`) |
| PR-5 | Target first-token < N sec on reference GPU | [Inferred/Target] — define in benchmark |
| PR-6 | Throughput/concurrency targets | [Inferred/Target] |

## 6. Explainability Requirements (XR)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| XR-1 | Every answer traceable to cited evidence | [Implemented] | citations array |
| XR-2 | Show retrieval mode (vector/repository/fallback) | [Implemented] | `retrieval_mode` in response |
| XR-3 | Surface governance facts used | [Implemented] | `facts` in response |
| XR-4 | Show RBAC decision + role | [Implemented] | `rbac` in response |
| XR-5 | Expose model/provider used | [Implemented] | `model`, `provider` in response |
| XR-6 | No hidden chain-of-thought | [Implemented] | `_strip_think` |
| XR-7 | Confidence scoring | [Inferred/Target] | not exposed today |

## 7. Auditability Requirements (AR)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| AR-1 | Governance actions written to `audit_log` | [Implemented] | repository audit |
| AR-2 | Evidence access logging | [Implemented] | `repository.yaml: log_evidence_access` |
| AR-3 | Citations enable answer reconstruction | [Implemented] | UID + timestamp + source |
| AR-4 | Index provenance (doc_kind, content_hash) | [Implemented] | `rag.py:327,335` |
| AR-5 | Prompt/response audit trail | [Partial] | AI governance posture tracks prompt audits (demo); no full prompt log table |
| AR-6 | Immutable/signed AI audit log | [Inferred/Target] | maturity target |

---

**Summary:** the AI feature set is **substantially implemented** with strong grounding, citation, RBAC-before-model, and on-prem defaults. Open items are **enhancements** (PII redaction, classification routing, eval harness, full prompt-audit table, confidence scoring, metrics) — documented as Phase 2/3 targets, not blockers.

**Cross-links:** [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) · [Security Architecture](ECS_AI_SECURITY_ARCHITECTURE.md) · [Governance Operating Model](ECS_AI_GOVERNANCE_OPERATING_MODEL.md)
