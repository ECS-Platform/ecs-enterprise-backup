# Evidence Reuse & Observation Lifecycle — Manual Testing Guide

**Status:** Current · **Owner:** Audit Intelligence
**Companion:** [`evidence_reuse_lifecycle_functional_design.md`](evidence_reuse_lifecycle_functional_design.md)

Step-by-step manual test cases for the **functional** Evidence Reuse &
Observation Lifecycle page. All actions run real server-side logic against the
evidence repository + observation engine. Only *Generate observations* and *Check
closure* mutate state (via the real, maker-checker-safe observation workflow).

---

## 0. Prerequisites

1. Start ECS (demo mode is fine):
   ```bash
   PYTHONPATH=. DEMO_MODE=true uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Open the page: **`http://localhost:8000/mvp/evidence-story`**
3. You should see a **Functional Workbench** panel at the top (teal border) with
   filters, six action buttons, a KPI strip, and a result area — followed by the
   original narrative sections.

### Sample evidence data
On a fresh process the repository is auto-seeded from the narrative (3 records:
DB-001 PostgreSQL, APP-001 SonarQube, OS-001 Linux). To test with your own data,
collect evidence via the normal evidence-run / predefined-query flow first; the
workbench then reflects those real records.

### KPIs
- **Evidence Records** — count matching current filters.
- **Reuse Factor** — obligations ÷ unique evidence.
- **Audit Readiness** — covered ÷ total obligations.
- **Open Observations** / **Ready for Closure** — from the real observation store.

---

## 1. Refresh evidence (retrieval + integrity)

- **URL:** `/mvp/evidence-story`
- **Prerequisite:** none (seeded).
- **Steps:** Click **Refresh evidence**.
- **Expected server-side action:** `GET /api/evidence-reuse/records`; table lists
  evidence keys, control, technology, application, verdict, **Integrity =
  verified** (sha256), collected timestamp.
- **Expected closure readiness:** n/a.
- **Pass/fail:** Pass if records render and Integrity shows `verified` for seeded
  records; **Evidence Records** KPI matches the row count.

## 2. Filter evidence

- **Steps:** Set **Status = FAIL**, click **Refresh evidence**. Then try
  **Control = DB-001**, **Technology = PostgreSQL**, or a **date range**.
- **Expected:** Only matching records appear; the KPI updates. `Status=PASS` and
  `Status=FAIL` return disjoint subsets.
- **Pass/fail:** Pass if filtering changes the result set consistently.

## 3. Run reuse analysis

- **Steps:** Click **Run reuse analysis**.
- **Expected server-side action:** `POST /api/evidence-reuse/analyze`; shows
  “N evidence records satisfy M framework obligations — reuse factor X×,
  K collections avoided (Hh saved)”, plus an Evidence→Framework matrix.
- **Pass/fail:** Pass if reuse factor ≥ 1 and the matrix lists framework rows;
  **Reuse Factor** KPI updates.

## 4. Validate completeness

- **Steps:** Click **Validate completeness**.
- **Expected server-side action:** `POST /api/evidence-reuse/validate-completeness`;
  per-framework drill-downs with each control marked **covered / failed / stale /
  missing** and a reason; a summary badge (COMPLETE or N gaps).
- **Pass/fail:** Pass if failing/violating controls show as `failed` and satisfied
  controls show as `covered`.

## 5. Refresh audit readiness

- **Steps:** Click **Refresh audit readiness**.
- **Expected server-side action:** `GET /api/evidence-reuse/readiness`; overall %
  + per-framework covered/total.
- **Pass/fail:** Pass if the **Audit Readiness** KPI and table agree.

## 6. Generate observations

- **Prerequisite:** at least one gap (e.g. `Status=FAIL` shows a violation, or a
  missing control).
- **Steps:** Click **Generate observations**.
- **Expected server-side action:** `POST /api/evidence-reuse/generate-observations`;
  “Created N observation(s); skipped K already-open”. New rows list observation ID,
  control, severity, status **Draft**.
- **Expected observation creation:** observations appear in the real store; the
  **Open Observations** KPI increases.
- **Idempotency:** click again → **Created 0**, skipped increases (no duplicates).
- **Pass/fail:** Pass if observations are created once and de-duplicated on re-run.

## 7. Check closure eligibility (maker-checker ON)

- **Prerequisite:** an open observation whose control now has **passing** evidence.
  To simulate: after step 6, collect passing evidence for that control (new
  version), or use the seeded satisfied control (OS-001).
- **Steps:** Ensure **Require maker-checker approval** is checked; click **Check
  closure eligibility**.
- **Expected server-side action:** `POST /api/evidence-reuse/check-closure?require_approval=true`;
  eligible observations shown as **READY FOR CLOSURE** (status **Submitted**).
- **Expected closure readiness:** **Closed = 0**, **Ready ≥ 1**; the observation is
  **not** auto-closed. The **Ready for Closure** KPI increases.
- **Pass/fail:** Pass if eligible observations are marked ready but remain open
  (Submitted), preserving the audit trail.

## 8. Check closure eligibility (maker-checker OFF)

- **Steps:** Uncheck **Require maker-checker approval**; click **Check closure
  eligibility**.
- **Expected:** `require_approval=false`; eligible observations advance to
  **Closed** (**Closed ≥ 1**).
- **Pass/fail:** Pass if eligible observations close and the audit trail records
  the transitions.

## 9. Error handling

- **Steps:** Set an impossible filter (e.g. **Technology = DoesNotExist**) and run
  any action.
- **Expected:** Empty result rendered safely ("No evidence records match"), no
  stack trace, KPIs show 0. If a backend error occurs, a warning banner shows a
  safe message only.
- **Pass/fail:** Pass if errors/empties are handled gracefully with no secret or
  stack-trace leakage.

---

## 10. Overall pass criteria

- Records load from the **real** repository with `verified` integrity.
- Reuse factor, readiness, and gaps reflect the filtered evidence.
- Observations are created via the real engine, de-duplicated, and visible in the
  KPIs and (existing) `/mvp/audit/observations` page.
- Closure respects maker-checker: **ready, not auto-closed** when approval is
  required; **closed** when not — always preserving the audit trail.

## 11. REST equivalents (automation)

```bash
curl "localhost:8000/api/evidence-reuse/records?status=FAIL"
curl -X POST "localhost:8000/api/evidence-reuse/analyze"
curl -X POST "localhost:8000/api/evidence-reuse/validate-completeness"
curl -X POST "localhost:8000/api/evidence-reuse/generate-observations"
curl -X POST "localhost:8000/api/evidence-reuse/check-closure?require_approval=true"
curl "localhost:8000/api/evidence-reuse/readiness"
curl "localhost:8000/api/evidence-reuse/observations"
```
