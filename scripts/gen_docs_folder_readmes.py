#!/usr/bin/env python3
"""Generate a newcomer-friendly README.md in each docs/ subfolder.

Each README explains what the folder contains, which document to read first, a
listed index of the folder's documents (auto-derived from actual files), and
related folders. Re-runnable; overwrites only the folder README.md files.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# folder -> (title, purpose, read_first_basename, related_folders)
FOLDERS: dict[str, tuple[str, str, str, list[str]]] = {
    "00-start-here": (
        "Start Here",
        "Orientation for anyone new to ECS: what it is, how to run it locally in "
        "demo mode, common commands, and troubleshooting. Read this folder first.",
        "ARCHITECTURE_OVERVIEW.md",
        ["developer-manual", "product", "operations"],
    ),
    "developer-manual": (
        "Developer Manual",
        "Everything an engineer needs to build on ECS: setup, engineering "
        "handbook, environment/config framework, module ownership, API reference, "
        "and coding/technology guides.",
        "README_DEVELOPER.md",
        ["00-start-here", "architecture", "testing", "connectors"],
    ),
    "operations": (
        "Operations",
        "Run and operate ECS: runbooks, UAT execution, predefined-query execution, "
        "backup/recovery, rollback, go-live, and support playbooks.",
        "ECS_OPERATIONS_RUNBOOK.md",
        ["production", "scheduler", "connectors", "testing"],
    ),
    "workbenches": (
        "Workbenches",
        "Interactive ECS test/debug surfaces: the Audit LLM Prompt Workbench and "
        "related frontend workbench guides. (Connector Test Workbench design lives "
        "in `connectors/`.)",
        "audit_llm_prompt_workbench_design.md",
        ["connectors", "audit-intelligence", "benchmarks"],
    ),
    "benchmarks": (
        "Benchmarks",
        "Local LLM benchmarking: 16 GB / 20 GB laptop testing, token estimation, "
        "benchmark plans and performance reports.",
        "audit_llm_local_benchmark_plan.md",
        ["audit-intelligence", "workbenches", "ai-sdlc"],
    ),
    "connectors": (
        "Connectors",
        "Enterprise evidence connectors: API reference, connector framework, the "
        "Connector Test Workbench, UAT setup, and per-connector integration docs "
        "(Jira, Confluence, ServiceNow, SonarQube, Prisma, Tripwire, etc.).",
        "enterprise_connector_api_reference.md",
        ["graph-api", "scheduler", "evidence-management", "operations"],
    ),
    "graph-api": (
        "Microsoft Graph API",
        "Microsoft Graph integration for SharePoint, Teams, and Outlook: auth flow, "
        "discovery/retrieval, pagination, and UAT testing. Connector-specific.",
        "microsoft_graph_connector_api_reference.md",
        ["connectors", "evidence-management"],
    ),
    "scheduler": (
        "Scheduler",
        "The asset-driven scheduler runtime: end-to-end flow, runtime call graph, "
        "asset discovery, and how scheduled evidence pull differs from the "
        "workbench.",
        "scheduler_runtime_flow.md",
        ["connectors", "evidence-management", "architecture"],
    ),
    "evidence-management": (
        "Evidence Management",
        "The evidence lifecycle: collection, validation, reuse, hash integrity, the "
        "evidence repository, observations, and predefined-query evidence.",
        "evidence_reuse_lifecycle_functional_design.md",
        ["audit-intelligence", "scheduler", "connectors"],
    ),
    "audit-intelligence": (
        "Audit Intelligence",
        "Audit LLM prompt inventory, server-side processing, natural-language audit "
        "queries, observation generation, and audit-intelligence persistence.",
        "audit_llm_prompt_inventory.md",
        ["workbenches", "benchmarks", "evidence-management"],
    ),
    "ai-sdlc": (
        "AI / AI-SDLC",
        "AI architecture, local-LLM strategy, model abstraction, AI governance, and "
        "the LLM use-case catalogs and coverage matrices.",
        "README.md",
        ["audit-intelligence", "benchmarks", "architecture"],
    ),
    "architecture": (
        "Architecture",
        "System architecture: index, HLD/LLD, data & deployment architecture, "
        "enterprise review, and workflow/state/sequence models.",
        "ARCHITECTURE_INDEX.md",
        ["diagrams", "developer-manual", "product"],
    ),
    "product": (
        "Product",
        "Product-facing documentation: master product manual, feature/module/KPI "
        "references, use-case catalogs, personas, screen catalog, compliance "
        "frameworks, and training/admin/operator guides.",
        "ECS_MASTER_PRODUCT_MANUAL.md",
        ["use-cases", "architecture", "00-start-here"],
    ),
    "testing": (
        "Testing",
        "Test strategy and validation: load testing, UAT validation runbooks, "
        "E2E/smoke test guides, and screen/KPI/workflow validation reports.",
        "E2E_SMOKE_TEST_GUIDE.md",
        ["operations", "developer-manual", "use-cases"],
    ),
    "production": (
        "Production",
        "Production readiness: deployment reference, hardening, monitoring, "
        "security, encryption, SSO/OIDC, DR/observability enablement, and the "
        "readiness gap register.",
        "PRODUCTION_READINESS_GAP_REGISTER.md",
        ["operations", "architecture", "developer-manual"],
    ),
    "use-cases": (
        "Use Cases",
        "ECS use-case documentation: implementation matrix, backend/API mapping, "
        "frontend manual testing, UAT readiness, and the phase-based use-case "
        "plans/backlogs.",
        "use_case_implementation_matrix.md",
        ["product", "evidence-management", "testing"],
    ),
    "diagrams": (
        "Diagrams",
        "Visual references: entity-relationship (ER) diagrams and sequence "
        "diagrams. Architecture prose lives in `architecture/`.",
        "ecs_sequence_diagrams.md",
        ["architecture", "scheduler"],
    ),
    "archive": (
        "Archive",
        "Point-in-time reports, audits, migration/rollback records, and superseded "
        "knowledge-consolidation documents. Retained for history — not the current "
        "source of truth. Prefer the live folders for up-to-date guidance.",
        "",
        ["product", "developer-manual"],
    ),
}


def title_from(basename: str) -> str:
    stem = basename[:-3] if basename.endswith(".md") else basename
    return stem.replace("_", " ")


def gen_readme(folder: str) -> str:
    title, purpose, read_first, related = FOLDERS[folder]
    fdir = DOCS / folder
    files = sorted(p.name for p in fdir.glob("*.md") if p.name != "README.md")

    lines = [f"# {title}", "", purpose, ""]

    if read_first and (fdir / read_first).exists():
        lines += [f"## Read first", "",
                  f"- [`{read_first}`]({read_first}) — {title_from(read_first)}", ""]
    elif folder == "archive":
        lines += ["> These documents are historical. Do not rely on them for "
                  "current behavior.", ""]

    lines += [f"## Documents in this folder ({len(files)})", ""]
    if files:
        for f in files:
            lines.append(f"- [`{f}`]({f}) — {title_from(f)}")
    else:
        lines.append("_(No documents yet.)_")
    lines.append("")

    if related:
        lines += ["## Related folders", ""]
        for r in related:
            rtitle = FOLDERS.get(r, (r,))[0]
            lines.append(f"- [`../{r}/`](../{r}/README.md) — {rtitle}")
        lines.append("")

    lines += ["---", "",
              "See the [documentation home](../README.md) for role-based reading "
              "paths (developer, tester, UAT operator, business/auditor, LLM/benchmark).",
              ""]
    return "\n".join(lines)


def main() -> int:
    for folder in FOLDERS:
        fdir = DOCS / folder
        fdir.mkdir(parents=True, exist_ok=True)
        (fdir / "README.md").write_text(gen_readme(folder), encoding="utf-8")
        print(f"wrote docs/{folder}/README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
