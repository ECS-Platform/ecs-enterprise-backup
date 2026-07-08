#!/usr/bin/env python3
"""ECS predefined-query test / inventory runner.

A thin, offline CLI over the EXISTING predefined-query engine
(``modules.operations.engines.predefined_queries_engine``) and the target
registry (``config.predefined_query_target_registry``). It does NOT create a new
engine, scheduler, or evidence repository — it exercises the existing ones in
safe/dry-run mode and (re)generates the inventory doc.

Subcommands
-----------
  inventory [--out PATH]      Regenerate docs/use-cases/PREDEFINED_QUERY_INVENTORY.md
  validate-targets [--all|ENV]  Validate config/predefined_query_targets.<env>.yaml
  dry-run [--technology T] [--limit N]
                              Mock/dry-run representative controls (no live systems)
  summary                     Print catalog + registry summary

All commands are read-only except `inventory` (writes the generated doc). No live
Docker / DB / network is required. Exit 0 on success, non-zero on validation fail.

Examples
--------
  python scripts/run_predefined_query_tests.py summary
  python scripts/run_predefined_query_tests.py inventory
  python scripts/run_predefined_query_tests.py validate-targets --all
  python scripts/run_predefined_query_tests.py dry-run --technology NGINX --limit 3
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_INVENTORY_DEFAULT = ROOT / "docs" / "use-cases" / "PREDEFINED_QUERY_INVENTORY.md"


def _controls():
    from modules.operations.engines import predefined_queries_engine as engine

    engine.load_predefined_queries()
    return engine.get_all_controls()


def _exec_type(control: dict) -> str:
    t = control.get("technology") or "Unknown"
    if t in ("PostgreSQL", "YugabyteDB", "Aurora MySQL", "Oracle", "SQL Server"):
        return "SQL"
    if t == "MongoDB":
        return "Mongo command"
    if t == "SonarQube":
        return "REST API"
    if t in ("Kubernetes", "OpenShift"):
        return "CLI (kubectl/oc)"
    if t in ("Trivy", "GitLeaks"):
        return "CLI scanner"
    return "Shell command"


# --------------------------------------------------------------------------- #
def cmd_summary(_args) -> int:
    from collections import Counter

    controls = _controls()
    techs = Counter((c.get("technology") or "Unknown") for c in controls)
    frameworks = sorted({f for c in controls for f in (c.get("frameworks") or [])})
    print("ECS Predefined-Query Summary")
    print("=" * 32)
    print(f"  Total controls:  {len(controls)}")
    print(f"  Executable:      {sum(1 for c in controls if c.get('executable'))}")
    print(f"  Technologies:    {len(techs)}")
    print(f"  Frameworks:      {len(frameworks)}")
    print("  Controls by technology:")
    for t, n in sorted(techs.items()):
        print(f"    {t:32} {n}")
    # registries
    try:
        from config import predefined_query_target_registry as reg

        print("  Target registries:")
        for env in reg.VALID_ENVIRONMENTS:
            n = len(reg.get_targets(env))
            en = len(reg.get_targets(env, enabled_only=True))
            print(f"    {env:8} {n} target(s) ({en} enabled)")
    except Exception as exc:  # noqa: BLE001
        print(f"  (registry load skipped: {type(exc).__name__})")
    return 0


def cmd_inventory(args) -> int:
    controls = sorted(_controls(), key=lambda c: (c.get("technology") or "zz", c.get("control_id") or ""))
    from collections import Counter

    techs = Counter((c.get("technology") or "Unknown") for c in controls)
    frameworks = sorted({f for c in controls for f in (c.get("frameworks") or [])})

    def esc(s):
        return str(s or "").replace("|", "\\|").replace("\n", " ")[:80]

    lines = [
        "# ECS Predefined Query Inventory",
        "",
        "> **Auto-generated** from the live control catalog (Excel control library +",
        "> `modules/operations/engines/supplementary_query_catalog.py`) via",
        "> `scripts/run_predefined_query_tests.py inventory`. Do not hand-edit; regenerate.",
        ">",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "## Summary",
        "",
        f"- **Total controls:** {len(controls)}",
        f"- **Executable (connector + driver/target available in a configured env):** "
        f"{sum(1 for c in controls if c.get('executable'))}",
        f"- **Technologies:** {len(techs)}",
        f"- **Frameworks:** {len(frameworks)}",
        "",
        "### Controls by technology",
        "",
        "| Technology | Controls |",
        "|---|---:|",
    ]
    for t, n in sorted(techs.items()):
        lines.append(f"| {t} | {n} |")
    lines += [
        "",
        "## Query catalog",
        "",
        "Columns: **Query ID · Name · Framework(s) · Technology · Exec type ·",
        "Evidence type · Status · Executable**. Query text, allow-list gating, parser",
        "and validation live in the engine and per-technology connectors.",
        "",
        "| Query ID | Name | Framework(s) | Technology | Exec type | Evidence type | Status | Executable |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in controls:
        lines.append(
            f"| {c.get('control_id','')} | {esc(c.get('control_name'))} | "
            f"{esc(', '.join(c.get('frameworks') or []))} | {c.get('technology') or 'Unknown'} | "
            f"{_exec_type(c)} | {esc(c.get('evidence_type'))} | {esc(c.get('status'))} | "
            f"{'yes' if c.get('executable') else 'no'} |"
        )
    out = Path(args.out) if args.out else _INVENTORY_DEFAULT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(controls)} controls).")
    return 0


def cmd_validate_targets(args) -> int:
    from config import predefined_query_target_registry as reg

    if args.env and args.env != "all":
        rep = reg.validate_registry(args.env)
        print(reg._fmt(rep))
        return 0 if rep.ok else 1
    reps = reg.validate_all()
    print("\n".join(reg._fmt(r) for r in reps.values()))
    return 0 if all(r.ok for r in reps.values()) else 1


def cmd_dry_run(args) -> int:
    """Mock/dry-run representative controls without touching live systems.

    Uses the engine's capability assessment (assess_execution_capability) and a
    mocked executor so nothing connects out. Prints per-control readiness.
    """
    from modules.operations.engines import predefined_queries_engine as engine

    controls = _controls()
    if args.technology:
        controls = [c for c in controls if (c.get("technology") or "").lower() == args.technology.lower()]
    controls = controls[: args.limit] if args.limit else controls
    if not controls:
        print(f"No controls matched technology='{args.technology}'.")
        return 0
    print(f"Dry-run readiness for {len(controls)} control(s) "
          f"(no live execution):")
    ok = 0
    for c in controls:
        cap = engine.assess_execution_capability(c)
        mark = "READY" if cap.get("executable") else "SKIP "
        if cap.get("executable"):
            ok += 1
        print(f"  [{mark}] {c.get('control_id'):10} {c.get('technology'):24} "
              f"{cap.get('status')}  {(cap.get('reason') or '')[:60]}")
    print(f"\n{ok}/{len(controls)} control(s) are execution-ready in the current environment.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ECS predefined-query test/inventory runner (offline).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="Catalog + registry summary.")

    p_inv = sub.add_parser("inventory", help="Regenerate the inventory doc.")
    p_inv.add_argument("--out", default="")

    p_val = sub.add_parser("validate-targets", help="Validate target registries.")
    p_val.add_argument("env", nargs="?", default="all")
    p_val.add_argument("--all", action="store_true")

    p_dry = sub.add_parser("dry-run", help="Mock/dry-run representative controls.")
    p_dry.add_argument("--technology", default="")
    p_dry.add_argument("--limit", type=int, default=0)

    args = parser.parse_args(argv)
    if args.command == "summary":
        return cmd_summary(args)
    if args.command == "inventory":
        return cmd_inventory(args)
    if args.command == "validate-targets":
        if getattr(args, "all", False):
            args.env = "all"
        return cmd_validate_targets(args)
    if args.command == "dry-run":
        return cmd_dry_run(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
