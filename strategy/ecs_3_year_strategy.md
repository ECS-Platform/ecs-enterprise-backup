# ECS — 3-Year Strategy

**Lens:** Chief Product Officer + Principal Enterprise Architect + CIO Advisory
**Horizon:** FY26 → FY28 (3 years)
**Anchor:** The strategy sequences the actual `product/ecs_enterprise_backlog.md` items and aligns to the `config/roi.yaml` rollout milestones (25 → 100 → 250 → 500 → 605 → 905 applications).

---

## 1. Strategic Intent

> Make ECS the bank's **enterprise system of record for compliance evidence** — where every framework obligation is satisfied by evidence collected once from real tools, kept fresh automatically, reused across frameworks, and defensible to any regulator, with AI that is governed and grounded.

Three pillars:
1. **Trust** — productionize identity, persistence, security and observability so ECS is safe to run on regulated workloads.
2. **Reach** — onboard the bank's real source systems and scale across the ~900-application portfolio.
3. **Differentiation** — extend the reuse crosswalk, continuous controls monitoring and AI-SDLC governance into capabilities incumbents do not have.

---

## 2. Year 1 (FY26) — Productionize & Prove

**Theme:** Turn a demonstrable platform into a secured single-tenant system of record, and prove value on the customer's data.

**Outcomes**
- Converge the dual data planes onto the `ecs_platform` Postgres repository (backlog #1–4).
- Enable OIDC/SSO, enforce RBAC on every route, map IdP groups → roles/scope (#5–9).
- CSRF, signed downloads, secret vault, encryption at rest, and a **formal security review + pen test** (#10–15).
- Stand up CI/CD with coverage gate and supply-chain scanning over the existing 38-suite test base (#42–43).
- Multi-worker-safe state; remove module-level mutable globals (#37).
- Onboard the first real enterprise connector beyond CI/CD (ServiceNow) (#16).
- **R1 pilot: 25 applications** on live Gitea/Jenkins/SonarQube — validate 5× reuse and readiness model on real data.

**Rollout milestone:** 25 → 100 applications.
**Financial checkpoint (`roi.yaml`/ROI model):** Expected net benefit ₹0.54 Cr (FY26, 25 apps) → ₹16.16 Cr (100 apps); payback inside Year 1–2.

**Exit criteria:** ECS passes the production-readiness gate in `governance/ecs_production_readiness.md` for single-tenant regulated use; pilot reports measured reuse multiple and FTE hours released.

---

## 3. Year 2 (FY27) — Integrate & Operate

**Theme:** Make ECS an enterprise-operated platform fed by the bank's real tool estate.

**Outcomes**
- Onboard the enterprise connector set: Jira, SharePoint + Teams (MS Graph), Prisma Cloud, GitHub/Azure DevOps (#17–20); add resilience, health SLOs and alerting (#21–22).
- Time-driven scheduled collection + background ingestion/embedding queue on Redis (#24–25, #28).
- Observability stack: OpenTelemetry tracing, structured logs, Prometheus metrics, error monitoring (#33–36).
- HA topology (k8s/helm), documented DR runbook, backup/restore, portfolio-scale load test (#38–40).
- Put evidence-sufficiency scoring into the reviewer loop and readiness (#27); RAG eval harness (#26).
- Real PDF/Excel/PPT report rendering + one-click auditor evidence packs (#50–51).
- Persisted exception/CAB workflow with SLA tracking (#58).

**Rollout milestone:** 100 → 250 → 500 applications.
**Financial checkpoint:** Expected net benefit ₹34.12 Cr (200 apps) → ₹88.60 Cr (500 apps); stable OPEX ₹2.2 Cr.

**Exit criteria:** ECS runs production-grade with HA/DR/observability; majority of pilot bank's frameworks fed by live connectors; auditor packs generated from the platform for a real audit cycle.

---

## 4. Year 3 (FY28) — Differentiate & Scale

**Theme:** Extend the moat and prepare for multi-institution scale.

**Outcomes**
- Multi-tenant scaffolding (`tenant_id` on every entity) to enable group entities / multiple banks (#41).
- Continuous Controls Monitoring: scheduled `control_validation_engine` with drift visualization (#55).
- AI-SDLC gates wired to live CI to block releases on failed compliance gates (#61); controlled-document e-signature (#62).
- AI maturation: enforce hallucination/unsafe-prompt guards on live calls, real token-spend governance, audit-response narrative generator, vector semantic search (#29–32).
- Promote AI Governance to a first-class framework; framework version management; crosswalk authoring UI (#54, #56–57).
- ML-based cross-tool correlation; queryable evidence-lineage graph; risk quantification (#60, #64, #59).
- Accessibility (WCAG 2.1 AA), responsive/mobile auditor experience, notification inbox (#45–46, #49).
- Regulator read-only dashboard (#53).

**Rollout milestone:** 500 → 605 → 905 applications (full portfolio).
**Financial checkpoint:** Year-7 trajectory toward ₹143.08 Cr Expected net benefit at scale.

**Exit criteria:** Full-portfolio coverage; continuous (not periodic) compliance posture; ECS positioned for a second institution.

---

## 5. Capability Roadmap at a Glance

| Capability area | FY26 | FY27 | FY28 |
|---|---|---|---|
| Identity & RBAC | Enable OIDC/SSO, enforce everywhere | Fine-grained scope, delegation | Tenant-aware identity |
| Persistence | Converge to Postgres SoR | Scale + backup/DR | Multi-tenant data model |
| Connectors | CI/CD live + ServiceNow | Jira, MS365, Prisma, ADO/GitHub | SIEM/Checkmarx/Tripwire + marketplace pattern |
| AI | Grounded RAG in prod, sufficiency in loop | RAG eval, auto-embedding | Guards enforced, narrative gen, semantic search |
| AI-SDLC | Gates operational | Linked to evidence | Release-blocking, e-sign, CCM |
| Reporting | Pilot reports | Real PDF/XLS/PPT, auditor packs | Scheduled + regulator views |
| Ops/Reliability | CI/CD, multi-worker safe | HA/DR/observability | Multi-tenant SRE |

---

## 6. Investment & Team (aligned to `config/roi.yaml` workstreams)

The ROI configuration models a 24-person program across seven workstreams:

| Workstream | Headcount | Annual cost |
|---|--:|--:|
| Core Platform | 6 | ₹1.8 Cr |
| Integrations | 4 | ₹1.1 Cr |
| AI & Evidence Intelligence | 4 | ₹1.3 Cr |
| DevOps & Platform | 3 | ₹0.9 Cr |
| Operations & Reliability | 3 | ₹0.8 Cr |
| Database & Data Platform | 2 | ₹0.6 Cr |
| Program Governance | 2 | ₹0.7 Cr |

**Program envelope:** ₹8 Cr implementation + ₹2 Cr/yr run (modeled), stabilizing at ₹2.2 Cr OPEX.

---

## 7. Strategic Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Productionization slips, eroding demo credibility | Hard R1 gate; pilot on 25 apps with the live connectors already working |
| Connector onboarding stalls on enterprise IT | Lead with self-hostable CI/CD connectors already live; sequence SaaS by customer priority |
| Data-residency/security objections | Default local Ollama + air-gap deployment; security review in FY26 |
| Scope creep into incumbent GRC turf | Position as the evidence-automation layer; reuse economics as the wedge |
| Key-person/state-coupling debt | FY26 multi-worker-safe refactor (#37) before scaling |

---

## 8. The North-Star Metric

**Cross-framework evidence reuse multiple** (demonstrated 5.0× today). Sustaining and raising this number across the growing portfolio is the single measure that proves ECS's core thesis and directly drives the ROI model. Secondary metrics: composite readiness %, observation closure acceleration, and connector-collected evidence freshness.
