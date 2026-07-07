#!/usr/bin/env python3
"""Regenerate docs/DOCUMENTATION_INVENTORY.md from the current folder structure."""

from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

PURPOSE = {
    "00-start-here": "Orientation, demo setup, commands, troubleshooting",
    "developer-manual": "Engineering handbook, setup, config, API reference",
    "operations": "Runbooks, UAT execution, backup/recovery, support",
    "workbenches": "Audit LLM Prompt Workbench + frontend workbench guides",
    "benchmarks": "Local LLM benchmarking (16/20 GB), token estimation",
    "connectors": "Enterprise connector API, framework, per-connector docs",
    "graph-api": "Microsoft Graph (SharePoint/Teams/Outlook)",
    "scheduler": "Asset-driven scheduler runtime, call graph",
    "evidence-management": "Evidence collection/validation/reuse/integrity/observations",
    "audit-intelligence": "Audit LLM prompt inventory, NL queries, processing",
    "ai-sdlc": "AI architecture, local-LLM strategy, governance",
    "architecture": "Architecture index, HLD/LLD, data/deployment, workflows",
    "product": "Product manual, KPI/feature/module refs, frameworks, training",
    "testing": "Test strategy, load testing, UAT validation, E2E/smoke",
    "production": "Deployment, hardening, monitoring, security, readiness",
    "use-cases": "Use-case matrix, API mapping, UAT readiness, phase plans",
    "diagrams": "ER + sequence diagrams",
    "archive": "Point-in-time reports/audits + superseded docs (history)",
}


def main() -> int:
    total = len(list(DOCS.rglob("*.md")))
    folders = sorted((p for p in DOCS.iterdir() if p.is_dir()), key=lambda p: p.name)

    out: list[str] = []
    out += [
        "# ECS Documentation Inventory",
        "",
        f"**Generated:** {date.today().isoformat()} · **Total:** {total} markdown files "
        f"across {len(folders)} folders.",
        "",
        "This inventory reflects the reorganized `docs/` structure. Every folder has a "
        "`README.md` describing its contents and what to read first. Start at the "
        "[documentation home](README.md).",
        "",
        "> Reorg tooling (re-runnable): `scripts/reorganize_docs.py` (moves + reference "
        "rewrite + relative-link fix), `scripts/gen_docs_folder_readmes.py` (folder "
        "READMEs), `scripts/gen_docs_inventory.py` (this file). Nothing was deleted — "
        "files were moved as git renames.",
        "",
        "## Folders",
        "",
        "| Folder | Docs | Purpose |",
        "|---|---:|---|",
    ]
    for f in folders:
        n = len(list(f.glob("*.md")))
        out.append(f"| [`{f.name}/`]({f.name}/README.md) | {n} | {PURPOSE.get(f.name, '')} |")

    out += ["", "## Root-level docs", ""]
    for p in sorted(DOCS.glob("*.md")):
        out.append(f"- [`{p.name}`]({p.name})")

    out += [
        "",
        "## Finding a document",
        "",
        "```bash",
        'find docs -name "*.md" | sort        # every doc',
        'find docs -name "README.md" | sort   # folder guides',
        'rg -i "search term" docs/            # full-text search',
        'find docs -iname "*keyword*.md"      # by filename',
        "```",
        "",
    ]
    (DOCS / "DOCUMENTATION_INVENTORY.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote docs/DOCUMENTATION_INVENTORY.md ({total} md, {len(folders)} folders)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
