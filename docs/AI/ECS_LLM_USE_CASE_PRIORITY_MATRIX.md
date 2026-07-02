# ECS LLM Use Case Priority Matrix

**Type:** AI value/priority classification. **Mode:** Documentation only. No code/UI/DB changes. No commits. **Grounding:** [Master Use Case & LLM Reference](ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md), `config/llm.yaml`, `ecs_platform/rag.py`, `config/roi.yaml`.

**Scales:** Business Value / Complexity / ROI = **H**igh · **M**edium · **L**ow. Fit = **Strong / Good / Limited / N/A**. "Neve" = sanctioned cloud-LLM slot (Gemini/OpenAI/Azure/Claude, off by default). Values **[Inferred/Target — validate]**.

> **Phasing logic:** **Phase 1** = high value, low–medium complexity, strong Local-LLM fit, reuses what already ships (RAG/embeddings/RBAC). **Phase 2** = medium-complex synthesis or needs durable/connector enablement. **Phase 3** = hybrid/cloud, advanced reasoning, or dependent on remote-connector build.

---

## 1. Priority matrix (per use case)

| Use Case | Biz Value | Complexity | ROI | Local Fit | Neve Fit | Hybrid Fit | Phase |
|---|---|---|---|---|---|---|---|
| UC-AI01 Citation-grounded Q&A | H | L | H | Strong | Good | Good | **1** |
| UC-AI02 Refuse without evidence | H | L | H | Strong | N/A | N/A | **1** |
| UC-AI03 / UC-E10 Semantic retrieval | H | L | H | Strong | Good | Good | **1** |
| UC-AI07 RBAC-scoped AI | H | L | H | Strong | N/A | N/A | **1** |
| UC-AI08 Local-first private AI | H | L | H | Strong | N/A | N/A | **1** |
| UC-AI06 Summarize framework posture | H | M | H | Strong | Good | Good | **1** |
| UC-A01 Audit readiness summary | H | M | H | Strong | Good | Good | **1** |
| UC-AI04 Observation/rejection drafting | H | M | H | Strong | Limited | Good | **1** |
| UC-E03 Validate evidence sufficiency | H | M | M | Strong | Limited | Good | **1** |
| UC-E02/E13 Auto-classify evidence | M | M | M | Strong | Limited | Good | **2** |
| UC-CP01 Audit Copilot | H | M | H | Strong | Good | Good | **1–2** |
| UC-CP02 Governance Copilot | H | M | M | Strong | Good | Good | **2** |
| UC-CP04 Ops Governance Copilot | M | M | M | Strong | Good | Good | **2** |
| UC-E08/F12 Evidence/framework reuse | H | M | H | Strong | Limited | Good | **2** |
| UC-C03/C10 Control maturity/effectiveness | M | M | M | Strong | Good | Good | **2** |
| UC-C08/RAF Risk assessment & acceptance | H | M | M | Strong | Limited | Good | **2** |
| UC-FW-* Framework guidance (PCI/DPSC/ITPP…) | H | M | M | Strong | Good | Good | **2** |
| UC-X02 Board-ready summary | H | M | M | Good | Strong | Strong | **2–3** |
| UC-CP03 Executive Copilot | H | M | M | Good | Strong | Strong | **2–3** |
| UC-X03 ROI narrative | M | M | M | Good | Strong | Strong | **3** |
| UC-F10/C06 Control→regulation mapping | H | H | M | Good | Strong | Strong | **3** |
| UC-AI09 AI-SDLC stage gating | M | M | M | Strong | Good | Good | **2** |
| UC-AI10 AI governance posture | M | M | M | Strong | Good | Good | **2** |
| UC-AI11 Hybrid cloud fallback | M | H | L | N/A | Strong | Strong | **3** |
| UC-PQ02 Remote-target query summarization | M | H | M | Strong | Limited | Good | **3** (after remote connectors) |

## 2. Classification summary

### Phase 1 — Quick wins (ship-now, local, low complexity)
UC-AI01, UC-AI02, UC-AI03/UC-E10, UC-AI07, UC-AI08, UC-AI06, UC-A01, UC-AI04, UC-E03, UC-CP01 (initial).
*Rationale:* all rely on already-shipping RAG + embeddings + RBAC + `refuse_without_evidence`; Qwen3:8B local; no connector/durability dependency.

### Phase 2 — High value, moderate enablement
UC-E02/E13, UC-CP02, UC-CP04, UC-E08/F12, UC-C03/C10, UC-C08/RAF, UC-FW-*, UC-AI09, UC-AI10.
*Rationale:* need light classification tuning, governance data plumbing, or observation-durability enablement; still local-first.

### Phase 3 — Hybrid / advanced / dependency-gated
UC-X02, UC-CP03, UC-X03, UC-F10/C06, UC-AI11, UC-PQ02.
*Rationale:* benefit from cloud/larger-model synthesis (de-identified aggregates) or depend on remote-connector build.

## 3. Local-LLM fit vs Neve fit (decision guidance)

| Dimension | Local (Qwen3) | Neve (cloud) |
|---|---|---|
| Sensitive evidence content | **Required** | Prohibited |
| Data residency (PCI/RBI) | ✅ on-host | ⚠ requires sign-off |
| Cost | zero per-token | per-token |
| Long-context synthesis | Good (8B/14B) | Stronger |
| Board narrative polish | Good | Stronger |
| Air-gap capability | ✅ | ✗ |

**Rule:** sensitive → Local; non-sensitive aggregate synthesis → Hybrid (cloud optional). No sensitive path is Cloud-only.

## Cross-references
- [Master Use Case & LLM Reference](ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) · [LLM Implementation Roadmap](ECS_LLM_IMPLEMENTATION_ROADMAP.md) · [Local vs Cloud Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md) · [LLM Use Case Coverage Matrix](ECS_LLM_USE_CASE_COVERAGE_MATRIX.md)
