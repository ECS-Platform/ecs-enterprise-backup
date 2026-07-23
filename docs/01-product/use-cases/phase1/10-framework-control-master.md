# Framework Control Master

## Purpose

Provide the canonical Phase-1 catalogue of frameworks, policies, controls, procedures, and evidence requirements—and connect application assignments to Evidence Dashboard progress and metadata tagging.

## Business problem solved

Auditors need a stable control hierarchy across ten frameworks. FCM defines what “done” means per control and which evidence requirements must be satisfied per application.

## Phase-1 scope

- **In scope:** YAML catalogue (`config/framework_control_master/`); ten frameworks; application assignments; repository/service layer; search and drill APIs; dashboard progress engine; cross-reference to common controls (not duplicate control definitions).
- **Out of scope:** Runtime control testing engines; regulator submission packs.

## High-level workflow

```
Load catalogue + application_assignments.yaml
  → FrameworkControlMasterService exposes frameworks/controls/requirements
  → Dashboard computes progress from enrollments + evidence workflow status
  → Metadata tagging enriches uploads with policy_refs / procedure_ids / evidence_requirement_ids
  → Common Control Library maps shared domains to FCM controls
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Repository | `modules/frameworks/repositories/framework_control_repository.py` |
| Service | `modules/frameworks/services/framework_control_master_service.py` |
| Config | `config/framework_control_master/catalog.yaml`, `frameworks/*.yaml`, `application_assignments.yaml` |
| Dashboard integration | `build_evidence_dashboard_progress`, `build_evidence_progress_drill` |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/framework-control-master/frameworks` | Framework list |
| GET | `/api/framework-control-master/frameworks/{framework_id}` | Framework document |
| GET | `/api/framework-control-master/controls/{framework_id}/{control_id}` | Control detail |
| GET | `/api/framework-control-master/search` | Search controls |
| GET | `/api/evidence-dashboard/fcm-progress` | Dashboard chart |
| GET | `/api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}` | Drill-down |

## Existing UI pages

| Page | Route |
|------|-------|
| Framework Control Master | `/mvp/framework-control-master` |
| Evidence Dashboard → Framework Progress | `/mvp/evidence-dashboard?tab=framework_progress` |

## Existing tests

- `tests/test_framework_control_master.py`
- `tests/test_evidence_dashboard_fcm_integration.py`

## Demo scenario

1. Open **Framework Control Master** — browse **PCI DSS**, open **PCI-C-01**.
2. Note linked policies, procedures, and evidence requirements.
3. Open **Evidence Dashboard → Framework Progress** for **Net Banking** — PCI segment shows closed/pending/blocked buckets.
4. Drill **PCI-C-01** — evidence requirement statuses reflect demo seed enrollments.

## Known Phase-1 limitations

- Progress relies on demo/workflow enrollments unless real evidence is linked to requirement IDs.
- File-based catalogue requires redeploy to change control definitions.
- Common controls are referenced by domain/slug, not embedded as duplicate FCM controls.
