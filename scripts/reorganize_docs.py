#!/usr/bin/env python3
"""One-shot docs/ reorganization into a newcomer-friendly folder structure.

Moves every ``docs/**/*.md`` into one of the 19 target folders using an explicit
mapping (git mv, so history is preserved as a rename), then rewrites every
``docs/<old>`` reference across the whole repo (md/code/config) to its new path.

Safe by design:
  * Nothing is deleted; every file is *moved* to a target folder.
  * Duplicate basenames are disambiguated by a per-destination prefix so no move
    overwrites another file.
  * A dry-run (default) prints the plan without touching anything.

Usage:
  python scripts/reorganize_docs.py --plan     # print the mapping only
  python scripts/reorganize_docs.py --apply    # git mv + rewrite references
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Target folders (created if missing).
TARGET_FOLDERS = [
    "00-start-here", "developer-manual", "operations", "workbenches", "benchmarks",
    "connectors", "graph-api", "scheduler", "evidence-management",
    "audit-intelligence", "ai-sdlc", "architecture", "product", "testing",
    "production", "use-cases", "diagrams", "archive",
]

# ---------------------------------------------------------------------------
# Explicit mapping: <relative path under docs/> -> <target folder>.
# Files not listed fall back to RULES (prefix/dir heuristics) below, and finally
# to "archive" so nothing is ever left unmapped.
# ---------------------------------------------------------------------------
EXPLICIT: dict[str, str] = {
    # ---- 00-start-here (orientation, setup, quickstart) ----
    "README.md": "__keep__",  # landing page stays at docs/README.md
    "ARCHITECTURE_OVERVIEW.md": "00-start-here",
    "COMMON_COMMANDS.md": "00-start-here",
    "DEMO_MODE_SETUP.md": "00-start-here",
    "ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md": "00-start-here",
    "LOCAL_AUTH_DEMO_FIX.md": "00-start-here",
    "TROUBLESHOOTING_GUIDE.md": "00-start-here",

    # ---- developer-manual ----
    "DEVELOPER_SETUP_GUIDE.md": "developer-manual",
    "LOCAL_DEVELOPMENT_GUIDE.md": "developer-manual",
    "ECS_ENGINEERING_HANDBOOK.md": "developer-manual",
    "ENVIRONMENT_CONFIGURATION.md": "developer-manual",
    "ENVIRONMENT_CONFIGURATION_FRAMEWORK.md": "developer-manual",
    "ENVIRONMENT_FRAMEWORK_READINESS_REPORT.md": "developer-manual",
    "ECS_APPLICATION_CONFIGURATION_MATRIX.md": "developer-manual",
    "ECS_CONFIGURATION_DEPENDENCY_MATRIX.md": "developer-manual",
    "ECS_ENVIRONMENT_VALIDATION_MATRIX.md": "developer-manual",
    "ECS_PERSONA_CONFIGURATION_MATRIX.md": "developer-manual",
    "ECS_HARDCODED_DEPENDENCY_INVENTORY.md": "developer-manual",
    "ECS_DEPENDENCY_REPORT.md": "developer-manual",
    "ECS_MODULE_OWNERSHIP.md": "developer-manual",
    "ECS_REFACTOR_PLAN.md": "developer-manual",
    "ECS_RBAC_LEGACY_FLAWS.md": "developer-manual",
    "ECS_MIGRATION_REPORT.md": "archive",
    "ECS_ROLLBACK_REPORT.md": "archive",
    "ECS_NAVIGATION_REGROUPING_REPORT.md": "archive",
    "AI_SDLC_RESTORATION_REPORT.md": "archive",

    # ---- product ----
    "ECS_BENCHMARK_DEMO_MODULE.md": "benchmarks",

    # ---- documentation meta (inventory / audits) ----
    "DOCUMENTATION_INVENTORY.md": "__keep__",  # stays at docs/ root (referenced widely)
    "DOCUMENTATION_AUDIT_REPORT.md": "archive",
    "DOCUMENTATION_GAP_ANALYSIS.md": "archive",
    "FINAL_REPOSITORY_HEALTH_REPORT.md": "archive",

    # ---- architecture (root-level) ----
    "ECS_Architecture_and_Deployment_Guide.md": "architecture",

    # ---- recovery/runbook root files -> operations ----
    "RECOVERY_RUNBOOK.md": "operations",

    # ---- connectors (root-level loose files) ----
    "enterprise_connector_api_reference.md": "connectors",
    "connector_test_workbench_design.md": "connectors",
    "connector_frontend_testing_matrix.md": "connectors",
    "connector_frontend_manual_testing.md": "connectors",
    "uat_connector_credentials_guide.md": "connectors",

    # ---- graph-api (root-level loose files) ----
    "microsoft_graph_connector_api_reference.md": "graph-api",
    "microsoft_graph_sharepoint_teams_uat_testing.md": "graph-api",

    # ---- scheduler ----
    "scheduler_runtime_flow.md": "scheduler",
    "runtime_call_graph.md": "scheduler",
    "test_workbench_vs_scheduler.md": "scheduler",

    # ---- evidence-management ----
    "evidence_reuse_lifecycle_functional_design.md": "evidence-management",
    "evidence_reuse_frontend_manual_testing.md": "evidence-management",
    "predefined_queries_by_technology.md": "evidence-management",

    # ---- workbenches ----
    "audit_llm_prompt_workbench_design.md": "workbenches",
    "audit_llm_frontend_manual_testing.md": "workbenches",

    # ---- benchmarks ----
    "audit_llm_16gb_20gb_testing_guide.md": "benchmarks",
    "audit_llm_local_benchmark_plan.md": "benchmarks",

    # ---- audit-intelligence ----
    "audit_llm_prompt_inventory.md": "audit-intelligence",
    "audit_llm_server_side_processing.md": "audit-intelligence",

    # ---- use-cases ----
    "use_case_backend_api_mapping.md": "use-cases",
    "use_case_frontend_manual_testing.md": "use-cases",
    "use_case_implementation_matrix.md": "use-cases",
    "use_case_uat_readiness_report.md": "use-cases",
    "usecase_batch1_evidence_workflows.md": "use-cases",
    "frontend_use_case_execution_verification.md": "use-cases",

    # ---- uat config -> operations ----
    "uat_ip_configuration_guide.md": "operations",

    # ---- API reference -> developer-manual ----
    "API/ECS_API_REFERENCE.md": "developer-manual",
}

# Directory-prefix rules (applied when a file is not in EXPLICIT). First match wins.
DIR_RULES: list[tuple[str, str]] = [
    ("AI/", "ai-sdlc"),
    ("API/", "developer-manual"),
    ("AUDIT/", "archive"),
    ("CONTROLS/", "product"),
    ("DEMO/", "00-start-here"),
    ("DEPLOYMENT/", "production"),
    ("DEVELOPER/", "developer-manual"),
    ("EVIDENCE/", "evidence-management"),
    ("FRAMEWORKS/", "product"),
    ("INTEGRATIONS/", "connectors"),
    ("KPI/", "product"),
    ("PHASE1/", "use-cases"),
    ("PRODUCT/", "product"),
    ("PRODUCTION/", "production"),
    ("SECURITY/", "production"),
    ("TESTING/", "testing"),
    ("TRAINING/", "product"),
    ("UAT/", "testing"),
    ("UX/", "archive"),
    ("WORKFLOWS/", "architecture"),
    ("architecture/", "architecture"),
    ("benchmarks/", "benchmarks"),
    ("diagrams/", "diagrams"),
    ("executive/", "archive"),
    ("hld/", "architecture"),
    ("lld/", "architecture"),
    ("operations/", "operations"),
    ("product_manual/", "product"),
]

# Per-file basename overrides within a directory (finer control than DIR_RULES).
FILE_OVERRIDES: dict[str, str] = {
    # DEVELOPER connector/graph/evidence/scheduler specifics -> their domains
    "DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md": "graph-api",
    "DEVELOPER/CONNECTOR_DEEPENING_GUIDE.md": "connectors",
    "DEVELOPER/ENTERPRISE_CONNECTOR_UAT_SETUP.md": "connectors",
    "DEVELOPER/INTEGRATION_ADAPTERS_GUIDE.md": "connectors",
    "DEVELOPER/EVIDENCE_COLLECTION_GUIDE.md": "evidence-management",
    "DEVELOPER/EVIDENCE_VALIDATION_GUIDE.md": "evidence-management",
    "DEVELOPER/OBSERVATION_AND_REPOSITORY_GUIDE.md": "evidence-management",
    "DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md": "scheduler",
    "DEVELOPER/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md": "audit-intelligence",
    "DEVELOPER/DEMO_RUNBOOK.md": "operations",
    "DEVELOPER/LEADERSHIP_DEMO_SCRIPT.md": "product",
    "DEVELOPER/E2E_SMOKE_TEST_GUIDE.md": "testing",
    "DEVELOPER/PERFORMANCE_AND_HARDENING_GUIDE.md": "production",
    "DEVELOPER/PRODUCTION_HARDENING_GUIDE.md": "production",
    "DEVELOPER/PRODUCTION_READINESS_GAP_REGISTER.md": "production",
    "DEVELOPER/UAT_INTEGRATION_GUIDE.md": "connectors",
    "DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md": "connectors",
    "DEVELOPER/ASSET_DISCOVERY_GUIDE.md": "scheduler",
    # AI benchmark/testing specifics
    "AI/ECS_LOCAL_LLM_TESTING_GUIDE.md": "benchmarks",
    "AI/ECS_AI_PERFORMANCE_BENCHMARK.md": "benchmarks",
    "AI/ECS_LOCAL_LLM_OPERATIONS_GUIDE.md": "operations",
    "AI/ECS_LOCAL_LLM_DEPLOYMENT_GUIDE.md": "production",
    # operations: predefined-query execution belongs to evidence-management
    "operations/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md": "evidence-management",
    # TESTING load
    "TESTING/ECS_LOAD_TESTING_REFERENCE.md": "testing",
    # benchmarks dir
    "benchmarks/16K_1K_TOKEN_VALIDATION_BENCHMARK.md": "benchmarks",
}

# Disambiguation prefixes for known duplicate basenames, keyed by original dir.
# Ensures no collision after the move.
DEDUP_PREFIX: dict[str, str] = {
    "AUDIT/ECS_KPI_DICTIONARY.md": "AUDIT_",
    "product_manual/ECS_KPI_DICTIONARY.md": "PRODUCT_MANUAL_",
    "AUDIT/ECS_SCREEN_CATALOG.md": "AUDIT_",
    "product_manual/ECS_SCREEN_CATALOG.md": "PRODUCT_MANUAL_",
    "product_manual/ECS_PRODUCT_MANUAL.md": "PRODUCT_MANUAL_",
    "TRAINING/ECS_PRODUCT_MANUAL.md": "TRAINING_",
    "AI/ECS_LOCAL_LLM_OPERATIONS_GUIDE.md": "AI_",
    "operations/ECS_LOCAL_LLM_OPERATIONS_GUIDE.md": "OPERATIONS_",
}


def all_md_files() -> list[str]:
    return sorted(
        str(p.relative_to(DOCS)) for p in DOCS.rglob("*.md")
    )


def target_for(rel: str) -> str:
    """Return the target folder for a docs-relative md path."""
    if rel in EXPLICIT:
        return EXPLICIT[rel]
    if rel in FILE_OVERRIDES:
        return FILE_OVERRIDES[rel]
    for prefix, folder in DIR_RULES:
        if rel.startswith(prefix):
            return folder
    # Root-level unmapped file -> archive (safe default; should be rare).
    return "archive"


def dest_path(rel: str, folder: str) -> str:
    """Compute the destination docs-relative path (with dedup prefix).

    Existing subfolder ``README.md`` files are preserved under a
    ``_legacy_<DIR>_index.md`` name so their content survives while leaving
    ``README.md`` free for the fresh, newcomer-friendly folder READMEs.
    """
    p = Path(rel)
    base = p.name
    if base == "README.md" and p.parent != Path("."):
        src_dir = p.parent.name.upper().replace("-", "_")
        return f"{folder}/_legacy_{src_dir}_index.md"
    if rel in DEDUP_PREFIX:
        base = DEDUP_PREFIX[rel] + base
    return f"{folder}/{base}"


def build_plan() -> list[tuple[str, str]]:
    """Return list of (old_rel, new_rel) moves (skipping __keep__ files)."""
    plan: list[tuple[str, str]] = []
    seen_dest: dict[str, str] = {}
    for rel in all_md_files():
        # Skip files already inside a target folder that keep their place? No —
        # we still normalize every folder. But skip folder README placeholders we
        # will generate fresh (existing README.md inside old dirs move too).
        folder = target_for(rel)
        if folder == "__keep__":
            continue
        new_rel = dest_path(rel, folder)
        if new_rel == rel:
            continue  # already in place
        if new_rel in seen_dest:
            raise SystemExit(
                f"COLLISION: {rel} and {seen_dest[new_rel]} both -> {new_rel}")
        seen_dest[new_rel] = rel
        plan.append((rel, new_rel))
    return plan


def git_mv(old_rel: str, new_rel: str) -> None:
    old = DOCS / old_rel
    new = DOCS / new_rel
    new.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "mv", str(old), str(new)], cwd=ROOT, check=True)


def git_rename_plan() -> list[tuple[str, str]]:
    """Derive (old_rel, new_rel) pairs from git's staged renames under docs/.

    Uses ``git status --porcelain -M`` so it reflects the moves already applied,
    returning docs-relative paths (stripping the leading ``docs/``).
    """
    out = subprocess.run(
        ["git", "status", "--porcelain", "-M"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout
    pairs: list[tuple[str, str]] = []
    for line in out.splitlines():
        # Rename lines look like: 'R  old -> new'
        if not line[:2].strip().startswith("R"):
            continue
        if " -> " not in line:
            continue
        body = line[3:]
        old, new = body.split(" -> ", 1)
        old, new = old.strip().strip('"'), new.strip().strip('"')
        if old.startswith("docs/") and new.startswith("docs/"):
            pairs.append((old[len("docs/"):], new[len("docs/"):]))
    return pairs


def rewrite_references(plan: list[tuple[str, str]]) -> dict[str, int]:
    """Rewrite every ``docs/<old>`` reference across the repo to ``docs/<new>``.

    Operates on absolute-style references (``docs/<path>.md``) which appear in
    code, config, CHANGELOG, and markdown. Case-insensitive on the old directory
    segment is NOT applied — we match the exact stored path. Returns a per-file
    change count. Relative in-markdown links are handled separately by
    :func:`fix_markdown_relative_links`.
    """
    mapping = {f"docs/{old}": f"docs/{new}" for old, new in plan}
    # Longest keys first so nested paths replace before shorter prefixes.
    keys = sorted(mapping, key=len, reverse=True)
    changed: dict[str, int] = {}
    # Scan the whole repo except VCS/venv/build dirs.
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
    text_ext = {".md", ".py", ".yaml", ".yml", ".txt", ".sh", ".cfg", ".ini",
                ".toml", ".example", ".env"}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix not in text_ext and path.name not in (".env.uat.example",):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        original = text
        n = 0
        for k in keys:
            if k in text:
                cnt = text.count(k)
                text = text.replace(k, mapping[k])
                n += cnt
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed[str(path.relative_to(ROOT))] = n
    return changed


def fix_markdown_relative_links(plan: list[tuple[str, str]]) -> dict[str, int]:
    """Repair relative ``*.md`` links inside docs after files were moved.

    Strategy: build a map of old_docs_relative -> new_docs_relative. For each
    CURRENT markdown file (at its NEW path), find its OLD path (reverse map). For
    every relative link, resolve it against the file's OLD directory to an old
    docs-relative target; if that target moved, recompute the link relative to the
    file's NEW directory. Absolute ``docs/...`` links are left to
    :func:`rewrite_references`. Returns per-file fix counts.
    """
    import os
    import re

    old_to_new = {old: new for old, new in plan}
    new_to_old = {new: old for old, new in plan}
    link_re = re.compile(r"(\]\()([^)]+?)(\))")

    changed: dict[str, int] = {}
    for md in DOCS.rglob("*.md"):
        new_rel = str(md.relative_to(DOCS))
        old_rel = new_to_old.get(new_rel, new_rel)  # unmoved files keep their path
        old_dir = str(Path(old_rel).parent)
        new_dir = str(Path(new_rel).parent)
        text = md.read_text(encoding="utf-8", errors="ignore")

        def repl(m: "re.Match[str]") -> str:
            pre, link, post = m.group(1), m.group(2), m.group(3)
            raw = link.strip()
            if raw.startswith(("http://", "https://", "#", "mailto:", "docs/")):
                return m.group(0)
            frag = ""
            if "#" in raw:
                raw, frag = raw.split("#", 1)
                frag = "#" + frag
            if not raw.endswith(".md"):
                return m.group(0)
            # Resolve against the file's OLD directory to an old docs-relative path.
            old_target = os.path.normpath(os.path.join(old_dir, raw)) if old_dir != "." else os.path.normpath(raw)
            old_target = old_target.replace(os.sep, "/")
            new_target = old_to_new.get(old_target)
            if new_target is None:
                return m.group(0)  # target didn't move (or link already valid)
            # Recompute relative path from the file's NEW directory.
            new_link = os.path.relpath(
                (DOCS / new_target).resolve(),
                (DOCS / new_dir).resolve() if new_dir != "." else DOCS.resolve(),
            ).replace(os.sep, "/")
            return f"{pre}{new_link}{frag}{post}"

        new_text, n = link_re.subn(repl, text)
        if n and new_text != text:
            # subn counts all links; recount actual changes
            actual = sum(1 for _ in link_re.finditer(text)) and (new_text != text)
            md.write_text(new_text, encoding="utf-8")
            changed[str(md.relative_to(ROOT))] = new_text != text and _count_link_diffs(text, new_text)
    return {k: v for k, v in changed.items() if v}


def _count_link_diffs(a: str, b: str) -> int:
    import re
    la = re.findall(r"\]\(([^)]+)\)", a)
    lb = re.findall(r"\]\(([^)]+)\)", b)
    return sum(1 for x, y in zip(la, lb) if x != y)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform git mv (default: plan only)")
    ap.add_argument("--rewrite-refs", action="store_true",
                    help="rewrite docs/<old> references repo-wide (run AFTER --apply)")
    ap.add_argument("--fix-relative-links", action="store_true",
                    help="repair relative *.md links inside docs (run AFTER --apply)")
    args = ap.parse_args()

    if args.rewrite_refs:
        # Prefer git's actual rename records (works AFTER moves are applied);
        # fall back to a freshly-computed plan if git shows nothing.
        plan = git_rename_plan() or build_plan()
        changed = rewrite_references(plan)
        total = sum(changed.values())
        print(f"# rewrote {total} reference(s) across {len(changed)} file(s)")
        for f, n in sorted(changed.items()):
            print(f"  {n:4}  {f}")
        return 0

    if args.fix_relative_links:
        plan = git_rename_plan() or build_plan()
        changed = fix_markdown_relative_links(plan)
        total = sum(changed.values())
        print(f"# fixed {total} relative link(s) across {len(changed)} file(s)")
        for f, n in sorted(changed.items()):
            print(f"  {n:4}  {f}")
        return 0

    # Ensure target folders exist (with .gitkeep so empty ones are trackable).
    if args.apply:
        for f in TARGET_FOLDERS:
            (DOCS / f).mkdir(parents=True, exist_ok=True)

    plan = build_plan()
    print(f"# {len(plan)} moves planned")
    for old_rel, new_rel in plan:
        print(f"docs/{old_rel}  ->  docs/{new_rel}")

    if not args.apply:
        print("\n(dry-run; pass --apply to perform git mv)")
        return 0

    for old_rel, new_rel in plan:
        git_mv(old_rel, new_rel)
    print(f"\nApplied {len(plan)} moves via git mv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
