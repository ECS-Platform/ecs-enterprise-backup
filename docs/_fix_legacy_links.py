#!/usr/bin/env python3
"""Fix legacy relative links after connectors/scheduler/api moved under developer-manual."""
from __future__ import annotations

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent

REPLACEMENTS_BY_PREFIX: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "03-development/developer-manual/",
        [
            (r"\]\(\.\./connectors/", "](../connectors/"),
            (r"\]\(\.\./scheduler/", "](../phase1/scheduler/"),
            (r"\]\(\.\./graph-api/", "](../connectors/"),
            (r"`\.\./connectors/", "`../connectors/"),
            (r"`\.\./scheduler/", "`../phase1/scheduler/"),
            (r"`\.\./graph-api/", "`../connectors/"),
        ],
    ),
    (
        "03-development/developer-manual/database/",
        [
            (r"\]\(\.\./architecture/", "](../../02-architecture/architecture/"),
            (r"\]\(\.\./evidence-management/", "](../../evidence-management/"),
        ],
    ),
    (
        "03-development/developer-manual/testing/",
        [
            (r"\]\(\.\./scheduler/", "](../phase1/scheduler/"),
            (r"\]\(\.\./developer-manual/", "](../"),
        ],
    ),
    (
        "03-development/developer-manual/connectors/",
        [
            (r"\]\(\.\./scheduler/", "](../phase1/scheduler/"),
            (r"\]\(\.\./graph-api/", "](../connectors/"),
            (r"\]\(\.\./connectors/", "](../connectors/"),
        ],
    ),
    (
        "03-development/developer-manual/phase1/scheduler/",
        [
            (r"\]\(\.\./evidence-management/", "](../../../evidence-management/"),
        ],
    ),
    (
        "03-development/operations/",
        [
            (r"\]\(\.\./connectors/", "](../developer-manual/connectors/"),
            (r"\]\(\.\./scheduler/", "](../developer-manual/phase1/scheduler/"),
            (r"\]\(\.\./graph-api/", "](../developer-manual/connectors/"),
            (r"\]\(connectors/", "](../developer-manual/connectors/"),
            (r"\]\(\.\./connector_test_workbench_design\.md\)\(\.\./connectors/", "](../developer-manual/connectors/"),
            (r"\]\(\.\./connector_test_workbench_design\.md\)\(\.\./connectors/", "](../02-architecture/design/connector_test_workbench_design.md)"),
            (r"\]\(\.\./connector_test_workbench_design\.md\)\(\.\./connectors/", ""),
            (r"\]\(\.\./enterprise_connector_api_reference\.md\)\(\.\./connectors/", "](../developer-manual/connectors/enterprise_connector_api_reference.md)"),
            (r"\]\(\.\./microsoft_graph_connector_api_reference\.md\)\(\.\./graph-api/", "](../developer-manual/connectors/microsoft_graph_connector_api_reference.md)"),
            (r"\]\(\.\./scheduler_runtime_flow\.md\)\(\.\./scheduler/", "](../developer-manual/phase1/scheduler/scheduler_runtime_flow.md)"),
            (r"\]\(\.\./runtime_call_graph\.md\)\(\.\./scheduler/", "](../developer-manual/phase1/scheduler/runtime_call_graph.md)"),
            (r"\]\(\.\./test_workbench_vs_scheduler\.md\)\(\.\./scheduler/", "](../developer-manual/phase1/scheduler/test_workbench_vs_scheduler.md)"),
            (r"docs/INTEGRATIONS/\)\(\.\./connectors/", "](../developer-manual/connectors/"),
        ],
    ),
    (
        "03-development/workbenches/",
        [
            (r"\]\(\.\./connectors/", "](../developer-manual/connectors/"),
        ],
    ),
    (
        "03-development/production/",
        [
            (r"\]\(\.\./connectors/", "](../developer-manual/connectors/"),
            (r"\]\(\.\./audit-intelligence/", "](../audit-intelligence/"),  # same parent - ok
        ],
    ),
    (
        "03-development/runbooks/",
        [
            (r"\]\(\.\./scheduler/", "](../developer-manual/phase1/scheduler/"),
        ],
    ),
    (
        "03-development/evidence-management/",
        [
            (r"\]\(\.\./design/", "](../../02-architecture/design/"),
        ],
    ),
]

# Files directly under developer-manual (not in subdirs) need special handling
DEV_MANUAL_ROOT_FILES = [
    "03-development/developer-manual/README_DEVELOPER.md",
    "03-development/developer-manual/ECS_DEVELOPER_ONBOARDING_GUIDE.md",
    "03-development/developer-manual/ECS_DEVELOPER_ONBOARDING_MANUAL.md",
    "03-development/developer-manual/DEVELOPER_MANUAL.md",
    "03-development/developer-manual/TEST_WORKBENCH_GUIDE.md",
    "03-development/developer-manual/ECS_API_REFERENCE.md",
]

DEV_MANUAL_ROOT_REPLACEMENTS = [
    (r"\]\(\.\./connectors/", "](connectors/"),
    (r"\]\(\.\./scheduler/", "](phase1/scheduler/"),
    (r"\]\(\.\./graph-api/", "](connectors/"),
    (r"`\.\./connectors/", "`connectors/"),
    (r"`\.\./scheduler/", "`phase1/scheduler/"),
    (r"`\.\./graph-api/", "`connectors/"),
]


def apply_replacements(path: Path, pairs: list[tuple[str, str]]) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    updated = text
    for old, new in pairs:
        updated = re.sub(old, new, updated)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def fix_operations_broken_links(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    updated = text
    fixes = {
        "../connector_test_workbench_design.md](../connectors/connector_test_workbench_design.md)": "../../02-architecture/design/connector_test_workbench_design.md)",
        "../enterprise_connector_api_reference.md](../connectors/enterprise_connector_api_reference.md)": "../developer-manual/connectors/enterprise_connector_api_reference.md)",
        "../microsoft_graph_connector_api_reference.md](../graph-api/microsoft_graph_connector_api_reference.md)": "../developer-manual/connectors/microsoft_graph_connector_api_reference.md)",
        "../scheduler_runtime_flow.md](../scheduler/scheduler_runtime_flow.md)": "../developer-manual/phase1/scheduler/scheduler_runtime_flow.md)",
        "../runtime_call_graph.md](../scheduler/runtime_call_graph.md)": "../developer-manual/phase1/scheduler/runtime_call_graph.md)",
        "../test_workbench_vs_scheduler.md](../scheduler/test_workbench_vs_scheduler.md)": "../developer-manual/phase1/scheduler/test_workbench_vs_scheduler.md)",
        "docs/INTEGRATIONS/](../connectors/_legacy_INTEGRATIONS_index.md)": "../developer-manual/connectors/_legacy_INTEGRATIONS_index.md)",
    }
    for old, new in fixes.items():
        updated = updated.replace(old, new)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for prefix, pairs in REPLACEMENTS_BY_PREFIX:
        base = DOCS / prefix
        if not base.exists():
            continue
        for path in base.rglob("*.md") if base.is_dir() else [base]:
            if path.is_file() and apply_replacements(path, pairs):
                changed += 1

    for rel in DEV_MANUAL_ROOT_FILES:
        path = DOCS / rel
        if path.exists() and apply_replacements(path, DEV_MANUAL_ROOT_REPLACEMENTS):
            changed += 1

    for path in (DOCS / "03-development/operations").rglob("*.md"):
        if fix_operations_broken_links(path):
            changed += 1

    # developer-manual/testing TESTING_GUIDE has ../developer-manual/ self refs
    testing_guide = DOCS / "03-development/developer-manual/testing/TESTING_GUIDE.md"
    if testing_guide.exists():
        text = testing_guide.read_text(encoding="utf-8")
        updated = text.replace("../developer-manual/", "../")
        if updated != text:
            testing_guide.write_text(updated)
            changed += 1

    print(f"Fixed {changed} files")


if __name__ == "__main__":
    main()
