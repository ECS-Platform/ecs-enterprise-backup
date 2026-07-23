# ECS Product User Manual

The task-oriented **user manual** for the ECS (Enterprise Evidence Collection
System) — written for the people who *use* ECS day to day: auditors, application
owners, security teams, IT operations, technology managers, and compliance teams.

It explains **what ECS does, how the evidence lifecycle works, and how each role
gets value from it**, with text diagrams and worked examples. It focuses on the
evidence-collection experience and **cross-references** (rather than repeats) the
deeper reference docs.

> **Companion documents (do not duplicate — use these for depth):**
> - Screen-by-screen master: [ECS_MASTER_PRODUCT_MANUAL.md](../product/ECS_MASTER_PRODUCT_MANUAL.md)
> - Functional operations manual + companions: [../product_manual/ECS_PRODUCT_MANUAL.md](../product/PRODUCT_MANUAL_ECS_PRODUCT_MANUAL.md)
>   (module, [persona](../product/ECS_PERSONA_GUIDE.md),
>   [screen catalog](../product/PRODUCT_MANUAL_ECS_SCREEN_CATALOG.md),
>   [KPI dictionary](../product/PRODUCT_MANUAL_ECS_KPI_DICTIONARY.md),
>   [feature reference](../product/ECS_FEATURE_REFERENCE.md),
>   [user journeys](../product/ECS_USER_JOURNEYS.md))
> - Use cases: [ECS_MASTER_USE_CASE_CATALOG.md](../product/ECS_MASTER_USE_CASE_CATALOG.md) · KPIs: [ECS_MASTER_KPI_DICTIONARY.md](../product/ECS_MASTER_KPI_DICTIONARY.md)
> - Developer/architecture: [../DEVELOPER/ECS_DEVELOPER_ONBOARDING_GUIDE.md](../../03-development/developer-manual/ECS_DEVELOPER_ONBOARDING_GUIDE.md)

**Safety:** this manual contains **no** bank-specific information, secrets, or real
IP addresses. All examples use `localhost`/mock values.

---

## Table of contents

1. [Product overview, business problem & vision](#1-product-overview-business-problem--vision)
2. [Key capabilities](#2-key-capabilities)
3. [What ECS supports](#3-what-ecs-supports) (frameworks, technologies, evidence types, connectors)
4. [User roles & who does what](#4-user-roles--who-does-what)
5. [Dashboards](#5-dashboards) (executive readiness + work queues)
6. [Asset discovery & technology classification](#6-asset-discovery--technology-classification)
7. [Scheduler overview](#7-scheduler-overview)
8. [Evidence collection lifecycle](#8-evidence-collection-lifecycle)
9. [Evidence repository & versioning](#9-evidence-repository--versioning)
10. [Evidence packs, framework packs & application packs](#10-evidence-packs-framework-packs--application-packs)
11. [Observation lifecycle](#11-observation-lifecycle)
12. [Evidence approval workflow](#12-evidence-approval-workflow)
13. [Search](#13-search)
14. [Diagnostics](#14-diagnostics)
15. [Reports & notifications](#15-reports--notifications)
16. [Troubleshooting](#16-troubleshooting)
17. [FAQs](#17-faqs)
18. [Best practices](#18-best-practices)
19. [Known limitations](#19-known-limitations)

---

## 1. Product overview, business problem & vision

### What ECS is
ECS is an enterprise **Evidence Collection & Audit-Readiness** platform. It
automatically collects the evidence that proves your technology estate complies
with regulatory and security frameworks, validates that evidence, raises
observations for gaps, and rolls everything into an executive audit-readiness
view — continuously, not just before an audit.

### The business problem
Traditional audit-evidence work is **manual, slow, and fragile**:
- Teams chase screenshots and logs across dozens of tools before every audit.
- Evidence goes **stale** between audits.
- The **same control** is re-proven separately for every framework.
- Leadership has **no real-time view** of how audit-ready the organization is.

### Product vision
> Turn a manual, weeks-long, screenshot-driven evidence exercise into a
> **repeatable, defensible, on-demand** one — with tamper-evident, hashed,
> versioned evidence and a verifiable audit pack an auditor can trust.

### The unifying chain
```
 Technology → Controls (predefined queries) → Frameworks
       │
       ▼
   Assets ── discovered & fingerprinted
       │
       ▼
   Evidence ── collected (connector or baseline), hashed, versioned
       │
       ▼
   Validation ── PASS / FAIL / WARNING (deterministic)
       │
       ▼
   Observations ── raised for gaps, worked to closure
       │
       ▼
   Evidence Packs ── verifiable, auditor-ready
       │
       ▼
   Executive Readiness ── continuous posture
```

For the leadership framing, see [../DEVELOPER/LEADERSHIP_DEMO_SCRIPT.md](../product/LEADERSHIP_DEMO_SCRIPT.md).

---

## 2. Key capabilities

| Capability | What it does | Where |
|-----------|--------------|-------|
| Asset discovery | Finds assets from CMDB / manual / compose / GRC and fingerprints technology | `/mvp/audit/assets` |
| Technology classification | Infers technology (+ version + confidence) from signals | `/mvp/audit/technology-inventory`, `/mvp/audit/mapping` |
| Technology → control → framework mapping | Shows which controls & frameworks apply to each technology | `/mvp/audit/mapping` |
| Evidence collection | Runs read-only checks / connector pulls; captures evidence + hash | `/mvp/audit/runs` |
| Validation | Deterministic PASS/FAIL/WARNING per control | `/mvp/audit/validation-results` |
| Observations | Findings from failures, worked through a workflow | `/mvp/audit/observations` |
| Evidence repository | Versioned, hashed evidence metadata store | `/mvp/audit/repository` |
| Evidence packs | Auditor-ready bundles with a verifiable manifest | `/mvp/audit/evidence-packs` |
| Executive readiness | Coverage, risk band, freshness, open observations | `/mvp/audit/executive-readiness` |
| Scheduler (asset-driven) | Plans collection from an asset inventory (dry-run) | CLI + [design](../../03-development/developer-manual/phase1/scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md) |
| Diagnostics | Config-only connector/environment readiness (no live calls) | CLI + `/api/audit/health` |

Deep feature inventory: [../product_manual/ECS_FEATURE_REFERENCE.md](../product/ECS_FEATURE_REFERENCE.md).

---

## 3. What ECS supports

### Supported frameworks
ECS maps evidence to the compliance frameworks in its catalog (e.g. **RBI Cyber
Security, PCI DSS, ISO 27001, SOC 2, ITPP, DPSC, CSITE** and more). The full,
authoritative list and per-framework control coverage is in the framework
reference: [../FRAMEWORKS/README.md](../product/_legacy_FRAMEWORKS_index.md) and
[../FRAMEWORKS/ECS_FRAMEWORK_REFERENCE.md](../product/ECS_FRAMEWORK_REFERENCE.md).

### Supported technologies
Baseline (predefined-query) collectors cover, among others:

```
Databases     : PostgreSQL, Oracle, SQL Server, MongoDB, Redis,
                YugabyteDB, Aurora/MySQL
OS            : Red Hat Enterprise Linux 8.x / 9.x, Linux, Windows
Middleware    : NGINX, Apache HTTPD, Tomcat
Containers    : Kubernetes, OpenShift
AppSec (tech) : SonarQube, Trivy, GitLeaks
```
Technology names align with the predefined-query catalog so evidence links cleanly
to controls. See [../DEVELOPER/TECHNOLOGY_MAPPING_GUIDE.md](../../03-development/developer-manual/TECHNOLOGY_MAPPING_GUIDE.md).

### Supported evidence types
Evidence is captured as **metadata + a content hash** (never raw secrets):
configuration output, query results, file/policy artefacts, connector-fetched
records (issues, scans, quality gates, CMDB items, documents), and manual uploads.
Each record carries verdict, control status, technology, frameworks, timestamps,
and a SHA-256 content hash. See [../DEVELOPER/EVIDENCE_COLLECTION_GUIDE.md](../../03-development/evidence-management/EVIDENCE_COLLECTION_GUIDE.md).

### Supported connectors
Eleven config-driven enterprise connectors (credentials from env/secret store,
never logged; no live calls in tests):

```
ITSM / CMDB / GRC : ServiceNow CMDB, Archer
Microsoft Graph   : SharePoint, Teams, Outlook   (shared ms_graph_base)
Collaboration/ALM : Jira, Confluence
AppSec            : SonarQube, Checkmarx, Prisma Cloud
File Integrity    : Tripwire
```
Plus baseline database/OS/middleware collectors via the predefined-query engine.
See [../DEVELOPER/INTEGRATION_ADAPTERS_GUIDE.md](../../03-development/developer-manual/connectors/INTEGRATION_ADAPTERS_GUIDE.md),
[../DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md](../../03-development/developer-manual/connectors/MS_GRAPH_CONNECTOR_GUIDE.md),
and the master matrix [../INTEGRATIONS/ECS_MASTER_INTEGRATION_MATRIX.md](../../03-development/developer-manual/connectors/ECS_MASTER_INTEGRATION_MATRIX.md).

---

## 4. User roles & who does what

ECS recognizes multiple personas. In **demo mode** all personas can reach all
screens; in production, RBAC scopes what each role sees/does. Full role model:
[../product_manual/ECS_PERSONA_GUIDE.md](../product/ECS_PERSONA_GUIDE.md).

| Audience | Primary goals in ECS | Start here |
|----------|----------------------|-----------|
| **Auditors** | Review evidence, verify pack integrity, close observations, assess readiness | `/mvp/audit/executive-readiness`, `/mvp/audit/evidence-packs` |
| **Application Owners** | See their apps' controls, collect/upload evidence, remediate observations | `/mvp/audit/assets`, `/mvp/audit/runs` |
| **Security Teams** | Track findings by severity, drive remediation, monitor posture | `/mvp/audit/observations` |
| **IT Operations** | Run/scheduling collection, connector health, diagnostics | `/mvp/audit/runs`, scheduler CLI |
| **Technology Managers** | Coverage per technology, gaps, mapping to frameworks | `/mvp/audit/technology-inventory`, `/mvp/audit/mapping` |
| **Compliance Teams** | Framework readiness, evidence reuse, framework packs | `/mvp/audit/executive-readiness`, framework packs |

---

## 5. Dashboards

### Executive Readiness dashboard (`/mvp/audit/executive-readiness`)
The single audit-readiness view. It aggregates:

```
┌──────────────────────── Executive Readiness ────────────────────────┐
│ Technology coverage   ██████████░░  (techs with executable controls) │
│ Framework readiness   per-framework % from evidence verdicts         │
│ Asset coverage        identified / in-catalog assets                 │
│ Evidence coverage     evidence keys, versions, by verdict/technology │
│ Collection progress   completed vs total controls across runs        │
│ Validation summary    PASS / FAIL / WARNING → compliance %           │
│ Open observations     by severity                                    │
│ Risk summary          risk score → band (Minimal/Low/Medium/High)    │
│ Evidence freshness    fresh vs stale (age threshold)                 │
└──────────────────────────────────────────────────────────────────────┘
```

Also available as JSON at `GET /api/audit/dashboard` (and per-section at
`/api/audit/dashboard/{section}`).

### Broader platform dashboards
ECS also ships enterprise/executive dashboards (Main, CIO, ROI, Trends, Enterprise,
Pan-India) documented in the master manual — see
[ECS_MASTER_PRODUCT_MANUAL.md](../product/ECS_MASTER_PRODUCT_MANUAL.md) (Group 1) and the
[KPI dictionary](../product/PRODUCT_MANUAL_ECS_KPI_DICTIONARY.md).

---

## 6. Asset discovery & technology classification

### Asset discovery (`/mvp/audit/assets`)
ECS builds a unified asset inventory from multiple sources — **ServiceNow CMDB**
(skeleton), **manual import**, **docker-compose** (offline parse), and the
**enterprise-GRC CMDB** — de-duplicated by asset id. Each asset is normalized and
fingerprinted. See [../DEVELOPER/ASSET_DISCOVERY_GUIDE.md](../../03-development/developer-manual/phase1/scheduler/ASSET_DISCOVERY_GUIDE.md).

### Technology classification
A deterministic fingerprint engine infers the technology (and often a version)
from discovery signals, with a confidence score and the signals that drove it:

```
signals → technology (confidence)
  explicit "PostgreSQL"        → PostgreSQL   (0.95)
  image "nginx:1.25"           → NGINX        (0.90 + version 1.25)
  port 5432                    → PostgreSQL   (0.50)
  CMDB class "load balancer"   → NGINX        (0.55)
  (nothing matched)            → Unknown      (0.00)  → manual review
```

Classified technology then links to the controls and frameworks that apply to it
(`/mvp/audit/mapping`, `/mvp/audit/technology-inventory`).

---

## 7. Scheduler overview

ECS has an **asset-driven scheduler** that reads an asset inventory, classifies
each asset, and routes it to the right collector — a baseline predefined-query
collector or an enterprise connector — producing a **bounded, deterministic plan**.

```
uat_assets.yaml → classify → route
  local-postgres      → baseline_collector   (PostgreSQL: N controls)
  local-sonarqube     → enterprise_connector (sonarqube)
  local-sharepoint    → enterprise_connector (sharepoint_graph)
  local-unknown-widget→ unsupported          (manual review)
```

Run a safe **dry-run** (no network, no connector, no query):
```bash
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --dry-run
```

Design + routing table: [../DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../../03-development/developer-manual/phase1/scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md).
Operational scheduler (jobs/history/SLA): [../operations/ECS_SCHEDULER_REFERENCE.md](../../03-development/operations/ECS_SCHEDULER_REFERENCE.md).

---

## 8. Evidence collection lifecycle

A collection **run** executes controls for a scope (asset / technology / framework)
and captures evidence for each. Statuses make failures explicit and safe.

```
   create run (scope) ──► records queued
        │
        ▼
   execute ──► per control:  Completed | Failed | Connector Missing
        │                     | Configuration Required | Cancelled
        ▼
   store evidence ──► hashed + versioned in the repository
        │
        ▼
   validate ──► PASS / FAIL / WARNING (+ compliance %)
        │
        ▼
   observations ──► generated for FAIL / WARNING
```

Runs are visible at `/mvp/audit/runs`; validation at `/mvp/audit/validation-results`.
A run never crashes on a missing connector or unsupported technology — it records a
clear status instead. See [../DEVELOPER/EVIDENCE_COLLECTION_GUIDE.md](../../03-development/evidence-management/EVIDENCE_COLLECTION_GUIDE.md)
and [../DEVELOPER/EVIDENCE_VALIDATION_GUIDE.md](../../03-development/evidence-management/EVIDENCE_VALIDATION_GUIDE.md).

---

## 9. Evidence repository & versioning

The repository (`/mvp/audit/repository`) stores **evidence metadata only** — never
credentials or raw secret content. Each record carries a SHA-256 **content hash**,
a short checksum, technology, frameworks, verdict, control status, source, and
timestamps.

### Versioning
Each re-collection of the same evidence key creates a **new version** — evidence is
never overwritten, so you keep a full, auditable timeline.

```
evidence_key = "web-1::NGX-003"
  v1  hash=ab12…  PASS   collected 2026-01-01
  v2  hash=cd34…  PASS   collected 2026-02-01   ← content changed
  v3  hash=cd34…  PASS   collected 2026-03-01   ← unchanged (same hash)
```

Version history and a per-key timeline are available in the UI and via
`GET /api/audit/evidence/{evidence_key}/versions` and `/timeline`. See
[../DEVELOPER/OBSERVATION_AND_REPOSITORY_GUIDE.md](../../03-development/evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md).

---

## 10. Evidence packs, framework packs & application packs

An **evidence pack** is an auditor-ready bundle assembled from the repository, with
a deterministic **manifest** and a pack-level hash an auditor can recompute to
confirm nothing was altered.

```
Pack manifest
  pack_type / pack_scope
  item_count
  pack_hash  = sha256(sorted item content hashes)   ← verifiable
  technologies[], frameworks[], verdict_summary
  items[]   (evidence_key, version, control, hash, …)
```

Pack types (all under `/mvp/audit/evidence-packs`, API `/api/audit/packs/...`):

| Pack | Scope | Use it for |
|------|-------|-----------|
| **Evidence pack** | explicit set of evidence keys | ad-hoc auditor request |
| **Framework pack** | all latest evidence for a framework | a regulator's audit (e.g. PCI DSS) |
| **Asset pack** | all latest evidence for one asset | app/asset-level review |
| **Application pack** | evidence for an application's assets | app-owner sign-off |
| **Technology pack** | all latest evidence for a technology | tech-manager coverage review |

Integrity: `verify_manifest()` recomputes and compares the pack hash. Large packs
paginate their `items` while preserving `item_count`/`pack_hash`. See
[../DEVELOPER/OBSERVATION_AND_REPOSITORY_GUIDE.md](../../03-development/evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md)
and [../operations/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md](../../03-development/evidence-management/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md).

---

## 11. Observation lifecycle

Failed/warning validations generate **observations** with a deterministic severity
(Critical/High/Medium/Low/Informational), impact, and recommendation. Each moves
through a governed workflow (`/mvp/audit/observations`):

```
 Draft ──► Submitted ──► Approved ──► Remediated ──► Closed
   │           │            │
   └──► Rejected◄───────────┘   (Rejected can return to Draft)
```

Only valid transitions are allowed (invalid ones are refused with a clear error).
Severity weighting also feeds the executive **risk band**. See
[../DEVELOPER/OBSERVATION_AND_REPOSITORY_GUIDE.md](../../03-development/evidence-management/OBSERVATION_AND_REPOSITORY_GUIDE.md)
and the workflow matrices in [../WORKFLOWS/ECS_STATE_TRANSITION_MATRIX.md](../../02-architecture/architecture/ECS_STATE_TRANSITION_MATRIX.md).

---

## 12. Evidence approval workflow

Beyond audit-intelligence observations, ECS provides an enterprise **evidence
review/approval** workflow (submit → review → approve/reject → resubmit) with SLAs,
role actions, and notifications. This is documented end-to-end in the workflow
package rather than duplicated here:

- Review UI & actions: [ECS_MASTER_PRODUCT_MANUAL.md](../product/ECS_MASTER_PRODUCT_MANUAL.md) (Governance group, `/evidence/review`).
- State transitions: [../WORKFLOWS/ECS_STATE_TRANSITION_MATRIX.md](../../02-architecture/architecture/ECS_STATE_TRANSITION_MATRIX.md)
- Role/CRUD matrix: [../WORKFLOWS/ECS_ROLE_ACTION_MATRIX.md](../../02-architecture/architecture/ECS_ROLE_ACTION_MATRIX.md)
- SLA & escalation: [../WORKFLOWS/ECS_SLA_ESCALATION_MATRIX.md](../../02-architecture/architecture/ECS_SLA_ESCALATION_MATRIX.md)
- Notifications: [../WORKFLOWS/ECS_NOTIFICATION_MATRIX.md](../../02-architecture/architecture/ECS_NOTIFICATION_MATRIX.md)

---

## 13. Search

You can search and filter across the evidence layer:

- **Evidence/repository search** — by query text, technology, framework, asset,
  verdict, tag, latest-only. UI: `/mvp/audit/repository`; API:
  `GET /api/audit/repository` (or `/api/audit/evidence`) with `limit`/`offset`.
- **Mapping search** — by technology / framework / free text
  (`/mvp/audit/mapping`, `GET /api/audit/mapping/search`).
- **Observations filter** — by status / severity / framework / technology.

All list responses are **paginated** (safe default + hard maximum) so large result
sets never overwhelm the UI or API. See
[../DEVELOPER/PERFORMANCE_AND_HARDENING_GUIDE.md](../../03-development/production/PERFORMANCE_AND_HARDENING_GUIDE.md).

---

## 14. Diagnostics

Before collecting anything, verify readiness **without** touching live systems:

```bash
# Connector readiness (config-only; SET/MISSING, never secret values):
python scripts/run_uat_connector_health.py --adapter all

# Live probe ONLY for configured adapters (explicit opt-in):
python scripts/run_uat_connector_health.py --adapter all --live

# Full offline platform check (no network/DB): expect 10/10 ALL PASS
python scripts/run_ecs_demo_smoke.py
```

Health is also exposed at `GET /api/audit/health` and
`GET /api/audit/integrations/health`. Diagnostics never print secrets. See
[../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md](../../03-development/operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md).

---

## 15. Reports & notifications

### Reports
ECS produces executive audit packs, interactive reports, gap exports, and
audit-bundle exports. The evidence layer contributes readiness, coverage, and pack
exports. Full report catalog and export center:
[../product_manual/ECS_FEATURE_REFERENCE.md](../product/ECS_FEATURE_REFERENCE.md)
and the Reports screen in [ECS_MASTER_PRODUCT_MANUAL.md](../product/ECS_MASTER_PRODUCT_MANUAL.md).

### Notifications
Workflow events (submissions, approvals, rejections, SLA breaches, escalations)
drive notifications per the
[../WORKFLOWS/ECS_NOTIFICATION_MATRIX.md](../../02-architecture/architecture/ECS_NOTIFICATION_MATRIX.md).

---

## 16. Troubleshooting

> Deep runbooks: [../TROUBLESHOOTING_GUIDE.md](../00-start-here/TROUBLESHOOTING_GUIDE.md),
> [../operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md](../../03-development/operations/CONNECTOR_TROUBLESHOOTING_RUNBOOK.md),
> [../operations/ECS_SUPPORT_RUNBOOK.md](../../03-development/operations/ECS_SUPPORT_RUNBOOK.md).

| Symptom | Likely cause & fix |
|---------|--------------------|
| A page shows no evidence | Nothing collected yet for that scope — run a collection (`/mvp/audit/runs`) or seed the demo. |
| A control shows **Connector Missing** / **Configuration Required** | The connector/driver isn't configured — provide config via env (see diagnostics), then re-run. |
| An asset is **Unsupported** | No connector and no predefined controls — check `asset_type`/technology; handle manually. |
| Connector shows **not_configured** | Expected until credentials are provisioned; set the `ECS_*` env vars, verify with the health CLI. |
| Microsoft Graph **auth_error** | Missing/invalid Graph app registration or consent — see the MS Graph guide. |
| Pack verification fails | The manifest's items were altered — rebuild the pack from the repository. |
| Everything empty on a fresh start | Run `python scripts/run_ecs_demo_smoke.py` once (seeds a representative run). |

---

## 17. FAQs

**Is ECS a GRC tool?** No — ECS is the **evidence engine**. It complements GRC /
workflow tooling; it collects, validates, governs, and packages evidence.

**Does ECS store our secrets?** No. ECS stores evidence **metadata + hashes**, and
connector credentials live in env/secret store — displayed only as `SET`/`MISSING`.

**Does running a check make changes to my systems?** No. Baseline checks are
**read-only**; connectors fetch read-only data. Nothing is mutated.

**Can auditors trust the evidence?** Yes — every record is hashed and versioned,
and packs carry a **verifiable manifest** an auditor can recompute.

**How does ECS move from demo to real UAT?** It's **environment-driven** — the same
code runs against localhost/demo today and bank UAT endpoints by setting env vars,
with no code change. See [connectors/UAT_INTEGRATION_GUIDE.md](../../03-development/developer-manual/connectors/UAT_INTEGRATION_GUIDE.md).

**What if a technology has no controls yet?** The asset is flagged **Unsupported**
(manual review) — it never crashes a run.

**Where do I see how audit-ready we are?** The Executive Readiness dashboard
(`/mvp/audit/executive-readiness`) and `GET /api/audit/dashboard`.

---

## 18. Best practices

- **Discover first, collect second.** Keep the asset inventory current so the right
  controls/connectors are selected.
- **Dry-run the scheduler** before a real cycle to review the plan and spot gaps
  (`--strict` flags unsupported assets).
- **Use least-privilege, read-only** service accounts for every connector; keep
  secrets out of Git (env/secret store only).
- **Re-collect on change, not blindly** — versioning + content hashes let you see
  what actually changed.
- **Package per framework** for audits (framework packs) and **verify the manifest**
  before sharing.
- **Work observations to closure** promptly; severity feeds the risk band leadership
  sees.
- **Run diagnostics** (`run_uat_connector_health.py`, `run_ecs_demo_smoke.py`)
  before and during UAT.

---

## 19. Known limitations

These are **operational/environment** items by design (the platform is complete
offline end-to-end); tracked in the
[../DEVELOPER/PRODUCTION_READINESS_GAP_REGISTER.md](../../03-development/production/PRODUCTION_READINESS_GAP_REGISTER.md):

- **In-memory stores by default** — a DB-ready durable persistence foundation
  exists (SQLite default, Postgres-ready) but engines are not auto-wired to it yet
  ([persistence guide](../../03-development/audit-intelligence/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md)).
- **Connector execution needs real credentials + live UAT validation** (skeletons
  degrade cleanly to `not_configured` until then).
- **Connector reliability** (HTTP 429 / circuit breaking) and **DR/backup** for the
  durable store are deployment-time hardening items.
- **Production auth (Azure AD/OIDC), secrets manager, monitoring/alerting, HA, and
  load testing** are provisioned at deployment.

---

*This user manual is intentionally task- and audience-oriented. For screen-level
detail, KPI formulas, use cases, and the broader GRC platform, follow the
cross-referenced companion documents above — they remain the single source of
truth for their areas.*
