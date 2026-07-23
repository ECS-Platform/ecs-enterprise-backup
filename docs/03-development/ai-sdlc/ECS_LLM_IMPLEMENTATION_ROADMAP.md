# ECS LLM Implementation Roadmap

**Type:** AI/LLM implementation sequencing. **Mode:** Documentation only. No code/UI/DB changes. No commits. **Grounding:** [Master Use Case & LLM Reference](ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md), [LLM Use Case Priority Matrix](ECS_LLM_USE_CASE_PRIORITY_MATRIX.md), [LLM Implementation Matrix](ECS_LLM_IMPLEMENTATION_MATRIX.md), `config/llm.yaml`, `ecs_platform/llm_engine/*`, `ecs_platform/rag.py`.

> **Baseline (verified):** ECS already ships a working local-first AI stack — provider abstraction (`ollama` default + gemini/openai/azure_openai/claude), `qwen3:8b`, `nomic-embed-text`, pgvector RAG with `require_citations`/`refuse_without_evidence`, and RBAC-before-AI. The roadmap below **enables and extends** use cases on top of this, it does not build the stack from scratch.

---

## 1. Quick wins (Phase 1 — ship-now, local, low complexity)
All reuse the shipping RAG/embeddings/RBAC; **Qwen3:8B** local; no connector/durability dependency.
| Use Case | LLM Role | Why quick |
|---|---|---|
| UC-AI01 Citation-grounded Q&A | Chatbot/RAG | Already core RAG path |
| UC-AI02 Refuse without evidence | Guardrail | Config-enforced (`refuse_without_evidence`) |
| UC-AI03/UC-E10 Semantic retrieval | RAG retrieval | pgvector + embeddings live |
| UC-AI07 RBAC-scoped AI | Access control | RBAC-before-AI live |
| UC-AI06 Summarize framework posture | Summarization | KPIs already computed |
| UC-A01 Audit readiness summary | Audit readiness | Readiness KPIs already computed |
| UC-AI04 Observation/rejection drafting | Observation drafting | Context available; HV-gated |

## 2. High-ROI use cases
| Use Case | ROI driver | Mode |
|---|---|---|
| UC-AI01/AI03 Q&A + retrieval | per-query minutes saved × high volume | L |
| UC-A01 Audit readiness | avoided audit overruns/fire-drills | L |
| UC-AI04 Observation drafting | reviewer throughput | L |
| UC-E08/F12 Evidence/framework reuse | collect-once savings (reuse multiplier) | L |
| UC-CP01 Audit Copilot | auditor productivity | L→ |
| UC-X02 Board summary | exec hours per cycle | H |

## 3. Local LLM candidates (Qwen3 on Ollama)
- **Qwen3:8B (default):** Q&A, summarization, drafting, framework guidance, copilots — the majority of use cases.
- **Qwen3:4B:** classification/tagging (UC-E02/E13, UC-AP01) on constrained hosts.
- **Qwen3:14B / Gemma2-9B:** control→regulation mapping (UC-F10/C06), board narrative, multi-doc synthesis.
- **nomic-embed-text:** all embeddings (always local).

## 4. Neve (cloud) candidates
Non-sensitive aggregate synthesis only, policy-gated: UC-X02 (board narrative), UC-CP03 (Executive Copilot), UC-X03 (ROI narrative), UC-F10/C06 (heavy mapping on de-identified inputs). **No sensitive-evidence path goes to cloud.**

## 5. Hybrid candidates
UC-X02, UC-CP03, UC-X03, UC-F10/C06, UC-AI11 — local default with optional cloud quality boost on de-identified aggregates; local remains fallback.

## 6. Implementation priority & sequencing
| Phase | Window | Scope | Dependencies |
|---|---|---|---|
| **1** | 0–4 wks | Quick wins (§1) — validate + expose on existing screens | none (stack live) |
| **2** | 4–10 wks | Classification, copilots, reuse, risk/framework guidance | light tuning; observation durability enablement |
| **3** | 10–20 wks | Hybrid exec synthesis, control mapping, remote-query summaries | cloud sign-off; remote connectors |

## 7. Effort (indicative [Inferred/Target])
| Workstream | Effort |
|---|---|
| Phase 1 validation + UI exposure of existing AI paths | 3–5 eng-days |
| Phase 2 classification tuning + copilots | 8–12 eng-days |
| Phase 2 observation-durability enablement | 3 eng-days (see [Durability Plan](../production/ECS_OBSERVATION_DURABILITY_ENABLEMENT_PLAN.md)) |
| Phase 3 hybrid + cloud enablement + mapping | 8–12 eng-days |

## 8. Risks
| Risk | Mitigation |
|---|---|
| Local model latency on large context | `keep_alive` resident; 14B async/offline; right-size per use case |
| Hallucination | `refuse_without_evidence` + citations + HV on drafts |
| Data residency (cloud) | Local-first; cloud only for de-identified aggregates w/ sign-off |
| RBAC leakage via AI | RBAC-before-AI enforced; per-role test matrix |
| Embedding drift / stale index | Scheduled reindex (Phase 2 enhancement) |

## 9. Expected business benefits
Faster audit prep (days→hours), higher reviewer throughput, evidence collect-once reuse savings, board-ready narratives in minutes, defensible (cited) answers, and data-sovereign AI (on-host) meeting PCI/RBI residency.

## 10. Final recommendation — LOCAL FIRST (with optional HYBRID)
Grounded in ECS's shipping architecture (`provider: ollama`, `qwen3:8b`, pgvector, `refuse_without_evidence`, RBAC-before-AI) and banking data-residency requirements: **default LOCAL ONLY** for all sensitive paths; add an **optional HYBRID tier** for non-sensitive executive synthesis. Cloud-only is not recommended for any sensitive use case.

## Cross-references
- [Master Use Case & LLM Reference](ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) · [Priority Matrix](ECS_LLM_USE_CASE_PRIORITY_MATRIX.md) · [Implementation Matrix](ECS_LLM_IMPLEMENTATION_MATRIX.md) · [Local vs Cloud Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) · [AI Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md)
