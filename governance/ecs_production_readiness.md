# ECS — Production Readiness Assessment

**Lens:** Principal Enterprise Architect + CIO Advisory
**Purpose:** An honest, evidence-based gate review of ECS for regulated-bank production use. Status is assigned strictly from what exists in `app/`, `modules/`, `ecs_platform/`, `config/`, `tests/`, `docker-compose.yml` and `docs/`.
**Verdict legend:** ✅ Ready · 🟡 Partial / needs configuration or hardening · ❌ Gap (must be built/enabled before regulated prod)

---

## 1. Overall Position

ECS is **production-architected but not yet production-deployed for regulated workloads.** The foundations for every production concern exist in code or config; the remaining work is enabling, converging, hardening and reviewing — not inventing. ECS should proceed to a **controlled R1 pilot** (single-tenant, 25 applications, live CI/CD connectors) while the P0 gate items below are closed.

**Production-readiness score: 3.0 / 5 (single-tenant pilot-ready; full regulated-prod requires R1 gate closure).**

---

## 2. Readiness Matrix

### 2.1 Architecture & Code
| Area | Status | Evidence |
|---|:--:|---|
| Modular decomposition | ✅ | Six domain modules + shared core + `ecs_platform/` infra |
| Containerization | ✅ | `Dockerfile` (python:3.12-slim, uvicorn) |
| Local full-stack compose | ✅ | `docker-compose.yml`: app, postgres ×3 roles, pgvector, redis, minio, gitea, jenkins, sonarqube |
| Multi-worker safety | ❌ | Module-level mutable state (`ecs_state.py`, `audit_trail.py`) not concurrency-safe; blocks `--workers > 1` |
| Config externalization | ✅ | All sensitive values via `${ENV}`; no hardcoded URLs/credentials in `config/*.yaml` |
| `app/*` → `modules/*` shims | 🟡 | Intentional migration shims; should be retired |

### 2.2 Identity & Access
| Area | Status | Evidence |
|---|:--:|---|
| RBAC policy model | ✅ | `config/rbac.yaml` canonical verb.resource catalog, 9 roles, scope filters, page guards |
| RBAC enforcement (phased) | 🟡 | Tested (`test_rbac_enforcement_phase2_step2b/c/d`, `_scope_filtering_phase2_step3`, `test_authz_phase2`, `test_rbac_delegation_parity`); not enforced on all legacy showcase routes |
| Authentication middleware | 🟡 | JWT/OIDC `AuthenticationMiddleware` exists (`app/auth/`) but pass-through when disabled |
| SSO / IdP integration | ❌ | Role-chooser login in showcase; real IdP not wired by default |
| MFA / session lifecycle | ❌ | Not implemented |
| URL-param role/user (showcase) | ❌ | Role/user carried in query params on `/mvp/*` legacy paths — must be removed |

### 2.3 Data & Persistence
| Area | Status | Evidence |
|---|:--:|---|
| Connector evidence repository | ✅ | `ecs_platform/repository` → PostgreSQL (`ecs_repository`) |
| Vector store | ✅ | pgvector (`config/vectorstore.yaml`, 768-dim) |
| Object store (evidence blobs) | ✅ | MinIO service (`minio` in compose) |
| Cache / queue substrate | ✅ | Redis service present |
| Showcase state persistence | ❌ | In-memory; resets on restart (reseeded deterministically) |
| Single system-of-record convergence | ❌ | Dual data planes must converge (backlog #1–4) |
| Audit-trail durability | 🟡 | Durability work tested (`test_audit_durability_phase4`); retention policy ≥1yr to confirm |
| Backup / restore | 🟡 | `scripts/restore/restore.sh` exists; DR runbook for prod to be finalized |

### 2.4 Integrations
| Area | Status | Evidence |
|---|:--:|---|
| Connector framework | ✅ | `ecs_platform/connectors/factory.py` + 12 connectors + http client + MS Graph helper |
| Live connectors (dev) | ✅ | Gitea, Jenkins, SonarQube — real connectivity, seed scripts in `demo-data/` |
| SaaS connectors | 🟡 | Jira, GitHub, Confluence, Figma, ServiceNow, Teams, SharePoint, Prisma, Azure DevOps — interface-complete, disabled until tenant onboarding |
| Connector resilience | 🟡 | Fast-fail defaults (timeout/retries) in `config/integrations.yaml`; circuit-breaker/backoff to add |
| Connector health monitoring | ✅ | `integration_health_engine.py`, `test_connectivity_assessment_phase5_3.py` |

### 2.5 AI / RAG
| Area | Status | Evidence |
|---|:--:|---|
| Grounded RAG | ✅ | `ecs_platform/rag.py`; `require_citations: true`, `refuse_without_evidence: true` |
| Provider portability | ✅ | Ollama (default, local/air-gap) / Gemini / OpenAI / Azure / Claude via `config/llm.yaml` |
| Evidence sufficiency scoring | 🟡 | Deterministic 5-dimension engine (`config/sufficiency.yaml`), flag-gated; wire into reviewer loop |
| AI governance posture | ✅ | Prompt audit, hallucination/unsafe-prompt signals, token usage (`modules/ai_sdlc/`) |
| Live guard enforcement | ❌ | Hallucination/unsafe-prompt guards not yet enforced on live calls |
| RAG quality eval harness | ❌ | Faithfulness/citation-precision harness to build |

### 2.6 Security
| Area | Status | Evidence |
|---|:--:|---|
| No hardcoded secrets | ✅ | `${ENV}` resolution across all configs |
| Cache-control on HTML | ✅ | `_no_cache_html` middleware |
| CSRF protection | ❌ | Not present on POST routes |
| Signed download URLs | ❌ | Export/report downloads not signed/expiring |
| CSP / security headers | ❌ | Not configured |
| Encryption at rest (blobs) | 🟡 | MinIO present; SSE/KMS to enable |
| Secret vault | ❌ | Env-based; vault integration to add |
| Formal security review / pen test | ❌ | Not on record — mandatory before regulated prod |

### 2.7 Reliability & Operations
| Area | Status | Evidence |
|---|:--:|---|
| Health checks | ✅ | Compose healthchecks (postgres/pgvector/minio) |
| Startup self-heal & validation | ✅ | `ecs_lifespan`: refresh repo, seed, self-heal governance, validate startup, warm RAG |
| HA topology | ❌ | Single app process; no documented replica/k8s topology |
| DR runbook (prod) | 🟡 | `docs/operations/ecs_runbook.md` + restore script; prod DR plan to finalize |
| Observability (APM/metrics/tracing) | ❌ | Structured logging exists (`ecs_logging.py`); no OTel/Prometheus/Sentry wired |
| Load/scale validation | ❌ | Not validated to ~900-app portfolio |

### 2.8 Quality & Delivery
| Area | Status | Evidence |
|---|:--:|---|
| Automated tests | ✅ | 38 pytest suites (RBAC, durability, evidence intel/analytics/sufficiency, ROI, AI-SDLC, certification, drilldowns, trends) |
| Platform certification test | ✅ | `test_platform_certification.py`, `test_ecs_demo_readiness.py` |
| CI/CD pipeline | ❌ | No pipeline definition in repo (tests run manually) |
| Coverage gate | ❌ | Not formalized |
| Supply-chain scanning | ❌ | `pip-audit`/`trivy` not wired |

---

## 3. Production Gate (must-pass before regulated prod)

**P0 — Blocking**
1. Enable OIDC/SSO; enforce RBAC on every route; remove URL-param role/user.
2. Converge to a single Postgres system of record; persist workflow/audit/observations.
3. Make state multi-worker safe.
4. CSRF + security headers + signed downloads + encryption at rest + secret vault.
5. Formal security review + penetration test, remediated.
6. CI/CD with coverage gate and supply-chain scanning.

**P1 — Required for enterprise operation**
7. HA topology + DR runbook + backup/restore validation + portfolio-scale load test.
8. Observability stack (OTel tracing, metrics, error monitoring).
9. Onboard the customer's top enterprise connectors (e.g. ServiceNow/Jira/SharePoint).
10. Wire sufficiency scoring into the reviewer loop; RAG eval harness.

---

## 4. Recommended Path

1. **Now → R1 (single-tenant pilot):** Close P0 items 1–4 and 6; run 25-application pilot on live Gitea/Jenkins/SonarQube. Acceptable risk posture: internal/controlled, not yet public regulated traffic.
2. **R1 → R2 (enterprise operation):** Close P0 #5 (security review) and all P1 items; expand connectors; HA/DR/observability.
3. **R2 → R3 (scale):** Multi-tenancy, CCM, release-blocking AI-SDLC gates (see `strategy/ecs_3_year_strategy.md`).

---

## 5. Statement of Honesty

ECS is materially more production-ready than a typical demo: it has a real connector layer, a real evidence repository with vector search, grounded AI, enforced-and-tested RBAC scaffolding, durable-audit work, and 38 automated test suites. It is materially less than "deploy to a regulated bank tomorrow": identity, persistence convergence, security review, HA/DR and observability remain. This document is the authoritative gate; the closing work is enumerated and sized in `product/ecs_enterprise_backlog.md`.
