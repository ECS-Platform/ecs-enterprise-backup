# Evidence Dashboard

## Purpose

Give compliance stakeholders a consolidated KPI and drill-down view of evidence collection health, repository coverage, framework progress, common-control summary, and integrity—scoped by role and application.

## Business problem solved

Leadership and control owners need at-a-glance status without opening individual evidence files. The dashboard ties repository data to framework obligations and collection outcomes.

## Phase-1 scope

- **In scope:** Overview KPIs (artifacts, controls tracked, repository keys, integrity %, health issues, failed collections); Framework Control Master progress chart and drill-down tab; common controls summary; collection/scheduler snapshot; RBAC-scoped application list.
- **Out of scope:** Real-time streaming analytics; multi-year trend warehousing.

## High-level workflow

```
User opens Evidence Dashboard (role-scoped)
  → module_capabilities._evidence_dashboard_view
  → KPIs from ecs_state analytics + repo stats + integrity + scheduler summary
  → FCM progress from FrameworkControlMasterService
  → Common controls summary from CommonControlsService
  → Drill-down via /api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Dashboard view | `modules/shared/services/module_capabilities._evidence_dashboard_view` |
| FCM progress | `modules/frameworks/services/framework_control_master_service.py` |
| Common controls KPI | `modules/frameworks/services/common_controls_service.dashboard_summary` |
| Template | `templates/mvp_evidence_dashboard.html` (Framework Progress tab) |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evidence-dashboard/fcm-progress` | Framework progress chart data |
| GET | `/api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}` | Control drill-down |
| GET | `/api/evidence/repository` | Repository stats for KPIs |

## Existing UI pages

| Page | Route |
|------|-------|
| Evidence Dashboard | `/mvp/evidence-dashboard` |
| Framework Progress tab | `/mvp/evidence-dashboard?tab=framework_progress&application=Net%20Banking` |

## Existing tests

- `tests/test_evidence_dashboard_fcm_integration.py`
- `tests/test_framework_control_master.py`
- `tests/test_dashboard_service.py`
- `tests/test_phase1_e2e_lifecycle_validation.py`

## Demo scenario

1. Seed demo workflow (`seed_demo_workflow_state`) or collect a few evidence items.
2. Open **Evidence Dashboard** as **owner** for **Net Banking**.
3. Confirm KPI tiles and **Framework Progress** stack chart (PCI DSS, ITPP, etc.).
4. Drill into **PCI-C-01** — policies, procedures, evidence requirements show accepted/pending segments.
5. Re-run identical scheduler collection — duplicate count increases but **new evidence** KPI does not inflate incorrectly.

## Known Phase-1 limitations

- FCM progress uses demo enrollments (`ecs_state.uploaded_evidence_enrollments`) rather than live SQL alone.
- Repository Keys KPI uses audit `repo.stats()`, which may differ slightly from authoritative reader totals when ops mirror is cleared.
- PASS/WARNING/FAIL segment detail is strongest for common-control validation verdicts, not all connector types.
