# Missing Mock Data Audit

Every widget/endpoint that previously returned an error, empty payload, or
"unavailable" state, with the failure cause and the fix applied.

| Page | Widget / Endpoint | Failure cause | Fix applied |
|---|---|---|---|
| Audit Prep (and any page drilling `page=audit_prep`) | `rejection_trend`, `pending_aging`, `approval_rate`, `avg_review_time`, `draft`, `submitted`, `reupload` KPI drilldowns | Audit-prep blocks return rows as lists-of-lists; `_normalize_columns` crashed on `list.setdefault` → HTTP 500 ("Failed") | List-rows converted to dicts via `_rows_to_dicts`; metrics absent from the map fall through to the generic generator |
| Main Dashboard / Executive Overview | Auditor SLA, Pending Aging, Rejection Trend, detail popups | Drill chain 500 propagated to the universal modal | Global never-fail `drill_metric` + guarded endpoints → ≥25 rows always |
| Enterprise | Enterprise Compliance, National Score, Open Observations, Frameworks at Risk drilldowns | Empty/error modal on delegated miss | Global fallback returns ≥25 realistic rows for every `page=enterprise` metric |
| Operations → Evidence Explorer | Evidence grid (all personas) | `list_evidence` returned `ok:false` ("Repository unavailable / psycopg2 required") with 0 rows when DB unreachable | `ecs_platform/demo_evidence.py` fallback — 1,200 records, all filters functional |
| Operations → Evidence Explorer | Evidence Relationships (CI/CD chains) | No correlations without DB | `demo_evidence.list_correlations()` — Commit → Build → Sonar → Deploy chains |
| Operations → Integration Health | Connectors table | Real probes returned Down/Disabled with 0 evidence; repo stats empty | Demo connector health for 10 connectors (status, last sync, evidence count, health score) |
| Operations → Integration Health | Total Evidence / Sync Runs / Audit Log | Repo unreachable → zeros/empty | Demo counts (1,200), demo sync runs, demo audit events |
| Any KPI / chart / row / badge click (all pages) | Universal, module, framework, demo, workflow drills | Any unhandled delegated-engine error | Never-fail guards on all 4 drill endpoints + client empty state |

## Deterministic datasets now guaranteed available (no DB / no external service)

Applications · Frameworks · Evidence (1,200 records) · Observations · VAPT findings ·
Audit history · SLA data · Compliance data · AI governance data · Risk data ·
Control data · Operational metrics · Evidence repository records · CI/CD correlations ·
Connector health.

## Verification

- Drill probe: **1,342 combinations → 0 failures** (previously 21 × HTTP 500).
- Evidence Explorer: **1,200 records**, 10 sources, 20 applications; source filters return non-empty subsets.
- Forced-error test: fallback returns **25 rows + friendly note** (never an error).

**Status: COMPLETE.**
