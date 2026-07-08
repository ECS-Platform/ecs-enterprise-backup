# ECS Master Integration Matrix

**Type:** Use Case → Integration → Evidence → Control → Framework → Workflow mapping. **Mode:** Documentation only. No code/UI/DB changes. No commits.
**Grounding:** `config/integrations.yaml`, `ecs_platform/connectors/*` (factory `_REGISTRY`), `modules/operations/engines/*connector*.py`, [per-connector guides](_legacy_INTEGRATIONS_index.md), [Predefined Query Architecture](../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md).
**Status:** ✅ implemented · ⚙ implemented, enable/config · 🔵 target/to-build.

> **Two integration planes:** (1) **SaaS/enterprise connectors** (`ecs_platform/connectors`) for evidence ingestion; (2) **Predefined-query connectors** (`modules/operations/engines`) for control testing. PostgreSQL/Linux/SonarQube/Trivy/Gitleaks execute today; remote DB/SSH/Windows/API are target (see [Remote Connector Expansion Plan](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md)).

---

## 1. SaaS / enterprise connectors (evidence ingestion plane)

| Use Case | Integration | Status | Evidence Generated | Control | Framework | Workflow | Auth |
|---|---|---|---|---|---|---|---|
| UC-I01 | **Jira** | ⚙ | issues, sprints, traceability | change/delivery controls | ITPP, AppSec | Evidence collection | PAT/OAuth2 |
| UC-I02 | **Confluence** | ⚙ | policy/standard pages | policy controls | ITPP, ISG | Evidence collection | PAT/OAuth2 |
| UC-I03 | **ServiceNow** | ⚙ | change/CAB records | change mgmt controls | ITPP, ITDRM | Evidence collection | OAuth2/Basic |
| UC-I04 | **Prisma Cloud** | ⚙ | cloud posture findings | cloud controls | Cloud Security | Evidence + risk | API key |
| UC-I05 | **SharePoint** | ⚙ | document artifacts | document controls | multiple | Evidence collection | Azure AD (Graph) |
| UC-I06 | **Microsoft Teams** | ⚙ | approvals/messages | approval trail | governance | Approval | Azure AD (Graph) |
| UC-I07 | **Azure DevOps** | ⚙ | PRs, pipelines, work items | SDLC controls | AppSec | Evidence collection | PAT |
| UC-I08 | **GitHub** | ⚙ | PRs, branches, protections | SCM controls | AppSec | Evidence collection | PAT/App |
| UC-I09 | **Jenkins** | ⚙ | builds, test results | CI/CD controls | AppSec | Evidence collection | token |
| UC-I11 | **Gitea** | ⚙ | repos, PRs | SCM controls | AppSec | Evidence collection | token |
| UC-I12 | **Figma** | ⚙ | design files | design controls | AppSec/UX | Evidence collection | token |
| UC-I13 | **Outlook** | ⚙ | mail folders/messages | approval/comms trail | governance | Evidence collection | Azure AD (Graph) |
| UC-I14 | **Checkmarx** | ⚙ | SAST scans | AppSec controls | Application Security | Evidence + risk | OAuth2 |
| UC-I15 | **Tripwire** | ⚙ | FIM policy results | integrity controls | Security | Evidence collection | Basic |
| UC-I16 | **AWS** (posture) | ⚙ | Security Hub findings, Config compliance | cloud controls | Cloud Security | Evidence + risk | access/secret key (+ collector) |
| UC-I17 | **Azure** (posture) | ⚙ | Defender security assessments | cloud controls | Cloud Security | Evidence + risk | OAuth2 / token |
| UC-I18 | **GCP** (posture) | ⚙ | SCC findings, asset inventory | cloud controls | Cloud Security | Evidence + risk | SA JSON / token (+ collector) |
| UC-I19 | **Nessus** (Tenable) | ⚙ | scans, vulnerabilities | vuln controls | VAPT | Evidence + risk | access/secret key |
| UC-I20 | **Qualys** | ⚙ | host detections, posture | vuln controls | VAPT | Evidence + risk | Basic |
| UC-I21 | **RSA Archer** | ⚙ | controls/frameworks | GRC controls | governance | Evidence collection | API token |

*Defaults (this plane): `enabled:false` in `config/integrations.yaml`; Scheduling = Scheduler; Frequency = daily [default]; Failure = retry + connector-health flag + structured error; Security = least-privilege API user, TLS, secrets via `*_env`/vault; UAT = sandbox tenant; PROD = prod tenant + vault creds.*

> **Adapter stack note:** UC-I01–I09 and I13–I21 are implemented as
> audit-intelligence adapters in `modules/operations/integrations/` (registry +
> Connector Test Workbench + scheduler + executor). UC-I07/I08/I09 (Azure DevOps,
> GitHub, Jenkins) are **thin wrappers that reuse the `ecs_platform/connectors/`
> clients** via `_platform_bridge.py` (no HTTP/auth duplication). UC-I11/I12
> (Gitea, Figma) currently exist in the `ecs_platform/connectors/` ingestion stack
> only. See [INTEGRATION_ADAPTERS_GUIDE.md](INTEGRATION_ADAPTERS_GUIDE.md) §1.

## 2. Predefined-query connectors (control testing plane)

| Use Case | Integration | Status | Evidence Generated | Control | Framework | Workflow | Mechanism |
|---|---|---|---|---|---|---|---|
| UC-BL03 | **PostgreSQL** | ✅ | DB config pass/fail | DB baseline controls | Database Baselining | Predefined query | psycopg2 + read-only allow-list |
| UC-BL01 | **Linux** | ✅ (demo) | OS config pass/fail | OS baseline controls | OS Baselining | Predefined query | docker exec / SSH 🔵 |
| UC-BL11 | **SonarQube** | ✅ | quality gate, issues | AppSec controls | Application Security | Predefined query | API |
| UC-BL09 | **Trivy** | ✅ | CVE findings | vuln controls | VAPT, AppSec | Predefined query | subprocess |
| UC-BL10 | **Gitleaks** | ✅ | secret findings | secret controls | AppSec | Predefined query | subprocess |
| UC-BL06 | **Nginx** | 🟡 | config check | middleware controls | Nginx Baselining | Predefined query | via Linux/SSH |
| UC-BL02 | **Windows** | 🔵 | OS config pass/fail | OS baseline controls | OS Baselining | Predefined query | WinRM (to build) |
| UC-BL07 | **Oracle** | 🔵 | DB config pass/fail | DB baseline controls | Database Baselining | Predefined query | oracledb (to build) |
| UC-BL04 | **Aurora MySQL** | 🔵 | DB config pass/fail | DB baseline controls | Database Baselining | Predefined query | PyMySQL (to build) |
| UC-BL08 | **SQL Server** | 🔵 | DB config pass/fail | DB baseline controls | Database Baselining | Predefined query | pyodbc (to build) |
| UC-BL05 | **Yugabyte** | 🟡 | DB config pass/fail | DB baseline controls | Database Baselining | Predefined query | PG-wire (validate) |

*Defaults (this plane): config via `config/environments/<env>.yaml` (`predefined_query_targets`); credentials via `ECS_*` env / vault; read-only allow-list + statement timeouts; Failure = structured (timeout/auth/connection); UAT = demo containers or UAT hosts; PROD = real targets + remote connectors.*

## 3. End-to-end flow (canonical)

```
Use Case → Integration (connector) → Data retrieved → Evidence generated
   → mapped to Control (evidence_control_map) → rolled to Framework (evidence_framework_map)
   → Workflow (collection / approval / predefined-query) → Repository → Dashboard/KPIs
```

## 4. Integration → Framework coverage summary
| Framework | Primary integrations |
|---|---|
| OS Baselining | Linux, Windows🔵 |
| Database Baselining | PostgreSQL, Oracle🔵, MySQL🔵, SQL Server🔵, Yugabyte🟡 |
| Nginx/Middleware Baselining | Linux/Nginx🟡 |
| Application Security | SonarQube, Trivy, Gitleaks, GitHub, Azure DevOps, Jenkins, Gitea |
| VAPT | Trivy, Prisma Cloud, Nessus, Qualys |
| Cloud Security | Prisma Cloud, AWS, Azure, GCP |
| ITPP / ITDRM | Jira, Confluence, ServiceNow |
| Governance | Teams, SharePoint |

## Cross-references
- [Integrations index](_legacy_INTEGRATIONS_index.md) · [Master Use Case Registry](../product/ECS_MASTER_USE_CASE_REGISTRY.md) · [Master Use Case & LLM Reference](../ai-sdlc/ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) · [Predefined Query Architecture](../operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md) · [Connector Activation Plan](../use-cases/ECS_CONNECTOR_ACTIVATION_PLAN.md) · [Remote Connector Expansion](../production/ECS_REMOTE_CONNECTOR_EXPANSION_PLAN.md)
