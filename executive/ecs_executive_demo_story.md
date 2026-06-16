# ECS — Executive Demo Story

**Purpose:** A precise, click-by-click narrative for a 25–30 minute executive demonstration of ECS. Every screen, route, role and number below maps to an actual implementation in the repository. Use this as the presenter's script.
**Demo timeline anchor:** the showcase layer is anchored to a deterministic demo date so audit calendars and aging always render consistently.

---

## 0. Pre-flight (presenter only)

| What | How |
|---|---|
| Local app | `./start_ecs.sh` (or `uvicorn app.main:app --reload`) → `http://localhost:8000` |
| Full stack (real connectors) | `docker compose up` (brings up `ecs`, `postgres`, `pgvector`, `redis`, `minio`; profiles `sources` add Gitea/Jenkins, `demo-connectors` add SonarQube) |
| Seed live evidence | `demo-data/seed_demo_environment.sh` (Gitea repos, Jenkins jobs, SonarQube projects, gitleaks sample) |
| Login | Role chooser on `/` — pick the persona for each act below |

Two demo modes exist and both are legitimate:
- **Showcase mode** (`/dashboard`, `/mvp/*`, `/framework/*`): deterministic, always-populated, no external dependencies — best for boardrooms.
- **Live platform mode** (`/mvp/platform/*`): real connector-collected evidence in PostgreSQL — best for technical buyers and auditors who want to see real artifacts.

---

## Act 1 — "The portfolio is the system of record" *(App Owner)*

**Screens:** `/mvp/platform/onboarding` → `/mvp/platform/inventory`

**Do:** Register an application — name, owner, business unit, criticality, environment, and the frameworks in scope (SOC2, ISO27001, PCI-DSS, RBI-CSF, AI-SDLC).

**Say:** *"Everything in ECS hangs off the application portfolio. Onboarding declares ownership and which frameworks apply — that becomes the denominator for every coverage and readiness number you'll see. Nothing is hand-waved; coverage is computed against declared scope."*

**Proof point:** A new row appears in the Application Inventory and an `application.onboard` entry lands in the immutable audit log. The demo environment ships with 10 applications onboarded (showcase layer carries 20 banking applications).

---

## Act 2 — "Evidence must stay fresh" *(Compliance Head)*

**Screen:** `/mvp/platform/scheduler`

**Do:** Add a recurring collection schedule (connector + cadence). Submit.

**Say:** *"Audit readiness fails when proof goes stale. Schedules define a collection cadence per connector and application with next-run tracking, so evidence is refreshed before — not during — an audit."*

**Proof point:** A schedule row with a computed `next_run`; a `schedule.create` audit entry. Freshness policy is configurable per evidence type in `config/sufficiency.yaml` (e.g. CI builds 14 days, quality gates 30 days, policies 365 days).

---

## Act 3 — "Connectors collect real artifacts" *(Compliance Head / Ops)*

**Screen:** `/mvp/integration-health` → **Sync Now** on Gitea / Jenkins / SonarQube

**Say:** *"These are real connectors, not screenshots. They pull commits, pull requests, build results, quality gates and security hotspots into PostgreSQL, then automatically assemble Commit → Build → Sonar correlation chains."*

**Proof point:** 54 evidence records collected; 6 CI/CD correlation chains; `evidence.collect` audit entries; each sync run logged with health status. The connector factory and 12 connector implementations live in `ecs_platform/connectors/`. (For a boardroom without Docker, narrate this against the showcase Integrations Hub instead.)

---

## Act 4 — "Approve once, the auditor's quality gate" *(Auditor)*

**Screen:** `/mvp/platform/evidence-lifecycle`

**Do:** Move an item Collected → Under Review → Approved (or Rejected); set a validity window.

**Say:** *"Only Approved evidence counts toward readiness, and approval carries a validity window. Expired evidence is flagged automatically. This is the auditor's quality gate, and it is enforced — auditors review, owners cannot self-approve."*

**Proof point:** 37 Approved / 11 Under Review / 3 Rejected / 2 Expired; `evidence.review` audit entries. RBAC is enforced (`config/rbac.yaml`, `app/auth/`): an owner attempting to approve is denied; an auditor attempting to upload is denied with a toast.

---

## Act 5 — THE DIFFERENTIATOR: "One artifact, many obligations" *(Compliance Head)*

**Screen:** `/mvp/platform/evidence-reuse`

**Say:** *"This is where ECS pays for itself. A single SonarQube quality gate satisfies SOC2 CC7.1, ISO 27001 A.14.2.1, PCI-DSS 6.3, RBI-CSF BCSF-SDLC and AI-SDLC simultaneously through the control→framework crosswalk. Collect once; comply many."*

**Proof point — the headline number:** **5.0× cross-framework reuse** — 48 evidence items satisfy 240 framework obligations = **192 collection operations saved**. The "One Evidence → Multiple Frameworks" tabs and the Control × Framework crosswalk matrix make it concrete and clickable.

*This is the single most important moment of the demo. Pause here.*

---

## Act 6 — "Same truth, framed for each leader" *(CIO / Vertical Head / Auditor / App Owner)*

**Screens:** `/mvp/platform/scorecard?role=…` (role switcher), `/mvp/platform/framework-coverage`, `/mvp/platform/control-coverage` — and the showcase persona dashboards: `/dashboard/cio`, `/dashboard/vertical-head`, `/dashboard/compliance-head`, `/dashboard/functional-head`.

**Say:** *"Every leader sees one version of the truth, framed for their role: onboarded apps, evidence collected, reuse multiple, framework coverage, open observations, rejected evidence and a composite compliance score. Switch the role and the same data re-frames — no separate spreadsheets, no reconciliation."*

**Proof point:** Framework coverage 66.7% overall (AI-SDLC 83.3%); control coverage 35.7%; composite compliance score 57.7% (banded "At Risk"); 12 open observations; 3 rejected. Every KPI is drillable to the supporting records.

---

## Act 7 — "Readiness is a number you can defend" *(Auditor / CIO)*

**Screens:** `/mvp/platform/audit-readiness`, `/mvp/platform/executive-summary`

**Say:** *"Readiness isn't a vibe. It's 50% control coverage + 30% approved evidence + 20% freshness, scored per application and overall. When an auditor asks 'why 57.7%?', we click through to the exact controls, the exact approved artifacts, and the exact stale items."*

**Proof point:** Per-app readiness bands, open gaps and expired counts, and the full audit log of every onboard / sync / review as the immutable trail.

---

## Act 8 — "Ask the platform in plain English" *(any role)*

**Screen:** The floating AI Copilot dock (present across all pages); platform RAG assistant.

**Do:** Ask *"Which applications have expired PCI-DSS evidence?"* or *"What is RBI Cyber Security Framework?"*

**Say:** *"The assistant is grounded. It answers only from evidence in the repository, cites its sources, and refuses to answer when it has no evidence — so it can't hallucinate a control into existence. Provider is pluggable (local Ollama, Gemini, OpenAI, Azure, Claude) with no code change."*

**Proof point:** `config/llm.yaml` (`require_citations: true`, `refuse_without_evidence: true`), `ecs_platform/rag.py`, pgvector store (`config/vectorstore.yaml`). The showcase Copilot additionally answers framework definitions, work-queue, rejection and SLA questions deterministically.

---

## Act 9 (optional, technical audience) — "Governance is shifted left" *(AI-SDLC)*

**Screens:** `/mvp/ai-sdlc` (home), `/mvp/sdlc-gates`, control tower

**Say:** *"AI-SDLC applies Audit Driven Development — compliance gates across requirement → design → development → testing → go-live, per release. Controls are satisfied as software is built, not bolted on before an audit. It also governs AI itself: model registry, prompt audit, hallucination and unsafe-prompt signals, and token-spend visibility."*

**Proof point:** `modules/ai_sdlc/` (stage gates, control tower, controlled documents, evidence governance, reports); per-stage readiness, control coverage, evidence coverage and open-gap counts.

---

## The Close (60 seconds)

> *"You just saw an application onboarded, evidence collected from real tools, approved once by an auditor, and then reused 5× across five frameworks — with every leadership number traceable to its source and an AI assistant that refuses to make things up. That is the entire compliance lifecycle, on one platform. The ROI model shows this pays back inside two years and returns nine figures at portfolio scale. The decision is whether to run a 25-application pilot on your own data next quarter."*

---

## Quick-reference: routes used in this demo

| Act | Primary route(s) |
|---|---|
| 1 | `/mvp/platform/onboarding`, `/mvp/platform/inventory` |
| 2 | `/mvp/platform/scheduler` |
| 3 | `/mvp/integration-health` |
| 4 | `/mvp/platform/evidence-lifecycle` |
| 5 | `/mvp/platform/evidence-reuse` |
| 6 | `/mvp/platform/scorecard`, `/framework-coverage`, `/control-coverage`, `/dashboard/cio` |
| 7 | `/mvp/platform/audit-readiness`, `/executive-summary` |
| 8 | AI Copilot dock / RAG assistant |
| 9 | `/mvp/ai-sdlc`, `/mvp/sdlc-gates` |

**Fallback:** if the live stack is unavailable, run the entire story in showcase mode (`/dashboard`, `/framework/{name}`, `/mvp/audit-prep`, `/mvp/reuse`, `/mvp/demo-overview`, `/mvp/reports`) — the narrative and numbers are deterministic and require no external services.
