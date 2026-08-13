---
name: ecs-phase3-use-cases
description: ECS Phase 3 use-case status, closeout notes, and known limitations. Use when checking whether a Phase 3 use case is closed, what was fixed in it, or which defects were accepted rather than fixed.
---

# ECS Phase 3 — Use Case Status

Working branch: `team/phase1-phase2`.

| Use case | Title | Status |
| --- | --- | --- |
| UC1 | Automated control validation | Closed |
| UC2 | Cross-application compliance comparison | Closed |
| UC4 | Predefined-query evidence collection & owner/auditor queues | **Closed** (2026-08-13) |

---

## UC4 — Closeout

### What was fixed

**1. Auditor-side queue pagination**

`build_auditor_review_queue()` defaults to `limit=80`. Two call sites took the bare
default while the owner-side equivalents had already been pinned to `limit=500`:

- [demo_metrics.py:158](modules/executive_overview/engines/demo_metrics.py:158) — the
  "Auditor Queue" summary tile.
- [main.py:904](app/main.py:904) — the `/dashboard` context that feeds both the
  auditor KPI cards and `partials/auditor_review_queue.html`.

Both now pass `limit=500` explicitly. The real auditor queue is 76 today, so this
was preemptive: under 80 the truncation is invisible, and past 80 the tile and the
queue's own count would silently disagree — the same failure mode already fixed on
the owner side.

**2. Application Owner Summary strip surfaced**

`role_dashboard_metrics('owner')` has always returned a populated
`Application Owner Summary` payload (`show_strip: True`, pending count,
applications owned, SLA breaches, resubmits), but `dashboard.html` never included
`partials/role_metrics_strip.html`, so the payload was dormant for every role.

[dashboard.html:64](modules/executive_overview/templates/dashboard.html:64) now
includes the strip under an `{% if role == 'owner' %}` guard, at the top of the
overview tab pane. The change is additive — the auditor path renders exactly what
it rendered before.

**3. Predefined-query dedup enrollment — fixed at the source**

Commit `43527a4` patched this at the *call site* of `_duplicate_receipt`, backfilling
`framework` / `control_name` / `workflow_key` onto the receipt after the fact. Two
holes remained:

- The exception / no-enrollment branch set `framework` and `control_name` but never
  `workflow_key`, so a caller reading `receipt["workflow_key"]` hit a `KeyError`.
- Evidence published *before* `control_name` was written onto upload metadata has no
  title on the record, so both the receipt and workflow enrollment fell back to the
  raw control id and the queue row rendered as `ASX-001 ASX-001`.

Both are now fixed inside
[`_duplicate_receipt`](modules/operations/engines/predefined_query_publisher.py:202):

- It always returns `framework`, `control_name`, `control_id`, and `workflow_key`,
  on every branch.
- A new `resolve_control_title()` helper resolves the human-readable title from the
  predefined-query catalog (`technology_control_mapping.get_control`) whenever the
  record carries no better title of its own — so receipts resolve to the title
  regardless of when the underlying evidence was published.
- The resolved title is written back onto the record's metadata *before* enrollment
  runs. Enrollment reads `control_name` from that same metadata, so a pre-fix record
  now produces one key instead of two.

The framework/control-id fallback chain deliberately mirrors
`_control_payload_from_upload` + `resolve_upload_workflow_target`, so the
`workflow_key` on the receipt is byte-identical to the key enrollment registers.

The redundant call-site backfill from `43527a4` was removed. The
`enroll_collected_evidence()` call itself stays — it is a required side effect
(it places the deduplicated evidence into the owner queue) — but now only refreshes
`evidence_version` and `workflow_status`, the two fields enrollment alone knows.

The same `resolve_control_title()` helper also backs the success-path metadata, so a
caller that omits `control_name` no longer seeds another id-only record.

---

## Known Limitations (UC4)

### ASX-001 / EVD-00829 — work queue surfacing under accumulated state

**Accepted, not fixed. Does not block UC4 closure.**

`EVD-00829` (and similar state-dependent cases) surfaces correctly on its own
Evidence tab, but does not reliably surface in the **App Owner → Pending Actions**
work queue.

- **Suspected mechanism:** auto-submit bypass under specific accumulated-state
  conditions — the evidence transitions past the pending state before the queue
  snapshot is taken.
- **Impact:** low. The evidence is retrievable and reviewable via its Evidence tab;
  only the work-queue entry is missing.
- **Reproducibility:** poor. Does not reproduce on a clean process; requires the
  accumulated in-process state of a long-running session.
- **Decision:** documented and accepted. Diagnosis stopped here deliberately. No
  code fix attempted — the fix would be speculative against a defect that cannot be
  reliably reproduced.

Revisit if it recurs on a clean process, or if the auto-submit path is refactored
for other reasons.
