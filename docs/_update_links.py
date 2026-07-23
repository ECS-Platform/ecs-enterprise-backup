#!/usr/bin/env python3
"""One-off link updater for docs parent-folder reorganization. Delete after use."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# old top-level folder -> new path relative to docs/
MOVED: dict[str, str] = {
    "00-start-here": "01-product/00-start-here",
    "product": "01-product/product",
    "use-cases": "01-product/use-cases",
    "architecture": "02-architecture/architecture",
    "design": "02-architecture/design",
    "diagrams": "02-architecture/diagrams",
    "developer-manual": "03-development/developer-manual",
    "operations": "03-development/operations",
    "evidence-management": "03-development/evidence-management",
    "audit-intelligence": "03-development/audit-intelligence",
    "deployment": "03-development/deployment",
    "production": "03-development/production",
    "workbenches": "03-development/workbenches",
    "runbooks": "03-development/runbooks",
    "ai-sdlc": "03-development/ai-sdlc",
    "testing": "04-testing/testing",
    "reports": "04-testing/reports",
    "benchmarking": "04-testing/benchmarking",
    "benchmarks": "04-testing/benchmarks",
    "archive": "05-archive/archive",
    "connectors": "03-development/developer-manual/connectors",
    "scheduler": "03-development/developer-manual/phase1/scheduler",
    "api": "03-development/developer-manual/api",
    "graph-api": "03-development/developer-manual/connectors",
}

LEGACY_ABS = sorted(MOVED.items(), key=lambda kv: -len(kv[0]))


def parent_bucket(rel: Path) -> str | None:
    parts = rel.parts
    if not parts:
        return None
    if parts[0] in {"01-product", "02-architecture", "03-development", "04-testing", "05-archive"}:
        return parts[0]
    return None


def resolve_relative(from_file: Path, link: str) -> Path | None:
    if link.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if link.startswith("/"):
        return None
    base = (from_file.parent / link).resolve()
    try:
        rel = base.relative_to(DOCS.resolve())
        return rel
    except ValueError:
        return None


def relpath(from_file: Path, target: Path) -> str:
    rel = Path(
        __import__("os").path.relpath(
            (DOCS / target).resolve(), from_file.parent.resolve()
        )
    )
    return rel.as_posix()


def fix_absolute(text: str) -> str:
    for old, new in LEGACY_ABS:
        text = text.replace(f"docs/{old}/", f"docs/{new}/")
        text = text.replace(f"docs/{old}\"", f"docs/{new}\"")
        text = text.replace(f"docs/{old}`", f"docs/{new}`")
        text = text.replace(f"docs/{old})", f"docs/{new})")
    return text


def target_for_first_segment(seg: str) -> str | None:
    return MOVED.get(seg)


def fix_relative_in_file(path: Path, text: str) -> str:
    file_rel = path.relative_to(DOCS)
    bucket = parent_bucket(file_rel)
    depth = len(file_rel.parts) - 1  # depth from docs/

    link_re = re.compile(r"(\[[^\]]*\]\()([^)#]+)(\))")

    def repl(m: re.Match[str]) -> str:
        prefix, link, suffix = m.group(1), m.group(2), m.group(3)
        if link.startswith(("http://", "https://", "mailto:", "#", "/")):
            return m.group(0)

        # Absolute-from-docs links in markdown (rare)
        if link.startswith("docs/"):
            return prefix + fix_absolute(link) + suffix

        parts = Path(link).parts
        if not parts or parts[0] == "..":
            # Walk up and find first non-.. segment
            ups = 0
            i = 0
            while i < len(parts) and parts[i] == "..":
                ups += 1
                i += 1
            if i >= len(parts):
                return m.group(0)
            first = parts[i]
            rest = parts[i + 1 :]
            new_base = target_for_first_segment(first)
            if not new_base:
                return m.group(0)

            # Same-bucket sibling: link still valid
            src_bucket = bucket
            tgt_bucket = new_base.split("/")[0]
            if src_bucket and src_bucket == tgt_bucket:
                return m.group(0)

            # Rebuild target under docs/
            target = Path(new_base).joinpath(*rest)
            new_link = relpath(path, target)
            return prefix + new_link + suffix

        # Bare folder link from docs/README (e.g. product/)
        new_base = target_for_first_segment(parts[0])
        if new_base and depth == 0:
            rest = parts[1:]
            target = Path(new_base).joinpath(*rest)
            return prefix + target.as_posix() + suffix

        return m.group(0)

    return link_re.sub(repl, text)


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    updated = fix_absolute(original)
    if path.suffix == ".md" and path.relative_to(DOCS).parts[0] != "_update_links.py":
        updated = fix_relative_in_file(path, updated)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed: list[str] = []
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "_update_links.py":
            continue
        if path.suffix not in {".md", ".sql"} and path.name not in {"DOCUMENTATION_INVENTORY.md"}:
            continue
        if process_file(path):
            changed.append(str(path.relative_to(ROOT)))

    readme = ROOT / "README.md"
    if readme.exists():
        original = readme.read_text(encoding="utf-8", errors="replace")
        updated = fix_absolute(original)
        if updated != original:
            readme.write_text(updated, encoding="utf-8")
            changed.append("README.md")

    inv = DOCS / "DOCUMENTATION_INVENTORY.md"
    if inv.exists():
        original = inv.read_text(encoding="utf-8", errors="replace")
        updated = fix_absolute(original)
        if updated != original:
            inv.write_text(updated, encoding="utf-8")
            changed.append("docs/DOCUMENTATION_INVENTORY.md")

    print(f"Updated {len(changed)} files")
    for c in changed[:40]:
        print(" ", c)
    if len(changed) > 40:
        print(f"  ... and {len(changed) - 40} more")


if __name__ == "__main__":
    main()
