# Evidence Reuse & Observation Lifecycle — Functional Design

**Status:** Current · **Owner:** Audit Intelligence · **Page:** `/mvp/evidence-story`

This document describes how the *Evidence Reuse & Observation Lifecycle* page was
converted from a **static/demo narrative** into a page that executes **real
server-side logic** against the evidence repository and observation engine.

The change is **orchestration only** — it reuses existing engines and does **not**
duplicate evidence, validation, observation, predefined-query, or workflow code.

---

## 1. What was static before

The page rendered a single deterministic dict from
`modules/operations/engines/evidence_reuse_story_engine.py`:

- Exactly three hard-coded controls (DB-001, APP-001, OS-001).
- Synthetic evidence + inline reuse/readiness/observation computation.
- No filters, no interactivity, no persisted observations, no integrity check.

That narrative is still shown (it is a good executive story), but a **Functional
Workbench** now sits above it and runs real logic.

---

## 2. Building blocks reused (no duplication)

| Concern | Reused module | Used for |
| --- | --- | --- |
| Evidence records + hashing | `engines/evidence_repository.py` (`search`, `all_latest`, `store_evidence`, `EvidenceArtifact.content_hash`) | Real evidence retrieval + integrity |
| Control/framework mapping | `engines/technology_control_mapping.py` (`frameworks_for_control`, `controls_for_framework`, `get_control`) | Reuse obligations + readiness scope |
| Validation model | `models.ValidationResult` | Input to observation generation |
| Observation engine | `engines/observation_generation.py` (`generate_observation`, `list_observations`, `transition`, `summary`) | Create + advance + close observations |
| Narrative seed | `engines/evidence_reuse_story_engine.py` | Seed the repository when empty |

New orchestration layer: **`modules/audit_intelligence/services/evidence_reuse_service.py`**.
New REST surface: **`/api/evidence-reuse/*`** in `routes_audit_intelligence.py`.
Enhanced template: **`modules/operations/templates/mvp_evidence_reuse_story.html`**.

---

## 3. Server-side capabilities

All actions operate on **real repository records**. When the repository is empty
(fresh process), `ensure_seeded()` writes the narrative evidence into the real
repository via `store_evidence()` — so every action runs against genuine
`EvidenceArtifact` records, not a parallel store. `ensure_seeded()` is idempotent.

### 3.1 Evidence retrieval (`records`)
- Latest version of every evidence key from `evidence_repository.search()`.
- Filters: **application** (tag `app:` / asset), **framework**, **control**,
  **technology**, **status** (verdict PASS/FAIL/WARNING), **date range**
  (`collected_at`).
- Each record carries an `integrity` block (`sha256` hash present + checksum
  consistency → `verified` / `unverified` / `no-hash`) and `stale` (older than
  `STALE_AFTER_DAYS = 90`).

### 3.2 Reuse analysis (`analyze`)
- For each evidence record, counts the **framework obligations** it satisfies
  (evidence `frameworks`, falling back to the control→framework mapping).
- Computes: `unique_evidence`, `reuse_count` (obligations), `reuse_factor`
  (`obligations / unique_evidence`), `frameworks_covered`, `controls_covered`,
  `collections_saved`, `effort_saved_hours` (`collections_saved × 4h`), and the
  most-reused evidence.

### 3.3 Completeness + readiness (`validate_completeness`, `readiness`)
- Obligation scope is **evidence-driven** by default (the controls that have
  evidence, evaluated across each framework they claim). `full_catalog=true`
  widens the scope to every catalog control mapped to the in-scope frameworks.
- Per control state: **covered** (evidence exists, satisfied, not stale),
  **failed** (present but not satisfied), **stale** (older than the threshold),
  **missing** (no evidence).
- Readiness = covered / total obligations, per framework and overall.

### 3.4 Observation creation (`generate_observations`)
- For each gap (missing/failed/stale) builds a `ValidationResult` and calls the
  **real** `observation_generation.generate_observation()` — same store, severity,
  workflow, and audit trail as the rest of ECS.
- **De-duplicates:** a control+framework that already has an *open* observation is
  skipped, never re-created.

### 3.5 Closure eligibility (`check_closure`)
- An open observation is *closure-eligible* when the latest evidence for its
  control now **satisfies** it.
- With **maker-checker** (`require_approval=true`, default): the observation is
  advanced to **Submitted** and marked **READY FOR CLOSURE** — it is **not**
  auto-closed (a checker must approve).
- Without approval gating: the observation is advanced through the existing
  workflow to **Closed**.
- Every step uses the engine's `transition()`, so the **audit trail is preserved**
  in the observation `history`.

### 3.6 Observation views (`observations`)
- Current **open** and **ready-for-closure** (Submitted) observations plus the
  engine `summary()`.

---

## 4. Workflow (unchanged engine)

```
Draft ──▶ Submitted ──▶ Approved ──▶ Remediated ──▶ Closed
  │           │            │
  └── Rejected┘◀───────────┘
```

- Maker-checker safe: `check_closure(require_approval=true)` stops at **Submitted**.
- `require_approval=false` completes Draft→Submitted→Approved→Remediated→Closed.

---

## 5. REST API

| Method + Path | Purpose |
| --- | --- |
| `GET /api/evidence-reuse/records` | Real evidence records + filters + integrity |
| `POST /api/evidence-reuse/analyze` | Reuse matrix + reuse factor + effort saved |
| `POST /api/evidence-reuse/validate-completeness` | Covered / missing / stale / failed obligations |
| `POST /api/evidence-reuse/generate-observations` | Create observations for gaps (deduped) |
| `POST /api/evidence-reuse/check-closure` | Advance satisfied observations (maker-checker safe) |
| `GET /api/evidence-reuse/readiness` | Covered vs total controls, per framework |
| `GET /api/evidence-reuse/observations` | Open + ready-for-closure observations |

Common query params: `application, framework, control, technology, status,
date_from, date_to`. Extra: `full_catalog` (completeness/readiness/generate),
`require_approval` (check-closure).

Responses use the standard audit envelope (`{"ok": true, ...}` / `{"ok": false,
"errors": [...]}`); errors never leak internals.

---

## 6. Frontend

The existing page template gained a **Functional Workbench** section (above the
narrative) with:

- Filter inputs (application, framework, control, technology, status, date range)
  and a maker-checker toggle.
- Six action buttons → the six functional endpoints.
- A live KPI strip (records, reuse factor, readiness, open observations, ready for
  closure), server-rendered initially and updated after each action.
- A result panel that renders evidence tables, reuse matrix, completeness drill,
  readiness, generated observations, and closure results — plus a raw-JSON toggle.
- Safe error display (no stack traces / secrets).

The original narrative sections (Evidence → Reuse → Readiness → Observations)
remain unchanged.

---

## 7. Safety

- **No secrets / credentials** anywhere — the evidence repository stores metadata +
  a SHA-256 hash only.
- **Read-only** except *Generate observations* and *Check closure*, which use the
  real observation workflow (and are maker-checker safe).
- The functional layer is wrapped so it can **never break the page** — if it is
  unavailable the narrative still renders.

---

## 8. Tests

`tests/test_evidence_reuse_lifecycle.py` covers evidence retrieval + filters +
integrity, reuse analysis, completeness/gaps, observation generation + dedupe,
closure (ready-not-closed with approval, closed without approval, not-eligible),
all seven API routes, and the page render. See
`docs/evidence_reuse_frontend_manual_testing.md` for manual steps.
