#!/usr/bin/env python3
"""One-shot ECS modular refactor: move engines to modules/, create app shims, rewrite imports."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
MODULES = ROOT / "modules"

# module -> list of python filenames (basename only)
PYTHON_MAP: dict[str, list[str]] = {
    "executive_overview": [
        "demo_kpi_drill_engine.py", "demo_metrics.py", "demo_seed.py",
        "executive_analytics_engine.py", "ecs_reports_engine.py", "reporting_module.py",
        "enterprise_mock_service.py", "integration_hub_executive_engine.py",
    ],
    "frameworks": [
        "framework_catalog.py", "framework_dashboards.py", "framework_governance_context.py",
        "framework_governance_data.py", "framework_intelligence.py", "framework_kpi_drill_engine.py",
        "framework_loader_service.py", "framework_onboarding_engine.py", "framework_trends_engine.py",
        "framework_workflow_engine.py", "ecs_row_drill_engine.py", "itpp_module.py",
        "control_validation_engine.py", "application_governance.py",
    ],
    "operations": [
        "scheduler_module.py", "scheduler_intelligence.py", "operations_intelligence.py",
        "operations_catalog.py", "operations_filter_engine.py", "operations_mock_data.py",
        "onboarding_engine.py", "integrations_module.py", "integration_health_engine.py",
        "ai_ops_assistant_engine.py", "ai_ops_summary_engine.py", "evidence_repository.py",
        "resubmission.py",
    ],
    "governance": [
        "audit_schedule_engine.py", "audit_prep_data.py", "analytics_module.py",
        "evidence_review.py", "evidence_approval_engine.py", "evidence_health_engine.py",
        "governance_completeness_engine.py", "governance_data_enrichment.py",
        "governance_intelligence.py", "governance_lifecycle_engine.py",
        "governance_relational_model.py", "governance_mock_data.py", "missing_evidence_engine.py",
        "search_module.py", "comparison_engine.py", "gap_export_engine.py", "workflow_module.py",
        "operational_workflows.py", "operational_mock_data.py", "exception_state_engine.py",
    ],
    "enterprise_grc": [
        "grc_module_demo.py", "grc_demo_service.py", "enterprise_grc.py", "correlation_engine.py",
        "ecs_governance_drilldowns.py", "ecs_governance_qa_engine.py", "ecs_governance_framework.py",
        "ecs_demo_remediation.py",
    ],
    "ai_sdlc": [
        "ai_sdlc_governance_service.py", "ai_sdlc_governance_mock.py", "ai_sdlc_control_tower_engine.py",
        "ai_sdlc_onboarding_engine.py", "ai_sdlc_workflow_engine.py", "ai_sdlc_workflow_store.py",
        "ai_sdlc_reports_engine.py", "ai_sdlc_knowledge_repository.py", "ai_sdlc_document_artifacts.py",
        "ai_sdlc_controlled_documents.py",
        "ecs_ai_governance_drilldowns.py", "ecs_sdlc_stage_dashboard.py",
    ],
}

ROUTE_MAP: dict[str, str] = {
    "routes_ai_sdlc_governance.py": "ai_sdlc/routes/routes_ai_sdlc_governance.py",
    "routes_grc_demo.py": "enterprise_grc/routes/routes_grc_demo.py",
    "evidence_routes.py": "shared/routes/evidence_routes.py",
    "routes_mvp.py": "shared/routes/routes_mvp.py",
}

SHARED_SUBDIRS: dict[str, list[str]] = {
    "services": [
        "ecs_state.py", "ecs_mock_engine.py", "enterprise_context.py", "module_capabilities.py",
        "module_workspace.py", "nav_counter_engine.py", "ecs_nav_framework.py", "role_permissions.py",
        "role_filter_scope.py", "audit_trail.py", "ecs_logging.py", "chatbot_engine.py",
        "chatbot_context_engine.py", "chatbot_nav.py", "chatbot_enhanced.py", "evidence_api.py",
        "evidence_workflow_engine.py",
    ],
    "drilldowns": [
        "ecs_universal_drill_engine.py", "module_kpi_drill_engine.py",
    ],
    "utils": [
        "demo_data_standards.py", "global_filter_engine.py", "standard_filter_engine.py",
        "pagination.py", "table_schemas.py",
    ],
}

# Build filename -> module path (e.g. framework_catalog.py -> frameworks/engines)
FILE_TO_MODULE: dict[str, str] = {}
for mod, files in PYTHON_MAP.items():
    for f in files:
        FILE_TO_MODULE[f] = f"{mod}/engines"
for sub, files in SHARED_SUBDIRS.items():
    for f in files:
        FILE_TO_MODULE[f] = f"shared/{sub}"

KEEP_IN_APP = {
    "main.py", "routes_mvp.py", "routes_grc_demo.py", "routes_ai_sdlc_governance.py",
    "evidence_routes.py", "__init__.py",
}

# Template page mapping (relative to app/templates)
TEMPLATE_MAP: dict[str, str] = {
    "executive_overview": [
        "dashboard.html", "cio_dashboard.html", "dashboard_vertical_head.html",
        "dashboard_compliance_head.html", "dashboard_functional_head.html",
        "mvp_demo_overview.html", "mvp_enterprise.html", "mvp_pan_india.html",
        "mvp_reports.html", "mvp_ecs_report.html", "mvp_trends.html", "login.html",
    ],
    "frameworks": ["framework.html", "framework_loader.html", "mvp_framework_admin.html"],
    "operations": [
        "mvp_scheduler.html", "mvp_bulk_upload.html", "mvp_integrations.html",
        "mvp_integrations_hub.html", "mvp_onboarding.html", "mvp_ai_ops_assistant.html",
        "mvp_ai_ops_summary.html",
    ],
    "governance": [
        "mvp_audit_prep.html", "mvp_evidence_health.html", "mvp_reuse.html", "mvp_lifecycle.html",
        "mvp_completeness.html", "mvp_comparison.html", "mvp_search.html", "mvp_evidence_approval.html",
        "evidence_review.html", "mvp_workflow_close_gap.html", "mvp_workflow_assign_owner.html",
        "mvp_workflow_upload_missing.html", "mvp_workflow_mock_audit.html",
    ],
    "enterprise_grc": [
        "mvp_risk_register.html", "mvp_exceptions.html", "mvp_exception_governance.html",
        "mvp_cmdb.html", "mvp_regulatory.html", "mvp_heatmaps.html", "mvp_correlation.html",
        "mvp_governance_analytics.html",
    ],
    "ai_sdlc": [
        "mvp_ai_sdlc_home.html", "mvp_ai_sdlc_control_tower.html", "mvp_ai_sdlc_onboarding.html",
        "mvp_ai_sdlc_worklist.html", "mvp_sdlc_gates.html", "mvp_sdlc_gate_stage.html",
        "mvp_ai_governance_posture.html", "mvp_ai_registry.html", "mvp_governance_quality.html",
        "mvp_ai_sdlc_reports.html", "mvp_ai_sdlc_report.html", "mvp_ai_sdlc_evidence_viewer.html",
    ],
}

PARTIAL_MAP: dict[str, str] = {
    "shared": [
        "enterprise_theme.html", "mvp_styles.html", "ecs_sidebar.html", "mvp_sidebar.html",
        "ecs_nav_groups.html", "ecs_nav_shell.js.html", "ecs_nav_ai_sdlc.html", "nav_badge.html",
        "ecs_ux_macros.html", "ecs_ux_system.html", "mvp_workspace_macros.html", "mvp_workspace_styles.html",
        "mvp_capability_styles.html", "mvp_module_header.html", "mvp_module_actions.html", "mvp_quick_links.html",
        "role_metrics_strip.html", "chatbot_global.html", "ecs_floating_action_portal.html",
        "enterprise_widgets.html", "workflow_styles.html", "workflow_guidance.html",
        "ecs_universal_drill.html", "ecs_module_kpi_drill.html", "ecs_pagination.html",
        "ecs_executive_table_system.html", "ecs_top_risk_table_fix.html",
        "ecs_governance_table_framework.html", "ecs_governance_table_macros.html",
        "executive_charts_system.html", "executive_chart_macros.html", "executive_chart_card.html",
        "compact_chart.html", "analytics_macros.html", "evidence_upload_modal.html",
        "raise_exception_modal.html", "evidence_workflow_macros.html", "evidence_workflow_system.html",
        "analytics_filter_bar.html", "standard_filter_include.html", "standard_filter_client.html",
        "executive_dashboard_client.html", "page_workflow_queue.html", "leadership_work_queue.html",
        "auditor_review_queue.html", "owner_work_queue.html",
    ],
    "frameworks": [
        "framework_executive_strip.html", "framework_executive_extras.html", "framework_drill_panels.html",
        "framework_relational_evidence.html", "framework_workflow_table.html", "framework_governance_panel.html",
        "framework_application_grid.html", "framework_trends_panel.html", "framework_insights.html",
        "itpp_command_center.html", "itpp_operational_panel.html", "control_validation_panel.html",
        "ecs_framework_kpi_drill.html",
    ],
    "governance": [
        "governance_analytics_panel.html", "grc_kpis.html", "mvp_upload_missing_panel.html",
        "gap_export_modal.html", "gap_export_client.html", "completeness_filter_client.html",
        "comparison_filter_client.html", "lifecycle_filter_client.html", "audit_prep_modals.html",
        "mvp_reuse_table.html",
    ],
    "operations": [
        "scheduler_styles.html", "operations_filter_client.html", "integrations_health_panel.html",
        "integrations_hub_executive_client.html", "upload_simulation_client.html", "onboarding_simulator.html",
        "ai_ops_assistant_client.html", "upload_modals.html", "scheduler_modals.html",
        "onboarding_modals.html", "integrations_modals.html",
    ],
    "enterprise_grc": [
        "grc_demo_drill_modal.html", "grc_governance_analytics_client.html", "analytics_filter_client.html",
    ],
    "ai_sdlc": [
        "ai_sdlc_styles.html", "ai_sdlc_subnav.html", "ai_sdlc_control_tower_client.html",
        "ai_sdlc_onboarding_client.html", "ai_sdlc_worklist.html", "ai_sdlc_workflow_modals.html",
        "ai_sdlc_stage_workspace.html", "ai_sdlc_stage_artifact_dashboard.html",
        "ecs_governance_chrome.html", "ecs_governance_shell.html", "ai_sdlc_drill_modal.html",
    ],
}


def module_import_path(filename: str) -> str:
    rel = FILE_TO_MODULE.get(filename)
    if not rel:
        return ""
    return "modules." + rel.replace("/", ".") + "." + filename[:-3]


def ensure_init_dirs():
    for mod in ["executive_overview", "frameworks", "operations", "governance", "enterprise_grc", "ai_sdlc"]:
        (MODULES / mod / "engines").mkdir(parents=True, exist_ok=True)
        (MODULES / mod / "templates").mkdir(parents=True, exist_ok=True)
        (MODULES / mod / "__init__.py").touch()
        (MODULES / mod / "engines" / "__init__.py").touch()
    for sub in ["services", "drilldowns", "utils"]:
        (MODULES / "shared" / sub).mkdir(parents=True, exist_ok=True)
        (MODULES / "shared" / sub / "__init__.py").touch()
    (MODULES / "shared" / "templates" / "partials").mkdir(parents=True, exist_ok=True)
    (MODULES / "shared" / "__init__.py").touch()
    (MODULES / "__init__.py").touch()


def move_python_files() -> list[tuple[str, str]]:
    moved = []
    for filename, rel in FILE_TO_MODULE.items():
        src = APP / filename
        if not src.exists():
            continue
        dest_dir = MODULES / rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        shutil.move(str(src), str(dest))
        moved.append((str(src.relative_to(ROOT)), str(dest.relative_to(ROOT))))
    return moved


def create_shims() -> list[str]:
    shims = []
    for filename in FILE_TO_MODULE:
        if filename in KEEP_IN_APP:
            continue
        imp = module_import_path(filename)
        if not imp:
            continue
        shim_path = APP / filename
        content = f'"""Compatibility shim — see {imp}."""\nfrom {imp} import *  # noqa: F401, F403\n'
        shim_path.write_text(content, encoding="utf-8")
        shims.append(str(shim_path.relative_to(ROOT)))
    return shims


def build_import_replacements() -> list[tuple[str, str]]:
    reps = []
    for filename in FILE_TO_MODULE:
        old = f"app.{filename[:-3]}"
        new = module_import_path(filename)
        if new:
            reps.append((old, new))
    reps.sort(key=lambda x: -len(x[0]))
    return reps


def rewrite_imports_in_file(path: Path, replacements: list[tuple[str, str]]) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
    orig = text
    for old, new in replacements:
        text = text.replace(f"from {old}", f"from {new}")
        text = text.replace(f"import {old}", f"import {new}")
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def rewrite_all_imports(replacements: list[tuple[str, str]]) -> int:
    count = 0
    for py in ROOT.rglob("*.py"):
        if "__pycache__" in str(py) or ".venv" in str(py):
            continue
        if rewrite_imports_in_file(py, replacements):
            count += 1
    return count


def move_templates() -> list[tuple[str, str]]:
    moved = []
    tpl_root = APP / "templates"
    for mod, pages in TEMPLATE_MAP.items():
        dest_dir = MODULES / mod / "templates"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for page in pages:
            src = tpl_root / page
            if src.exists():
                dest = dest_dir / page
                shutil.move(str(src), str(dest))
                moved.append((str(src.relative_to(ROOT)), str(dest.relative_to(ROOT))))
    partials_src = tpl_root / "partials"
    for mod, partials in PARTIAL_MAP.items():
        dest_partials = MODULES / mod / "templates" / "partials"
        dest_partials.mkdir(parents=True, exist_ok=True)
        for p in partials:
            src = partials_src / p
            if src.exists():
                dest = dest_partials / p
                shutil.move(str(src), str(dest))
                moved.append((str(src.relative_to(ROOT)), str(dest.relative_to(ROOT))))
    return moved


def template_loader_dirs() -> list[str]:
    dirs = []
    for mod in ["shared", "executive_overview", "frameworks", "operations", "governance", "enterprise_grc", "ai_sdlc"]:
        p = MODULES / mod / "templates"
        if p.exists():
            dirs.append(str(p))
    dirs.append("app/templates")
    return dirs


def patch_main_templates():
    main = APP / "main.py"
    text = main.read_text(encoding="utf-8")
    if "ChoiceLoader" in text:
        return
    old = 'templates = Jinja2Templates(directory="app/templates")'
    new = '''from jinja2 import ChoiceLoader, Environment, FileSystemLoader

_template_dirs = [
    "modules/shared/templates",
    "modules/executive_overview/templates",
    "modules/frameworks/templates",
    "modules/operations/templates",
    "modules/governance/templates",
    "modules/enterprise_grc/templates",
    "modules/ai_sdlc/templates",
    "app/templates",
]
templates = Jinja2Templates(
    env=Environment(loader=ChoiceLoader([FileSystemLoader(d) for d in _template_dirs]))
)'''
    if old in text:
        text = text.replace(old, new)
        main.write_text(text, encoding="utf-8")


def main():
    ensure_init_dirs()
    py_moved = move_python_files()
    tpl_moved = move_templates()
    shims = create_shims()
    reps = build_import_replacements()
    n_updated = rewrite_all_imports(reps)
    patch_main_templates()

    report = ROOT / "docs" / "ECS_MIGRATION_REPORT.md"
    lines = [
        "# ECS Module Migration Report",
        "",
        f"Python files moved: {len(py_moved)}",
        f"Template files moved: {len(tpl_moved)}",
        f"Compatibility shims created: {len(shims)}",
        f"Files with imports rewritten: {n_updated}",
        "",
        "## Python files moved",
        "",
    ]
    for a, b in py_moved:
        lines.append(f"- `{a}` → `{b}`")
    lines.extend(["", "## Templates moved", ""])
    for a, b in tpl_moved:
        lines.append(f"- `{a}` → `{b}`")
    lines.extend(["", "## Shims", ""])
    for s in shims:
        lines.append(f"- `{s}`")
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Done: {len(py_moved)} py, {len(tpl_moved)} tpl, {len(shims)} shims, {n_updated} import updates")


if __name__ == "__main__":
    main()
