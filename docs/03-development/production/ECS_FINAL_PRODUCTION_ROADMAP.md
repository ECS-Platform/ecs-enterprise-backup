# ECS Final Production Roadmap

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Synthesizes:** all PRODUCTION + PHASE1 plans and the go-live readiness report.

> **Baseline:** Demo/UAT readiness is **GO today**. This roadmap closes **production** gates: enterprise auth, encryption-at-rest, durable observations, validated connectors, and remote evidence collection.

---

## 1. Prioritized backlog

### P1 — Production go-live gates
| ID | Item | Effort | Plan |
|---|---|---:|---|
| P1-A | SSO/OIDC config + role mapping (Azure AD/Entra) | 3–6d | [SSO Plan](../production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md) |
| P1-B | Encryption at rest (DB/object/backups) + KMS | 4–6d | [Encryption Plan](../production/ECS_ENCRYPTION_AT_REST_PLAN.md) |
| P1-C | Observation durability enablement + migration | 3d | [Durability Plan](../production/ECS_OBSERVATION_DURABILITY_ENABLEMENT_PLAN.md) |
| P1-D | Source connector enable + per-tenant validation | 3–5d | [Activation Plan](../../01-product/use-cases/ECS_CONNECTOR_ACTIVATION_PLAN.md) |
| P1-E | Populate per-env target lists | 1–2d | [Predefined Query Plan](../../01-product/use-cases/ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md) |
| P1-F | Demo-target query validation (PG/Linux/Sonar/Trivy/Gitleaks) | 3–5d | [Activation Plan](../../01-product/use-cases/ECS_CONNECTOR_ACTIVATION_PLAN.md) |

### P2 — Hardening / completeness
| ID | Item | Effort | Plan |
|---|---|---:|---|
| P2-A | Remote DB connectors (Oracle/MySQL/SQL Server) | 5–7d | [Remote Connector Plan](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md) |
| P2-B | Generic SSH + Windows (WinRM) | 6–7d | [Remote Connector Plan](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md) |
| P2-C | RAF first-class entity + ISG approval | ~14d | [RAF Plan](../../01-product/use-cases/ECS_RAF_IMPLEMENTATION_PLAN.md) |
| P2-D | Automated RAG reindex scheduler | 2–3d | — |
| P2-E | Dedicated RBAC roles (Audit Mgr/Governance/Risk/ISG approver) | 2–3d | — |
| P2-F | Middleware baseline control catalog | 3–5d | — |

### P3 — Optional / future
| ID | Item | Effort |
|---|---|---:|
| P3-A | Generic API connector | 2d |
| P3-B | Tech signatures + parsers (MySQL/SQLServer/Tomcat/App) | 3–4d |
| P3-C | Cloud LLM providers default-active option | 2d |
| P3-D | Extended SaaS connectors live (Prisma/Azure DevOps) | 3–5d |
| P3-E | Document 38 undocumented action endpoints | 2–3d |

## 2. Time-boxed roadmaps

### 2-Week — UAT-credible + lowest-risk prod gates
- P1-C (durability), P1-E (target lists), P1-F (demo-target validation), P1-D start (Jira/Confluence/ServiceNow enable+validate).
- **Exit:** durable observations; demo-target evidence validated; first source connectors live in UAT.

### 4-Week — Core production gates cleared
- Adds: **P1-A** (SSO/OIDC), **P1-B** (encryption at rest), P1-D finish (SharePoint/Teams Graph).
- **Exit:** enterprise auth + at-rest encryption verified → **hard production gates cleared**; production go-live feasible for demo-class + validated SaaS evidence.

### 8-Week — Remote evidence collection
- Adds: **P2-A** (Oracle/MySQL/SQL Server), **P2-D** (reindex scheduler), **P2-E** (RBAC roles), P3-B (tech signatures/parsers).
- **Exit:** automated evidence from remote DB targets; AI freshness automated; governance roles formalized.

### 12-Week — Full Phase-1 closure + hardening
- Adds: **P2-B** (SSH + Windows/WinRM), **P2-C** (RAF + ISG), **P2-F** (middleware catalog), P3-A/C/D/E.
- **Exit:** full target-class coverage (DB/OS/Win/API), formal time-boxed RAF governance, complete docs/hardening.

## 3. Resources
| Role | 2-wk | 4-wk | 8-wk | 12-wk |
|---|---|---|---|---|
| Backend engineer (Python/FastAPI) | 1 | 2 | 2 | 2–3 |
| DevOps/Infra (IdP, KMS, vault, containers) | 0.5 | 1 | 1 | 1 |
| Security engineer (auth, encryption, KMS) | 0.25 | 1 | 0.5 | 0.5 |
| QA/UAT engineer | 0.5 | 1 | 1 | 1 |
| GRC SME (controls/RAF/ISG) | 0.25 | 0.5 | 0.5 | 1 |
| DBA / Network (remote targets) | — | 0.25 | 1 | 1 |

## 4. Skills required
Python/FastAPI; OIDC/SAML + Azure AD/Entra; JWT/JWKS; KMS/HSM + envelope encryption; PostgreSQL/MinIO/S3 ops; DB drivers (`oracledb`/`PyMySQL`/`pyodbc`); SSH (`paramiko`) + WinRM (`pywinrm`); Docker/Compose; vault/secrets; GRC domain (PCI/RBI/ISG/DPSC).

## 5. Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IdP/KMS dependent on infra teams | Med | High | Raise infra requests week 1; track as critical path |
| Key-management misconfiguration | Low | High | KMS managed durability, documented custody, tested restore |
| Role-mapping over/under-privilege | Med | High | Per-role access test matrix; default least-privilege |
| Remote target dialect/firewall variance | Med | Med | Phase by dialect; read-only allow-lists; pilot one host |
| Scope creep (RAF/remote pulled early) | Med | Med | Hold P2 unless compliance-mandated |
| Tenant credential delays | Med | Med | Sandbox-tenant validation first |

## 6. Success criteria
| Gate | Criteria |
|---|---|
| Authentication | Azure AD/Entra login enforced; tokens validated (pos/neg tests); IdP roles → ECS roles correct per access matrix; federated logout works |
| Encryption | DB volume/TDE + object-store SSE-KMS + encrypted backups verified; restore from encrypted backup succeeds; KMS rotation policy documented |
| Observations | Flag ON; migration `errors=0`; restart hydration matches; `observation.*` audit chain intact |
| Connectors (demo) | All 5 execute live; pos/neg validation; KPIs update; structured errors (no 500) |
| Connectors (SaaS) | Enabled + validated per tenant; evidence ingested |
| Connectors (remote) | Target DB/OS evidence collected with read-only accounts; allow-list enforced |
| Targets | Per-env lists populated; reachable |
| Docs/audit | Each gate has evidence captured for audit sign-off |

## 7. Recommendation
Run **2-week** now (high value, low risk), commit to **4-week** to clear the two hard production gates (SSO + encryption) → **production go-live feasible at week 4** for demo-class + validated SaaS evidence. **8/12-week** tracks extend to remote/automated evidence collection and formal RAF governance.

## Cross-references
- [Production Master Plan](../production/ECS_PRODUCTION_READINESS_MASTER_PLAN.md) · [SSO/OIDC](../production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md) · [Encryption](../production/ECS_ENCRYPTION_AT_REST_PLAN.md) · [Durability](../production/ECS_OBSERVATION_DURABILITY_ENABLEMENT_PLAN.md) · [Remote Connectors](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md)
- [Phase 1 Execution Roadmap](../../01-product/use-cases/ECS_PHASE1_EXECUTION_ROADMAP.md) · [Go-Live Readiness](../../05-archive/archive/ECS_PHASE1_GO_LIVE_READINESS_REPORT.md)
