# ECS — Enterprise Backlog

**Owner:** Office of the CPO
**Scope:** Productionization and growth backlog for ECS, grounded in the current implementation. Each item names the actual module/file/config it extends or hardens. Nothing here invents a capability ECS does not have a foundation for.

**Conventions**
- **Priority:** P0 (production-blocking) · P1 (high) · P2 (medium) · P3 (opportunistic)
- **Size:** S (≤1 wk) · M (1–3 wk) · L (3–6 wk) · XL (6 wk+)
- **Theme codes:** PERSIST, IDENTITY, CONNECT, AI, OBSERV, SECURITY, SCALE, UX, REPORT, FRAMEWORK, GOV, AISDLC, DATA, PLATFORM, QA, GTM

| # | Theme | Item | Grounding (actual code) | Priority | Size |
|--:|---|---|---|:--:|:--:|
| 1 | PERSIST | Converge in-memory showcase state onto the `ecs_platform` Postgres repository as single system of record | `modules/shared/services/ecs_state.py` shims → `ecs_platform/repository` | P0 | XL |
| 2 | PERSIST | Persist evidence workflow state (submitted/approved/rejected/escalated/closed) to DB | `evidence_workflow_engine.py` | P0 | L |
| 3 | PERSIST | Durable audit trail with ≥1-year retention + indexed query | `app/audit/`, `test_audit_durability_phase4.py` | P0 | M |
| 4 | PERSIST | Durable observations + remediation records | `missing_evidence_engine.py`, `test_observation_durability_phase4_step3.py` | P0 | M |
| 5 | IDENTITY | Enable OIDC/SSO IdP integration (replace role-chooser) end-to-end | `app/auth/middleware.py`, `register_authentication` | P0 | L |
| 6 | IDENTITY | Enforce RBAC on every route (close pass-through gaps) | `config/rbac.yaml`, `app/auth/authz.py` | P0 | M |
| 7 | IDENTITY | Map IdP groups → ECS canonical roles + scope (vertical/function/app) | `config/rbac.yaml` `role_scope`, `scope_filters` | P0 | M |
| 8 | IDENTITY | Retire URL-param role/user passing in showcase routes | `app/routes_mvp.py` query-param plumbing | P1 | M |
| 9 | IDENTITY | MFA + session lifecycle (timeout, revoke, refresh) | `app/auth/` | P1 | M |
| 10 | SECURITY | CSRF tokens on all POST routes | `app/main.py`, route registrars | P0 | M |
| 11 | SECURITY | Signed, expiring URLs for evidence/report downloads | `/mvp/exports/download/*`, `/mvp/reports/download/*` | P1 | M |
| 12 | SECURITY | Content Security Policy + security headers middleware | `app/main.py` middleware stack | P1 | S |
| 13 | SECURITY | Secret management via vault (no env secrets at rest) | `config/*.yaml` `${ENV}` resolution | P1 | M |
| 14 | SECURITY | Full security review + pen test of regulated deployment | whole platform | P0 | L |
| 15 | SECURITY | Encryption at rest for evidence blobs (MinIO/S3 SSE) + KMS | `minio` service, `ecs_platform/repository` | P1 | M |
| 16 | CONNECT | Onboard ServiceNow connector to a real tenant (incidents/CHG/PRB/CAB) | `ecs_platform/connectors/servicenow_connector.py`, `config/integrations.yaml` | P0 | M |
| 17 | CONNECT | Onboard Jira connector (epics/issues/approvals → exceptions) | `jira_connector.py` | P1 | M |
| 18 | CONNECT | Onboard SharePoint + Teams via MS Graph app registration | `sharepoint_connector.py`, `teams_connector.py`, `_msgraph.py` | P1 | L |
| 19 | CONNECT | Onboard Prisma Cloud (cloud findings/compliance violations) | `prisma_connector.py` | P1 | M |
| 20 | CONNECT | Onboard GitHub + Azure DevOps for enterprise repos/pipelines | `github_connector.py`, `azure_devops_connector.py` | P2 | M |
| 21 | CONNECT | Connector retry/backoff, circuit-breaker, partial-sync recovery | `ecs_platform/connectors/http_client.py`, `defaults` in `integrations.yaml` | P1 | M |
| 22 | CONNECT | Connector health SLOs + alerting on sync failures | `integration_health_engine.py`, `test_connectivity_assessment_phase5_3.py` | P1 | M |
| 23 | CONNECT | Add Checkmarx / Tripwire / Splunk SIEM connectors | connector factory pattern in `ecs_platform/connectors/factory.py` | P2 | L |
| 24 | DATA | Scheduled, time-driven evidence collection (real scheduler workers) | `scheduler_module.py`, Redis service | P1 | L |
| 25 | DATA | Background job queue for ingestion/embedding (Celery/RQ on Redis) | `ecs_platform/ingestion.py`, `redis` | P1 | L |
| 26 | AI | Production-grade RAG eval harness (faithfulness, citation precision) | `ecs_platform/rag.py`, `config/llm.yaml` | P1 | M |
| 27 | AI | Wire evidence-sufficiency scoring into reviewer UI + readiness | `config/sufficiency.yaml`, `app/sufficiency`, `evidence_review` | P1 | M |
| 28 | AI | Re-index/embedding pipeline on connector ingest (auto-warm vectors) | `vectorstore.yaml`, `ecs_platform/vectorstore` | P1 | M |
| 29 | AI | Enforce hallucination + unsafe-prompt guards on live assistant calls | `modules/ai_sdlc/` AI governance signals | P2 | M |
| 30 | AI | Real token-spend governance integrated with provider billing | AI governance token-usage analytics | P2 | M |
| 31 | AI | LLM-assisted audit-response narrative generator (grounded in evidence) | `ecs_platform/rag.py` | P2 | M |
| 32 | AI | Vector-based semantic search replacing heuristic search | `search_module`, pgvector | P2 | M |
| 33 | OBSERV | OpenTelemetry tracing on every request | `app/main.py` | P1 | M |
| 34 | OBSERV | Structured JSON logs + log shipping | `app/ecs_logging.py` | P1 | S |
| 35 | OBSERV | Metrics (evidence backlog, approval SLA, connector lag) to Prometheus | engine layer | P1 | M |
| 36 | OBSERV | Error monitoring (Sentry) + alert routing | `app/main.py` | P2 | S |
| 37 | SCALE | Multi-worker safe state (remove module-level mutable globals) | `ecs_state.py`, `audit_trail.py` | P0 | L |
| 38 | SCALE | HA topology (≥2 app replicas, managed Postgres, Redis cluster) | `docker-compose.yml` → k8s/helm | P1 | L |
| 39 | SCALE | Documented DR runbook + backup/restore for repository + vectors | `scripts/restore/restore.sh`, `docs/operations/ecs_runbook.md` | P1 | M |
| 40 | SCALE | Load/scale test to ~900 applications portfolio | `config/roi.yaml` `applications_in_bank: 905` | P1 | M |
| 41 | PLATFORM | Multi-tenant scaffolding (`tenant_id` on every entity) | `config/integrations.yaml` tenant note | P2 | XL |
| 42 | PLATFORM | CI/CD pipeline (pytest + coverage gate + container build + pip-audit/trivy) | `tests/` (38 suites), no CI in repo | P0 | M |
| 43 | PLATFORM | Promote validation scripts to coverage-gated test suite | `scripts/validate_*.py` → `tests/` | P1 | S |
| 44 | QA | Contract tests for every connector against recorded fixtures | `demo-data/` seed scripts | P1 | M |
| 45 | QA | Accessibility (WCAG 2.1 AA) audit + fixes | `partials/`, accessibility theme template | P2 | M |
| 46 | UX | Responsive/mobile layouts (auditor "approve from phone") | `modules/shared/templates/partials/` | P2 | L |
| 47 | UX | Reduce Jinja context density via view-model assembly layer | dense templates (20+ context vars) | P2 | M |
| 48 | UX | Global command palette + saved filter views | `global_filter_engine.py`, filter clients | P3 | M |
| 49 | UX | Notification inbox with email/Teams delivery | `audit_trail` notifications ring | P2 | M |
| 50 | REPORT | Real PDF/Excel/PPT rendering for the 30 report packs | `reporting_module._REPORT_DEFS` | P1 | M |
| 51 | REPORT | One-click auditor evidence pack (files + approval trail per cycle) | `audit/package/generate`, `export` | P1 | M |
| 52 | REPORT | Scheduled report delivery + subscription | `reporting_module.py` | P2 | M |
| 53 | REPORT | Regulator read-only dashboard (anonymized app names) | persona dashboards | P2 | M |
| 54 | FRAMEWORK | Promote AI Governance to a first-class framework in the catalog | `framework_catalog.py`, `modules/ai_sdlc/` | P2 | M |
| 55 | FRAMEWORK | Continuous Controls Monitoring (scheduled `control_validation_engine` + drift) | `control_validation_engine.py`, baselining drift | P2 | L |
| 56 | FRAMEWORK | Framework version management (control changes across revisions) | `framework_onboarding_engine.py` lifecycle | P2 | M |
| 57 | FRAMEWORK | Expand crosswalk authoring UI for new framework obligations | control→framework crosswalk | P2 | M |
| 58 | GOV | Exception/CAB approval workflow persisted + SLA-tracked | `exception_state_engine.py`, exception governance | P1 | M |
| 59 | GOV | Risk register quantification (likelihood×impact scoring, heat aging) | `grc_module_demo._generate_risk_rows` | P2 | M |
| 60 | GOV | Cross-tool correlation graduating to ML anomaly clustering | `correlation_engine.py` | P3 | L |
| 61 | AISDLC | Wire AI-SDLC gates to live CI signals (block release on failed gate) | `modules/ai_sdlc/`, Jenkins/Sonar connectors | P2 | L |
| 62 | AISDLC | Controlled-documents e-signature + versioned approval | `ai_sdlc_controlled_documents.py` | P2 | M |
| 63 | AISDLC | Knowledge-reuse recommendations across releases | `ai_sdlc_knowledge_repository.py` | P3 | M |
| 64 | DATA | Evidence lineage as a queryable graph (beyond demo table) | `generate_evidence_lineage`, lineage views | P2 | M |
| 65 | GTM | Tenant onboarding kit (env templates, runbook, sizing guide) | `.env.example`, `docker-compose.yml`, `docs/` | P1 | M |
| 66 | GTM | Demo-to-pilot data migration tooling (seed → customer data) | `demo-data/seed_*` scripts | P2 | M |

> **Item count: 66** (exceeds the 50+ requirement). Every entry references a concrete module, engine, config or test that exists in the repository today.

---

## Release Grouping

### R1 — Production Foundation (P0)
Items 1–7, 10, 14, 16, 37, 42. *Outcome: ECS runs as a secured, persistent, single-tenant system of record with enforced identity and CI.*

### R2 — Enterprise Integration & Trust (P1)
Items 8–9, 11–13, 15, 17–22, 24–28, 33–35, 38–40, 43–44, 50–51, 58, 65. *Outcome: real enterprise connectors, observability, HA/DR, sufficiency in the loop, real reports.*

### R3 — Differentiation & Scale (P2/P3)
Items 23, 29–32, 36, 41, 45–49, 52–57, 59–64, 66. *Outcome: multi-tenant, CCM, ML correlation, mobile/accessibility, AI-SDLC enforcement, regulator views.*

---

## Definition of Done (applies to every P0/P1 item)
1. Backed by automated tests in `tests/` (consistent with the existing 38-suite pattern).
2. RBAC-enforced and scope-filtered per `config/rbac.yaml`.
3. No hardcoded secrets/URLs (all via `${ENV}` per existing config convention).
4. Drill-down/traceability preserved (every KPI traces to supporting records).
5. Documented in the relevant `docs/` artifact (HLD/LLD/runbook) in the same change.
