# ECS Role Action Matrix

**Type:** Auditor / architecture-grade RBAC reference. No code modified.
**Date:** 2026-06-17
**Grounding:** `config/rbac.yaml` (`rbac.roles`, `rbac_catalog.roles`,
`rbac_legacy_compat.capabilities`, `role_scope`) and
`modules/shared/services/role_permissions.py`. Roles requested but not present as
distinct code roles are mapped to the nearest implemented role and marked
**(Inferred)**.

**Navigation:** [Workflow Orchestration Guide](ECS_WORKFLOW_ORCHESTRATION_GUIDE.md) ·
[State Transition Matrix](ECS_STATE_TRANSITION_MATRIX.md) ·
[SLA & Escalation](ECS_SLA_ESCALATION_MATRIX.md) ·
[Notification Matrix](ECS_NOTIFICATION_MATRIX.md)

---

## 1. Role mapping (requested → implemented)

| Requested role | Implemented role (rbac.yaml) | Scope |
|----------------|------------------------------|-------|
| Auditor | `auditor` | enterprise |
| Audit Manager | `auditor` (elevated) **(Inferred)** | enterprise |
| Application Owner | `application_owner` | application |
| Evidence Owner | `application_owner` / `control_owner` | application/control |
| Reviewer | `auditor` (review capability) | enterprise |
| Approver | `auditor` / `cio` (per gate) | enterprise |
| Function Head | `functional_head` | function |
| Vertical Head | `vertical_head` | vertical |
| CIO | `cio` | enterprise |
| CISO | `security_officer` **(Inferred mapping)** | enterprise (security) |
| ISG | `compliance_officer` (governance) **(Inferred)** | enterprise |
| Governance Team | `compliance_officer` | enterprise |
| Risk Team | `compliance_officer` / `cio` (exception.approve) **(Inferred)** | enterprise |
| Compliance Team | `compliance_officer` | enterprise |
| ECS Administrator | `admin` / `system_admin` / `enterprise_admin` | enterprise |

## 2. CRUD + workflow action matrix

Legend: ✅ allowed · ➖ not granted · ◔ inferred/governance overlay (not yet
enforced in code).

| Role | View | Create | Edit | Approve | Reject | Close | Escalate | Reassign | Exception Approval | RAF Approval | Dashboard Access |
|------|:----:|:------:|:----:|:-------:|:------:|:-----:|:--------:|:--------:|:------------------:|:------------:|:----------------:|
| Auditor | ✅ | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ◔ | Auditor |
| Audit Manager (Inf) | ✅ | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ◔ | Auditor |
| Application Owner | ✅ | ✅ | ✅ | ➖ | ➖¹ | ➖ | ✅ | ➖ | ➖ | ➖ | Owner |
| Evidence Owner | ✅ | ✅ | ✅ | ➖ | ➖ | ➖ | ◔ | ➖ | ➖ | ➖ | Owner |
| Reviewer | ✅ | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ◔ | ◔ | Auditor |
| Approver | ✅ | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | ◔ | ◔ | ◔ | per gate |
| Function Head | ✅ | ➖ | ➖ | ◔ | ◔ | ➖ | ✅ | ➖ | ➖ | ➖ | Functional |
| Vertical Head | ✅ | ➖ | ➖ | ◔ | ◔ | ➖ | ✅ | ➖ | ◔ | ◔ | Vertical |
| CIO | ✅ | ➖ | ➖ | ◔ | ◔ | ➖ | ✅ | ➖ | ✅ | ◔ | CIO |
| CISO (Inf) | ✅ | ➖ | ➖ | ◔ | ◔ | ➖ | ✅ | ➖ | ◔ | ◔ | Security |
| ISG (Inf) | ✅ | ◔ | ◔ | ◔ | ◔ | ➖ | ✅ | ✅ | ✅ | ✅ | Compliance |
| Governance Team | ✅ | ◔ | ◔ | ➖ | ➖ | ➖ | ✅ | ✅ | ◔ | ◔ | Compliance |
| Risk Team (Inf) | ✅ | ◔ | ◔ | ➖ | ➖ | ➖ | ✅ | ➖ | ✅ | ✅ | Compliance |
| Compliance Team | ✅ | ◔ | ◔ | ➖ | ➖ | ➖ | ✅ | ✅ | ◔ | ◔ | Compliance |
| ECS Administrator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | All |

¹ Application Owner can issue an owner-side rejection (`owner_rejected → Rejected
By App Owner`) for sub-owner submissions, but cannot perform auditor approval.

## 3. Grounded capability map (from `rbac_legacy_compat.capabilities`)

| Capability | Roles granted (legacy-normalized) |
|------------|-----------------------------------|
| `can_upload_evidence` | owner |
| `can_submit_to_auditor` | owner |
| `can_review_evidence` | auditor, enterprise_admin |
| `can_request_reupload` | auditor |
| `can_export_reports` | owner, auditor, cio, vertical_head, compliance_head, enterprise_admin |
| `can_manage_frameworks` | cio, compliance_head, enterprise_admin, admin |
| `can_assign_owner` | owner, auditor, compliance_head, enterprise_admin |
| `can_escalate` | owner, auditor, cio, vertical_head, compliance_head, enterprise_admin |
| `can_raise_exception` | owner, auditor, compliance_head, cio, vertical_head, enterprise_admin |
| `can_review_framework_onboarding` | auditor, enterprise_admin, admin, cio, compliance_head |
| `can_reuse_evidence_decision` | owner, auditor, cio, compliance_head, enterprise_admin, admin |
| `can_admin_platform` | system_admin, enterprise_admin, admin |

## 4. Canonical permission set (from `rbac_catalog.roles`)

| Role | Permissions | Page |
|------|-------------|------|
| `system_admin` | `*` | `*` |
| `cio` | evidence.read/export, analytics.read, lineage.read, framework.read, rag.read, exception.raise, exception.approve | dashboard.cio |
| `auditor` | evidence.read/review/approve/reject/export, observation.close/reupload, analytics.read, framework.read/review, lineage.read, rag.read, exception.approve | dashboard.auditor |
| `application_owner` | evidence.read/collect/upload/submit, lineage.read, rag.read, exception.raise | dashboard.owner |
| `compliance_officer` | evidence.read/export, analytics.read, framework.read/manage, lineage.read, rag.read, exception.raise | dashboard.compliance |
| `security_officer` | evidence.read, security.read, analytics.read, lineage.read, rag.read | dashboard.security |
| `vertical_head` | evidence.read/export, analytics.read, lineage.read, rag.read | dashboard.vertical |
| `functional_head` | evidence.read/export, analytics.read, lineage.read, rag.read | dashboard.functional |
| `control_owner` | evidence.read/collect, lineage.read, rag.read | — |

## 5. Scope filters (data visibility)

From `rbac.scope_filters` / `rbac_catalog.role_scope`:

| Scope | Filter |
|-------|--------|
| enterprise | no restriction (admin, cio, auditor, compliance, security) |
| vertical | `field: vertical, source: user_assignments` (vertical_head) |
| function | `field: function, source: user_assignments` (functional_head) |
| application | `field: application, source: user_assignments` (application_owner) |
| control | `field: control, source: user_assignments` (control_owner) |
| assigned | `field: application, source: auditor_assignments` |

## 6. Notes on inferred roles
- **Audit Manager / Reviewer / Approver:** ECS implements a single `auditor`
  review role; these are organisational sub-roles over the same capability set
  (recommended as Phase 2 distinct roles with maker-checker separation).
- **CISO / ISG / Risk Team:** governance overlays mapped to
  `security_officer` / `compliance_officer` / `cio` exception authority. RAF/
  exception approval is granted via `exception.approve` + `can_raise_exception`.
