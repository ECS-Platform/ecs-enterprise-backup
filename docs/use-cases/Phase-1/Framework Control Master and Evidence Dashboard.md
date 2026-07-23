# Software Requirements Specification (SRS)

## Framework Control Master and Evidence Dashboard Integration

| Field | Value |
|-------|-------|
| **Document ID** | ECS-UC-P1-FCM-001 |
| **Version** | 1.0 |
| **Status** | Implementation-aligned (Phase 1) |
| **Last updated** | 2026-07-23 |
| **Primary UI** | Governance → **Framework Control Master** (`/mvp/framework-control-master`); Operations → **Evidence Dashboard** → Framework Progress tab (`/mvp/evidence-dashboard?tab=framework_progress`) |
| **Implementation maturity** | 🟢 **COMPLETE (Phase 1)** — file catalogue, repository/service layer, dashboard integration, APIs, DEMO seed |

---

## 1. Purpose

Phase 1 delivers a **Framework Control Master (FCM)** catalogue and wires it into the **Evidence Dashboard** so framework-wise application progress is computed from:

- FCM policies, controls, procedures, and evidence requirements  
- Application ↔ framework assignments  
- Persisted evidence and workflow status (in-memory / demo enrollments)

The UI and routes consume **`FrameworkControlMasterService` only**. YAML and storage details are hidden behind **`FrameworkControlRepository`**.

---

## 2. Framework hierarchy

Each framework document under `config/framework_control_master/frameworks/*.yaml` follows:

```
Framework
 └── policies[]          (id, title, description, owner, status, review_frequency)
 └── controls[]
      ├── policy_refs[]  → links to policy.id
      ├── procedures[]   (id, title, owner, frequency, steps[])
      └── evidence_requirements[]  (id, title, artefact_type, frequency, collection_method, retention_period)
```

**Example (PCI DSS):** `PCI-POL-NETWORK-01` → control `PCI-C-01` → procedure `PCI-PROC-01` → requirements `PCI-EVR-011`, `PCI-EVR-012`.

**Catalogue index:** `config/framework_control_master/catalog.yaml` (10 frameworks, aliases, version `2026.1`).

| Framework ID | Display name |
|--------------|--------------|
| `itpp` | Information Technology Policies & Procedures |
| `asst` | Application Security Self-Assessment |
| `mbss` | Minimum Baseline Security Standard |
| `pci_dss` | PCI DSS |
| `dpsc` | Digital Payment Security Controls |
| `csite` | C-SITE |
| `vapt` | VAPT |
| `os_baseline` | OS Baseline |
| `middleware_baseline` | Middleware Baseline |
| `database_baseline` | Database Baseline |

---

## 3. Application assignment model

**Source:** `config/framework_control_master/application_assignments.yaml`  
**Loaded by:** `FileFrameworkControlRepository.list_application_assignments()`

Each row:

```yaml
- application: Net Banking
  owner: R. Mehta
  frameworks: [pci_dss, itpp, vapt, os_baseline, mbss, csite]
```

Nine applications are assigned in Phase 1 (Net Banking, Mobile Banking, Payments, UPI, CBS Oracle, Treasury, Loan System, API Gateway, Internet Banking).

Optional **`not_applicable`** entries exclude specific controls per application (empty `control_ids` lists are placeholders for future exclusions).

---

## 4. Control applicability

A control applies to an `(application, framework)` pair when:

1. The framework is listed in that application's assignment, **and**  
2. `is_control_applicable(application, framework_id, control_id)` is true (not in `not_applicable`).

Non-applicable controls are bucketed as **`not_applicable`** (grey) in progress charts.

---

## 5. Evidence mapping

| Direction | Phase 1 implementation |
|-----------|------------------------|
| **Control → required evidence** | FCM `evidence_requirements[]` on each control |
| **Evidence → control** | Primary: `ecs_state.uploaded_evidence_enrollments` with `fcm_framework_id`, `fcm_control_id`, `fcm_evr_id`; key `fcm:{fw}:{control}:{evr}:{app}`. Fallback: legacy `ecs_state.build_evidence_analytics()` rows matched by framework name + control title + application |
| **Evidence → application** | `application` field on enrollments and analytics rows |

**Not wired in Phase 1:** Postgres audit repository search (`audit_repository_service`) is not merged into FCM progress unless evidence is already reflected in enrollments or analytics.

---

## 6. Control closure rules

Implemented in `modules/governance/engines/fcm_evidence_progress_engine.py` → `_classify_control()`.

A control is **Closed** (green) only when **every** mandatory evidence requirement for that `(application, control)` is classified **`accepted`** (audit status Approved/Accepted, evidence not Expired).

| Bucket | Key | Meaning |
|--------|-----|---------|
| **Closed** | `closed` | All requirements accepted |
| **Pending** | `pending` | Partial submission, under review, or missing with other pending items |
| **Blocked** | `blocked` | Rejected, expired, or mandatory evidence missing with no pending path |
| **Not started** | `not_started` | No satisfying submissions |
| **Not applicable** | `not_applicable` | Control excluded or framework not assigned |

Requirement-level states: `accepted`, `pending`, `rejected`, `expired`, `missing`.

---

## 7. Evidence Dashboard KPIs (Overview tab)

Sourced from `module_capabilities._evidence_dashboard_view()` (legacy + repository signals):

| KPI | Source |
|-----|--------|
| Evidence Artifacts | `ecs_state.build_evidence_analytics()` totals |
| Controls Tracked | Workflow controls in ECS state |
| Repository Keys | `audit_repository_service.repository_stats()` |
| Integrity Valid | `get_health_dashboard()` |
| Health Issues | `build_evidence_health_view()` row count |
| Failed Collections | Scheduler yesterday summary |

**Framework Progress tab** adds FCM-specific totals via `fcm_progress.totals` (controls counted, frameworks in chart).

---

## 8. Framework Progress chart

**Tab:** Evidence Dashboard → **Framework Progress**  
**Data:** `FrameworkControlMasterService.build_evidence_dashboard_progress(role, application, framework_id)`

- One **stacked vertical bar per framework** for the selected application  
- Segments = control counts per status bucket  
- Application selector filters scope (role-aware)

### Colour conventions

| Colour | CSS tone | Status keys |
|--------|----------|-------------|
| **Green** | `tone-green` | `closed` |
| **Orange** | `tone-orange` | `pending` |
| **Red** | `tone-red` | `blocked` |
| **Grey** | `tone-grey` | `not_started`, `not_applicable` |

Legend labels are returned in `fcm_progress.legend` (not hardcoded in the template).

---

## 9. Application Owner RBAC

Uses demo scope in `modules/shared/services/role_filter_scope.py`:

| Role | Applications visible |
|------|----------------------|
| `owner` | Net Banking, Mobile Banking, Payments |

- `list_assigned_applications("owner")` returns only these apps.  
- Progress API ignores out-of-scope `application` query values (falls back to first allowed app).  
- Drill API returns **403 payload** (`ok: false`) when `application` is outside role scope and `role` is supplied.

---

## 10. Compliance / CIO RBAC

| Role | Applications visible |
|------|----------------------|
| `compliance_head`, `compliance_officer` (normalized to compliance_head), `cio`, `auditor`, `admin` | All nine assignment applications (`apps_for_role` → `None`) |

Compliance officers see the full assignment catalogue in the Framework Progress application selector.

---

## 11. DEMO_MODE behaviour

When `DEMO_MODE=true`:

1. `seed_demo_workflow_state()` runs at startup (`modules/executive_overview/engines/demo_seed.py`).  
2. **`seed_fcm_evidence_progress_demo()`** runs idempotently (`modules/governance/engines/fcm_evidence_demo_seed.py`):
   - Skips if any enrollment already has `fcm_framework_id`  
   - Seeds sample enrollments for closed / pending / blocked states across owner apps  
   - Sets `ecs_state.approved_controls`, `submitted_controls`, `rejected_controls` for demo controls  

**Production:** No FCM seed runs when enrollments exist; production data is preserved.

---

## 12. Architecture (Phase 1)

```
┌─────────────────────────────────────────────────────────────┐
│  Jinja dashboards (FCM page, Evidence Dashboard tab)        │
│  — no YAML access; module_view / fcm_progress only          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  FrameworkControlMasterService                              │
│  modules/frameworks/services/framework_control_master_service.py │
│  — list/detail/search/dashboard/progress/drill                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  FrameworkControlRepository (ABC)                           │
│  FileFrameworkControlRepository (Phase 1)                   │
│  modules/frameworks/repositories/framework_control_repository.py │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  config/framework_control_master/                           │
│  catalog.yaml, application_assignments.yaml, frameworks/*.yaml │
└─────────────────────────────────────────────────────────────┘

Progress engine (service-internal):
  modules/governance/engines/fcm_evidence_progress_engine.py
Evidence state:
  ecs_state.uploaded_evidence_enrollments, build_evidence_analytics()
```

**Future backends (not Phase 1):** database, Excel import, SharePoint, framework upload — implement `FrameworkControlRepository` and swap via `get_framework_control_repository()`.

---

## 13. Repository pattern

| Method | Purpose |
|--------|---------|
| `source_type()` | `"file"` in Phase 1 |
| `list_framework_summaries()` | Catalogue index |
| `get_framework(id)` | Full document + stats |
| `get_control(fw, control_id)` | Control + linked policies |
| `search_controls(query, fw, domain)` | Cross-framework search |
| `list_application_assignments()` | App ↔ framework map |
| `frameworks_for_application(app)` | Framework IDs for app |
| `applications_for_framework(fw)` | Apps for framework |
| `is_control_applicable(app, fw, control_id)` | Applicability gate |
| `resolve_framework_id(name)` | Alias resolution (`PCI DSS` → `pci_dss`) |
| `catalog_stats()` | Aggregate KPI counts |

---

## 14. Service layer

| Service method | Consumer |
|----------------|----------|
| `list_frameworks()` | FCM API |
| `get_framework_detail(id)` | FCM API |
| `get_control_detail(fw, control_id)` | FCM API / drill |
| `search_controls(...)` | FCM API |
| `build_dashboard(...)` | FCM page |
| `build_evidence_dashboard_progress(role, application, framework_id)` | Evidence Dashboard |
| `build_evidence_progress_drill(fw, control_id, application, role)` | Evidence Dashboard drill API |
| `list_assigned_applications(role)` | Application selector |

Factory: `get_framework_control_master_service()` (cached singleton).

---

## 15. API endpoints

See [`docs/api/framework_control_master.md`](../../api/framework_control_master.md).

Summary:

| Method | Path |
|--------|------|
| GET | `/mvp/framework-control-master` |
| GET | `/api/framework-control-master/frameworks` |
| GET | `/api/framework-control-master/frameworks/{framework_id}` |
| GET | `/api/framework-control-master/controls/{framework_id}/{control_id}` |
| GET | `/api/framework-control-master/search` |
| GET | `/mvp/evidence-dashboard` |
| GET | `/api/evidence-dashboard/fcm-progress` |
| GET | `/api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}` |

---

## 16. Drill-down flow

**Evidence Dashboard → Framework Progress → Drill button**

1. **Framework** — display name from FCM catalogue  
2. **Policy** — first linked policy from `policy_refs` (multi-policy controls show primary only in Phase 1)  
3. **Control** — title, domain, criticality  
4. **Procedures** — nested procedure list with steps  
5. **Required evidence** — each `evidence_requirements[]` row  
6. **Submitted evidence** — matched enrollment or legacy analytics row  
7. **Status** — requirement status + aggregate `control_status`

API: `GET /api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}?application=&role=`  
Returns `drill_path[]` array for breadcrumb rendering.

---

## 17. Phase 1 limitations

| Limitation | Notes |
|------------|-------|
| File-only catalogue | No DB/Excel/SharePoint upload backend yet |
| Legacy evidence matching | Non-FCM enrollments matched by control **title**, not FCM control ID |
| Audit repository | Postgres evidence artifacts not auto-linked to FCM requirements |
| Single policy in drill UI | Controls with multiple `policy_refs` surface first policy only |
| Demo RBAC | `role_filter_scope` demo map; not Phase 2 `app/auth/scope.py` enforcement |
| Separate from legacy catalog | `framework_catalog.py` (15 frameworks, mock evidence) still powers `/framework/{name}` dashboards |
| CIO Approval tab | Evidence Dashboard hides Approval tab for `cio` role (unchanged) |

---

## 18. Tests

Focused suite:

```bash
pytest tests/test_framework_control_master.py tests/test_evidence_dashboard_fcm_integration.py -q
```

---

## 19. Related code paths

| Area | Path |
|------|------|
| Repository | `modules/frameworks/repositories/framework_control_repository.py` |
| Service | `modules/frameworks/services/framework_control_master_service.py` |
| Progress engine | `modules/governance/engines/fcm_evidence_progress_engine.py` |
| DEMO seed | `modules/governance/engines/fcm_evidence_demo_seed.py` |
| Dashboard view | `modules/shared/services/module_capabilities.py` → `_evidence_dashboard_view` |
| Routes | `modules/shared/routes/routes_mvp.py` |
| FCM template | `modules/frameworks/templates/mvp_framework_control_master.html` |
| Evidence Dashboard template | `modules/governance/templates/mvp_evidence_dashboard.html` |
| Config | `config/framework_control_master/` |
