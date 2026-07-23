# Evidence Dashboard — Phase-1 Implementation

## Purpose

Render role-scoped KPIs, framework progress (FCM), common-control summary, and collection health from persisted evidence data.

## Business requirement

See [Evidence Dashboard (business)](../../../01-product/use-cases/phase1/06-evidence-dashboard.md).

## Functional flow

```
GET /mvp/evidence-dashboard
  → module_capabilities.get_module_capability("evidence_dashboard", role)
  → _evidence_dashboard_view: analytics, repo stats, integrity, FCM progress, common_controls summary
  → Template tabs (overview, framework_progress, ...)
Drill: GET /api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}
```

## High-level design

UI consumes **FrameworkControlMasterService** for progress; does not read YAML directly. KPIs blend `ecs_state` analytics, audit `repository_stats`, and scheduler collection snapshot.

Design reference: [../../design/phase1/Framework Control Master and Evidence Dashboard.md](../../../02-architecture/design/phase1/Framework%20Control%20Master%20and%20Evidence%20Dashboard.md).

## Components

| Component | Path |
|-----------|------|
| Module view | `modules/shared/services/module_capabilities._evidence_dashboard_view` |
| FCM service | `modules/frameworks/services/framework_control_master_service.py` |
| Common controls summary | `modules/frameworks/services/common_controls_service.dashboard_summary` |
| FCM repository | `modules/frameworks/repositories/framework_control_repository.py` |
| Demo seed | `modules/executive_overview/engines/demo_seed.py` |

## APIs

| Method | Path |
|--------|------|
| GET | `/api/evidence-dashboard/fcm-progress` |
| GET | `/api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}` |
| GET | `/api/framework-control-master/*` |
| GET | `/api/evidence/repository` |

API supplement: [../api/framework_control_master.md](../api/framework_control_master.md).

## Database objects

Progress uses enrollments + audit stats; catalogue from YAML not DB.

## Metadata

Drill-down surfaces `policy_refs`, `procedure_ids`, `evidence_requirement_ids` from FCM control documents.

## Scheduler interaction

Dashboard **collection** block embeds scheduler yesterday summary / failed collections KPI.

## Object storage

Integrity KPI reflects hash validation; object counts via repo stats `with_object_storage`.

## Repository integration

`repository_stats()` from audit service; authoritative reader for row counts in common-controls summary.

## Dashboard integration

(This document.) Template: `templates/mvp_evidence_dashboard.html`.

## Search integration

Cross-link: users discover evidence in Search; dashboard shows aggregate KPIs not row-level search.

## Chatbot integration

AI Ops Assistant separate module; dashboard KPIs not directly queried by chatbot presets.

## Configuration

FCM: `config/framework_control_master/`. Demo: seed via `seed_demo_workflow_state()`.

## Feature flags

Demo mode affects analytics source label (`data_source` DEMO vs PARTIAL).

## Source files

See **Components**. Tests: `tests/test_evidence_dashboard_fcm_integration.py`, `tests/test_framework_control_master.py`.

## Testing

- `tests/test_evidence_dashboard_fcm_integration.py`
- `tests/test_framework_control_master.py`
- `tests/test_dashboard_service.py`

## Troubleshooting

Empty FCM chart: run demo seed or link evidence enrollments to requirements. KPI mismatch: compare audit `repo.stats()` vs authoritative reader totals.

## Known limitations

FCM progress driven by demo enrollments unless real evidence linked. Common-control PASS/FAIL not all connector types.
