# ECS Demo Data Rationalization

**Status:** Implemented (scoped, referentially-safe change) + recommendations
**Scope:** Demo-data realism only. No routes, APIs, UI templates, navigation, or business
functionality were added or removed.
**Owner:** Demo / Product enablement
**Last updated:** 2026-06-21

---

## 1. Objective

Make ECS demo data look like a *real* bank's evidence-collection programme: controls,
frameworks, and applications should carry **distinct, internally-consistent** values —
different readiness percentages, evidence counts, applications, findings, observations,
open gaps, audit histories, and framework mappings — instead of repeating identical
placeholder values.

The hard constraint is **referential integrity**: a number shown in one place (e.g. a
control's status in the Control Library) must agree with the same control's state shown
elsewhere (the Control Breakdown, the dashboard rejection table, drilldowns). Improving
"realism" by fabricating disconnected numbers would *reduce* trust, not increase it.

This document records:
1. How ECS demo data is actually generated (grounded in code).
2. Measured realism gaps (with evidence).
3. The change that was implemented and why it is safe.
4. Before/after measurements.
5. Recommendations for the remaining gaps, ranked by risk.

---

## 2. How ECS demo data is generated (current architecture)

ECS demo data is **not** seeded from a single fixture file. It is produced by layered,
deterministic generators. Understanding the layers is essential before changing anything.

| Layer | Source | What it produces | Determinism |
|-------|--------|------------------|-------------|
| **Catalog (source of truth)** | `modules/frameworks/engines/framework_catalog.py` → `FRAMEWORK_CATALOG` | 15 frameworks, ~305 controls, ~700 evidence records. Each control's evidences are **hand-authored** (`evidence_specs`) with explicit application, server, owner, reviewer, status, timestamps. | Static literals |
| **Applications** | `modules/shared/services/ecs_mock_engine.py` → `list_banking_applications()` | Per-app `audit_readiness_pct`, `evidence_count`, `pending_observations`, framework count. | Seeded (`_seed`, `_between`) |
| **Framework rollups** | `ecs_mock_engine.list_frameworks_catalog()` | Per-framework `readiness_pct`, `control_count`, `evidence_count`, `audit_cycle`. | Avg of owner apps + seed fallback |
| **Workflow state** | `app/ecs_state.py` populated by `modules/executive_overview/engines/demo_seed.py` (`seed_demo_workflow_state`, `seed_workflow_targets`) | Which controls are approved / submitted / rejected / escalated. **83 approved, 77 submitted, 10 rejected** at startup. | Deterministic targets |
| **Framework graph** | `framework_dashboards.get_framework_graph()` | Per-framework `controls` + `findings` (with `linked_control`, `application`, `severity`). | Seeded |
| **Per-control views** | `framework_dashboards.build_control_library()` / `build_control_breakdown()` | The Control Library table and the Control Breakdown drill table. | Derived |
| **Framework workflow ranges** | `framework_workflow_engine._FW_RANGES` | Per-framework draft/submitted/approved/findings/readiness ranges (already differentiated, e.g. PCI 78–92, DPSC 82–94). | Seeded ranges |

**Key takeaway:** the *catalog* and *application* layers are already realistic and varied.
The realism problems live in the **derived per-control view** and in one **referential
mismatch** in the framework graph.

---

## 3. Measured realism gaps (evidence)

All numbers below were measured against the running app (`DEMO_MODE=1`, startup seeding
applied) prior to the change.

### 3.1 Control Library was uniform — **primary gap**

`build_control_library()` derived status purely from a catalog `validation` field that
defaults to `PENDING`, and it ignored the runtime workflow state. Result:

```
PCI DSS  (17 controls): status = {Pending: 17}    evidence = {2: 17}        finding = {0: 17}
DPSC     (19 controls): status = {Pending: 19}    evidence = {2: 13, 3: 6}  finding = {0: 19}
OS Base. (18 controls): status = {Pending: 18}    evidence = {2: 12, 3: 6}  finding = {0: 18}
```

Every control rendered as **Pending / Medium / 0 findings**, and the Control Library table
(`partials/framework_drill_panels.html`) colours every `Pending` row yellow — so the whole
table looked identical.

### 3.2 This was also an internal **inconsistency**

The *same* controls, viewed through `build_control_breakdown()` (which **does** read
`ecs_state`), showed realistic variation:

```
PCI DSS  build_control_breakdown: {Approved: 5, Pending Auditor Validation: 4, Draft: 8}
DPSC     build_control_breakdown: {Approved: 5, Pending Auditor Validation: 5, Draft: 8, Rejected — Remediation: 1}
```

So ECS already *knew* these controls were approved/submitted/rejected — the Control Library
simply wasn't reflecting it. This is a referential-integrity defect, not just cosmetics.

### 3.3 Finding → control linkage is broken in the framework graph

Graph findings reference control IDs that **do not exist** in the catalog:

```
PCI DSS:  graph finding linked_control = ['PCI-7.2', 'PCI-8.3']
          catalog control_ids          = ['PCI-C01' … 'PCI-C17']   → 0 matches
DPSC:     graph finding linked_control = ['DP-C-04']
          catalog control_ids          = ['DPS-C01' … 'DPS-C19']   → 0 matches
```

Consequences: the Control Library Finding Count is always `0`, and clicking a finding's
linked control drills to a non-existent control. (Addressed by recommendation R2 below — not
changed in code in this pass because the graph findings feed multiple drilldowns and warrant
a dedicated, separately-tested change.)

### 3.4 Per-framework readiness is nearly uniform

`list_frameworks_catalog()` computes `readiness_pct` as the average readiness of a
framework's owner applications. Because most frameworks map to an overlapping app set, the
averages cluster:

```
Distinct framework readiness values across 15 frameworks: [50.2, 51.3, 51.5, 52.6, 54.5]
```

(Addressed by recommendation R1 — not changed in this pass to avoid touching the executive
dashboard rollups and their tests.)

### 3.5 What was already realistic (left untouched)

- **Per-application data** is well-varied: readiness 45–69%, evidence 28–212,
  pending observations 4–16, framework count 3–7.
- **Catalog evidence** is hand-authored per control (distinct applications, servers, owners,
  statuses, timestamps, regions, versions).
- **Framework workflow ranges** (`_FW_RANGES`) are already differentiated per framework.
- **Control Breakdown / rejection table** already reflect real workflow state.

---

## 4. Change implemented

**File:** `modules/frameworks/engines/framework_dashboards.py` — `build_control_library()`
**Nature:** derive the per-control view from the **same runtime workflow state** the rest of
the framework view already uses, and correlate findings / gaps / readiness with that state.

### 4.1 Status & risk — now sourced from real workflow state

Resolution order (mirrors `build_control_breakdown()` so the two views agree):

| Condition (real state) | Status | Risk |
|------------------------|--------|------|
| `ckey ∈ ecs_state.approved_controls` or catalog validation PASS/APPROVED | **Approved** | Low |
| `ckey ∈ rejected/escalated_controls` or validation FAIL/REJECTED | **Failed** | High |
| `ckey ∈ submitted_controls` | **Submitted** | Medium |
| no evidence | **Pending** | Medium |
| otherwise (has evidence, not yet submitted) | **Draft** | Medium |

### 4.2 Findings / observations / open gaps — correlated with status

Findings start from the real linked-finding count and are made consistent with the resolved
status (a failed control has open findings; an approved control has none), with a stable
per-control seed (`_seed_int(control_id + "fnd", …)`):

| Status | Open findings (= open_gaps = observation_count) |
|--------|--------------------------------------------------|
| Approved | real linked findings only (typically 0) |
| Submitted | `max(real, 0–1)` |
| Draft | `max(real, 0–2)` |
| Pending | `max(real, 0–1)` |
| Failed | `max(real, 1–4)` — always ≥ 1 |

### 4.3 Per-control readiness — new, banded by status

Each control now carries a deterministic `readiness_pct`, banded by status so the number is
coherent with the control's posture:

| Status | Readiness band |
|--------|----------------|
| Approved | 88–99 |
| Submitted | 72–86 |
| Draft | 60–78 |
| Pending | 48–68 |
| Failed | 28–52 |

`open_gaps`, `observation_count`, and `readiness_pct` are **additive** fields. They make the
row self-describing for drilldowns/APIs that read these rows and do not remove or rename any
existing field, so existing consumers and templates are unaffected.

### 4.4 Why this is referentially safe

- Status is the **same state** that drives the Control Breakdown, the dashboard rejection
  table, and approvals — so all views now agree.
- Findings are **never positive for an approved control** and **always positive for a failed
  control** — a coherent story.
- Everything is **deterministic** (MD5-seeded), so values are stable across reloads and
  across the two views.
- No existing field was removed or renamed; the change is additive plus a status correction.

---

## 5. Before / after (measured)

```
                     BEFORE (uniform)                AFTER (control-specific, consistent)
PCI DSS    status   {Pending: 17}                    {Approved: 5, Submitted: 4, Draft: 8}
           risk     {Medium: 17}                      {Low: 5, Medium: 12}
           findings {0: 17}                           {0: 8, 1: 4, 2: 5}
           readiness (not present)                    63–98, 14 distinct values

DPSC       status   {Pending: 19}                     {Approved: 5, Submitted: 5, Draft: 8, Failed: 1}
           risk     {Medium: 19}                       {Low: 5, Medium: 13, High: 1}
           findings {0: 19}                            {0: 10, 1: 7, 2: 1, 4: 1}
           readiness (not present)                     47–99, 17 distinct values

OS Base.   status   {Pending: 18}                      {Approved: 5, Submitted: 5, Draft: 8}
           findings {0: 18}                            {0: 9, 1: 8, 2: 1}
           readiness (not present)                     60–98, 15 distinct values
```

Consistency checks (all pass):
- Control Library status distribution now equals the Control Breakdown distribution.
- No `Approved` control has `finding_count > 0`.
- Values are deterministic across repeated calls.

---

## 6. Validation performed

- `build_control_library()` re-measured for PCI DSS / DPSC / OS Baselining — varied,
  consistent, deterministic (Section 5).
- Framework page rendered end-to-end: `GET /framework/PCI%20DSS` → **200**, Control Library
  table present.
- Regression suite: ran `tests/` filtered to framework/dashboard/drill/control plus the
  governance / enterprise-drilldown / ROI suites **with and without** the change. The change
  introduces **no new failures** — every failure observed (enterprise-drilldown uniqueness
  assertions, ROI center counts, the RBAC parity matrix, and the
  `test_nav_module_present_on_framework_and_dashboard` navigation assertion) reproduces
  identically on the pre-change baseline and is unrelated to demo data.
- No linter errors in the edited file.

---

## 7. Recommendations (remaining gaps — not changed in this pass)

These are documented for a follow-up, separately-tested change. They were intentionally left
out of this pass because they touch shared rollups/graph generators consumed by many
screens.

### R1 — Differentiate per-framework readiness (`list_frameworks_catalog`)
**Gap:** only 5 distinct readiness values across 15 frameworks (§3.4).
**Recommended approach:** blend the owner-app average with a framework-specific signal that
already exists and is referentially grounded — e.g. the framework's approved-control ratio
from `ecs_state`, and/or the per-framework readiness band already defined in
`framework_workflow_engine._FW_RANGES`. This produces a realistic 68–94% spread tied to real
state.
**Risk:** Medium — feeds executive dashboards; `test_ecs_platform_governance` /
`test_enterprise_drilldown_validation` assert framework-metric uniqueness, so re-baseline
those tests as part of the change.

### R2 — Fix finding → control linkage in `get_framework_graph`
**Gap:** graph findings reference non-existent control IDs (§3.3), so Finding Counts are
forced to 0 and finding→control drills break.
**Recommended approach:** generate finding `linked_control` values from the actual catalog
`control_id` pool for the framework (deterministically), so findings attach to real controls.
Then `build_control_library` can use real linked findings directly instead of the
status-correlated fallback in §4.2.
**Risk:** Medium — graph findings feed `ecs_row_drill_engine`, `application_governance`, and
the framework findings panel; validate those drilldowns after the change.

### R3 — Audit-history variety
Audit history is generated centrally (`generate_audit_trail`). It is already varied by
action/date; if more per-control audit depth is wanted, key audit events off each control's
resolved status (Approved → "Evidence Approved", Failed → "Finding Raised") for a tighter
control→history story.

---

## 8. Constraints honoured

- ✅ No routes added, removed, or modified.
- ✅ No API contracts changed (additive row fields only).
- ✅ No UI templates / CSS / navigation changed.
- ✅ No new business functionality.
- ✅ Referential integrity preserved (Control Library now *agrees* with Control Breakdown).
- ✅ Deterministic — reproducible demo runs.
- ✅ Change confined to one derived demo-data function; no source-of-truth catalog edits.
