# ECS ↔ ADIP Convergence Strategy

Premise: ECS (Evidence Collection System — audit/compliance/evidence) and ADIP (sibling
platform) become **complementary products on a shared enterprise foundation**. This document
defines the shared services, AI layer, governance, knowledge base, and workflow engine, plus a
target-state architecture and phased convergence plan.

Goal: one foundation, two products — maximize reuse, minimize duplication, present a unified
enterprise experience to shared users (CIO/CISO/CRO/Audit).

---

## 1. Strategic rationale
- Both products serve overlapping enterprise buyers (CIO/CISO/CRO/Head Audit).
- Both need: identity & RBAC, evidence/artefact handling, AI copilot + RAG, dashboards,
  workflow, integrations, audit trail.
- Converging the foundation reduces TCO, accelerates each product's roadmap, and enables
  cross-product insights (e.g. ADIP signals feeding ECS evidence/observations).

---

## 2. Shared Services (foundation layer)

| Shared service | Source of truth | Both products consume |
|---|---|---|
| Identity & Access (OIDC/JWT, RBAC, scope) | ECS `app/auth/` (mature) | Yes |
| Audit Trail (immutable) | Unified service | Yes |
| Object/Evidence storage (MinIO) | Shared bucket strategy | Yes |
| Notification & alerting | Unified | Yes |
| Reporting & export (PDF/XLSX) | Unified engine | Yes |
| Connector framework (Git/Jira/SNOW/SIEM) | Unified connector SDK | Yes |
| Tenant & org model | Unified | Yes |

**Principle:** extract ECS's mature auth, audit-trail, reporting, and connector primitives into
a shared platform package consumed by both products.

## 3. Shared AI Layer
- **One AI service** providing: RAG (pgvector), grounded Copilot, summarization, Q&A-with-
  citations, embeddings, evaluation/guardrails.
- ECS uses it for evidence/audit Q&A; ADIP uses it for its domain.
- **Cross-product grounding:** a shared embedding/index namespace allows a copilot answer to
  cite both ECS evidence and ADIP artefacts where authorized.
- Shared **AI governance**: prompt/audit traceability, hallucination monitoring, model registry.

## 4. Shared Governance
- Unified **policy, control-ownership (RACI), exception/waiver, attestation** services.
- Single **governance audit trail** and **regulatory mapping registry**.
- Consistent **risk register** model so risks raised in either product roll up to one enterprise
  view.

## 5. Shared Knowledge Base
- Common **knowledge hub**: frameworks, controls, policies, runbooks, remediation playbooks.
- Indexed once into the shared RAG layer; both copilots draw from it.
- Versioned, access-controlled, and citable.

## 6. Shared Workflow Engine
- One **workflow runtime**: tasks, approvals, SLAs, escalation, delegation, conditional routing.
- ECS configures audit/evidence workflows; ADIP configures its own — same engine, different
  templates.
- Shared **SLA + escalation matrix** and **workflow analytics**.

---

## 7. Target-state architecture

```
+---------------------------------------------------------------+
|                    Unified Experience Layer                   |
|   ECS UI (audit/evidence)        ADIP UI (domain)             |
+---------------------------------------------------------------+
|                    Product Domain Services                    |
|   ECS domain (frameworks,        ADIP domain services         |
|   evidence-intel, observations)                                |
+---------------------------------------------------------------+
|                 Shared Platform Foundation                    |
|  Identity/RBAC | Audit Trail | Workflow Engine | Reporting    |
|  Connector SDK | Notifications | Tenant/Org | Knowledge Hub   |
+---------------------------------------------------------------+
|                    Shared AI Layer                            |
|  RAG (pgvector) | Copilot | Summarize | Q&A | Eval/Guardrails |
+---------------------------------------------------------------+
|                    Shared Data Spine                          |
|  Postgres | pgvector | Redis | MinIO | Event backbone         |
+---------------------------------------------------------------+
```

---

## 8. Convergence phases

| Phase | Focus | Outcome |
|---|---|---|
| C1 — Identity & Audit | Extract ECS auth + audit-trail as shared services | Single sign-on, one audit trail across both |
| C2 — AI Layer | Promote RAG/Copilot to a shared AI service | One copilot foundation, cross-product grounding |
| C3 — Connectors & Reporting | Unify connector SDK + reporting/export | Shared integrations, consistent exports |
| C4 — Workflow & Governance | Unify workflow runtime + governance services | One SLA/escalation/policy/risk model |
| C5 — Knowledge & Data spine | Shared knowledge hub + event backbone | Unified knowledge, real-time cross-product events |
| C6 — Unified Experience | Cross-product navigation + rollups | One enterprise pane for shared executives |

---

## 9. Risks & mitigations
- **Coupling risk:** keep the shared foundation behind stable, versioned interfaces; products
  depend on contracts, not internals.
- **Release cadence:** independent product release trains on a shared, semver'd platform.
- **Data isolation:** shared spine with per-product/per-tenant scoping enforced at the auth layer.
- **Ownership:** a platform team owns the foundation; product teams own their domains.

## 10. Recommendation
Begin with **C1 (Identity & Audit)** and **C2 (AI Layer)** — the highest-reuse, lowest-
regret extractions, both anchored in ECS's already-mature subsystems. This establishes the
shared foundation while each product continues to ship, and unlocks cross-product intelligence
that neither product could deliver alone.
