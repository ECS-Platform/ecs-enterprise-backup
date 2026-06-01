"""Tab-driven workspace configuration for MVP module pages."""

from __future__ import annotations

from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG
from modules.operations.engines.operations_catalog import BANKING_APPLICATIONS, MODULE_STATUSES, OWNERS

Tab = dict[str, str]

DEFAULT_TABS: dict[str, list[Tab]] = {
    "enterprise": [
        {"id": "overview", "label": "Overview"},
        {"id": "frameworks", "label": "Frameworks"},
        {"id": "business_units", "label": "Business Units"},
        {"id": "gaps", "label": "Open Gaps"},
        {"id": "analytics", "label": "Analytics"},
    ],
    "pan_india": [
        {"id": "overview", "label": "Overview"},
        {"id": "regions", "label": "Regions"},
        {"id": "sla", "label": "SLA Breaches"},
        {"id": "analytics", "label": "Analytics"},
    ],
    "reports": [
        {"id": "overview", "label": "Overview"},
        {"id": "catalog", "label": "Reports"},
        {"id": "observations", "label": "Observation Detail"},
        {"id": "scheduled", "label": "Scheduled"},
        {"id": "history", "label": "History"},
    ],
    "trends": [
        {"id": "overview", "label": "Overview"},
        {"id": "coverage", "label": "Coverage"},
        {"id": "observations", "label": "Observations"},
        {"id": "rejections", "label": "Rejections"},
        {"id": "sla", "label": "SLA"},
        {"id": "aging", "label": "Evidence Aging"},
    ],
    "audit_prep": [
        {"id": "overview", "label": "Overview"},
        {"id": "audits", "label": "Upcoming Audits"},
        {"id": "gaps", "label": "Open Gaps"},
        {"id": "requests", "label": "Auditor Requests"},
        {"id": "submissions", "label": "Pending Submissions"},
        {"id": "actions", "label": "Actions"},
    ],
    "reuse": [
        {"id": "overview", "label": "Overview"},
        {"id": "candidates", "label": "Reuse Candidates"},
        {"id": "mappings", "label": "Mappings"},
        {"id": "workbench", "label": "Mapping Workbench"},
        {"id": "pending", "label": "Pending"},
        {"id": "analytics", "label": "Analytics"},
    ],
    "completeness": [
        {"id": "overview", "label": "Overview"},
        {"id": "frameworks", "label": "Frameworks"},
        {"id": "applications", "label": "Applications"},
        {"id": "controls", "label": "Controls"},
        {"id": "gaps", "label": "Gaps"},
        {"id": "uploads", "label": "Upload Missing"},
    ],
    "lifecycle": [
        {"id": "controls", "label": "Control Lifecycle"},
        {"id": "evidence", "label": "Evidence Lifecycle"},
        {"id": "observations", "label": "Observation Lifecycle"},
        {"id": "remediation", "label": "Remediation Lifecycle"},
        {"id": "audit", "label": "Audit Lifecycle"},
        {"id": "exceptions", "label": "Exception Lifecycle"},
        {"id": "timeline", "label": "Timeline View"},
    ],
    "search": [
        {"id": "overview", "label": "Overview"},
        {"id": "results", "label": "Evidence Results"},
        {"id": "controls", "label": "Control Lookup"},
        {"id": "findings", "label": "Audit Findings"},
        {"id": "reuse", "label": "Reuse Suggestions"},
    ],
    "evidence_approval": [
        {"id": "overview", "label": "Overview"},
        {"id": "approved", "label": "Approved"},
        {"id": "rejected", "label": "Rejected"},
        {"id": "pending", "label": "Pending Validation"},
        {"id": "quality", "label": "Quality Scorecard"},
        {"id": "analytics", "label": "Analytics"},
        {"id": "audit_trail", "label": "Audit Trail"},
    ],
    "exception_governance": [
        {"id": "overview", "label": "Overview"},
        {"id": "approved_recent", "label": "Recently Approved"},
        {"id": "rejected_recent", "label": "Recently Rejected"},
        {"id": "expiring", "label": "Expiring This Month"},
        {"id": "pending_cab", "label": "Pending CAB"},
        {"id": "all_exceptions", "label": "All Exceptions"},
    ],
    "integrations": [
        {"id": "overview", "label": "Overview"},
        {"id": "connectors", "label": "Connectors"},
        {"id": "sync", "label": "Sync Status"},
        {"id": "logs", "label": "Logs"},
    ],
    "scheduler": [
        {"id": "overview", "label": "Overview"},
        {"id": "applications", "label": "App Scans"},
        {"id": "cron", "label": "Cron Timeline"},
        {"id": "history", "label": "Run History"},
        {"id": "failures", "label": "Failures"},
        {"id": "upcoming", "label": "Tomorrow Plan"},
        {"id": "integrations", "label": "Integrations"},
    ],
    "evidence_health": [
        {"id": "overview", "label": "Overview"},
        {"id": "queue", "label": "Evidence Queue"},
        {"id": "stale", "label": "Stale"},
        {"id": "expired", "label": "Expired"},
        {"id": "frameworks", "label": "By Framework"},
        {"id": "analytics", "label": "Analytics"},
    ],
    "comparison": [
        {"id": "overview", "label": "Overview"},
        {"id": "applications", "label": "Applications"},
        {"id": "pairs", "label": "App Pairs"},
        {"id": "variance", "label": "Variance"},
        {"id": "rankings", "label": "Rankings"},
    ],
    "onboarding": [
        {"id": "overview", "label": "Overview"},
        {"id": "applications", "label": "Applications"},
        {"id": "pipeline", "label": "Pipeline"},
        {"id": "post_onboarding", "label": "Post-Onboarding"},
    ],
    "framework_admin": [
        {"id": "overview", "label": "Overview"},
        {"id": "catalog", "label": "ECS Catalog"},
        {"id": "onboarded", "label": "Onboarded"},
        {"id": "mapping", "label": "Control Mapping"},
        {"id": "gaps", "label": "Gaps & Tasks"},
    ],
    "upload": [
        {"id": "overview", "label": "Overview"},
        {"id": "uploads", "label": "Uploads"},
        {"id": "tracker", "label": "Tracker"},
    ],
    "governance_analytics": [
        {"id": "overview", "label": "Overview"},
        {"id": "coverage", "label": "Coverage"},
        {"id": "observations", "label": "Observations"},
        {"id": "applications", "label": "Applications"},
        {"id": "failures", "label": "Failures"},
    ],
    "risk_register": [
        {"id": "overview", "label": "Overview"},
        {"id": "register", "label": "Risk Register"},
        {"id": "heatmap", "label": "Heatmap"},
    ],
    "exceptions_td": [
        {"id": "overview", "label": "Overview"},
        {"id": "active", "label": "Active"},
        {"id": "expired", "label": "Expired"},
    ],
    "cmdb": [
        {"id": "overview", "label": "Overview"},
        {"id": "assets", "label": "Assets"},
    ],
    "regulatory_mapping": [
        {"id": "overview", "label": "Overview"},
        {"id": "mapping", "label": "Mapping"},
    ],
    "executive_heatmaps": [
        {"id": "overview", "label": "Overview"},
        {"id": "frameworks", "label": "Frameworks"},
        {"id": "applications", "label": "Applications"},
        {"id": "regional", "label": "Regional"},
    ],
    "integrations_hub": [
        {"id": "connectors", "label": "Connector Status"},
        {"id": "sync", "label": "Sync Monitoring"},
        {"id": "evidence", "label": "Evidence Collection"},
        {"id": "processes", "label": "Business Processes"},
        {"id": "issues", "label": "Open Issues"},
        {"id": "logs", "label": "Connector Logs"},
    ],
    "correlation": [
        {"id": "overview", "label": "Overview"},
        {"id": "chains", "label": "Chains"},
    ],
}

ROLE_TABS: dict[tuple[str, str], list[Tab]] = {
    ("reuse", "owner"): [
        {"id": "overview", "label": "Overview"},
        {"id": "candidates", "label": "Reuse Candidates"},
        {"id": "mappings", "label": "My Mappings"},
        {"id": "workbench", "label": "Workbench"},
        {"id": "pending", "label": "Pending"},
        {"id": "analytics", "label": "Analytics"},
    ],
    ("reuse", "auditor"): [
        {"id": "overview", "label": "Overview"},
        {"id": "candidates", "label": "Candidates"},
        {"id": "mappings", "label": "Approval Queue"},
        {"id": "workbench", "label": "Workbench"},
        {"id": "pending", "label": "Rejections"},
        {"id": "analytics", "label": "Analytics"},
    ],
    ("audit_prep", "owner"): [
        {"id": "overview", "label": "Overview"},
        {"id": "gaps", "label": "My Gaps"},
        {"id": "uploads", "label": "Upload Missing"},
        {"id": "audits", "label": "Upcoming Audits"},
    ],
    ("audit_prep", "auditor"): [
        {"id": "overview", "label": "Overview"},
        {"id": "queue", "label": "Approval Queue"},
        {"id": "gaps", "label": "High Risk"},
        {"id": "audits", "label": "Audits"},
    ],
    ("audit_prep", "cio"): [
        {"id": "overview", "label": "Overview"},
        {"id": "readiness", "label": "Audit Readiness"},
        {"id": "gaps", "label": "Open Gaps"},
        {"id": "heatmaps", "label": "Trends"},
        {"id": "audits", "label": "Upcoming Audits"},
    ],
    ("completeness", "owner"): [
        {"id": "overview", "label": "Overview"},
        {"id": "gaps", "label": "My Gaps"},
        {"id": "controls", "label": "Controls"},
        {"id": "uploads", "label": "Upload Missing"},
        {"id": "applications", "label": "Applications"},
    ],
    ("completeness", "auditor"): [
        {"id": "overview", "label": "Overview"},
        {"id": "gaps", "label": "Review Queue"},
        {"id": "controls", "label": "Controls"},
        {"id": "uploads", "label": "Missing Evidence"},
        {"id": "applications", "label": "Applications"},
    ],
    ("enterprise", "cio"): [
        {"id": "overview", "label": "Overview"},
        {"id": "business_units", "label": "Business Units"},
        {"id": "frameworks", "label": "Frameworks"},
        {"id": "gaps", "label": "Open Gaps"},
        {"id": "analytics", "label": "Analytics"},
    ],
    ("lifecycle", "owner"): [
        {"id": "controls", "label": "Control Lifecycle"},
        {"id": "evidence", "label": "Evidence Lifecycle"},
        {"id": "observations", "label": "Observations"},
        {"id": "remediation", "label": "Remediation"},
        {"id": "timeline", "label": "Timeline"},
    ],
    ("evidence_health", "owner"): [
        {"id": "overview", "label": "Overview"},
        {"id": "queue", "label": "My Queue"},
        {"id": "stale", "label": "Stale"},
        {"id": "expired", "label": "Expired"},
        {"id": "frameworks", "label": "By Framework"},
    ],
    ("evidence_health", "auditor"): [
        {"id": "overview", "label": "Overview"},
        {"id": "queue", "label": "Review Queue"},
        {"id": "stale", "label": "Stale"},
        {"id": "expired", "label": "Expired"},
        {"id": "frameworks", "label": "By Framework"},
        {"id": "analytics", "label": "Analytics"},
    ],
    ("evidence_health", "cio"): [
        {"id": "overview", "label": "Overview"},
        {"id": "queue", "label": "Enterprise Queue"},
        {"id": "frameworks", "label": "By Framework"},
        {"id": "analytics", "label": "Analytics"},
    ],
    ("evidence_health", "compliance_head"): [
        {"id": "overview", "label": "Overview"},
        {"id": "queue", "label": "Compliance Queue"},
        {"id": "frameworks", "label": "By Framework"},
        {"id": "analytics", "label": "Analytics"},
    ],
}


def build_module_workspace(module: str, role: str = "owner") -> dict:
    tabs = ROLE_TABS.get((module, role)) or ROLE_TABS.get((module, role.replace("compliance_officer", "compliance_head"))) or DEFAULT_TABS.get(module)
    if not tabs:
        tabs = [
            {"id": "overview", "label": "Overview"},
            {"id": "data", "label": "Data"},
            {"id": "analytics", "label": "Analytics"},
        ]
    ws = {
        "module": module,
        "role": role,
        "tabs": tabs,
        "default_tab": tabs[0]["id"],
        "filter_profile": "standard",
        "frameworks": ["All Frameworks"] + list(FRAMEWORK_CATALOG.keys()),
        "applications": ["All Applications"] + BANKING_APPLICATIONS,
        "statuses": ["All Status", "Approved", "Pending", "Rejected", "Draft", "Open", "Failed Validation"],
        "risks": ["All Risk", "Critical", "High", "Medium", "Low"],
        "owners": ["All Owners"] + OWNERS,
        "regions": ["All Regions", "North", "South", "East", "West", "Central"],
        "severities": ["All Severities", "Critical", "High", "Medium", "Low"],
        "audit_cycles": ["All Cycles", "Q1 2026", "Q2 2026 Audit Cycle", "Q3 2026", "FY 2026"],
        "date_ranges": ["Last 7 days", "Last 30 days", "Last 90 days", "Quarterly", "Yearly"],
    }
    filter_profiles = {
        "lifecycle": "lifecycle",
        "completeness": "completeness",
        "comparison": "comparison",
        "integrations_hub": "integrations_hub",
    }
    if module in filter_profiles:
        ws["filter_profile"] = filter_profiles[module]
    if module == "comparison":
        from modules.governance.engines.comparison_engine import COMPARE_SCOPES, TIME_RANGES
        ws["compare_frameworks"] = ["All Frameworks"] + list(FRAMEWORK_CATALOG.keys())
        ws["compare_scopes"] = COMPARE_SCOPES
        ws["compare_applications"] = ["All Applications"] + BANKING_APPLICATIONS
        ws["time_ranges"] = TIME_RANGES
    if module == "lifecycle":
        from modules.governance.engines.governance_lifecycle_engine import LIFECYCLE_APPS
        ws["applications"] = ["All Applications"] + LIFECYCLE_APPS
    status_overrides = {
        "integrations": MODULE_STATUSES["integrations"],
        "scheduler": MODULE_STATUSES["scheduler"],
        "upload": MODULE_STATUSES["upload"],
        "onboarding": MODULE_STATUSES["onboarding"],
    }
    if module in status_overrides:
        ws["statuses"] = ["All Status"] + status_overrides[module]
    return ws
