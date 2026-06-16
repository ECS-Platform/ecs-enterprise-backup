# ECS — Customer Pitch

**Lens:** Principal Presales Architect
**Audience:** A regulated bank's CIO, CISO, Chief Compliance Officer and Head of Internal Audit.
**Ground rule:** Every capability in this pitch is implemented in the ECS repository. Roadmap items are clearly labeled as roadmap.

---

## 1. The One-Sentence Pitch

> **ECS turns scattered tool output into audit-ready evidence: onboard an application, schedule collection, and real connectors pull live artifacts into one repository with lineage — auditors approve once, and the control→framework crosswalk reuses that single artifact across SOC2, ISO 27001, PCI-DSS, RBI-CSF and AI-SDLC, with every leadership number traceable and an AI assistant that refuses to make things up.**

---

## 2. The Problem You Have Today

Your bank runs hundreds of applications against RBI Cyber Security / CSITE, PCI DSS, DPSC, ISO 27001, SOC 2, VAPT and more. Compliance today means:

- **Evidence chased over email** — industry-typical ~7 emails per observation.
- **Re-collected per framework** — the same control proof gathered again and again.
- **Audit as a scramble** — readiness is a point-in-time fire drill, not a state.
- **No single truth** — leadership reconciles spreadsheets instead of reading one number.

This is expensive, slow and risky — and it does not scale to your full application portfolio.

---

## 3. What ECS Does (and how it's built)

### 3.1 Collect once
Onboard an application (owner, BU, criticality, frameworks in scope). Real connectors — **Gitea, Jenkins, SonarQube live today; GitHub, Jira, Confluence, ServiceNow, SharePoint, Teams, Prisma Cloud, Azure DevOps, Figma interface-complete** — pull commits, PRs, builds, quality gates, security hotspots and findings into a PostgreSQL evidence repository with lineage. *(Built: `ecs_platform/connectors/`, 13 connectors.)*

### 3.2 Approve once, the auditor's quality gate
Evidence moves Collected → Under Review → Approved (or Rejected) with a validity window. Only **Approved** evidence counts toward readiness; expired evidence is flagged automatically. Roles are enforced — owners can't self-approve, auditors can't upload. *(Built: evidence workflow engine + `config/rbac.yaml`.)*

### 3.3 Comply to many — THE DIFFERENTIATOR
One artifact satisfies many obligations. A single SonarQube quality gate satisfies **SOC2 CC7.1, ISO 27001 A.14.2.1, PCI-DSS 6.3, RBI-CSF BCSF-SDLC and AI-SDLC** at once via the control→framework crosswalk. In our reference flow: **5.0× reuse — 48 evidence items satisfied 240 framework obligations, eliminating 192 collection operations.** *(Built: 18-theme crosswalk in `framework_intelligence.py`.)*

### 3.4 Stay ready, always
Dynamic audit calendars (quarterly + annual) across 16 frameworks, with a transparent readiness score: **50% control coverage + 30% approved evidence + 20% freshness**, per app and overall. *(Built: `audit_schedule_engine.py`, audit-prep cockpit.)*

### 3.5 One truth, framed per leader
CIO, Vertical Head, Compliance Head, Functional Head, Auditor and App Owner each see the same data, framed for them — every KPI drills to its supporting records. *(Built: persona dashboards + universal drilldown engine.)*

### 3.6 AI you can trust
A grounded assistant answers in plain English, **cites its sources, and refuses to answer without evidence** — so it can't invent a control. It runs on a **local model by default (air-gap capable)** or your choice of Gemini/OpenAI/Azure/Claude with no code change. *(Built: `ecs_platform/rag.py`, `config/llm.yaml`, pgvector.)*

### 3.7 AI governs AI
AI-SDLC applies "Audit Driven Development" — compliance gates across requirement → design → development → testing → go-live — plus AI governance posture (prompt audit, hallucination and unsafe-prompt signals, token spend). *(Built: `modules/ai_sdlc/`.)*

---

## 4. Why ECS Fits a Regulated Indian Bank

| Your requirement | ECS answer |
|---|---|
| RBI Cyber Security / CSITE, DPSC native | In the framework catalog out of the box (16 frameworks) |
| Data residency / air-gap | Default local Ollama model + self-hostable connectors — runs fully offline |
| Defensible numbers for regulators | Transparent readiness/sufficiency formulas; every metric drills to source; immutable audit log |
| No vendor lock-in on AI | Provider-pluggable LLM + vector store via config |
| Lower TCO than enterprise GRC | Modeled stable OPEX ₹2.2 Cr/yr |

---

## 5. The Numbers (deterministic ROI model)

| Headline (Expected scenario) | Value |
|---|--:|
| Annual saving per 25 applications | ₹4.54 Cr |
| FTE equivalent released (25 apps) | 22.7 |
| Cross-framework reuse demonstrated | 5.0× |
| Net benefit at 500 apps | ₹88.60 Cr |
| Stable operating cost | ₹2.2 Cr/yr |
| Payback | Inside Year 1–2 (all scenarios) |

*Every figure is computed by the ROI engine from editable assumptions (`config/roi.yaml`) — substitute your own blended rate and portfolio size and it recomputes. Full model: `strategy/ecs_roi_model.md`.*

---

## 6. Proof-of-Value Offer (R1 Pilot)

**Scope:** 25 of your applications, your live CI/CD (Gitea/Jenkins/SonarQube or GitHub/Azure DevOps), 4–6 anchor frameworks (RBI-CSF, PCI-DSS, ISO 27001, AppSec/VAPT + AI-SDLC).

**You will see, on your own data:**
- Real evidence collected from your tools into one repository.
- Your measured cross-framework reuse multiple.
- Composite readiness scored and defensible per application.
- FTE hours released vs. your current email-driven baseline.

**Timeline:** ~8–12 weeks, running on your infrastructure (on-prem / air-gap supported).

---

## 7. What We'll Be Straight With You About

ECS is **production-architected and demonstrable today**, and we are completing a hardening phase before regulated production traffic. Before go-live we will, with you: enable your SSO/IdP and enforce RBAC end-to-end, converge onto a single system of record, complete a security review and penetration test, and stand up HA/DR and observability. The full gate is documented in `governance/ecs_production_readiness.md` — we lead with it, we don't hide it.

---

## 8. The Close

> *"You already pay for compliance — in people, email and re-collected evidence. ECS doesn't add another tool to chase; it collects your evidence once, reuses it across every framework, and proves readiness on demand. Let's run a 25-application pilot on your data and measure the reuse multiple ourselves."*

**Next step:** schedule the R1 pilot scoping workshop. Demo script: `executive/ecs_executive_demo_story.md`.
