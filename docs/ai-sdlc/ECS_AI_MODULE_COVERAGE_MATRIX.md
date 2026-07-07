# ECS AI Module Coverage Matrix (Phase 3)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Local-LLM readiness legend:**
- ✅ **Ready** — works fully on local LLM/local stack (either provider-based or no model needed)
- ✅* **Ready (deterministic)** — no model call; provider-agnostic, identical air-gapped
- 🔶 **Optional upgrade** — could route through local LLM later; not required for local operation
- ❌ **Not found in code**

Every AI/LLM path defaults to **local Ollama** (`config/llm.yaml:7`), so every module below is
**local-LLM ready** for the air-gapped target.

---

## Operations

| Module | Route / file | AI class | Local-LLM readiness |
|---|---|---|---|
| Scheduler | `/mvp/scheduler`, `scheduler_module.py` | Deterministic | ✅* |
| Predefined Queries | `/mvp/predefined-queries`, `query_connectors.py` | Deterministic (connector exec) | ✅* |
| Integrations Health | `/mvp/integrations`, `/mvp/integrations-hub`, `integrations_module.py` | Deterministic (mock health) | ✅* |
| Onboarding | `/mvp/onboarding`, `onboarding_engine.py` (`/api/onboarding/simulate`) | Deterministic simulation | ✅* |
| Workflow Engine | `operational_workflows.py`, `workflow_module.py` | Deterministic | ✅* |
| Evidence Workflow | `evidence_workflow_engine.py` | Deterministic | ✅* |
| AI Ops Assistant | `/mvp/ai-ops-assistant`, `operations_intelligence.py` | Deterministic (keyword) | ✅* |

## Frameworks (catalog = `framework_catalog.py:740-756`)

| Requested framework | In catalog? | AI class | Readiness |
|---|---|---|---|
| C-SITE | **Yes** (`CSITE`) | Deterministic | ✅* |
| PCI DSS | Yes | Deterministic | ✅* |
| DPSC | Yes | Deterministic | ✅* |
| ISG | Yes | Deterministic | ✅* |
| MBSS | **❌ Not in catalog** | — | ❌ |
| ASST | Yes | Deterministic | ✅* |
| ITPP | Yes (+ ITPP command center) | Deterministic | ✅* |
| ITDRM | Yes | Deterministic | ✅* |
| OS Baselining | Yes | Deterministic | ✅* |
| DB Baselining | Yes | Deterministic | ✅* |
| Middleware Baselining | **❌ Not in catalog** (only `Nginx Baselining` exists; "Middleware Baseline" string in `ecs_governance_drilldowns.py:13`) | — | ❌ (use Nginx Baselining) |
| Application Security | Yes (`AppSec`) | Deterministic | ✅* |
| VAPT | Yes | Deterministic | ✅* |
| *(also in catalog)* SOC2, ISO27001, RBI Cyber Security | Yes | Deterministic | ✅* |

> All framework logic is catalog/rule driven (`FRAMEWORK_CATALOG`), so it is **fully air-gap safe** and
> provider-independent. The 15 catalog frameworks: PCI DSS, DPSC, OS Baselining, DB Baselining, Nginx
> Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST.

## Evidence Governance

| Module | Route / file | AI class | Readiness |
|---|---|---|---|
| Evidence Collection | scheduler/onboarding + connectors | Deterministic | ✅* |
| Evidence Repository | `evidence_repository.py` | Deterministic ("simulate vector reuse" `:104`) | ✅* |
| Evidence Validation | sufficiency/validation engines (`.env.example:128-157`, NON-LLM) | Deterministic | ✅* |
| Evidence Approval | `/mvp/evidence-approval`, `evidence_approval_engine.py` | Deterministic | ✅* |
| Evidence Reuse | `/mvp/reuse`, `reuse.py` ("NO-LLM" `:8`) | Deterministic | ✅* / 🔶 (embeddings optional) |
| Evidence Search | `/mvp/search`, `search_module.py:119-137` | Heuristic-search | ✅* / 🔶 (upgrade to embeddings) |
| Evidence Lifecycle | `/mvp/lifecycle`, `/mvp/platform/evidence-lifecycle` | Deterministic | ✅* |

## Governance Dashboards

| Module | Route | AI class | Readiness |
|---|---|---|---|
| Governance Dashboard | `/mvp/governance-analytics` | Deterministic | ✅* |
| Compliance Dashboard | `/mvp/comparison`, `/mvp/completeness` | Deterministic | ✅* |
| Risk Dashboard | `/mvp/risk-register` | Deterministic | ✅* |
| Audit Dashboard | `/mvp/audit-prep`, `/mvp/platform/audit-readiness` | Deterministic | ✅* |
| Findings Dashboard | `/mvp/evidence-health` | Deterministic | ✅* |
| Remediation Dashboard | `/mvp/exceptions`, `/mvp/exception-governance`, `/mvp/correlation` | Deterministic | ✅* |

## Executive

| Module | Route | AI class | Readiness |
|---|---|---|---|
| Executive Overview | `/dashboard/cio`, `/mvp/demo-overview` | Deterministic | ✅* |
| Enterprise | `/mvp/enterprise` | Deterministic | ✅* |
| Pan India | `/mvp/pan-india` | Deterministic | ✅* |
| Trends | `/mvp/trends` | Deterministic | ✅* |
| Reports | `/mvp/reports`, `/mvp/reports/view/{type}` | Deterministic | ✅* |
| Value Realization / ROI | `/mvp/roi`, `mvp_roi_center.html` | Deterministic | ✅* |

## AI Governance

| Module | Route / file | AI class | Readiness |
|---|---|---|---|
| Model Registry | `/mvp/ai-registry`, `ai_sdlc_governance_mock.py:1448-1567` | Deterministic (mock) | ✅* |
| Prompt Registry | `ai_sdlc_governance_mock.py:1475-1502` | Deterministic (mock) | ✅* |
| AI Governance Posture | `/mvp/ai-governance`, `build_ai_posture :898-1006` | Deterministic (mock) | ✅* |
| AI Risk Monitoring | posture/hallucination/token mock | Deterministic (mock) | ✅* |

## AI SDLC

| Stage | Route | AI class | Readiness |
|---|---|---|---|
| Requirements | `/mvp/ai-sdlc/requirements` | Deterministic (mock) | ✅* |
| Design | `/mvp/ai-sdlc/design` | Deterministic (mock) | ✅* |
| Development | `/mvp/ai-sdlc/development` | Deterministic (mock) | ✅* |
| Testing | `/mvp/ai-sdlc/testing` | Deterministic (mock) | ✅* |
| Release Readiness | `/mvp/ai-sdlc/golive` | Deterministic (mock) | ✅* |
| Production Monitoring | control tower / posture | Deterministic (mock) | ✅* |

---

## Coverage Summary

| Module group | Modules assessed | Local-LLM ready | Gaps |
|---|---|---|---|
| Operations | 7 | 7 | — |
| Frameworks | 13 requested (15 in catalog) | 13 | MBSS, Middleware Baselining not in catalog |
| Evidence Governance | 7 | 7 | — |
| Governance | 6 | 6 | — |
| Executive | 6 | 6 | — |
| AI Governance | 4 | 4 | — |
| AI SDLC | 6 | 6 | — |

**Every implemented module is local-LLM ready** because (a) deterministic modules need no model, and
(b) the only LLM paths (RAG/embeddings) default to local Ollama. Gaps are **missing frameworks**
(MBSS, Middleware Baselining), not AI-runtime gaps.
