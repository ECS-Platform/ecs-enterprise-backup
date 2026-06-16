# ECS — Board Summary

**Platform:** ECS (Evidence & Compliance System)
**Prepared by:** Office of the CPO / Enterprise Architecture / CIO Advisory
**Basis:** Direct inspection of the ECS repository (`app/`, `modules/`, `ecs_platform/`, `config/`, `tests/`, `docs/`). No projected or aspirational capability is presented as built.
**Audience:** Board, CIO, CISO, Chief Compliance Officer

---

## 1. What ECS Is (in one paragraph)

ECS is a single-pane Governance, Risk, Compliance, Audit and Evidence-Management platform for a regulated bank. It replaces fragmented spreadsheets, ServiceNow queues, SharePoint repositories and auditor email threads with one role-aware control surface. It is built as a **modular monolith** on FastAPI + Jinja2 (Python 3.12), decomposed into six business domains (`executive_overview`, `frameworks`, `operations`, `governance`, `enterprise_grc`, `ai_sdlc`) plus a shared core and an infrastructure layer (`ecs_platform/`) that provides real connectors, an evidence repository, a vector store and a grounded LLM-RAG assistant.

The platform exists in **two operating layers that both run today**:

1. **A deterministic governance showcase** — 16 pre-built compliance frameworks, ~307 controls and ~706 evidence records across 20 banking applications, seven role-tailored dashboards, full evidence workflow, audit-prep "war-room", cross-framework reuse intelligence and 30 regulator/audit report packs. State is hash-seeded so the demo is stable across reloads.
2. **A real connector-driven evidence platform** (`ecs_platform/` + `/mvp/platform/*`) — 13 source-system connectors (Gitea, GitHub, SonarQube, Jenkins, Jira, Confluence, Figma, ServiceNow, Teams, SharePoint, Prisma Cloud, Azure DevOps) ingest real artifacts into PostgreSQL, with a pgvector store, MinIO object store, Redis, deterministic evidence-sufficiency scoring, a control→framework crosswalk for evidence reuse, and a citation-grounded RAG assistant.

---

## 2. The Business Problem

A large bank runs ~900 applications against multiple regulatory and security frameworks (RBI Cyber Security / CSITE, PCI DSS, ISO 27001, SOC 2, DPSC, VAPT, AppSec, OS/DB/Nginx baselining, ITPP, ITDRM). Today that work is manual:

- Evidence is chased over email (industry-typical ~7 emails per observation), stored in SharePoint, and re-collected separately for each framework.
- Audit readiness is a point-in-time scramble, not a continuous state.
- Leadership has no single, drillable view of compliance posture across the portfolio.

ECS attacks this directly: **collect evidence once, map it to many frameworks, keep it fresh automatically, and make every number on every dashboard click-through traceable to its supporting records.**

---

## 3. What Has Actually Been Built (verified in code)

| Capability | Evidence in repository | Status |
|---|---|---|
| Role-aware platform, 7 UI personas + 9-role RBAC catalog | `modules/shared/.../role_permissions.py`, `config/rbac.yaml`, `app/auth/` | Built |
| 16 framework catalogs, ~307 controls, ~706 evidence records | `modules/frameworks/.../framework_catalog.py` | Built |
| Full evidence workflow (upload→submit→review→approve/reject/clarify/escalate→close) | `modules/shared/services/evidence_workflow_engine.py` | Built |
| Audit-prep cockpit: dynamic calendars, readiness scoring, KPI drill-downs | `audit_schedule_engine.py`, `mvp_audit_prep.html` | Built |
| Cross-framework reuse intelligence (18 control themes, overlap matrix, crosswalk) | `framework_intelligence.py`, control→framework crosswalk | Built |
| 13 real source-system connectors | `ecs_platform/connectors/` (factory + 13 connectors) | Built (3 live in dev: Gitea/Jenkins/SonarQube; SaaS interface-complete) |
| Evidence repository + pgvector + MinIO + Redis | `ecs_platform/repository`, `ecs_platform/vectorstore`, `docker-compose.yml` | Built |
| Grounded LLM-RAG assistant (citations required, refuses without evidence) | `ecs_platform/rag.py`, `config/llm.yaml` | Built (provider-pluggable: Ollama/Gemini/OpenAI/Azure/Claude) |
| Deterministic evidence-sufficiency scoring (5 weighted dimensions) | `config/sufficiency.yaml`, `app/sufficiency` | Built (flag-gated) |
| AI-SDLC "Audit Driven Development" — shift-left gates across requirement→go-live | `modules/ai_sdlc/` | Built |
| AI Governance posture (prompt audit, hallucination/unsafe-prompt signals, token usage) | `modules/ai_sdlc/`, demo engine | Built |
| RBAC enforcement, audit durability, evidence intel/analytics | `tests/test_rbac_*`, `test_audit_durability_phase4`, `test_evidence_intel_phase5_4` | Built (phased) |
| 30 regulator/audit report packs | `reporting_module._REPORT_DEFS` | Built |
| Automated test suite | 38 pytest files in `tests/` | Built |
| Containerized deployment | `Dockerfile`, `docker-compose.yml` (10 services) | Built |

---

## 4. Demonstrated Outcomes (from the live connector-driven flow)

These figures come from the platform's real evidence flow as documented in `demo-data/ECS_DEMO_NARRATIVE.md`, not from slideware:

- **5.0× cross-framework evidence reuse** — 48 evidence items satisfied 240 framework obligations = **192 collection operations eliminated**.
- A single SonarQube quality gate simultaneously satisfies **SOC2 CC7.1, ISO 27001 A.14.2.1, PCI-DSS 6.3, RBI-CSF BCSF-SDLC and AI-SDLC** via the control→framework crosswalk.
- Auditor quality gate operating: 37 Approved / 11 Under Review / 3 Rejected / 2 Expired evidence states.
- Composite readiness scored transparently: **50% control coverage + 30% approved evidence + 20% freshness**, per application and overall.

---

## 5. Financial Case (deterministic ROI model, `config/roi.yaml`)

The ROI engine computes every figure from editable assumptions (no hardcoded outputs). At the bank's stated scale (905 applications, 600 in VAPT scope; blended ₹1,500/hr):

| Headline | Conservative | Expected | Aggressive |
|---|--:|--:|--:|
| 25-application annual saving | ₹3.63 Cr | ₹4.54 Cr | ₹5.45 Cr |
| FTE equivalent released (25 apps) | 18.2 | 22.7 | 27.3 |
| Year-7 net benefit at scale | ₹114.46 Cr | ₹143.08 Cr | ₹171.70 Cr |
| Stable annual operating cost | ₹2.2 Cr | ₹2.2 Cr | ₹2.2 Cr |

**Program investment:** ₹8 Cr implementation + ₹2 Cr/yr run (per `config/roi.yaml`). **Payback is inside Year 1–2 in every scenario**, with nine-figure (₹114 Cr+) net benefit at portfolio scale even in the conservative case. (Full derivation: `strategy/ecs_roi_model.md`.)

---

## 6. Honest Risk & Readiness Position

ECS is **production-architected but not yet production-deployed in the bank's environment**. The board should fund a hardening phase, not assume completion. Key gaps (detailed in `governance/ecs_production_readiness.md`):

- **Identity:** JWT/OIDC middleware exists (`app/auth/`) but runs in pass-through mode by default; real IdP/SSO integration must be enabled and tested.
- **Persistence:** the showcase layer is in-memory; the connector platform persists to PostgreSQL/MinIO — the two must be fully converged onto the system-of-record.
- **Connector coverage:** 3 connectors are live in dev (Gitea/Jenkins/SonarQube); the 10 enterprise SaaS connectors are interface-complete but require tenant credentials and onboarding.
- **Scale/HA, observability, DR, and a formal security review** are required before regulated production use.

---

## 7. The Ask

1. **Approve a 9–12 month productionization program** (persistence convergence, IdP, enterprise connector onboarding, HA/observability, security review) at the modeled ₹8 Cr + ₹2 Cr/yr envelope.
2. **Authorize a controlled R1 pilot** on 25 in-scope applications and the live CI/CD connectors (Gitea/Jenkins/SonarQube) to validate the 5× reuse and readiness model on the bank's own data.
3. **Endorse RBI-CSF / CSITE / PCI-DSS as the anchor frameworks** for the pilot, with AI-SDLC governance as the differentiating capability.

---

## 8. One-Line Summary for the Board

> ECS already demonstrates collect-once / comply-to-many evidence automation with 5× reuse, real tool connectors, grounded AI and a transparent ROI model showing payback inside two years; the decision before the board is to fund the productionization that turns a working, demonstrable platform into the bank's enterprise system of record for compliance.
