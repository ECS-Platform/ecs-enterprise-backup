# Evidence Rejection Traceability

**Surface reviewed:** Main Dashboard → Evidence tab → **Evidence Rejections** table (`/dashboard?role=owner|auditor`).
**Data model:** `modules.operations.engines.resubmission.init_rejection()` writes
`ecs_state.rejected_controls["<Framework>::<Control>"] = {reason, rejected_by, rejected_at, internal, resubmission_stage}` (later augmented with `team_resubmission_requested` / `revised_uploaded` / `reevaluated`).
**Template:** `modules/executive_overview/templates/dashboard.html` (scoped class `ecs-rejections-table`).

## Required vs. available rejection context

| Required field | Available in record? | Shown after fix | Notes |
|---|---|---|---|
| Rejection Reason | ✅ `reason` (full sentence) | ✅ (wrapped + tooltip) | Already fixed previously (column readability) |
| Rejecting User | ✅ `rejected_by` | ✅ | — |
| Timestamp | ✅ `rejected_at` (UTC) | ✅ **added** ("Rejected At") | Populated by `init_rejection()` |
| Control ID | ✅ (key suffix `::Control`) | ✅ | Derived from the row key |
| Framework | ✅ (key prefix `Framework::`) | ✅ | Derived from the row key |
| Workflow State | ✅ `resubmission_stage` | ✅ **added** ("Workflow State") | e.g. Owner Review, Team Resubmission, Reevaluate, Ready Resubmit |
| Evidence ID | ❌ not stored on the rejection record | — (documented) | Evidence IDs exist elsewhere (AI-SDLC controlled docs) but are **not** linked to these dashboard rejections; not fabricated |
| Observation ID | ❌ not stored on the rejection record | — (documented) | Same as above; would require a new data linkage (out of scope — would be new functionality) |

## Fix applied (this pass)

The Evidence Rejections table previously showed only **Framework · Control · Reason · Rejected By**. It now also shows the **Rejected At** timestamp and **Workflow State**, both already present in the record — so each rejection carries its full available context:

- Added `<th class="rej-col-when">Rejected At</th>` and `<th class="rej-col-state">Workflow State</th>`.
- Added the corresponding cells: `{{ info.rejected_at|default('—') }}` and `{{ (info.resubmission_stage|default('—'))|replace('_',' ')|title }}`.
- Rebalanced the scoped column widths (12/19/31/13/14/11) and updated the empty-state `colspan` 4 → 6.

All selectors remain scoped to `.ecs-rejections-table` (used only by this table on this page); no shared component, no other dashboard, and no backend logic was changed.

## No-fabrication guarantees

- **Reason** is the real seeded/recorded sentence (e.g. *"Evidence package incomplete for &lt;control&gt;: reviewer requires updated production artefact and signed attestation."*) — not a generic placeholder. The 5 governance "rejection reason" categories in `governance_intelligence.REJECTION_REASONS` are a separate analytics breakdown and are not substituted here.
- **Evidence ID / Observation ID** are intentionally **omitted rather than invented** — they are not part of the rejection record. Linking them would be new functionality, which is out of scope for this trustability pass.
- Duplicate reasons are not collapsed or duplicated; each row is a distinct `Framework::Control` rejection.

## Verdict

✅ Every rejection record now displays its complete **available** context (Reason, Rejecting User, Timestamp, Control, Framework, Workflow State). Missing linkages (Evidence ID / Observation ID) are documented as a future data-model enhancement, not faked.
