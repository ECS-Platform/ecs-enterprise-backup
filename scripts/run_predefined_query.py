#!/usr/bin/env python3
"""General, safe CLI runner for ALL predefined controls (any technology).

Lists every predefined control (databases, Oracle, NGINX, Linux, RHEL 8.x/9.x,
SonarQube, Trivy, GitLeaks, ...) with its status, and can run a single control
through the same live-execution path used by the Predefined Queries UI. It never
runs anything outside the engine's allow-list / live-execution gate, and never
prints credentials.

Examples:
    python scripts/run_predefined_query.py --list
    python scripts/run_predefined_query.py --list --technology Oracle
    python scripts/run_predefined_query.py --control ORX-001
    python scripts/run_predefined_query.py --control NGX-001
    python scripts/run_predefined_query.py --control RH8-001 --user analyst

For a database-only view, scripts/run_predefined_db_query.py still works.
Exit code 0 on success (or a successful listing); 1 on execution failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _all_controls():
    from modules.operations.engines.predefined_queries_engine import (
        get_all_controls,
        load_predefined_queries,
    )

    load_predefined_queries()
    return get_all_controls()


def cmd_list(technology: str = "") -> int:
    controls = _all_controls()
    if technology:
        controls = [c for c in controls if (c.get("technology") or "") == technology]
    controls = [c for c in controls if c.get("predefined")]
    if not controls:
        print("No predefined controls found." + (f" (technology={technology})" if technology else ""))
        return 0
    width = max(len(c["control_id"]) for c in controls)
    tech_w = max(len(c.get("technology", "") or "") for c in controls)
    print(f"{'CONTROL':<{width}}  {'TECHNOLOGY':<{tech_w}}  {'STATUS':<22}  QUERY/COMMAND")
    print("-" * 110)
    for c in sorted(controls, key=lambda x: (x.get("technology") or "", x["control_id"])):
        q = (c.get("query") or "").replace("\n", " ")
        if len(q) > 40:
            q = q[:37] + "..."
        print(f"{c['control_id']:<{width}}  {(c.get('technology') or ''):<{tech_w}}  "
              f"{(c.get('status') or ''):<22}  {q}")
    print(f"\n{len(controls)} predefined controls listed"
          + (f" for technology '{technology}'." if technology else "."))
    return 0


def cmd_run(control_id: str, user: str, *, persist: bool = False) -> int:
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

    result = run_predefined_query(control_id, user, persist=persist)
    # Never echo credentials; result payload contains only output + metadata.
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run predefined controls of any technology (safe, allow-listed).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List predefined controls and status.")
    group.add_argument("--control", metavar="CONTROL_ID", help="Run a single control (e.g. ORX-001).")
    parser.add_argument("--technology", default="", help="Filter --list by exact technology label.")
    parser.add_argument("--user", default="cli", help="Actor name recorded in the audit log.")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist successful output as JSON evidence (default: preview only).",
    )
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list(args.technology)
    return cmd_run(args.control, args.user, persist=bool(args.persist))


if __name__ == "__main__":
    raise SystemExit(main())
