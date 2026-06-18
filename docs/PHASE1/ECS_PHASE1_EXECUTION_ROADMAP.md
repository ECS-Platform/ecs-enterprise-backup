# ECS Phase 1 Execution Roadmap

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Inputs:** the four companion PHASE1 plans + the validation/readiness reports. **Goal:** sequence P1/P2/P3 work into 2/4/8-week roadmaps with resources, skills, dependencies, risks.

---

## 1. Prioritized backlog

### P1 — Production go-live gates
| ID | Item | Effort | Type |
|---|---|---:|---|
| P1-01 | Remote-target query connectors (DB/SSH/API) | 8–13d | Build |
| P1-02 | Source connector enable + per-tenant validation | 3–5d | Config/Validate |
| P1-03 | Populate per-env target lists | 1–2d | Config |
| P1-04 | SSO/OIDC + at-rest encryption (+infra) | 3–6d | Build/Verify |
| P1-05 | Observation durability enablement + migration | 2–4d | Enable/Validate |

### P2 — Hardening / completeness
| ID | Item | Effort |
|---|---|---:|
| P2-01 | RAF first-class entity + ISG approval | ~14d |
| P2-02 | Automated RAG reindex scheduler | 2–3d |
| P2-03 | Dedicated RBAC roles (Audit Manager, Governance, Risk, ISG approver) | 2–3d |
| P2-04 | Middleware baseline control catalog | 3–5d |
| P2-05 | Document/standardize 38 undocumented action endpoints | 2–3d |
| P2-06 | ROI rate-basis reconciliation (`config/roi.yaml`) | 1d |

### P3 — Optional / future
| ID | Item | Effort |
|---|---|---:|
| P3-01 | Cloud LLM providers default-active option | 2d |
| P3-02 | MySQL/SQL Server/Tomcat/Application tech signatures + parsers | 3–4d |
| P3-03 | Extended connector coverage (Prisma/Azure DevOps live) | 3–5d |

## 2. 2-week roadmap (fastest UAT-credible path)
**Focus:** config-driven gates + low-risk enablement; demo/UAT fully live.
- Wk1: P1-03 (target lists), P1-05 (observation durability enable + migrate + validate), P1-02 start (enable + validate Jira/Confluence/ServiceNow).
- Wk2: P1-02 finish (SharePoint/Teams Graph), connector activation validation (PG/Linux/Sonar/Trivy/Gitleaks per [Activation Plan](ECS_CONNECTOR_ACTIVATION_PLAN.md)), P2-06 (ROI reconcile).
- **Exit:** UAT GO for demo-target evidence + validated source connectors; observations durable.

## 3. 4-week roadmap (production-credible core)
- Adds to 2-week: **P1-04** (SSO/OIDC wiring + at-rest encryption verification with infra), **P1-01 partial** (DatabaseConnector for the single highest-priority prod DB dialect + SSHConnector), P2-05 (endpoint docs).
- **Exit:** production auth/encryption gate cleared; remote evidence for priority DB/OS targets.

## 4. 8-week roadmap (full Phase-1 + hardening)
- Adds: **P1-01 complete** (all dialects + APIConnector + parsers + tests), **P2-01 RAF**, P2-02 reindex scheduler, P2-03 RBAC roles, P2-04 middleware catalog, P3 items as capacity allows.
- **Exit:** full automated evidence collection across target classes; RAF/ISG governance live; hardening complete.

## 5. Resource requirements
| Role | 2-wk | 4-wk | 8-wk |
|---|---|---|---|
| Backend engineer (Python/FastAPI) | 1 | 2 | 2 |
| DevOps/Infra (IdP, KMS, vault, containers) | 0.5 | 1 | 1 |
| QA/UAT engineer | 0.5 | 1 | 1 |
| GRC SME (controls/frameworks/RAF) | 0.25 | 0.5 | 0.5 |

## 6. Skills required
- Python/FastAPI, psycopg2 + DB drivers (`oracledb`/`PyMySQL`/`pyodbc`), `paramiko` (SSH), OIDC/SAML integration, Docker/Compose, PostgreSQL ops, MinIO/object-store encryption, vault/secrets, GRC domain (PCI/RBI/ISG).

## 7. Dependencies
- P1-03 → P1-01 (targets must exist to execute remotely).
- P1-04 → enterprise IdP metadata + KMS/disk encryption from infra.
- P1-02 → tenant credentials + Azure AD app registration (Graph).
- P2-01 (RAF) → P2-03 (ISG approver role) for clean routing.
- P1-05 → reachable Postgres repository (already present).

## 8. Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IdP/encryption depends on external infra teams | Med | High | Start P1-04 infra requests in Wk1 |
| Remote DB/SSH dialect/firewall variance | Med | Med | Phase by dialect; read-only allow-lists; test targets |
| Tenant credentials delayed | Med | Med | Validate connectors against sandbox tenants first |
| Scope creep (RAF/P2 pulled into Phase 1) | Med | Med | Keep RAF as P2 unless compliance-mandated |
| In-memory-wins hydration edge cases | Low | Low | Documented; flag-gated rollout in UAT first |

## 9. Recommendation
Execute the **2-week roadmap immediately** (high value, low risk, mostly config/enablement) to reach a credible UAT GO, then commit to the **4-week** track to clear the hard production gate (P1-04). Treat the **8-week** track as full Phase-1 closure including RAF and hardening. **Demo/UAT readiness is GO today; these tracks close production live-evidence and compliance gates.**

## Cross-references
- [Engineering Gap Analysis](ECS_P1_ENGINEERING_GAP_ANALYSIS.md) · [Predefined Query Plan](ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md) · [Observation Plan](ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md) · [RAF Plan](ECS_RAF_IMPLEMENTATION_PLAN.md) · [Connector Activation Plan](ECS_CONNECTOR_ACTIVATION_PLAN.md)
- Source: [Go-Live Readiness](../executive/ECS_PHASE1_GO_LIVE_READINESS_REPORT.md)
