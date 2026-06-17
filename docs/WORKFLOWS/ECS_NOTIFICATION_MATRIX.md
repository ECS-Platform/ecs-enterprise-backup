# ECS Notification Matrix

**Type:** Enterprise / auditor-grade notification reference. No code modified.
**Date:** 2026-06-17
**Grounding:** in-app notifications are implemented as **toasts**
(`evidence_workflow_engine.toast_payload`) and **audit-trail events**
(`audit_trail.log_event`: "Evidence Uploaded", "Predefined Query Executed",
"Observation Closed", etc.). Out-of-band channels (email/Slack/SMS) are
**Inferred Enterprise Workflow** — recommended delivery channels with
enterprise-banking defaults.

**Navigation:** [Workflow Orchestration Guide](ECS_WORKFLOW_ORCHESTRATION_GUIDE.md) ·
[SLA & Escalation](ECS_SLA_ESCALATION_MATRIX.md) ·
[Role Action Matrix](ECS_ROLE_ACTION_MATRIX.md)

---

## 1. Grounded in-app notifications (toasts)

`toast_payload` emits structured messages for: `approved` ("✓ Evidence Approved
Successfully — Observation closed"), `rejected` ("⚠ Evidence Rejected — Re-upload
requested"), `submitted` ("✓ Evidence Submitted To Auditor"), `reupload`
("Re-upload Requested — Returned to App Owner queue"). Each carries
`observation_id`, `framework`, `control`, `action`, and a tone.

## 2. Notification matrix

| Event | Recipient(s) | Trigger | Channel | Frequency | Escalation |
|-------|--------------|---------|---------|-----------|------------|
| Evidence Submitted | Auditor (queue), Owner (ack) | `record_transition "submitted"` | In-app toast (✓) + audit event; email (Inferred) | Immediate | If unreviewed > 5d → Function Head |
| Evidence Rejected | Application Owner | auditor reject / reupload | In-app toast (⚠) + audit event; email (Inferred) | Immediate | ≥3 rejections → Compliance |
| Evidence Approved | Owner, Compliance | `record_transition "approved"` + `close_observations_for_control` | In-app toast (✓) + audit event | Immediate | — |
| Observation Assigned | Assigned Owner | observation assignment | In-app + email (Inferred) | Immediate | Unactioned > 5d → Vertical Head |
| Observation Closed | Owner, Auditor, Compliance | `log_event "Observation Closed"` | In-app + audit event | Immediate | — |
| RAF Raised | ISG / Compliance, CIO | `exception.raise` | In-app + email (Inferred) | Immediate | Pending > 7d → CIO |
| RAF Approved | Owner, Auditor, Risk | `exception.approve` | In-app + audit event | Immediate | On expiry → re-review |
| RAF Rejected | Owner | exception denied | In-app + email (Inferred) | Immediate | → remediation plan |
| Framework Due | Compliance, Owners | assessment window approaching | Email + dashboard banner (Inferred) | Daily digest near due | < target near end → CIO |
| Control Failed | Owner, Security, Auditor | predefined query `Failed` / control non-compliant | In-app + audit event | Immediate | Critical → CISO |
| Audit Started | All in-scope roles | audit kickoff | Email + dashboard (Inferred) | Once | — |
| Audit Completed | Executives, Auditors, Owners | audit sign-off | Email + report distribution (Inferred) | Once | — |

## 3. Channel model

| Channel | Status | Notes |
|---------|--------|-------|
| In-app toast | ✅ Implemented | `toast_payload` structured messages |
| Audit-trail event | ✅ Implemented | `log_event` — durable, queryable |
| Dashboard counters/queues | ✅ Implemented | `build_summary` / `build_queues` |
| Email | ◌ Inferred | recommended via notification service (Phase 2) |
| Slack / Teams | ◌ Inferred | optional ops channel for connector/query failures |
| SMS / Pager | ◌ Inferred | critical findings / audit escalations only |

## 4. Frequency & digest policy (Inferred enterprise defaults)
- **Immediate:** workflow state changes (submit/approve/reject/close, RAF, control
  failure).
- **Daily digest:** pending queues, aging items, frameworks approaching due date.
- **Weekly:** readiness summary to FH/VH/CIO/CISO.
- **De-duplication:** group by `observation_id` / `reuse_group` to avoid noise.

## 5. Recipient resolution
Recipients are resolved through RBAC scope (`role_scope`) and assignment sources
(`user_assignments`, `auditor_assignments`) so each notification reaches only
in-scope actors (e.g. a vertical_head receives only their vertical's events).
