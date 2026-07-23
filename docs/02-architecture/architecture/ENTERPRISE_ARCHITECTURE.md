# ECS Enterprise Architecture (Bank Deployment)

End-to-end enterprise architecture for deploying ECS inside a bank: GCP hosting
model, cross-cloud application connectivity (AWS/GCP), the jump-server model for
internal targets, security zones, and the evidence/audit data flows.

> **Scope & status.** This document is the **bank-deployment topology** view. It
> complements — and does not duplicate — the existing architecture docs:
> - Current-state, code-grounded design: [`ecs_enterprise_architecture_review.md`](ecs_enterprise_architecture_review.md)
> - Container / runtime / generic K8s-HA-DR: [`ecs_deployment_architecture.md`](ecs_deployment_architecture.md)
> - HLD (Mermaid, non-C4): [`ecs_hld.md`](ecs_hld.md) · LLD: [`ecs_lld.md`](ecs_lld.md)
> - GCP provisioning detail: [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../../03-development/deployment/GCP_DEPLOYMENT_GUIDE.md)
> - C4 model: [`HIGH_LEVEL_DESIGN.md`](HIGH_LEVEL_DESIGN.md)
>
> Items marked **[TARGET]** are recommended target-state (bank-specific) and are
> not all present in the repo today; the platform's config framework
> (`ECS_ENV`, `config/environments/*`) makes them configuration, not code, changes.

---

## 1. Enterprise context

ECS is the Enterprise Evidence Collection System: it collects compliance evidence
from bank systems (databases, hosts, SaaS/DevSecOps tools, cloud posture),
validates and versions it, maps it to controls/frameworks, and serves audit
intelligence (dashboards, RAG Q&A, prompt workbench).

```mermaid
flowchart TD
  subgraph Users["Bank users"]
    OWN["Application Owners"]
    AUD["Auditors"]
    CISO["CISO / CIO / Leadership"]
    ADM["Platform Admins"]
  end
  subgraph ECS["ECS Platform (hosted on GCP)"]
    UI["Web UI + REST API"]
    ENG["Evidence / Audit / Connector / Scheduler / LLM engines"]
    REPO[("Evidence Repository")]
    VEC[("Vector store (pgvector)")]
  end
  subgraph Targets["Evidence sources"]
    DBs["Databases (PostgreSQL/Oracle/MySQL/SQL Server)"]
    Hosts["Linux/Windows hosts"]
    SaaS["Jira/Confluence/ServiceNow/SharePoint/Teams"]
    SEC["SonarQube/Checkmarx/Prisma/Nessus/Qualys/Tripwire"]
    CICD["GitHub/Jenkins/Azure DevOps"]
    CLOUD["AWS / Azure / GCP posture"]
  end
  Users --> UI --> ENG
  ENG --> REPO & VEC
  ENG -. collectors .-> DBs & Hosts & SaaS & SEC & CICD & CLOUD
```

See [`00-start-here/ARCHITECTURE_OVERVIEW.md`](../../01-product/00-start-here/ARCHITECTURE_OVERVIEW.md)
for the code-grounded module tour.

---

## 2. GCP hosting model **[TARGET]**

ECS is hosted on Google Cloud. The web tier is stateless (once `ecs_state` is
externalized — see the architecture review) and runs on GKE behind a managed
load balancer; state lives in managed data services.

```mermaid
flowchart TD
  subgraph Internet["Bank corporate network / VPN"]
    U["Users (browser, SSO)"]
  end
  subgraph GCP["GCP Project (per environment: uat / prod / dr)"]
    subgraph Edge["Edge zone"]
      GLB["Cloud Load Balancing (HTTPS, TLS)"]
      ARMOR["Cloud Armor (WAF)"]
    end
    subgraph GKEz["GKE (private cluster)"]
      SVC["ECS Service (Ingress)"]
      P1["ECS pod"]
      P2["ECS pod"]
      RAG["LLM-RAG pod pool"]
    end
    subgraph Data["Managed data services (private IP)"]
      SQL[("Cloud SQL PostgreSQL — repository + governance")]
      PGV[("Cloud SQL / AlloyDB pgvector — vectors")]
      MEM[("Memorystore Redis — cache/state")]
      GCS[("Cloud Storage — evidence objects")]
    end
    SM["Secret Manager"]
    LOGS["Cloud Logging + Monitoring"]
  end
  U --> GLB --> ARMOR --> SVC --> P1 & P2
  P1 & P2 --> SQL & PGV & MEM & GCS & SM
  P1 & P2 --> RAG
  P1 & P2 --> LOGS
```

Provisioning specifics (GKE, Cloud SQL + pgvector, GCS, IAM, secrets, logging,
CI/CD, env promotion) are in
[`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../../03-development/deployment/GCP_DEPLOYMENT_GUIDE.md).

---

## 3. Cross-cloud application connectivity (AWS / GCP)

Bank applications span clouds. ECS collects posture/evidence from each via the
connector framework (config-driven; credentials from a secret manager) — see
[`../connectors/INTEGRATION_ADAPTERS_GUIDE.md`](../../03-development/developer-manual/connectors/INTEGRATION_ADAPTERS_GUIDE.md).

| Application (example) | Cloud | ECS connectivity |
|---|---|---|
| **Net Banking** | AWS | AWS posture connector (Security Hub / Config via a collector endpoint) + DB/host evidence via the jump server |
| **Mobile Banking** | GCP | GCP posture connector (Security Command Center / Asset Inventory) + DB/host evidence |
| **Payments** | On-prem / hybrid | DB + host (SSH) evidence via the jump server; SaaS/DevSecOps connectors as applicable |

```mermaid
flowchart LR
  subgraph GCP["GCP (ECS home)"]
    ECS["ECS on GKE"]
  end
  subgraph AWSc["AWS (Net Banking)"]
    SH["Security Hub / Config"]
    NBDB[("Net Banking DBs")]
  end
  subgraph GCPc["GCP (Mobile Banking)"]
    SCC["Security Command Center"]
    MBDB[("Mobile Banking DBs")]
  end
  subgraph OnPrem["On-prem / hybrid (Payments)"]
    JS["Jump server (DB Agent)"]
    PAYDB[("Payments DBs")]
    PAYH["Payments hosts"]
  end
  ECS -->|HTTPS + IAM/keys via Secret Manager| SH
  ECS -->|HTTPS + workload identity| SCC
  ECS -->|via jump server| JS
  JS --> PAYDB & PAYH
  ECS -. peering / interconnect / VPN .- AWSc
  ECS -. private connectivity .- OnPrem
```

> **Connectivity assumptions [TARGET].** Cross-cloud traffic uses private
> connectivity where available (Cloud Interconnect / VPN to AWS Direct Connect;
> VPC Service Controls around GCP data services). AWS access uses least-privilege
> IAM (read-only Security Hub/Config) with keys/roles in Secret Manager; GCP
> cross-project access uses workload identity / least-privilege service accounts.
> Payments connectivity assumes ECS reaches on-prem targets **only** through the
> jump server (§4) — ECS never holds direct network routes to production DBs.

---

## 4. Bank jump-server model

For internal bank targets (databases, hosts) that must not be exposed to the ECS
web tier, evidence collection runs through a **jump server** inside the secured
internal network. The **ECS DB Agent** (a prototype micro-service) runs there and
performs DB/host connectivity checks and predefined-query execution, uploading
results to ECS. Network isolation is the primary control.

```mermaid
flowchart LR
  subgraph GCPz["GCP (ECS)"]
    ECS["ECS API"]
  end
  subgraph DMZ["Bank DMZ / restricted subnet"]
    JUMP["Jump server\nECS DB Agent (:8099)"]
  end
  subgraph Internal["Bank internal network (no inbound from ECS)"]
    DB[("Databases")]
    HOST["Hosts (SSH)"]
  end
  ECS <-->|"HTTPS (results/upload)"| JUMP
  JUMP -->|"DB drivers / SSH (read-only)"| DB & HOST
```

- The DB Agent depends on **no** enterprise security infrastructure to run (mTLS,
  JWT, OIDC, Vault are optional, off-by-default extension points). See
  [`../developer-manual/DATABASE_AGENT_GUIDE.md`](../../03-development/developer-manual/DATABASE_AGENT_GUIDE.md).
- The ECS platform's own security framework (auth/RBAC/OIDC) is separate and
  unaffected — see [`../production/ECS_SECURITY_REFERENCE.md`](../../03-development/production/ECS_SECURITY_REFERENCE.md).

---

## 5. Security zones **[TARGET]**

```mermaid
flowchart TD
  subgraph Z0["Zone 0 — Users"]
    B["Browser + Bank SSO/IdP"]
  end
  subgraph Z1["Zone 1 — Edge (public/DMZ)"]
    LB["Cloud LB + Cloud Armor (TLS)"]
  end
  subgraph Z2["Zone 2 — Application (private GKE)"]
    APP["ECS pods (auth + RBAC enforced)"]
    RAGP["LLM-RAG pods"]
  end
  subgraph Z3["Zone 3 — Data (private, no public IP)"]
    D[("Cloud SQL / pgvector / Redis / GCS")]
    SEC["Secret Manager"]
  end
  subgraph Z4["Zone 4 — Bank internal (via jump server only)"]
    JMP["Jump server / DB Agent"]
    TGT[("Internal DBs / hosts")]
  end
  B -->|HTTPS| LB --> APP
  APP --> RAGP
  APP --> D & SEC
  APP <-->|HTTPS| JMP --> TGT
```

| Zone | Contents | Controls |
|---|---|---|
| 0 Users | Browsers, bank IdP | SSO/OIDC/JWT (production mode) |
| 1 Edge | Load balancer, WAF | TLS termination, Cloud Armor, rate limiting |
| 2 App | ECS + RAG pods (private GKE) | Auth middleware, RBAC enforcement, security headers, request-ID |
| 3 Data | Cloud SQL, pgvector, Redis, GCS, Secret Manager | Private IP, IAM, encryption at rest, no public exposure |
| 4 Bank internal | Jump server + internal targets | Network isolation; read-only accounts; no inbound from ECS |

Security modes (demo / uat / production) that gate auth/RBAC/TLS/secrets are
documented in [`../operations/PROTOTYPE_DEMO_RUN_MODE.md`](../../03-development/operations/PROTOTYPE_DEMO_RUN_MODE.md)
and the [security-mode flow](#8-security-mode-flow) below.

---

## 6. Evidence flow

```mermaid
flowchart LR
  SRC["Source system\n(connector / predefined query / upload)"] --> COL["Collector\n(adapter / executor / DB Agent)"]
  COL --> NORM["Normalize\n(evidence record)"]
  NORM --> HASH["SHA-256 + version"]
  HASH --> REPO[("Evidence repository")]
  REPO --> MIR["Audit-intelligence mirror"]
  MIR --> MAP["Map to control -> framework"]
  MAP --> READY["Readiness / reuse / completeness"]
  READY --> DASH["Dashboards / packs / RAG"]
```

Detailed lifecycle sequences: [`ECS_SEQUENCE_DIAGRAMS.md`](ECS_SEQUENCE_DIAGRAMS.md)
(§ evidence, § reuse) and
[`../evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md`](../../03-development/evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md).

---

## 7. Audit flow

```mermaid
flowchart LR
  EV[("Evidence repository")] --> VAL["Validation engine\n(quality / sufficiency)"]
  VAL --> OBS["Observations\n(raise -> track -> close)"]
  EV --> RAG["RAG / prompt workbench\n(grounded, cited answers)"]
  VAL --> RDY["Audit readiness scoring"]
  OBS --> PACK["Evidence packs / reports"]
  RDY --> EXEC["Executive dashboards"]
  RAG --> EXEC
```

Audit workflow + observation lifecycle sequences:
[`ECS_SEQUENCE_DIAGRAMS.md`](ECS_SEQUENCE_DIAGRAMS.md) and
[`ECS_WORKFLOW_ORCHESTRATION_GUIDE.md`](ECS_WORKFLOW_ORCHESTRATION_GUIDE.md).

---

## 8. Security-mode flow

ECS resolves a single security mode (`demo | uat | production`) that gates every
enforcement layer; production/DR stay strict, demo is non-blocking for prototype.

```mermaid
flowchart TD
  START["Request / startup"] --> MODE{"ECS_SECURITY_MODE\n(or derived from ECS_ENV)"}
  MODE -->|demo| DEMO["Auth/RBAC/TLS/secrets OFF\nin-memory OK · config errors warn"]
  MODE -->|uat| UAT["Auth ON · RBAC opt-in\nplaceholder config OK unless strict"]
  MODE -->|production| PROD["Auth + RBAC + TLS + secrets required\nconfig errors fail startup"]
```

Reference: [`../operations/PROTOTYPE_DEMO_RUN_MODE.md`](../../03-development/operations/PROTOTYPE_DEMO_RUN_MODE.md)
· [`../production/ECS_SECURITY_REFERENCE.md`](../../03-development/production/ECS_SECURITY_REFERENCE.md)
· [`../production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md`](../../03-development/production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md).

---

## Related documents

- [`SOLUTION_ARCHITECTURE.md`](SOLUTION_ARCHITECTURE.md) — functional/runtime/integration/data/AI layers
- [`HIGH_LEVEL_DESIGN.md`](HIGH_LEVEL_DESIGN.md) — C4 context/container/component
- [`LOW_LEVEL_DESIGN.md`](LOW_LEVEL_DESIGN.md) — service/module LLD + sequences
- [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../../03-development/deployment/GCP_DEPLOYMENT_GUIDE.md) — GCP provisioning
- [`ecs_enterprise_architecture_review.md`](ecs_enterprise_architecture_review.md) — current-state review + gaps
- [`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md) — full architecture doc index
