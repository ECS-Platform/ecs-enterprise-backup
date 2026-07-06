#!/usr/bin/env python3
"""Minimal, safe CLI runner for predefined DATABASE queries.

Lists the PostgreSQL / YugabyteDB / Aurora MySQL predefined queries and their
execution status, and can run a single allow-listed query against a reachable
database. It never executes anything outside the per-technology allow-list and
never prints credentials.

Examples:
    python scripts/run_predefined_db_query.py --list
    python scripts/run_predefined_db_query.py --control PGX-001
    python scripts/run_predefined_db_query.py --control MYX-001 --user analyst

Exit code 0 on success (or successful listing); 1 on execution failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Technologies handled by this DB runner.
_DB_TECHNOLOGIES = {"PostgreSQL", "YugabyteDB", "Aurora MySQL"}


def _db_controls() -> list[dict]:
    from modules.operations.engines.predefined_queries_engine import (
        get_all_controls,
        load_predefined_queries,
    )

    load_predefined_queries()
    return [c for c in get_all_controls() if c.get("technology") in _DB_TECHNOLOGIES]


def cmd_list() -> int:
    controls = _db_controls()
    if not controls:
        print("No database predefined queries found.")
        return 0
    width = max(len(c["control_id"]) for c in controls)
    print(f"{'CONTROL':<{width}}  {'TECHNOLOGY':<14}  {'STATUS':<22}  QUERY")
    print("-" * 100)
    for c in sorted(controls, key=lambda x: x["control_id"]):
        q = (c.get("query") or "").replace("\n", " ")
        if len(q) > 40:
            q = q[:37] + "..."
        print(f"{c['control_id']:<{width}}  {c.get('technology', ''):<14}  "
              f"{c.get('status', ''):<22}  {q}")
    print(f"\n{len(controls)} database predefined queries "
          f"(PostgreSQL / YugabyteDB / Aurora MySQL).")
    return 0


def cmd_run(control_id: str, user: str) -> int:
    from modules.operations.engines.predefined_queries_engine import (
        get_control_by_id,
        load_predefined_queries,
        run_predefined_query,
    )

    load_predefined_queries()
    control = get_control_by_id(control_id)
    if not control:
        print(json.dumps({"ok": False, "error": f"Unknown control: {control_id}"}, indent=2))
        return 1
    if control.get("technology") not in _DB_TECHNOLOGIES:
        print(json.dumps({
            "ok": False,
            "error": f"{control_id} is not a database control "
                     f"(technology={control.get('technology')!r}). Use --list to see DB controls.",
        }, indent=2))
        return 1

    result = run_predefined_query(control_id, user)
    # Never echo credentials; result payload contains only query output + metadata.
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run predefined database queries (safe, allow-listed).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List DB predefined queries and status.")
    group.add_argument("--control", metavar="CONTROL_ID", help="Run a single control (e.g. PGX-001).")
    parser.add_argument("--user", default="cli", help="Actor name recorded in the audit log.")
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list()
    return cmd_run(args.control, args.user)


if __name__ == "__main__":
    raise SystemExit(main())
