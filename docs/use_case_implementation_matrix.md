# ECS Use-Case Implementation Matrix

**Purpose:** Map each of the 19 ECS enterprise use cases to its **existing**
implementation in the repository, with an honest status, the concrete source
files, and the exposed route/CLI. Produced by direct code inspection (no
assumptions). ECS is feature-complete; this matrix is a reconciliation, not a
redesign — it introduces no duplicate modules.

**Status legend:** ✅ **EXISTS** (end-to-end) · 🟡 **PARTIAL** (core present; demo/
CLI-only or split across stacks) · ⛳ **MISSING**.

> Architectural note: ECS maintains two evidence layers by design — the **MVP/demo
> stack** (`modules/operations/engines/evidence_repository.py`, in-memory upload +
> hash + health) and the **audit-intelligence stack**
> (`modules/audit_intelligence/engines/evidence_repository.py`, versioned artifacts
> + search + packs + orchestrator). Several use cases are satisfied by one or both.
> No use case is fully MISSING.

---

## Phase 1

| # | Use case | Status | Primary implementation | Exposure (route / CLI) |
|---|----------|--------|------------------------|------------------------|
| 1 | Automated scheduled evidence pull | 🟡 | `modules/audit_intelligence/services/asset_scheduler.py` (`classify_asset`, `plan_evidence`, `dry_run`, `execute_plan`); `evidence_orchestrator.enqueue_scheduled_run`/`due_runs`; `modules/operations/engines/scheduler_module.py` (`run_scheduled_pull`) | CLI `scripts/run_uat_asset_scheduler.py [--dry-run\|--json]`; UI `GET /mvp/scheduler` + `POST /mvp/scheduler/run`; REST `POST /api/audit/runs` |
| 2 | Bulk evidence upload | ✅ | `modules/shared/routes/routes_mvp.py` (`mvp_bulk_upload`); `modules/shared/services/evidence_api.py` (`upload_evidence`); `modules/operations/engines/evidence_repository.py` (`register_upload`) | UI `GET /mvp/upload`, `POST /mvp/upload/bulk`; API `POST /evidence/upload` |
| 3 | Metadata tagging & naming convention | 🟡 | `evidence_repository.enforce_naming` (`{PREFIX}_{APP}_{YYYYMMDD}_{file}`); `models.EvidenceArtifact.tags`; audit `evidence_repository.search(tag=,framework=,technology=,asset_id=)` | API `GET /api/audit/evidence?tag=&framework=&technology=`; `GET /api/audit/repository` |
| 4 | Evidence dashboard & hash integrity check | 🟡 | `evidence_repository.compute_hash`/`integrity_check` (SHA-256); audit `evidence_repository._hash_content`; `evidence_packs.verify_manifest`; `get_health_dashboard` | UI `GET /mvp/evidence-health`; pack verify via `GET /api/audit/packs/{pack_type}/{scope}` |
| 5 | Common evidence querying | ✅ | `predefined_queries_engine.get_predefined_queries_dashboard`/`filter_controls`/`run_predefined_query`; `governance/engines/search_module.build_search_discovery` | UI `GET /mvp/predefined-queries`, `GET /mvp/search`; API `GET /api/audit/evidence`; CLI `scripts/run_predefined_query.py` |

## Phase 2

| # | Use case | Status | Primary implementation | Exposure (route / CLI) |
|---|----------|--------|------------------------|------------------------|
| 6 | Evidence completeness detection | 🟡 | `governance/engines/governance_completeness_engine.build_completeness_dashboard`; `missing_evidence_engine.generate_missing_evidence`/`compute_completeness_pct`; `analytics_module.completeness_report` | UI `GET /mvp/completeness`; gap export `POST /mvp/comparison/export-gaps` |
| 7 | Evidence similarity & reuse | 🟡 | `ecs_platform/vectorstore/pgvector_store.PgVectorStore` (+ `factory.get_vector_store`); `ecs_platform/rag._retrieve`; `app/evidence_intel/reuse.score_reuse`; `evidence_repository._link_reuse` | UI `GET /mvp/reuse`, `GET /mvp/evidence-reuse-story`; RAG `POST /api/platform/rag/reindex` |
| 8 | AI-generated evidence summaries | 🟡 | `ecs_platform/llm_engine/provider.LLMProvider` (gemini/openai/azure/ollama) + `generator.ResponseGenerator`; `ecs_platform/rag.answer` (offline fallback modes); `ai_ops_summary_engine.build_summary_page` | UI `GET /mvp/ai-ops-assistant/summary/{mode}`; RAG answer via `/chat`, `/api/platform/assistant` |
| 9 | Natural language audit queries | ✅ | `ecs_platform/rag.answer` (citations: `evidence_uid`, `source_system`, `frameworks`, `controls`); `chatbot_engine`/`chatbot_enhanced`; `governance.governance_qa` fallback | API `GET /api/platform/assistant`, `POST /chat`; status `GET /api/platform/rag/status` |
| 10 | Leadership compliance dashboards | ✅ | `dashboard_service.executive_readiness`/`framework_readiness`/`open_observations`/`risk_summary`/`evidence_freshness`; `analytics_module.enterprise_dashboard`; `governance.governance_scorecard` | UI `GET /mvp/audit/executive-readiness`, `GET /dashboard/cio`; API `GET /api/audit/dashboard`, `GET /api/platform/scorecard` |

## Phase 3

| # | Use case | Status | Primary implementation | Exposure (route / CLI) |
|---|----------|--------|------------------------|------------------------|
| 11 | Multi-application onboarding | 🟡 | `operations/engines/onboarding_engine.simulate_onboarding`; `ecs_platform/governance.onboard_application`/`list_applications`; `asset_discovery.*`; `asset_scheduler.load_assets` (`config/uat_assets.template.yaml`) | UI `GET/POST /mvp/onboarding`, `GET/POST /mvp/platform/onboarding`; API `POST /api/onboarding/simulate`; CLI `scripts/run_uat_asset_scheduler.py` |
| 12 | Evidence lifecycle management | 🟡 | `observation_generation` `OBS_WORKFLOW` (Draft→Submitted→Approved→Remediated→Closed\|Rejected); `ecs_platform/governance` `_REVIEW_STATES` (+`Expired`, `valid_days` retention); `app/evidence_intel/models.EvidenceStatus`; `audit_trail` | UI `GET /mvp/lifecycle`, `GET/POST /mvp/platform/evidence-lifecycle`; API `POST /api/audit/observations/{id}/transition` |
| 13 | Cross-application compliance comparison | ✅ | `governance/engines/comparison_engine.build_comparison_dashboard`/`build_readiness_matrix`/`build_heatmap_cards`; `analytics_module.application_comparison` | UI `GET /mvp/comparison`; export `POST /mvp/comparison/export-gaps` → `GET /mvp/exports/download/{id}` |
| 14 | SharePoint & ServiceNow integration | 🟡 | `integrations/sharepoint_graph.py` (`SharePointGraphClient`), `integrations/servicenow_cmdb.py` (`ServiceNowAdapter`, OAuth/Basic); registry `integrations/__init__.py` (`health_check_all`) | API `GET /api/audit/integrations`, `/health`, `/{name}/health`; CLI `scripts/run_uat_connector_health.py` |
| 15 | Enterprise compliance dashboards | 🟡 | `dashboard_service.executive_readiness`; `analytics_module.enterprise_dashboard` (`national_score`, `regions`, `kpis`); `governance.executive_summary` | UI `GET /mvp/enterprise`; API `GET /api/audit/dashboard`, `GET /api/platform/executive-summary` |

## Pan India

| # | Use case | Status | Primary implementation | Exposure (route / CLI) |
|---|----------|--------|------------------------|------------------------|
| 16 | Automated regulatory reporting | 🟡 | `executive_overview/engines/reporting_module.list_reports`/`generate_report_export` (PDF/Excel/CSV; incl. `pan-india` report def); `ecs_reports_engine.build_report` | UI `GET /mvp/reports`, `GET /mvp/reports/download/{id}?format=`; CLI `scripts/audit_intelligence_report.py` |
| 17 | AI-assisted audit preparation | 🟡 | `governance/engines/analytics_module.audit_preparation_checklist`; `audit_prep_data.build_audit_package_preview`; `audit_intelligence/engines/evidence_packs.*` (readiness + `verify_manifest`) | UI `GET /mvp/audit-prep`, `GET /mvp/audit/packs`; API `/api/audit-prep/*`, `GET /api/audit/packs/{pack_type}/{scope}` |
| 18 | Compliance trend & closure | ✅ | `governance/engines/analytics_module.compliance_trends` (`closure_rate_pct`, `avg_days_to_close`, `aging_buckets`); `governance_intelligence.build_contextual_trends` (`repeat_failures`, `remediation_closure_velocity`); `trends_analytics_engine` | UI `GET /mvp/trends`; API `GET /mvp/api/analytics-intel` |
| 19 | National compliance dashboard | ✅ | `executive_overview/templates/mvp_pan_india.html`; `enterprise_mock_service.build_pan_india_posture`; `executive_analytics_engine.enhance_pan_india_regions`; `ecs_state.PAN_INDIA_REGIONS` | UI `GET /mvp/pan-india` |

---

## Summary

- **EXISTS (end-to-end): 8** — #2, #5, #9, #10, #13, #18, #19 (and #4 dashboard portion).
- **PARTIAL: 11** — core logic present but demo/CLI-only, split across the two
  stacks, or missing a thin REST/UI surface. None require a new module; each is an
  *extension* opportunity on existing code.
- **MISSING: 0** — no capability is absent.

**Highest-overlap zones (extend, never duplicate):** completeness (pick
`governance_completeness_engine` over `analytics_module.completeness_report`),
evidence repository (MVP vs audit-intelligence), scheduler (wire
`enqueue_scheduled_run` + `asset_scheduler` into a frequency runner), and
enterprise/national rollups (`dashboard_service` vs `analytics_module`).

See also: [use_case_backend_api_mapping.md](use_case_backend_api_mapping.md),
[use_case_frontend_manual_testing.md](use_case_frontend_manual_testing.md),
[use_case_uat_readiness_report.md](use_case_uat_readiness_report.md).
