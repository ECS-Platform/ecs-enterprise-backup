# ECS Production Readiness Master Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code/UI/CSS/HTML changes. No commits/pushes.** **Inputs reviewed:** `ECS_PHASE1_GO_LIVE_READINESS_REPORT.md`, `ECS_P1_ENGINEERING_GAP_ANALYSIS.md`, `ECS_CONNECTOR_ACTIVATION_PLAN.md`, `ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md`, `ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md`, `ECS_RAF_IMPLEMENTATION_PLAN.md`. **Grounding:** `config/auth.yaml`, `app/auth/*`, `config/environments/_base.yaml`, `app/observations/store.py`, `modules/operations/engines/*connector*.py`.

> ### ⚠ Corrections carried forward (verified by source inspection)
> - **Authentication is largely built, secure-by-default.** `config/auth.yaml` + `app/auth/` (14 modules: `providers.py`, `jwt_validator.py`, `middleware.py`, `roles.py`, `authz.py` PolicyEngine over `config/rbac.yaml`, `enforcement.py`) implement Azure AD / OIDC / dev providers, JWT/JWKS validation, claims mapping, and RBAC enforcement. `ECS_AUTH_ENABLED` defaults **true**. Production SSO is mostly **configuration + IdP-claim→role mapping + validation**, not a build.
> - **Predefined-query execution works for demo targets** (PostgreSQL/Linux/SonarQube/Trivy/Gitleaks). Only generic remote `DatabaseConnector`/`SSHConnector`/`APIConnector` are `NotImplementedError`.
> - **Observation durability is implemented**, flag-gated by `OBSERVATIONS_DURABLE_ENABLED` (default off).

---

## 1. Production readiness — current vs target state

| Domain | Current state | Target state |
|---|---|---|
| **Authentication / SSO** | Auth+JWT+RBAC framework built; `azure_ad`/`oidc` providers present but unconfigured (tenant/client/issuer blank); `ECS_SSO_ENABLED:-false` SSO slot | Azure AD/Entra configured + enabled; IdP claims → ECS roles; token validation, session, logout verified |
| **Encryption at rest** | `MINIO_SECURE:-false`; Postgres/object-store encryption infra-dependent, not verified | DB + object store + backups encrypted; KMS-managed keys + rotation; evidenced for audit |
| **Observation durability** | Write-through store present, flag OFF | Flag ON in UAT→PROD; data migrated; restart hydration validated |
| **Predefined queries (demo targets)** | Live execution implemented | Validated per env; targets populated |
| **Predefined queries (remote targets)** | `DatabaseConnector`/`SSHConnector`/`APIConnector` stubs | Oracle/MySQL/SQL Server/Windows/SSH/API connectors built + validated |
| **Source connectors** | Runtime-complete, `enabled:false`, unvalidated | Enabled + validated per tenant |
| **RAF / risk acceptance** | Handled via exception/TD workflow; no first-class RAF | (P2) First-class RAF + ISG approval, time-boxed |
| **Demo / UAT** | GO | Maintained |

## 2. Production gaps (consolidated)

| Gap | Priority | Plan |
|---|---|---|
| SSO/OIDC configuration + role mapping | P1 | [SSO/OIDC Plan](../production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md) |
| Encryption at rest (DB/object/backups) + KMS | P1 | [Encryption Plan](../production/ECS_ENCRYPTION_AT_REST_PLAN.md) |
| Observation durability enablement | P1 | [Durability Plan](../production/ECS_OBSERVATION_DURABILITY_ENABLEMENT_PLAN.md) |
| Remote query connectors | P1/P2 | [Remote Connector Plan](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md) |
| Source connector enable + validation | P1 | [Connector Activation Plan](../use-cases/ECS_CONNECTOR_ACTIVATION_PLAN.md) |
| Per-env target lists | P1 | [Predefined Query Plan](../use-cases/ECS_PREDEFINED_QUERY_IMPLEMENTATION_PLAN.md) |
| RAF first-class entity | P2 | [RAF Plan](../use-cases/ECS_RAF_IMPLEMENTATION_PLAN.md) |

## 3. Dependencies
- **External infra:** enterprise IdP (Azure AD/Entra) metadata + app registration; KMS/HSM; vault for secrets; encrypted storage volumes; network egress to target systems.
- **Internal sequencing:** target lists (config) precede remote execution; ISG role precedes clean RAF routing; durability flag needs reachable Postgres (present).

## 4. Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IdP/KMS gated on infra teams | Med | High | Raise infra tickets in week 1 |
| Remote DB/SSH dialect & firewall variance | Med | Med | Phase by dialect; read-only allow-lists |
| Tenant credentials delayed | Med | Med | Validate against sandbox tenants first |
| Misconfigured role mapping → over/under-privilege | Med | High | Map to 9 canonical roles; test matrix per role |
| Scope creep (RAF into Phase 1) | Med | Med | Keep RAF P2 unless mandated |

## 5. Owners (RACI — role placeholders)
| Workstream | Accountable | Responsible | Consulted |
|---|---|---|---|
| SSO/OIDC | Platform Lead | Backend Eng + IdP/Infra | Security, IAM team |
| Encryption at rest | Security Lead | Infra/DevOps | DBA, Compliance |
| Observation durability | Backend Lead | Backend Eng | QA |
| Remote connectors | Backend Lead | Backend Eng | DBA, Network |
| Source connectors | Integration Lead | Backend Eng | Tenant owners |
| RAF (P2) | Governance Lead | Backend Eng | ISG, CIO |

## Cross-references
- [Final Production Roadmap](../production/ECS_FINAL_PRODUCTION_ROADMAP.md) · [Phase 1 Execution Roadmap](../use-cases/ECS_PHASE1_EXECUTION_ROADMAP.md) · [Go-Live Readiness](../archive/ECS_PHASE1_GO_LIVE_READINESS_REPORT.md)
