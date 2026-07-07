# ECS Use-Case UAT Readiness Report

**Purpose:** Assess UAT readiness of the 19 ECS enterprise use cases, based on the
verified implementation inventory. States whether each is demo-ready and what (if
anything) is required before live bank-UAT sign-off. No new modules were created
for this report; it reconciles existing implementation.

**Readiness legend:** 🟢 **UAT-ready** (works end-to-end offline/demo; live wiring
is config-only) · 🟡 **Ready with caveat** (functional but demo-seeded or thin
surface) · 🔴 **Blocked** (not usable).

---

## Readiness summary

| # | Use case | Phase | Readiness | Blocking gap for live UAT |
|---|----------|-------|-----------|---------------------------|
| 1 | Automated scheduled evidence pull | 1 | 🟡 | No always-on cron; use manual trigger + dry-run planner. Live pull needs real connector creds + a scheduler/worker if unattended runs are required. |
| 2 | Bulk evidence upload | 1 | 🟢 | None (per-file error detail is thin; single-file API has it). |
| 3 | Metadata tagging & naming convention | 1 | 🟡 | Naming applied at ingest; tag normalization/validation is minimal. |
| 4 | Evidence dashboard & hash integrity | 1 | 🟢 | None for demo; add an interactive re-verify action if auditors need on-read checks. |
| 5 | Common evidence querying | 1 | 🟢 | None. |
| 6 | Evidence completeness detection | 2 | 🟡 | Page uses simpler engine; richer matrix via module-view. No standalone REST. |
| 7 | Evidence similarity & reuse | 2 | 🟡 | Vector similarity used in RAG; reuse score is rule-based/flag-gated. PGVector needs Postgres+pgvector for live semantic reuse. |
| 8 | AI-generated evidence summaries | 2 | 🟡 | Live summaries need an LLM provider (env). Offline fallback works. |
| 9 | Natural language audit queries | 2 | 🟢 | Works with citations; grounding improves with a warm RAG index / provider. |
| 10 | Leadership compliance dashboards | 2 | 🟢 | Two dashboards coexist; some persona widgets use demo metrics. |
| 11 | Multi-application onboarding | 3 | 🟡 | Dual flows (demo + platform DB); no unified transactional API. |
| 12 | Evidence lifecycle management | 3 | 🟡 | Three lifecycle models; `Reviewed`/`Archived` not unified; retention only in platform DB. |
| 13 | Cross-application compliance comparison | 3 | 🟢 | Works (demo data) with export. |
| 14 | SharePoint & ServiceNow integration | 3 | 🟡 | Adapters + health + mock tests ready; live calls need `ECS_GRAPH_*`/`ECS_SERVICENOW_*` from a secret store. |
| 15 | Enterprise compliance dashboards | 3 | 🟡 | Enterprise rollup + audit-intelligence dashboard are separate sources. |
| 16 | Automated regulatory reporting | PI | 🟡 | PDF/Excel/CSV ready; no markdown export; PDFs are summary-level. |
| 17 | AI-assisted audit preparation | PI | 🟡 | Checklist + packs ready; no dedicated AI-prep-notes engine; AI needs provider. |
| 18 | Compliance trend & closure | PI | 🟢 | Works (governance engines, demo-seeded). |
| 19 | National compliance dashboard | PI | 🟢 | Works (server-rendered); no dedicated REST API. |

**Totals:** 🟢 UAT-ready: **8** · 🟡 Ready-with-caveat: **11** · 🔴 Blocked: **0**.

---

## Cross-cutting UAT prerequisites (live bank environment)

These are **operational/environment** items — not product gaps — required before
live UAT for the caveated (🟡) use cases:

1. **Credentials via secret store.** Populate `ECS_GRAPH_*`, `ECS_SERVICENOW_*`,
   `ECS_SHAREPOINT_*`, DB `ECS_*` and LLM provider keys in `.env.uat`/vault
   (never committed). Verify with `scripts/run_uat_connector_health.py` and
   `GET /api/audit/integrations/health` (SET/MISSING only).
2. **Durable persistence.** For UAT that must survive restarts, enable the
   Postgres persistence foundation (`sql_persistence`) + apply
   `docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`; enable PGVector for live similarity.
3. **LLM provider (optional).** Configure a provider for live AI summaries/prep
   notes; otherwise the offline fallback is used.
4. **Auth/RBAC.** Enable auth (`ECS_AUTH_ENABLED=true`) + role mapping; demo mode
   bypasses auth.
5. **Scheduler runner (optional).** If unattended scheduled pulls are in UAT
   scope, wire `enqueue_scheduled_run` + `asset_scheduler.execute_plan` into a
   worker; otherwise use the manual trigger + dry-run.

See [DEVELOPER/UAT_INTEGRATION_GUIDE.md](../connectors/UAT_INTEGRATION_GUIDE.md)
(§ Bank Developer UAT Checklist),
[DEVELOPER/ENTERPRISE_CONNECTOR_UAT_SETUP.md](../connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md),
and [DEVELOPER/PRODUCTION_READINESS_GAP_REGISTER.md](../production/PRODUCTION_READINESS_GAP_REGISTER.md).

---

## Demo-mode UAT smoke (all 19, offline)

```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off
# Platform smoke (imports, routes, adapters, config masking, persistence, env):
PYTHONPATH=. python scripts/run_production_smoke.py --strict
# End-to-end audit-intelligence walkthrough (catalog → run → validation →
# observation → pack → dashboard → integrations):
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py        # expect ALL PASS
# Connector health (config-only; no live calls):
PYTHONPATH=. python scripts/run_uat_connector_health.py --adapter all --no-network
# UAT asset-scheduler dry-run:
PYTHONPATH=. python scripts/run_uat_asset_scheduler.py --dry-run
```
Then walk the UI routes per
[use_case_frontend_manual_testing.md](use_case_frontend_manual_testing.md).

---

## Sign-off checklist (per use case)

For each use case, UAT sign-off = (a) the demo-mode manual test in
[use_case_frontend_manual_testing.md](use_case_frontend_manual_testing.md) passes,
**and** (b) for 🟡 items, the relevant cross-cutting prerequisite above is
provisioned and re-verified against the live target, **and** (c) no secret values
appear in any UI/API/log output. Record results in the change ticket.

---

## Conclusion

All 19 use cases are **implemented** and demo-ready; **none are blocked**. The
remaining work to reach live bank-UAT for the 11 caveated use cases is
**configuration and operations** (credentials, persistence, provider, auth,
optional scheduler), not new feature development. This is consistent with
`docs/archive/FINAL_REPOSITORY_HEALTH_REPORT.md` (repository health **A-**,
UAT-ready pending environment wiring).

Cross references: [use_case_implementation_matrix.md](use_case_implementation_matrix.md) ·
[use_case_backend_api_mapping.md](use_case_backend_api_mapping.md) ·
[use_case_frontend_manual_testing.md](use_case_frontend_manual_testing.md).
