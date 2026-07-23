# ECS Application Onboarding Guide

**Type:** Operations onboarding reference. **No code/UI/DB changes.** **Grounding:** `/mvp/onboarding`, `/mvp/platform/onboarding`, `/mvp/platform/inventory`, `/mvp/cmdb`, `ecs_platform/repository/schema.sql` (`applications`, `application_frameworks`, `connectors`), `framework_catalog` app list, `config/integrations.yaml`. Inferred items marked **[Inferred/Target]**.

---

## Overview
Onboarding brings a banking application (e.g., `NETBANKING_PROD`, `UPI_SWITCH_CLUSTER`, `CBS_ORACLE_CLUSTER`) under ECS governance: register it, identify its technology + applicable frameworks/controls, wire connectors + evidence sources + schedules, map controls, run an initial assessment, then operate on a periodic review cycle.

## End-to-end onboarding workflow

```
CMDB Entry → App Registration → Inventory → Technology ID → Framework ID → Control ID
→ Connector Assignment → Evidence Source Assignment → Scheduler Registration
→ Control Mapping → Framework Mapping → Initial Assessment → Ongoing Monitoring
→ Periodic Review → (Offboarding)
```

## Steps

1. **CMDB Entry** (`/mvp/cmdb`): record asset (host/app, owner, environment, criticality). Anchors evidence to assets.
2. **Application Registration** (`/mvp/onboarding`, `/mvp/platform/onboarding`): create application record (`applications` table) — name, owner, business unit, environment.
3. **Application Inventory** (`/mvp/platform/inventory`): app becomes visible in system-of-record inventory.
4. **Technology Identification**: tag stack (OS, DB, web tier, language) — drives which baselining frameworks/queries apply.
5. **Framework Identification**: select applicable frameworks (`application_frameworks` map) — e.g., PCI DSS + DPSC + OS/DB Baselining for a payment app.
6. **Control Identification**: frameworks expand to controls via `FRAMEWORK_CATALOG`.
7. **Connector Assignment** (`/mvp/integrations`): bind source systems (`connectors` table; `config/integrations.yaml`).
8. **Evidence Source Assignment**: map each control to an evidence source (connector pull, scheduler, manual, SharePoint/ServiceNow).
9. **Scheduler Registration** (`/mvp/scheduler`, `/mvp/platform/scheduler`): schedule automated collection — see [Scheduler Reference](ECS_SCHEDULER_REFERENCE.md).
10. **Control Mapping** (`evidence_control_map`): link evidence to controls.
11. **Framework Mapping** (`evidence_framework_map`, crosswalk): enable cross-framework reuse.
12. **Initial Assessment** (`/mvp/completeness`, `/mvp/platform/audit-readiness`): baseline coverage/maturity/readiness.
13. **Ongoing Monitoring** (`/mvp/evidence-health`, `/mvp/integration-health`): freshness, failures, expiring evidence.
14. **Periodic Review** (`/mvp/audit-prep`, Trends): recurring re-attestation/refresh; exceptions via `/mvp/exceptions`.
15. **Offboarding** **[Inferred/Target]**: decommission app — archive evidence, disable connectors/schedules, secure-disposal certificate (see PCI/ITDRM evidence), close controls.

## Roles
Admin/Ops (registration, connectors, schedulers), Application Owner (evidence), Compliance/Framework Owner (framework + control mapping, assessment), Auditor (review).

## Success criteria
App appears in inventory + CMDB; frameworks/controls mapped; ≥1 connector or evidence source per control; initial readiness computed; monitoring + review cadence active.

## Cross-references
- Scheduler: [ECS_SCHEDULER_REFERENCE.md](ECS_SCHEDULER_REFERENCE.md)
- Queries: [ECS_PREDEFINED_QUERY_ARCHITECTURE.md](ECS_PREDEFINED_QUERY_ARCHITECTURE.md)
- Integrations: [docs/INTEGRATIONS/](../connectors/_legacy_INTEGRATIONS_index.md)
- Data model: [ECS_DATA_ARCHITECTURE_REFERENCE.md](../../02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
