# ECS Use-Case → Backend API / Service Mapping

**Purpose:** For each ECS use case, the concrete backend surface that serves it —
REST route(s), CLI script(s), and the underlying service/engine function. Routes
were verified against the route-registration modules. Only **implemented**
endpoints are listed (no invented endpoints).

**Route registration entry points** (`app/main.py`): `register_mvp_routes`
(`modules/shared/routes/routes_mvp.py`), `register_evidence_routes`
(`app/evidence_routes.py`), `register_governance_routes` (`app/routes_governance.py`),
`register_audit_intelligence_routes` (`modules/audit_intelligence/routes/routes_audit_intelligence.py`),
`register_audit_ui_routes` (`.../routes_audit_ui.py`).

---

## Phase 1

### 1. Automated scheduled evidence pull
| Kind | Surface | Backend function |
|------|---------|------------------|
| CLI | `python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml [--dry-run\|--json\|--strict]` | `asset_scheduler.dry_run()` / `plan_evidence()` / `execute_plan()` |
| REST | `POST /api/audit/runs` (`{scope_kind, scope_value, control_ids?, asset_id?}`) | `evidence_service.start_run()` → `evidence_orchestrator.create_run/execute_run` |
| REST | `POST /api/audit/runs/{run_id}/retry`, `/cancel` | `evidence_orchestrator.retry_run/cancel_run` |
| UI action | `POST /mvp/scheduler/run` (manual trigger) | `scheduler_module.run_scheduled_pull(user)` |
| Engine hooks | (no cron process) | `evidence_orchestrator.enqueue_scheduled_run`, `due_runs` |

### 2. Bulk evidence upload
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI/API | `POST /mvp/upload/bulk` (multipart `files[]`, `framework`, `application`) | `routes_mvp.mvp_bulk_upload` → `evidence_repository.register_upload` |
| API | `POST /evidence/upload` (single, richer metadata; JSON error envelope) | `evidence_api.upload_evidence` |

### 3. Metadata tagging & naming convention
| Kind | Surface | Backend function |
|------|---------|------------------|
| Engine | (applied at upload) | `evidence_repository.enforce_naming(filename, framework, application)` |
| REST | `GET /api/audit/evidence?query=&technology=&framework=&asset_id=&verdict=&tag=` | `audit_repository_service.repository_search` → audit `evidence_repository.search` |
| Model | — | `models.EvidenceArtifact` (`tags`, `frameworks`, `technology`, `asset_id`, `content_hash`) |

### 4. Evidence dashboard & hash integrity check
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/evidence-health` | `evidence_repository.get_health_dashboard` |
| Engine | — | `evidence_repository.compute_hash` (SHA-256), `integrity_check(stored_hash, content)` |
| REST | `GET /api/audit/packs/{pack_type}/{scope}` (pack build, manifest incl. `pack_hash`) | `audit_repository_service` → `evidence_packs.verify_manifest` |
| REST | `GET /api/audit/evidence/{evidence_key}/versions` | audit `evidence_repository.get_versions` |

### 5. Common evidence querying
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/predefined-queries` (filter: search/framework/technology/status) | `predefined_queries_engine.get_predefined_queries_dashboard` |
| UI | `POST /mvp/predefined-queries/run` | `predefined_queries_engine.run_predefined_query(control_id, user)` |
| UI | `GET /mvp/search` (app/framework/owner/status) | `search_module.build_search_discovery` |
| REST | `GET /api/audit/evidence` | `audit_repository_service.repository_search` |
| CLI | `python scripts/run_predefined_query.py --list [--technology T] / --control ID` | `predefined_queries_engine.run_predefined_query` |

## Phase 2

### 6. Evidence completeness detection
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/completeness` | `analytics_module.completeness_report` (page) / `governance_completeness_engine.build_completeness_dashboard` (rich, via `module_capabilities`) |
| Export | `POST /mvp/comparison/export-gaps` | `gap_export_engine.build_gap_export_payload` |

### 7. Evidence similarity & reuse
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/reuse`, `GET /mvp/evidence-reuse-story` | `routes_mvp.get_reuse_graph`, `evidence_reuse_story_engine` |
| Vector | (RAG retrieval) | `pgvector_store.PgVectorStore.search`, `rag._retrieve` (vector-first, keyword fallback) |
| Engine | — | `app/evidence_intel/reuse.score_reuse` (rule-based; flag `EVIDENCE_REUSE_SCORING_ENABLED`); `governance.evidence_reuse` |
| REST | `POST /api/platform/rag/reindex`, `GET /api/platform/rag/status` | `rag.reindex_evidence` |

### 8. AI-generated evidence summaries
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/ai-ops-assistant/summary/{mode}` | `ai_ops_summary_engine.build_summary_page` |
| Engine | — | `llm_engine/provider.LLMProvider` + `generator.ResponseGenerator`; `rag.answer` (offline fallback: `no_evidence`/`fallback`/`error`) |
| API | `POST /chat`, `GET /api/platform/assistant` | `rag.answer` |

### 9. Natural language audit queries
| Kind | Surface | Backend function |
|------|---------|------------------|
| API | `GET /api/platform/assistant?q=&role=&application=&framework=` | `routes_governance.api_assistant` → `rag.answer` (returns `citations`) |
| API | `POST /chat` | `main.chatbot_answer` → `rag.answer` / `chatbot_engine` |
| API | `GET /api/platform/rag/status`, `POST /api/platform/rag/warm` | RAG lifecycle |

### 10. Leadership compliance dashboards
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/audit/executive-readiness` (alias `/mvp/audit/dashboard`) | `dashboard_service.executive_readiness` |
| REST | `GET /api/audit/dashboard`, `GET /api/audit/dashboard/{section}` | `dashboard_service.*` (framework_readiness, open_observations, risk_summary, evidence_freshness, …) |
| UI/REST | `GET /dashboard/cio`; `GET /api/platform/scorecard`, `/executive-summary`, `/audit-readiness` | `enterprise_widgets_context`, `governance.governance_scorecard/executive_summary/audit_readiness` |

## Phase 3

### 11. Multi-application onboarding
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET/POST /mvp/onboarding` | `onboarding_engine.simulate_onboarding` |
| API | `POST /api/onboarding/simulate`, `POST /api/onboarding/export` | `onboarding_engine.simulate_onboarding/export_onboarding_summary` |
| UI (DB) | `GET/POST /mvp/platform/onboarding`, `GET /mvp/platform/inventory` | `governance.onboard_application/list_applications` |
| REST | `GET /api/platform/inventory`; `GET /api/audit/assets`; `GET /api/audit/mapping/*` | `governance.list_applications`; `asset_service`; `mapping_service` |

### 12. Evidence lifecycle management
| Kind | Surface | Backend function |
|------|---------|------------------|
| REST | `POST /api/audit/observations/{obs_id}/transition` (`{to_status, user, note}`) | `observation_generation.transition` (OBS_WORKFLOW) |
| REST | `GET /api/audit/observations`, `/observations/summary` | `observation_generation.list_observations/summary` |
| UI (DB) | `GET/POST /mvp/platform/evidence-lifecycle`, `/review` (`valid_days` retention) | `governance` `_REVIEW_STATES` |
| UI | `GET /mvp/lifecycle` | `analytics_module.lifecycle_timeline` + `audit_trail` |

### 13. Cross-application compliance comparison
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/comparison` | `comparison_engine.build_comparison_dashboard` |
| Export | `POST /mvp/comparison/export-gaps` → `GET /mvp/exports/download/{export_id}` (excel/csv/pdf) | `gap_export_engine.generate_gap_export_file` |

### 14. SharePoint & ServiceNow integration
| Kind | Surface | Backend function |
|------|---------|------------------|
| REST | `GET /api/audit/integrations` (masked config, no secrets) | `integrations.masked_config_all` |
| REST | `GET /api/audit/integrations/health`, `/{name}/health` (e.g. `sharepoint_graph`, `servicenow_cmdb`) | `integrations.health_check_all` / adapter `health_check` |
| CLI | `python scripts/run_uat_connector_health.py --adapter {sharepoint\|servicenow\|all} [--live]` | adapter `is_configured`/`health_check` |
| Engine | — | `sharepoint_graph.SharePointGraphClient.fetch_documents`; `servicenow_cmdb.ServiceNowAdapter.fetch_cis` |

### 15. Enterprise compliance dashboards
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/enterprise` | `analytics_module.enterprise_dashboard` |
| REST | `GET /api/audit/dashboard`; `GET /api/platform/executive-summary` | `dashboard_service.executive_readiness`; `governance.executive_summary` |

## Pan India

### 16. Automated regulatory reporting
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/reports`, `GET /mvp/reports/download/{report_id}?format=pdf\|excel\|csv&framework=&application=` | `reporting_module.list_reports/generate_report_export` |
| UI | `GET /mvp/reports/view/{report_type}` (HTML) | `ecs_reports_engine.build_report` |
| CLI | `python scripts/audit_intelligence_report.py [--section mapping\|assets] [--json]` | `build_mapping_section/build_assets_section` |

### 17. AI-assisted audit preparation
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/audit-prep` | `analytics_module.audit_preparation_checklist`, `audit_prep_data.build_audit_package_preview` |
| REST | `GET /api/audit-prep/kpi-drill`, `/audit-detail`, `/upcoming` | `audit_schedule_engine.*` |
| UI/REST | `GET /mvp/audit/packs`; `GET /api/audit/packs/{pack_type}/{scope}`; `POST /api/audit/packs/application` | `evidence_packs.*` (readiness + `verify_manifest`) |

### 18. Compliance trend & closure
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/trends?framework=&application=&risk_level=&time_period=&region=` | `analytics_module.compliance_trends` (`closure_rate_pct`, `avg_days_to_close`, `aging_buckets`) |
| API | `GET /mvp/api/analytics-intel` | `governance_intelligence.build_contextual_trends` (`repeat_failures`, `remediation_closure_velocity`) |
| Drill | `GET /api/ecs/universal-drill?scope=&page=trends` | `trends_drill_engine.drill_trends_kpi` |

### 19. National compliance dashboard
| Kind | Surface | Backend function |
|------|---------|------------------|
| UI | `GET /mvp/pan-india?role=cio&user=CIO` | `routes_mvp.mvp_pan_india` → `enterprise_mock_service.build_pan_india_posture`, `module_capabilities._pan_india_view` |
| Data | — | `ecs_state.PAN_INDIA_REGIONS`; `analytics_module.enterprise_dashboard` (`national_score`, `regions`) |

---

## Notes on configuration (no hardcoded secrets)

All connector targets/credentials resolve from env / YAML (`.env.example`,
`config/environments/*.yaml`, `config/uat_assets.template.yaml`): e.g.
`ECS_GRAPH_*`, `ECS_SERVICENOW_*`, `ECS_SHAREPOINT_*`, DB `ECS_*` vars. Masked
config endpoints show `SET`/`MISSING` only. LLM provider selection is env-driven
(`ecs_platform/llm_engine/provider.py`) with an offline fallback.

Cross references: [use_case_implementation_matrix.md](use_case_implementation_matrix.md) ·
[use_case_frontend_manual_testing.md](use_case_frontend_manual_testing.md) ·
[use_case_uat_readiness_report.md](use_case_uat_readiness_report.md) ·
[API/ECS_API_REFERENCE.md](../../../../03-development/developer-manual/ECS_API_REFERENCE.md).
