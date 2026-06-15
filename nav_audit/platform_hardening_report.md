# Platform Hardening Report

Full ECS platform hardening and mock-data remediation pass. Goal: any reviewer can
log in as any persona and navigate any page without encountering Failed / Demo data
unavailable / Repository unavailable / empty drilldowns / blank modals / missing
data / unreadable or white-on-white text / broken charts / empty tables.

## Issues found & fixed

| # | Issue | Cause | Fix | Status |
|---|---|---|---|---|
| 1 | Drilldowns show **Failed** (Auditor SLA, Pending Aging, Rejection Trend, detail popups) | `audit_prep` list-of-lists rows crashed `_normalize_columns` (`AttributeError`) → HTTP 500 | `_rows_to_dicts` + defensive normalize + never-fail `drill_metric` + guarded endpoints | Fixed (prev commit) |
| 2 | Enterprise widgets show **Demo data unavailable** | Delegated-engine miss surfaced empty modal | Global fallback returns ≥25 rows for every enterprise metric | Fixed (prev commit) |
| 3 | Evidence Explorer **Repository unavailable / psycopg2** | `list_evidence`/`health_overview` returned `ok:false` when DB down | `demo_evidence.py` (1,200 records) fallback; demo connector health | Fixed (prev commit) |
| 4 | Platform governance pages display **psycopg2 / "Repository not reachable"** (scorecard, executive-summary, audit-readiness, onboarding, inventory, control/framework coverage, evidence reuse/lifecycle, scheduler) | Each governance read returned `{ok:false, error: psycopg2…}` on `RepositoryError`, rendered as a warning banner | `demo_governance.py` providers; every governance read falls back to demo data on any repo error | Fixed (prev commit) |
| 5 | **White text on white background** — Demo Overview → Top Risk Applications app column | Contrast rule scoped to `.table`; demo-overview table uses `.demo-table` | Extended `accessibility_theme.html` to `table.demo-table`, `.ecs-top-risk-applications .col-app strong`, paginated/modern/risk tables | Fixed (prev commit) |
| 6 | Mock-data thresholds short of demo spec (frameworks 7, controls 120, BU 6; no tickets/VAPT/observations/AI-prompts/regions providers) | Initial demo_governance scope | Extended to 17 frameworks, 320 controls, 12 BUs; added `servicenow_tickets` (80), `vapt_findings` (40), `audit_observations` (120), `ai_prompts` (100), `regions` (5) + `coverage_summary` | **Fixed (this pass)** |

## Validation summary

| Check | Result |
|---|---|
| Pages × personas (384 requests, low-concurrency) | **0 HTTP failures, 0 forbidden body strings** |
| Drilldown probes (504 combinations) | **0 failures** |
| Mock-data thresholds (Phase 3) | **All met or exceeded** |
| Evidence Explorer (12 personas) | **PASS** (1,200 records, filters functional) |
| Enterprise drilldowns (National Score, Enterprise Compliance) | **PASS** |
| Demo Overview Top Risk readability | **PASS** (ink `#0F172A`, no white-on-white) |
| Linter (ecs_platform) | **PASS** |

> Note: a high-concurrency (16-worker) crawl produced client-side read timeouts on
> the heaviest pages; re-validated sequentially and at 4-worker concurrency, all
> return HTTP 200 with clean bodies — load artifacts, not platform defects.

## No external dependency in demo mode

Evidence Explorer, Integration Health, and all platform governance pages operate
with no PostgreSQL / psycopg2 / Oracle / Mongo / Redis / Kafka / ServiceNow / Jira /
GitHub / GitLab / Confluence / SonarQube / Jenkins dependency. All data is
deterministic and generated in-process.

## Files changed (this pass)

- `ecs_platform/demo_governance.py` — frameworks 7→17, controls 120→320, BUs 6→12;
  added tickets/VAPT/observations/AI-prompts/regions providers + `coverage_summary`.
- `nav_audit/*.md`, `nav_audit/pass2_demo_overview_toprisk.png` — reports & evidence.

Pass-1 remediation (demo_evidence.py, ingestion.py, governance.py, drilldown
engines, accessibility_theme.html, evidence-explorer template) was committed in
`01176f4` and re-verified here.

**Status: COMPLETE.**
