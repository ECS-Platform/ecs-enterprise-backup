# Use-Case Batch 1 — Core Evidence Workflows

**Status:** Implemented · **Owner:** Audit Intelligence / Platform
**Scope:** Gap closure for 6 use cases (manual upload, bulk upload, metadata/naming,
evidence dashboard & hash integrity, ECS admin users/roles/apps, scheduled pull).

This batch **reuses** existing engines and adds thin REST/UI/service layers only
where the repository had gaps. No connector logic, hashing, naming, scheduler, or
evidence store was duplicated.

---

## What changed

| UC | Gap closed | Implementation (reused → added) |
| --- | --- | --- |
| 1 Manual evidence upload | Uploads landed only in the MVP in-memory list, invisible to readiness/reuse/dashboards | **Bridge**: `operations/evidence_repository.register_upload()` now mirrors each upload into the audit-intelligence repo via `audit_intelligence.engines.evidence_repository.store_evidence()` (SHA-256 versioned, framework/app tags, tech/frameworks enriched from `technology_control_mapping`). No new store. |
| 3 Bulk evidence upload | Same disconnect (bulk calls `register_upload`) | Automatically bridged by the same change; `POST /mvp/upload/bulk` now creates real audit evidence per file. |
| 4 Metadata tagging & naming | No API to preview/validate naming + tags | `GET /api/evidence/naming-preview`, `POST /api/evidence/validate-metadata` — both reuse `enforce_naming()`. |
| 5 Evidence dashboard & hash integrity | No per-evidence hash verify endpoint | `GET /api/evidence/{evidence_id}/integrity` — reuses `integrity_check()` + stored SHA-256. |
| 6 ECS Admin: users, roles, applications | No users/roles CRUD or admin console | New `admin_service` (roles read-only from `app.auth.roles.CANONICAL_ROLES`; apps from `ecs_state.onboarded_applications`; in-memory user registry, **no secrets**) + RBAC-guarded `/api/admin/*` + `/admin/users-roles` UI. |
| 2 Automated scheduled evidence pull | Scheduler was CLI-only | `GET /api/audit/scheduler/plan`, `POST /api/audit/scheduler/dry-run` — wrap `asset_scheduler.plan_evidence/dry_run`. No new scheduler; dry-run performs no queries/connector calls. |

---

## APIs added

| Method + Path | Purpose | Reuses |
| --- | --- | --- |
| `GET /api/audit/scheduler/plan` | Evidence plan for UAT assets (no execution) | `asset_scheduler.plan_evidence` |
| `POST /api/audit/scheduler/dry-run` | Deterministic scheduler dry-run + connector readiness | `asset_scheduler.dry_run` |
| `GET /api/evidence/naming-preview` | Preview standardized evidence filename | `enforce_naming` |
| `POST /api/evidence/validate-metadata` | Validate required tags + naming | `enforce_naming` |
| `GET /api/evidence/{evidence_id}/integrity` | Verify SHA-256 integrity of an uploaded item | `integrity_check` |
| `GET /api/admin/roles` | Canonical roles + capabilities (read-only) | `CANONICAL_ROLES`, `role_permissions` |
| `GET /api/admin/applications` | Onboarded applications (read-only) | `ecs_state.onboarded_applications` |
| `GET /api/admin/users` | List admin users | `admin_service` |
| `POST /api/admin/users` | Create admin user (RBAC: admin) | `admin_service` |
| `POST /api/admin/users/{id}/role` | Reassign user role (RBAC: admin) | `admin_service` |
| `POST /api/admin/users/{id}/active` | Activate/deactivate user (RBAC: admin) | `admin_service` |

## Existing APIs reused (unchanged)

`POST /evidence/upload`, `POST /mvp/upload/bulk`, `GET /evidence/repository`,
`GET /api/audit/dashboard`, `GET /api/evidence-reuse/records` (integrity),
`GET /api/audit/evidence/{key}/versions|timeline`.

## Frontend

- **New:** `/admin/users-roles` (alias `/mvp/admin/users-roles`) — ECS Admin console
  (users CRUD, canonical roles view, applications view). RBAC-aware (non-admins see
  a restriction notice; mutations rejected server-side with 403).
- **Existing (now backed by real audit evidence):** `/mvp/upload` (manual + bulk),
  `/mvp/evidence-health`, `/mvp/audit/executive-readiness`, `/mvp/evidence-story`.

---

## RBAC & safety

- Admin **mutations** require `role_permissions.can_admin_platform(role)` (platform
  admin). Listing/roles/applications are read-only.
- The admin user registry holds **no passwords or secrets** — ECS auth remains
  IdP/OIDC or demo-persona based; this is a management surface only.
- The upload→audit-repo bridge is **best-effort**: a bridge failure never breaks the
  primary upload (records carry `audit_repository_synced: true|false`).
- Scheduler endpoints are **read-only / dry-run** (no queries, no connector calls).

---

## Tests

`tests/test_usecase_batch1_evidence_workflows.py` (19 tests): upload bridge (manual
+ bulk), naming preview/validation, integrity verify (+404), scheduler plan/dry-run,
admin roles/apps/users, RBAC enforcement (auditor→403, admin→200), create/update/
deactivate + validation, and admin UI render. Regression: evidence repository,
evidence reuse lifecycle, connector workbench, asset scheduler, audit route smoke
(121 tests) remain green.

---

## Not in this batch

Batch 2 (completeness, similarity/reuse, AI summaries, quality scoring, NL queries,
leadership dashboards), Batch 3 (multi-app onboarding, lifecycle, comparison,
control validation, GRC integration, enterprise dashboards), and Batch 4 (regulatory
reporting, cross-region analytics, audit prep, trend analysis, national dashboard)
are **not started**.
