# ECS Documentation Inventory

**Generated:** 2026-07-07 · **Total:** 287 markdown files across 18 folders.

This inventory reflects the reorganized `docs/` structure. Every folder has a `README.md` describing its contents and what to read first. Start at the [documentation home](README.md).

> Reorg tooling (re-runnable): `scripts/reorganize_docs.py` (moves + reference rewrite + relative-link fix), `scripts/gen_docs_folder_readmes.py` (folder READMEs), `scripts/gen_docs_inventory.py` (this file). Nothing was deleted — files were moved as git renames.

## Folders

| Folder | Docs | Purpose |
|---|---:|---|
| [`00-start-here/`](00-start-here/README.md) | 8 | Orientation, demo setup, commands, troubleshooting |
| [`ai-sdlc/`](ai-sdlc/README.md) | 33 | AI architecture, local-LLM strategy, governance |
| [`architecture/`](architecture/README.md) | 16 | Architecture index, HLD/LLD, data/deployment, workflows |
| [`archive/`](archive/README.md) | 30 | Point-in-time reports/audits + superseded docs (history) |
| [`audit-intelligence/`](audit-intelligence/README.md) | 4 | Audit LLM prompt inventory, NL queries, processing |
| [`benchmarks/`](benchmarks/README.md) | 7 | Local LLM benchmarking (16/20 GB), token estimation |
| [`connectors/`](connectors/README.md) | 22 | Enterprise connector API, framework, per-connector docs |
| [`developer-manual/`](developer-manual/README.md) | 22 | Engineering handbook, setup, config, API reference |
| [`diagrams/`](diagrams/README.md) | 3 | ER + sequence diagrams |
| [`evidence-management/`](evidence-management/README.md) | 9 | Evidence collection/validation/reuse/integrity/observations |
| [`graph-api/`](graph-api/README.md) | 4 | Microsoft Graph (SharePoint/Teams/Outlook) |
| [`operations/`](operations/README.md) | 35 | Runbooks, UAT execution, backup/recovery, support |
| [`product/`](product/README.md) | 47 | Product manual, KPI/feature/module refs, frameworks, training |
| [`production/`](production/README.md) | 13 | Deployment, hardening, monitoring, security, readiness |
| [`scheduler/`](scheduler/README.md) | 6 | Asset-driven scheduler runtime, call graph |
| [`testing/`](testing/README.md) | 6 | Test strategy, load testing, UAT validation, E2E/smoke |
| [`use-cases/`](use-cases/README.md) | 17 | Use-case matrix, API mapping, UAT readiness, phase plans |
| [`workbenches/`](workbenches/README.md) | 3 | Audit LLM Prompt Workbench + frontend workbench guides |

## Root-level docs

- [`DOCUMENTATION_INVENTORY.md`](DOCUMENTATION_INVENTORY.md)
- [`README.md`](README.md)

## Finding a document

```bash
find docs -name "*.md" | sort        # every doc
find docs -name "README.md" | sort   # folder guides
rg -i "search term" docs/            # full-text search
find docs -iname "*keyword*.md"      # by filename
```
