# ECS LLM Implementation Matrix

**Type:** Per-use-case LLM fit + effort + priority matrix. **Mode:** Documentation only. No code/UI/DB changes. No commits.
**Grounding:** [Master Use Case & LLM Reference](ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md), [LLM Use Case Priority Matrix](ECS_LLM_USE_CASE_PRIORITY_MATRIX.md), `config/llm.yaml`, `ecs_platform/rag.py`.
**Scales:** Fit = Strong/Good/Limited/N/A · Complexity/Value/ROI = H/M/L · Effort in eng-days **[Inferred/Target]** · Priority P1/P2/P3. "Neve" = sanctioned cloud slot (off by default).

> **Effort note:** Phase-1 items mostly **validate/expose existing** shipping AI paths (low effort). Higher effort reflects new tuning, plumbing, or dependency on durability/remote-connector enablement.

---

## 1. Implementation matrix

| Use Case | Local Fit | Neve Fit | Hybrid Fit | Complexity | Biz Value | ROI | Effort (d) | Priority |
|---|---|---|---|---|---|---|---:|---|
| UC-AI01 Citation Q&A | Strong | Good | Good | L | H | H | 1–2 | P1 |
| UC-AI02 Refuse w/o evidence | Strong | N/A | N/A | L | H | H | 0.5 | P1 |
| UC-AI03/E10 Semantic retrieval | Strong | Good | Good | L | H | H | 1–2 | P1 |
| UC-AI07 RBAC-scoped AI | Strong | N/A | N/A | L | H | H | 0.5 | P1 |
| UC-AI08 Local-first private AI | Strong | N/A | N/A | L | H | H | 0 (live) | P1 |
| UC-AI06 Framework posture summary | Strong | Good | Good | M | H | H | 2–3 | P1 |
| UC-A01 Audit readiness summary | Strong | Good | Good | M | H | H | 2–3 | P1 |
| UC-AI04 Observation/rejection drafting | Strong | Limited | Good | M | H | H | 3–4 | P1 |
| UC-E03 Evidence sufficiency | Strong | Limited | Good | M | H | M | 2–3 | P1 |
| UC-CP01 Audit Copilot | Strong | Good | Good | M | H | H | 4–6 | P1–P2 |
| UC-E02/E13 Auto-classify evidence | Strong | Limited | Good | M | M | M | 4–6 | P2 |
| UC-CP02 Governance Copilot | Strong | Good | Good | M | H | M | 4–6 | P2 |
| UC-CP04 Ops Copilot | Strong | Good | Good | M | M | M | 3–5 | P2 |
| UC-E08/F12 Evidence/framework reuse | Strong | Limited | Good | M | H | H | 3–5 | P2 |
| UC-C03/C10 Control maturity/effectiveness | Strong | Good | Good | M | M | M | 3–4 | P2 |
| UC-C08/RAF Risk assessment | Strong | Limited | Good | M | H | M | 3–5 | P2 |
| UC-FW-* Framework guidance | Strong | Good | Good | M | H | M | 4–6 | P2 |
| UC-AI09 AI-SDLC gating | Strong | Good | Good | M | M | M | 3–4 | P2 |
| UC-AI10 AI governance posture | Strong | Good | Good | M | M | M | 2–3 | P2 |
| UC-X02 Board summary | Good | Strong | Strong | M | H | M | 3–5 | P2–P3 |
| UC-CP03 Executive Copilot | Good | Strong | Strong | M | H | M | 4–6 | P2–P3 |
| UC-X03 ROI narrative | Good | Strong | Strong | M | M | M | 2–3 | P3 |
| UC-F10/C06 Control→regulation mapping | Good | Strong | Strong | H | H | M | 6–8 | P3 |
| UC-AI11 Hybrid cloud fallback | N/A | Strong | Strong | H | M | L | 4–6 | P3 |
| UC-PQ02 Remote-query summarization | Strong | Limited | Good | H | M | M | 2–3 (after connectors) | P3 |

## 2. Effort rollup by phase [Inferred/Target]
| Phase | Use cases | Effort |
|---|---|---|
| **P1** | 10 quick-win/local | ~16–26 eng-days (much is validate+expose) |
| **P2** | 11 enablement/copilots | ~35–50 eng-days |
| **P3** | 6 hybrid/advanced/dependency-gated | ~20–30 eng-days |

## 3. Model assignment summary
| Tier | Model | Use cases |
|---|---|---|
| Light | Qwen3:4B | classification/tagging (E02/E13, AP01) |
| Default | **Qwen3:8B** | Q&A, retrieval, summary, drafting, copilots, guidance, risk |
| Heavy | Qwen3:14B / Gemma2-9B | control mapping (F10/C06), board narrative (X02/CP03) |
| Embeddings | nomic-embed-text | all vector search (always local) |

## Cross-references
- [Priority Matrix](ECS_LLM_USE_CASE_PRIORITY_MATRIX.md) · [Implementation Roadmap](ECS_LLM_IMPLEMENTATION_ROADMAP.md) · [Master Use Case & LLM Reference](ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) · [Local vs Cloud Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md)
