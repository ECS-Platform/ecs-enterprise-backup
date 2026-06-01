# ECS Module Migration Report

**Date:** 2026-06-01  
**Status:** Complete — validation passed

## Summary

| Metric | Count |
|--------|-------|
| Python files moved | 98 |
| Template files moved | 149 |
| Compatibility shims in `app/` | 98 |
| Import rewrites (files updated) | 98 |
| Route handlers preserved | 188 |
| Critical tests passed | 87 / 87 |

## Validation Results

### Post-migration smoke (`scripts/validate_post_migration.py`)
- All MVP pages return HTTP 200
- All framework pages return HTTP 200
- All AI SDLC pages return HTTP 200
- Left-nav groups present (Executive, Frameworks, Operations, Governance, Enterprise GRC)
- Drill APIs functional (universal, workflow, framework KPI, module KPI, AI SDLC posture)
- Module imports verified (`modules.shared`, `modules.frameworks`, `modules.ai_sdlc`)

### Critical test suites (inline runner, no pytest required)
- `test_ecs_platform_governance` — PASS
- `test_framework_kpi_drilldowns` — PASS
- `test_enterprise_drilldown_validation` — PASS
- `test_ai_sdlc_control_tower` — PASS
- `test_ai_ops_assistant` — PASS
- `test_ecs_demo_readiness` — PASS
- `test_demo_polish` — PASS
- `test_module_kpi_drill` — PASS
- `test_top_risk_application_rendering` — PASS

**Total: 87 tests, 0 failures**

### Unchanged (by design)
- All URLs and routes
- `app/main.py`, `app/routes_*.py`, `app/evidence_routes.py` remain bootstrap entry points
- Mock datasets and workflow logic unchanged
- `app/*.py` shims preserve `from app.X` imports for backward compatibility

## Module Structure Created

```
modules/
├── executive_overview/engines/ + templates/
├── frameworks/engines/ + templates/
├── operations/engines/ + templates/
├── governance/engines/ + templates/
├── enterprise_grc/engines/ + templates/
├── ai_sdlc/engines/ + templates/
└── shared/
    ├── services/      (ecs_state, enterprise_context, chatbot, workflow)
    ├── drilldowns/    (universal drill, module KPI drill)
    ├── utils/         (demo_data_standards, pagination, filters)
    └── templates/partials/
```

Jinja2 template loader updated in `app/main.py` to use `ChoiceLoader` across all module template directories.

---

- `app/demo_kpi_drill_engine.py` → `modules/executive_overview/engines/demo_kpi_drill_engine.py`
- `app/demo_metrics.py` → `modules/executive_overview/engines/demo_metrics.py`
- `app/demo_seed.py` → `modules/executive_overview/engines/demo_seed.py`
- `app/executive_analytics_engine.py` → `modules/executive_overview/engines/executive_analytics_engine.py`
- `app/ecs_reports_engine.py` → `modules/executive_overview/engines/ecs_reports_engine.py`
- `app/reporting_module.py` → `modules/executive_overview/engines/reporting_module.py`
- `app/enterprise_mock_service.py` → `modules/executive_overview/engines/enterprise_mock_service.py`
- `app/integration_hub_executive_engine.py` → `modules/executive_overview/engines/integration_hub_executive_engine.py`
- `app/framework_catalog.py` → `modules/frameworks/engines/framework_catalog.py`
- `app/framework_dashboards.py` → `modules/frameworks/engines/framework_dashboards.py`
- `app/framework_governance_context.py` → `modules/frameworks/engines/framework_governance_context.py`
- `app/framework_governance_data.py` → `modules/frameworks/engines/framework_governance_data.py`
- `app/framework_intelligence.py` → `modules/frameworks/engines/framework_intelligence.py`
- `app/framework_kpi_drill_engine.py` → `modules/frameworks/engines/framework_kpi_drill_engine.py`
- `app/framework_loader_service.py` → `modules/frameworks/engines/framework_loader_service.py`
- `app/framework_onboarding_engine.py` → `modules/frameworks/engines/framework_onboarding_engine.py`
- `app/framework_trends_engine.py` → `modules/frameworks/engines/framework_trends_engine.py`
- `app/framework_workflow_engine.py` → `modules/frameworks/engines/framework_workflow_engine.py`
- `app/ecs_row_drill_engine.py` → `modules/frameworks/engines/ecs_row_drill_engine.py`
- `app/itpp_module.py` → `modules/frameworks/engines/itpp_module.py`
- `app/control_validation_engine.py` → `modules/frameworks/engines/control_validation_engine.py`
- `app/application_governance.py` → `modules/frameworks/engines/application_governance.py`
- `app/scheduler_module.py` → `modules/operations/engines/scheduler_module.py`
- `app/scheduler_intelligence.py` → `modules/operations/engines/scheduler_intelligence.py`
- `app/operations_intelligence.py` → `modules/operations/engines/operations_intelligence.py`
- `app/operations_catalog.py` → `modules/operations/engines/operations_catalog.py`
- `app/operations_filter_engine.py` → `modules/operations/engines/operations_filter_engine.py`
- `app/operations_mock_data.py` → `modules/operations/engines/operations_mock_data.py`
- `app/onboarding_engine.py` → `modules/operations/engines/onboarding_engine.py`
- `app/integrations_module.py` → `modules/operations/engines/integrations_module.py`
- `app/integration_health_engine.py` → `modules/operations/engines/integration_health_engine.py`
- `app/ai_ops_assistant_engine.py` → `modules/operations/engines/ai_ops_assistant_engine.py`
- `app/ai_ops_summary_engine.py` → `modules/operations/engines/ai_ops_summary_engine.py`
- `app/evidence_repository.py` → `modules/operations/engines/evidence_repository.py`
- `app/resubmission.py` → `modules/operations/engines/resubmission.py`
- `app/audit_schedule_engine.py` → `modules/governance/engines/audit_schedule_engine.py`
- `app/audit_prep_data.py` → `modules/governance/engines/audit_prep_data.py`
- `app/analytics_module.py` → `modules/governance/engines/analytics_module.py`
- `app/evidence_review.py` → `modules/governance/engines/evidence_review.py`
- `app/evidence_approval_engine.py` → `modules/governance/engines/evidence_approval_engine.py`
- `app/evidence_health_engine.py` → `modules/governance/engines/evidence_health_engine.py`
- `app/governance_completeness_engine.py` → `modules/governance/engines/governance_completeness_engine.py`
- `app/governance_data_enrichment.py` → `modules/governance/engines/governance_data_enrichment.py`
- `app/governance_intelligence.py` → `modules/governance/engines/governance_intelligence.py`
- `app/governance_lifecycle_engine.py` → `modules/governance/engines/governance_lifecycle_engine.py`
- `app/governance_relational_model.py` → `modules/governance/engines/governance_relational_model.py`
- `app/governance_mock_data.py` → `modules/governance/engines/governance_mock_data.py`
- `app/missing_evidence_engine.py` → `modules/governance/engines/missing_evidence_engine.py`
- `app/search_module.py` → `modules/governance/engines/search_module.py`
- `app/comparison_engine.py` → `modules/governance/engines/comparison_engine.py`
- `app/gap_export_engine.py` → `modules/governance/engines/gap_export_engine.py`
- `app/workflow_module.py` → `modules/governance/engines/workflow_module.py`
- `app/operational_workflows.py` → `modules/governance/engines/operational_workflows.py`
- `app/operational_mock_data.py` → `modules/governance/engines/operational_mock_data.py`
- `app/exception_state_engine.py` → `modules/governance/engines/exception_state_engine.py`
- `app/grc_module_demo.py` → `modules/enterprise_grc/engines/grc_module_demo.py`
- `app/grc_demo_service.py` → `modules/enterprise_grc/engines/grc_demo_service.py`
- `app/enterprise_grc.py` → `modules/enterprise_grc/engines/enterprise_grc.py`
- `app/correlation_engine.py` → `modules/enterprise_grc/engines/correlation_engine.py`
- `app/ecs_governance_drilldowns.py` → `modules/enterprise_grc/engines/ecs_governance_drilldowns.py`
- `app/ecs_governance_qa_engine.py` → `modules/enterprise_grc/engines/ecs_governance_qa_engine.py`
- `app/ecs_governance_framework.py` → `modules/enterprise_grc/engines/ecs_governance_framework.py`
- `app/ecs_demo_remediation.py` → `modules/enterprise_grc/engines/ecs_demo_remediation.py`
- `app/ai_sdlc_governance_service.py` → `modules/ai_sdlc/engines/ai_sdlc_governance_service.py`
- `app/ai_sdlc_governance_mock.py` → `modules/ai_sdlc/engines/ai_sdlc_governance_mock.py`
- `app/ai_sdlc_control_tower_engine.py` → `modules/ai_sdlc/engines/ai_sdlc_control_tower_engine.py`
- `app/ai_sdlc_onboarding_engine.py` → `modules/ai_sdlc/engines/ai_sdlc_onboarding_engine.py`
- `app/ai_sdlc_workflow_engine.py` → `modules/ai_sdlc/engines/ai_sdlc_workflow_engine.py`
- `app/ai_sdlc_workflow_store.py` → `modules/ai_sdlc/engines/ai_sdlc_workflow_store.py`
- `app/ai_sdlc_reports_engine.py` → `modules/ai_sdlc/engines/ai_sdlc_reports_engine.py`
- `app/ai_sdlc_knowledge_repository.py` → `modules/ai_sdlc/engines/ai_sdlc_knowledge_repository.py`
- `app/ai_sdlc_document_artifacts.py` → `modules/ai_sdlc/engines/ai_sdlc_document_artifacts.py`
- `app/ecs_ai_governance_drilldowns.py` → `modules/ai_sdlc/engines/ecs_ai_governance_drilldowns.py`
- `app/ecs_sdlc_stage_dashboard.py` → `modules/ai_sdlc/engines/ecs_sdlc_stage_dashboard.py`
- `app/ecs_state.py` → `modules/shared/services/ecs_state.py`
- `app/ecs_mock_engine.py` → `modules/shared/services/ecs_mock_engine.py`
- `app/enterprise_context.py` → `modules/shared/services/enterprise_context.py`
- `app/module_capabilities.py` → `modules/shared/services/module_capabilities.py`
- `app/module_workspace.py` → `modules/shared/services/module_workspace.py`
- `app/nav_counter_engine.py` → `modules/shared/services/nav_counter_engine.py`
- `app/ecs_nav_framework.py` → `modules/shared/services/ecs_nav_framework.py`
- `app/role_permissions.py` → `modules/shared/services/role_permissions.py`
- `app/role_filter_scope.py` → `modules/shared/services/role_filter_scope.py`
- `app/audit_trail.py` → `modules/shared/services/audit_trail.py`
- `app/ecs_logging.py` → `modules/shared/services/ecs_logging.py`
- `app/chatbot_engine.py` → `modules/shared/services/chatbot_engine.py`
- `app/chatbot_context_engine.py` → `modules/shared/services/chatbot_context_engine.py`
- `app/chatbot_nav.py` → `modules/shared/services/chatbot_nav.py`
- `app/chatbot_enhanced.py` → `modules/shared/services/chatbot_enhanced.py`
- `app/evidence_api.py` → `modules/shared/services/evidence_api.py`
- `app/evidence_workflow_engine.py` → `modules/shared/services/evidence_workflow_engine.py`
- `app/ecs_universal_drill_engine.py` → `modules/shared/drilldowns/ecs_universal_drill_engine.py`
- `app/module_kpi_drill_engine.py` → `modules/shared/drilldowns/module_kpi_drill_engine.py`
- `app/demo_data_standards.py` → `modules/shared/utils/demo_data_standards.py`
- `app/global_filter_engine.py` → `modules/shared/utils/global_filter_engine.py`
- `app/standard_filter_engine.py` → `modules/shared/utils/standard_filter_engine.py`
- `app/pagination.py` → `modules/shared/utils/pagination.py`
- `app/table_schemas.py` → `modules/shared/utils/table_schemas.py`

## Templates moved

- `app/templates/dashboard.html` → `modules/executive_overview/templates/dashboard.html`
- `app/templates/cio_dashboard.html` → `modules/executive_overview/templates/cio_dashboard.html`
- `app/templates/dashboard_vertical_head.html` → `modules/executive_overview/templates/dashboard_vertical_head.html`
- `app/templates/dashboard_compliance_head.html` → `modules/executive_overview/templates/dashboard_compliance_head.html`
- `app/templates/dashboard_functional_head.html` → `modules/executive_overview/templates/dashboard_functional_head.html`
- `app/templates/mvp_demo_overview.html` → `modules/executive_overview/templates/mvp_demo_overview.html`
- `app/templates/mvp_enterprise.html` → `modules/executive_overview/templates/mvp_enterprise.html`
- `app/templates/mvp_pan_india.html` → `modules/executive_overview/templates/mvp_pan_india.html`
- `app/templates/mvp_reports.html` → `modules/executive_overview/templates/mvp_reports.html`
- `app/templates/mvp_ecs_report.html` → `modules/executive_overview/templates/mvp_ecs_report.html`
- `app/templates/mvp_trends.html` → `modules/executive_overview/templates/mvp_trends.html`
- `app/templates/login.html` → `modules/executive_overview/templates/login.html`
- `app/templates/framework.html` → `modules/frameworks/templates/framework.html`
- `app/templates/framework_loader.html` → `modules/frameworks/templates/framework_loader.html`
- `app/templates/mvp_framework_admin.html` → `modules/frameworks/templates/mvp_framework_admin.html`
- `app/templates/mvp_scheduler.html` → `modules/operations/templates/mvp_scheduler.html`
- `app/templates/mvp_bulk_upload.html` → `modules/operations/templates/mvp_bulk_upload.html`
- `app/templates/mvp_integrations.html` → `modules/operations/templates/mvp_integrations.html`
- `app/templates/mvp_integrations_hub.html` → `modules/operations/templates/mvp_integrations_hub.html`
- `app/templates/mvp_onboarding.html` → `modules/operations/templates/mvp_onboarding.html`
- `app/templates/mvp_ai_ops_assistant.html` → `modules/operations/templates/mvp_ai_ops_assistant.html`
- `app/templates/mvp_ai_ops_summary.html` → `modules/operations/templates/mvp_ai_ops_summary.html`
- `app/templates/mvp_audit_prep.html` → `modules/governance/templates/mvp_audit_prep.html`
- `app/templates/mvp_evidence_health.html` → `modules/governance/templates/mvp_evidence_health.html`
- `app/templates/mvp_reuse.html` → `modules/governance/templates/mvp_reuse.html`
- `app/templates/mvp_lifecycle.html` → `modules/governance/templates/mvp_lifecycle.html`
- `app/templates/mvp_completeness.html` → `modules/governance/templates/mvp_completeness.html`
- `app/templates/mvp_comparison.html` → `modules/governance/templates/mvp_comparison.html`
- `app/templates/mvp_search.html` → `modules/governance/templates/mvp_search.html`
- `app/templates/mvp_evidence_approval.html` → `modules/governance/templates/mvp_evidence_approval.html`
- `app/templates/evidence_review.html` → `modules/governance/templates/evidence_review.html`
- `app/templates/mvp_workflow_close_gap.html` → `modules/governance/templates/mvp_workflow_close_gap.html`
- `app/templates/mvp_workflow_assign_owner.html` → `modules/governance/templates/mvp_workflow_assign_owner.html`
- `app/templates/mvp_workflow_upload_missing.html` → `modules/governance/templates/mvp_workflow_upload_missing.html`
- `app/templates/mvp_workflow_mock_audit.html` → `modules/governance/templates/mvp_workflow_mock_audit.html`
- `app/templates/mvp_risk_register.html` → `modules/enterprise_grc/templates/mvp_risk_register.html`
- `app/templates/mvp_exceptions.html` → `modules/enterprise_grc/templates/mvp_exceptions.html`
- `app/templates/mvp_exception_governance.html` → `modules/enterprise_grc/templates/mvp_exception_governance.html`
- `app/templates/mvp_cmdb.html` → `modules/enterprise_grc/templates/mvp_cmdb.html`
- `app/templates/mvp_regulatory.html` → `modules/enterprise_grc/templates/mvp_regulatory.html`
- `app/templates/mvp_heatmaps.html` → `modules/enterprise_grc/templates/mvp_heatmaps.html`
- `app/templates/mvp_correlation.html` → `modules/enterprise_grc/templates/mvp_correlation.html`
- `app/templates/mvp_governance_analytics.html` → `modules/enterprise_grc/templates/mvp_governance_analytics.html`
- `app/templates/mvp_ai_sdlc_home.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_home.html`
- `app/templates/mvp_ai_sdlc_control_tower.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_control_tower.html`
- `app/templates/mvp_ai_sdlc_onboarding.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_onboarding.html`
- `app/templates/mvp_ai_sdlc_worklist.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_worklist.html`
- `app/templates/mvp_sdlc_gates.html` → `modules/ai_sdlc/templates/mvp_sdlc_gates.html`
- `app/templates/mvp_sdlc_gate_stage.html` → `modules/ai_sdlc/templates/mvp_sdlc_gate_stage.html`
- `app/templates/mvp_ai_governance_posture.html` → `modules/ai_sdlc/templates/mvp_ai_governance_posture.html`
- `app/templates/mvp_ai_registry.html` → `modules/ai_sdlc/templates/mvp_ai_registry.html`
- `app/templates/mvp_governance_quality.html` → `modules/ai_sdlc/templates/mvp_governance_quality.html`
- `app/templates/mvp_ai_sdlc_reports.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_reports.html`
- `app/templates/mvp_ai_sdlc_report.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_report.html`
- `app/templates/mvp_ai_sdlc_evidence_viewer.html` → `modules/ai_sdlc/templates/mvp_ai_sdlc_evidence_viewer.html`
- `app/templates/partials/enterprise_theme.html` → `modules/shared/templates/partials/enterprise_theme.html`
- `app/templates/partials/mvp_styles.html` → `modules/shared/templates/partials/mvp_styles.html`
- `app/templates/partials/ecs_sidebar.html` → `modules/shared/templates/partials/ecs_sidebar.html`
- `app/templates/partials/mvp_sidebar.html` → `modules/shared/templates/partials/mvp_sidebar.html`
- `app/templates/partials/ecs_nav_groups.html` → `modules/shared/templates/partials/ecs_nav_groups.html`
- `app/templates/partials/ecs_nav_shell.js.html` → `modules/shared/templates/partials/ecs_nav_shell.js.html`
- `app/templates/partials/ecs_nav_ai_sdlc.html` → `modules/shared/templates/partials/ecs_nav_ai_sdlc.html`
- `app/templates/partials/nav_badge.html` → `modules/shared/templates/partials/nav_badge.html`
- `app/templates/partials/ecs_ux_macros.html` → `modules/shared/templates/partials/ecs_ux_macros.html`
- `app/templates/partials/ecs_ux_system.html` → `modules/shared/templates/partials/ecs_ux_system.html`
- `app/templates/partials/mvp_workspace_macros.html` → `modules/shared/templates/partials/mvp_workspace_macros.html`
- `app/templates/partials/mvp_workspace_styles.html` → `modules/shared/templates/partials/mvp_workspace_styles.html`
- `app/templates/partials/mvp_capability_styles.html` → `modules/shared/templates/partials/mvp_capability_styles.html`
- `app/templates/partials/mvp_module_header.html` → `modules/shared/templates/partials/mvp_module_header.html`
- `app/templates/partials/mvp_module_actions.html` → `modules/shared/templates/partials/mvp_module_actions.html`
- `app/templates/partials/mvp_quick_links.html` → `modules/shared/templates/partials/mvp_quick_links.html`
- `app/templates/partials/role_metrics_strip.html` → `modules/shared/templates/partials/role_metrics_strip.html`
- `app/templates/partials/chatbot_global.html` → `modules/shared/templates/partials/chatbot_global.html`
- `app/templates/partials/ecs_floating_action_portal.html` → `modules/shared/templates/partials/ecs_floating_action_portal.html`
- `app/templates/partials/enterprise_widgets.html` → `modules/shared/templates/partials/enterprise_widgets.html`
- `app/templates/partials/workflow_styles.html` → `modules/shared/templates/partials/workflow_styles.html`
- `app/templates/partials/workflow_guidance.html` → `modules/shared/templates/partials/workflow_guidance.html`
- `app/templates/partials/ecs_universal_drill.html` → `modules/shared/templates/partials/ecs_universal_drill.html`
- `app/templates/partials/ecs_module_kpi_drill.html` → `modules/shared/templates/partials/ecs_module_kpi_drill.html`
- `app/templates/partials/ecs_pagination.html` → `modules/shared/templates/partials/ecs_pagination.html`
- `app/templates/partials/ecs_executive_table_system.html` → `modules/shared/templates/partials/ecs_executive_table_system.html`
- `app/templates/partials/ecs_top_risk_table_fix.html` → `modules/shared/templates/partials/ecs_top_risk_table_fix.html`
- `app/templates/partials/ecs_governance_table_framework.html` → `modules/shared/templates/partials/ecs_governance_table_framework.html`
- `app/templates/partials/ecs_governance_table_macros.html` → `modules/shared/templates/partials/ecs_governance_table_macros.html`
- `app/templates/partials/executive_charts_system.html` → `modules/shared/templates/partials/executive_charts_system.html`
- `app/templates/partials/executive_chart_macros.html` → `modules/shared/templates/partials/executive_chart_macros.html`
- `app/templates/partials/executive_chart_card.html` → `modules/shared/templates/partials/executive_chart_card.html`
- `app/templates/partials/compact_chart.html` → `modules/shared/templates/partials/compact_chart.html`
- `app/templates/partials/analytics_macros.html` → `modules/shared/templates/partials/analytics_macros.html`
- `app/templates/partials/evidence_upload_modal.html` → `modules/shared/templates/partials/evidence_upload_modal.html`
- `app/templates/partials/raise_exception_modal.html` → `modules/shared/templates/partials/raise_exception_modal.html`
- `app/templates/partials/evidence_workflow_macros.html` → `modules/shared/templates/partials/evidence_workflow_macros.html`
- `app/templates/partials/evidence_workflow_system.html` → `modules/shared/templates/partials/evidence_workflow_system.html`
- `app/templates/partials/analytics_filter_bar.html` → `modules/shared/templates/partials/analytics_filter_bar.html`
- `app/templates/partials/standard_filter_include.html` → `modules/shared/templates/partials/standard_filter_include.html`
- `app/templates/partials/standard_filter_client.html` → `modules/shared/templates/partials/standard_filter_client.html`
- `app/templates/partials/executive_dashboard_client.html` → `modules/shared/templates/partials/executive_dashboard_client.html`
- `app/templates/partials/page_workflow_queue.html` → `modules/shared/templates/partials/page_workflow_queue.html`
- `app/templates/partials/leadership_work_queue.html` → `modules/shared/templates/partials/leadership_work_queue.html`
- `app/templates/partials/auditor_review_queue.html` → `modules/shared/templates/partials/auditor_review_queue.html`
- `app/templates/partials/owner_work_queue.html` → `modules/shared/templates/partials/owner_work_queue.html`
- `app/templates/partials/framework_executive_strip.html` → `modules/frameworks/templates/partials/framework_executive_strip.html`
- `app/templates/partials/framework_executive_extras.html` → `modules/frameworks/templates/partials/framework_executive_extras.html`
- `app/templates/partials/framework_drill_panels.html` → `modules/frameworks/templates/partials/framework_drill_panels.html`
- `app/templates/partials/framework_relational_evidence.html` → `modules/frameworks/templates/partials/framework_relational_evidence.html`
- `app/templates/partials/framework_workflow_table.html` → `modules/frameworks/templates/partials/framework_workflow_table.html`
- `app/templates/partials/framework_governance_panel.html` → `modules/frameworks/templates/partials/framework_governance_panel.html`
- `app/templates/partials/framework_application_grid.html` → `modules/frameworks/templates/partials/framework_application_grid.html`
- `app/templates/partials/framework_trends_panel.html` → `modules/frameworks/templates/partials/framework_trends_panel.html`
- `app/templates/partials/framework_insights.html` → `modules/frameworks/templates/partials/framework_insights.html`
- `app/templates/partials/itpp_command_center.html` → `modules/frameworks/templates/partials/itpp_command_center.html`
- `app/templates/partials/itpp_operational_panel.html` → `modules/frameworks/templates/partials/itpp_operational_panel.html`
- `app/templates/partials/control_validation_panel.html` → `modules/frameworks/templates/partials/control_validation_panel.html`
- `app/templates/partials/ecs_framework_kpi_drill.html` → `modules/frameworks/templates/partials/ecs_framework_kpi_drill.html`
- `app/templates/partials/governance_analytics_panel.html` → `modules/governance/templates/partials/governance_analytics_panel.html`
- `app/templates/partials/grc_kpis.html` → `modules/governance/templates/partials/grc_kpis.html`
- `app/templates/partials/mvp_upload_missing_panel.html` → `modules/governance/templates/partials/mvp_upload_missing_panel.html`
- `app/templates/partials/gap_export_modal.html` → `modules/governance/templates/partials/gap_export_modal.html`
- `app/templates/partials/gap_export_client.html` → `modules/governance/templates/partials/gap_export_client.html`
- `app/templates/partials/completeness_filter_client.html` → `modules/governance/templates/partials/completeness_filter_client.html`
- `app/templates/partials/comparison_filter_client.html` → `modules/governance/templates/partials/comparison_filter_client.html`
- `app/templates/partials/lifecycle_filter_client.html` → `modules/governance/templates/partials/lifecycle_filter_client.html`
- `app/templates/partials/audit_prep_modals.html` → `modules/governance/templates/partials/audit_prep_modals.html`
- `app/templates/partials/mvp_reuse_table.html` → `modules/governance/templates/partials/mvp_reuse_table.html`
- `app/templates/partials/scheduler_styles.html` → `modules/operations/templates/partials/scheduler_styles.html`
- `app/templates/partials/operations_filter_client.html` → `modules/operations/templates/partials/operations_filter_client.html`
- `app/templates/partials/integrations_health_panel.html` → `modules/operations/templates/partials/integrations_health_panel.html`
- `app/templates/partials/integrations_hub_executive_client.html` → `modules/operations/templates/partials/integrations_hub_executive_client.html`
- `app/templates/partials/upload_simulation_client.html` → `modules/operations/templates/partials/upload_simulation_client.html`
- `app/templates/partials/onboarding_simulator.html` → `modules/operations/templates/partials/onboarding_simulator.html`
- `app/templates/partials/ai_ops_assistant_client.html` → `modules/operations/templates/partials/ai_ops_assistant_client.html`
- `app/templates/partials/upload_modals.html` → `modules/operations/templates/partials/upload_modals.html`
- `app/templates/partials/scheduler_modals.html` → `modules/operations/templates/partials/scheduler_modals.html`
- `app/templates/partials/onboarding_modals.html` → `modules/operations/templates/partials/onboarding_modals.html`
- `app/templates/partials/integrations_modals.html` → `modules/operations/templates/partials/integrations_modals.html`
- `app/templates/partials/grc_demo_drill_modal.html` → `modules/enterprise_grc/templates/partials/grc_demo_drill_modal.html`
- `app/templates/partials/grc_governance_analytics_client.html` → `modules/enterprise_grc/templates/partials/grc_governance_analytics_client.html`
- `app/templates/partials/analytics_filter_client.html` → `modules/enterprise_grc/templates/partials/analytics_filter_client.html`
- `app/templates/partials/ai_sdlc_styles.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_styles.html`
- `app/templates/partials/ai_sdlc_subnav.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_subnav.html`
- `app/templates/partials/ai_sdlc_control_tower_client.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_control_tower_client.html`
- `app/templates/partials/ai_sdlc_onboarding_client.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_onboarding_client.html`
- `app/templates/partials/ai_sdlc_worklist.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_worklist.html`
- `app/templates/partials/ai_sdlc_workflow_modals.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_workflow_modals.html`
- `app/templates/partials/ai_sdlc_stage_workspace.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_stage_workspace.html`
- `app/templates/partials/ai_sdlc_stage_artifact_dashboard.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_stage_artifact_dashboard.html`
- `app/templates/partials/ecs_governance_chrome.html` → `modules/ai_sdlc/templates/partials/ecs_governance_chrome.html`
- `app/templates/partials/ecs_governance_shell.html` → `modules/ai_sdlc/templates/partials/ecs_governance_shell.html`
- `app/templates/partials/ai_sdlc_drill_modal.html` → `modules/ai_sdlc/templates/partials/ai_sdlc_drill_modal.html`

## Shims

- `app/demo_kpi_drill_engine.py`
- `app/demo_metrics.py`
- `app/demo_seed.py`
- `app/executive_analytics_engine.py`
- `app/ecs_reports_engine.py`
- `app/reporting_module.py`
- `app/enterprise_mock_service.py`
- `app/integration_hub_executive_engine.py`
- `app/framework_catalog.py`
- `app/framework_dashboards.py`
- `app/framework_governance_context.py`
- `app/framework_governance_data.py`
- `app/framework_intelligence.py`
- `app/framework_kpi_drill_engine.py`
- `app/framework_loader_service.py`
- `app/framework_onboarding_engine.py`
- `app/framework_trends_engine.py`
- `app/framework_workflow_engine.py`
- `app/ecs_row_drill_engine.py`
- `app/itpp_module.py`
- `app/control_validation_engine.py`
- `app/application_governance.py`
- `app/scheduler_module.py`
- `app/scheduler_intelligence.py`
- `app/operations_intelligence.py`
- `app/operations_catalog.py`
- `app/operations_filter_engine.py`
- `app/operations_mock_data.py`
- `app/onboarding_engine.py`
- `app/integrations_module.py`
- `app/integration_health_engine.py`
- `app/ai_ops_assistant_engine.py`
- `app/ai_ops_summary_engine.py`
- `app/evidence_repository.py`
- `app/resubmission.py`
- `app/audit_schedule_engine.py`
- `app/audit_prep_data.py`
- `app/analytics_module.py`
- `app/evidence_review.py`
- `app/evidence_approval_engine.py`
- `app/evidence_health_engine.py`
- `app/governance_completeness_engine.py`
- `app/governance_data_enrichment.py`
- `app/governance_intelligence.py`
- `app/governance_lifecycle_engine.py`
- `app/governance_relational_model.py`
- `app/governance_mock_data.py`
- `app/missing_evidence_engine.py`
- `app/search_module.py`
- `app/comparison_engine.py`
- `app/gap_export_engine.py`
- `app/workflow_module.py`
- `app/operational_workflows.py`
- `app/operational_mock_data.py`
- `app/exception_state_engine.py`
- `app/grc_module_demo.py`
- `app/grc_demo_service.py`
- `app/enterprise_grc.py`
- `app/correlation_engine.py`
- `app/ecs_governance_drilldowns.py`
- `app/ecs_governance_qa_engine.py`
- `app/ecs_governance_framework.py`
- `app/ecs_demo_remediation.py`
- `app/ai_sdlc_governance_service.py`
- `app/ai_sdlc_governance_mock.py`
- `app/ai_sdlc_control_tower_engine.py`
- `app/ai_sdlc_onboarding_engine.py`
- `app/ai_sdlc_workflow_engine.py`
- `app/ai_sdlc_workflow_store.py`
- `app/ai_sdlc_reports_engine.py`
- `app/ai_sdlc_knowledge_repository.py`
- `app/ai_sdlc_document_artifacts.py`
- `app/ecs_ai_governance_drilldowns.py`
- `app/ecs_sdlc_stage_dashboard.py`
- `app/ecs_state.py`
- `app/ecs_mock_engine.py`
- `app/enterprise_context.py`
- `app/module_capabilities.py`
- `app/module_workspace.py`
- `app/nav_counter_engine.py`
- `app/ecs_nav_framework.py`
- `app/role_permissions.py`
- `app/role_filter_scope.py`
- `app/audit_trail.py`
- `app/ecs_logging.py`
- `app/chatbot_engine.py`
- `app/chatbot_context_engine.py`
- `app/chatbot_nav.py`
- `app/chatbot_enhanced.py`
- `app/evidence_api.py`
- `app/evidence_workflow_engine.py`
- `app/ecs_universal_drill_engine.py`
- `app/module_kpi_drill_engine.py`
- `app/demo_data_standards.py`
- `app/global_filter_engine.py`
- `app/standard_filter_engine.py`
- `app/pagination.py`
- `app/table_schemas.py`