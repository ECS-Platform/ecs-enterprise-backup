"""Classification of workbook rows into automation *families* (used by tools/build_registry.py).

The workbook has two kinds of rows:
  * use-case specific functional tests (first ~8 per UC) -> family chosen from keywords in the test name
  * generated cross-cutting rows "Validate <topic> for <UC name>" -> family fixed by <topic>
A family names the reusable helper group (and pytest markers) that automate the row. Fine-grained capability,
ECS component and test data are declared per case in the use-case modules and exported to the traceability file.
"""

from __future__ import annotations

import re

# topic text (as in the workbook) -> (slug, family)
TOPICS: dict[str, tuple[str, str]] = {
    "role-based access": ("rbac_access", "security"),
    "performance": ("performance", "performance"),
    "notification mechanism": ("notification", "notification"),
    "security controls": ("security_controls", "security"),
    "evidence integrity": ("evidence_integrity", "integrity"),
    "compliance mapping": ("compliance_mapping", "compliance"),
    "concurrent user operations": ("concurrency", "concurrency"),
    "dashboard/report visibility": ("dashboard_visibility", "dashboard"),
    "retention and archival": ("retention_archival", "retention"),
    "integration flow": ("integration_flow", "integration"),
    "retry and recovery": ("retry_recovery", "workflow"),
    "data accuracy": ("data_accuracy", "dashboard"),
    "audit logging": ("audit_logging", "audit"),
    "error handling": ("error_handling", "api"),
}
CROSSCUT_RE = re.compile(r"^Validate (?P<topic>.+?) for (?P<uc>.+)$")

# ordered (regex on test name, family); first match wins
CORE_RULES: list[tuple[str, str]] = [
    (r"refresh after|dashboard|leadership compliance summary|enterprise dashboard", "dashboard"),
    (r"audit preparation|assemble|audit package", "reporting"),
    (r"common.control", "compliance"),
    (r"duplicate application", "onboarding"),
    (r"schedul|next scheduled run|restart durability", "scheduler"),
    (r"connect to|connector|sharepoint|servicenow|source change|authorization failure|authentication failure", "connector"),
    (r"hash|tamper|integrity", "integrity"),
    (r"restart|persistence after restart|preserve metadata across restart", "lifecycle"),
    (r"upload|persist collected|duplicate", "evidence"),
    (r"metadata|naming|tag", "metadata"),
    (r"summary|summar|ai |provenance|grounding|citation|natural-language|no-answer|vector|suggestions|similar|unrelated|similarity", "ai"),
    (r"predefined query|query|search|filter common", "search"),
    (r"onboard|configure applicable|standard configuration|evidence sources", "onboarding"),
    (r"version|retention|lifecycle|historical|retained", "lifecycle"),
    (r"report|export|reporting period|traceability|deterministic", "reporting"),
    (r"compare|comparison|gaps between|out-of-scope|cross-application", "dashboard"),
    (r"dashboard|kpi|drill|trend|aggregate|reconcile|enterprise|national|region|leadership|exception|hotspot|refresh|time range|historical calculation|improving", "dashboard"),
    (r"common control|framework|mapping|applicab|completeness|missing|complete control|expired", "compliance"),
    (r"role|permission|access control|segregation|scope|unauthorized", "security"),
    (r"audit", "audit"),
]

FAMILY_DEPENDENCIES: dict[str, list[str]] = {
    "scheduler": ["api_client", "scheduler", "connectors", "evidence", "metadata", "audit", "notification", "storage"],
    "connector": ["api_client", "connectors", "evidence", "audit", "scheduler"],
    "integrity": ["api_client", "evidence", "storage", "db"],
    "evidence": ["api_client", "evidence", "data_factory", "db", "storage"],
    "metadata": ["api_client", "evidence", "data_factory", "search"],
    "ai": ["api_client", "ai", "evidence", "audit"],
    "search": ["api_client", "search", "evidence"],
    "onboarding": ["api_client", "onboarding", "compliance", "db"],
    "lifecycle": ["api_client", "lifecycle", "evidence", "db", "audit"],
    "reporting": ["api_client", "reporting", "evidence", "audit"],
    "dashboard": ["api_client", "dashboard", "evidence"],
    "compliance": ["api_client", "compliance", "evidence", "db"],
    "security": ["api_client", "rbac", "security", "audit"],
    "audit": ["api_client", "audit", "db"],
    "performance": ["api_client", "perf"],
    "notification": ["api_client", "notification", "evidence"],
    "concurrency": ["api_client", "concurrency", "evidence"],
    "retention": ["api_client", "lifecycle", "storage", "db"],
    "integration": ["api_client", "evidence", "search", "dashboard", "audit", "storage"],
    "workflow": ["api_client", "evidence", "scheduler"],
    "api": ["api_client"],
}

FAMILY_MARKERS: dict[str, list[str]] = {
    "scheduler": ["integration", "api"], "connector": ["integration", "api"], "integrity": ["integrity", "database", "api"],
    "evidence": ["api", "database"], "metadata": ["api"], "ai": ["ai", "api"], "search": ["api"], "onboarding": ["api", "database"],
    "lifecycle": ["retention", "database"], "reporting": ["reporting", "api"], "dashboard": ["dashboard", "api"],
    "compliance": ["api", "database"], "security": ["security", "rbac"], "audit": ["audit", "database"],
    "performance": ["performance"], "notification": ["notification"], "concurrency": ["concurrency"], "retention": ["retention"],
    "integration": ["integration", "api"], "workflow": ["integration"], "api": ["api"],
}


def parse_topic(name: str) -> tuple[str, str]:
    """Return (topic_slug, family) for generated cross-cutting rows, ('', '') otherwise."""
    m = CROSSCUT_RE.match(name)
    if not m:
        return "", ""
    topic = m.group("topic").strip().lower()
    if topic in TOPICS:
        return TOPICS[topic]
    return "", ""


def core_family(name: str) -> str:
    low = name.lower()
    for pat, fam in CORE_RULES:
        if re.search(pat, low):
            return fam
    return "api"
