# ECS Local LLM Screen Mapping (Phase 3)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

For every page: **Current Behaviour**, **Local LLM Opportunity**, **Implementation Effort**.

**Legend — current AI capability:**
- **RAG** = already uses the provider (local Ollama) when configured
- **Det** = deterministic (no model); works identically air-gapped
- **Heur** = keyword/heuristic search labeled "semantic"

**Effort:** S (config/wire existing provider) · M (new prompt + RAG wiring on existing data) · L (new pipeline)

> Important: **no page "Requires cloud AI."** The only model-using paths default to local Ollama. Cloud
> is never required.

---

## Executive Overview

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| CIO Dashboard | `/dashboard/cio` | Det | Executive narrative summary of KPIs (local gen) | M |
| Enterprise | `/mvp/enterprise` | Det | BU posture narrative; anomaly callouts | M |
| Pan India | `/mvp/pan-india` | Det | Regional risk narrative | M |
| Trends | `/mvp/trends` | Det | Trend explanation / MoM commentary | M |
| Reports | `/mvp/reports`, `/mvp/reports/view/{type}` | Det | NL report summary + Q&A over report | M |
| ROI / Value Realization | `/mvp/roi` | Det | Plain-language ROI narrative | M |
| Demo Overview | `/mvp/demo-overview` | Det | Guided narrative | S |

## Frameworks

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| Framework page | `/framework/{name}` | Det (catalog) | Control-gap explanation; control recommendation | M |
| Framework Admin | `/mvp/framework-admin` | Det | NL framework mapping assist | M |
| Framework Loader | `/mvp/framework-loader` | Det | Control-mapping suggestions | M |
| ITPP Command Center | (ITPP) | Det | Problem RCA narrative | M |

## Operations

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| Scheduler | `/mvp/scheduler` | Det | Run-failure explanation | M |
| Predefined Queries | `/mvp/predefined-queries` | Det (connectors) | NL→query intent; scan-result summary | M |
| Integrations Hub | `/mvp/integrations-hub` | Det | Connector failure analysis assistant | M |
| Onboarding | `/mvp/onboarding` | Det (simulator) | Onboarding gap narrative | M |
| AI Ops Assistant | `/mvp/ai-ops-assistant` | Det (keyword) | Upgrade to RAG (local) | M |

## Governance

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| Completeness | `/mvp/completeness` | Det | Gap-analysis narrative | M |
| Audit Prep | `/mvp/audit-prep` | Det | Audit-readiness assessment summary | M |
| Lifecycle | `/mvp/lifecycle` | Det | Stale/aging explanation | M |
| Comparison | `/mvp/comparison` | Det | Cross-framework correlation narrative | M |
| Governance Analytics | `/mvp/governance-analytics` | Det | Governance posture narrative | M |

## Evidence Governance

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| Evidence Health | `/mvp/evidence-health` | Det | Evidence quality review; sufficiency narrative | M |
| Evidence Approval | `/mvp/evidence-approval` | Det | Rejection-reason drafting; approval rationale | M |
| Evidence Search | `/mvp/search` | **Heur** | Upgrade to embeddings (true semantic) | M |
| Evidence Reuse | `/mvp/reuse` | Det ("NO-LLM") | Similar-evidence discovery via embeddings | M |
| Evidence Repository | (repository engine) | Det | Classification / metadata tagging | M |
| Evidence Lifecycle (platform) | `/mvp/platform/evidence-lifecycle` | Det | Lifecycle risk narrative | M |

## Enterprise GRC

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| Risk Register | `/mvp/risk-register` | Det | Risk summarization | M |
| Exceptions / Exception Governance | `/mvp/exceptions`, `/mvp/exception-governance` | Det | Exception analysis; expiry rationale | M |
| CMDB | `/mvp/cmdb` | Det | Asset risk narrative | M |
| Regulatory | `/mvp/regulatory` | Det | Regulatory mapping explanation | M |
| Heatmaps | `/mvp/heatmaps` | Det | Hotspot narrative | M |
| Correlation | `/mvp/correlation` | Det | Cross-signal correlation narrative | M |

## AI Governance / AI SDLC

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| AI Governance Posture | `/mvp/ai-governance` | Det (mock) | Posture narrative; prompt-risk summary | M |
| AI Registry | `/mvp/ai-registry` | Det (mock) | Model/prompt registry assist | M |
| AI SDLC stages | `/mvp/ai-sdlc/*` | Det (mock) | Stage-gate readiness narrative | M |
| Control Tower | `/mvp/ai-sdlc/control-tower` | Det (mock) | Production-monitoring narrative | M |

## Platform Assistant (already local LLM)

| Page | Route | Current | Local LLM opportunity | Effort |
|---|---|---|---|---|
| Platform / AI Assistant | `/mvp/ai-assistant`, `/mvp/platform/assistant`, `/api/platform/assistant` | **RAG (local)** | Already local-LLM; expand grounding scope | S |
| Showcase Copilot | `/mvp/chat` | Det (keyword) | Optional upgrade to local RAG | M |

---

## Roll-up

| Category | Pages | RAG today | Det today | Heur today | Requires cloud |
|---|---|---|---|---|---|
| Executive | 7 | 0 | 7 | 0 | **0** |
| Frameworks | 4 | 0 | 4 | 0 | **0** |
| Operations | 5 | 0 | 5 | 0 | **0** |
| Governance | 5 | 0 | 5 | 0 | **0** |
| Evidence Gov | 6 | 0 | 5 | 1 | **0** |
| Enterprise GRC | 6 | 0 | 6 | 0 | **0** |
| AI Gov / SDLC | 4 | 0 | 4 | 0 | **0** |
| Platform Assistant | 2 | 1 | 1 | 0 | **0** |

**Conclusion:** every screen is **either already local-RAG or deterministic** — none requires cloud AI.
Each deterministic page has a clear, **M-effort** local-LLM enhancement that reuses the existing
Ollama provider + pgvector. The single Heur page (Evidence Search) is the best first upgrade to true
local embeddings.
