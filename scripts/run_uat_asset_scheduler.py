#!/usr/bin/env python3
"""ECS UAT asset-driven scheduler — plan evidence collection from an asset config.

Reads a UAT/local asset inventory (YAML), classifies each asset's technology, and
routes it to either a baseline predefined-query collector or an existing
enterprise connector — then prints (or emits as JSON) the resulting evidence plan.

SAFETY MODEL
------------
* ``--dry-run`` (default, and the ONLY supported action here) makes **no** network
  call, runs **no** query, and calls **no** connector. It only plans + reports
  what *would* run, plus config-only connector readiness (SET/MISSING).
* Secrets are NEVER printed; connector config is shown masked exactly as the
  adapters expose it. The local config ships localhost/mock assets only.

USAGE
-----
    python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --dry-run
    python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --json
    python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --strict

Exit codes: 0 = OK. With ``--strict``, exit 1 if any asset is unsupported (no
connector and no predefined controls) — useful to catch inventory gaps in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Offline-safe defaults; never implicitly enable live systems.
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _default_config() -> str:
    return str(ROOT / "config" / "uat_assets.local.yaml")


def render(report: dict) -> str:
    lines = ["ECS UAT Asset-Driven Scheduler (dry-run)",
             "========================================",
             f"environment: {report['config'].get('environment', 'local')}",
             f"assets loaded: {report['config'].get('asset_count', 0)}", ""]

    lines.append("Classifications:")
    for c in report.get("classifications", []):
        route = c["route"]
        mark = {"baseline_collector": "BASE", "enterprise_connector": "CONN",
                "unsupported": "----"}.get(route, "?")
        tech = c["technology"] or "-"
        target = c["connector"] or (c["scope_value"] if route == "baseline_collector" else "-")
        lines.append(
            f"  [{mark}] {c['asset_id']:26} tech={tech:26} "
            f"route={route:20} target={target:18} controls={c['control_count']}"
        )
        if c.get("reasons"):
            lines.append(f"          reasons: {'; '.join(c['reasons'])}")

    ready = report.get("connector_readiness") or {}
    if ready:
        lines.append("")
        lines.append("Connector readiness (config-only, no live calls):")
        for name, r in sorted(ready.items()):
            lines.append(f"  - {name:20} configured={str(r.get('configured')):5} "
                         f"status={r.get('status')}")

    s = report.get("summary", {})
    lines.append("")
    lines.append(
        f"Plan: {s.get('planned_jobs', 0)} job(s) "
        f"({s.get('by_route', {}).get('baseline_collector', 0)} baseline, "
        f"{s.get('by_route', {}).get('enterprise_connector', 0)} connector), "
        f"{s.get('total_planned_controls', 0)} planned control(s), "
        f"{s.get('unsupported_assets', 0)} unsupported."
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan ECS evidence collection from a UAT/local asset inventory (dry-run).")
    parser.add_argument("--config", default=_default_config(),
                        help="Path to a UAT asset YAML (default: config/uat_assets.local.yaml).")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Plan only; make no network/connector/query calls (default).")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero if any asset is unsupported (inventory gap).")
    parser.add_argument("--no-diagnostics", action="store_true",
                        help="Skip config-only connector readiness checks.")
    args = parser.parse_args(argv)

    # Import here so the module path is set up first.
    from modules.audit_intelligence.services import asset_scheduler

    report = asset_scheduler.dry_run(
        config_path=args.config,
        include_diagnostics=not args.no_diagnostics,
    )
    print(json.dumps(report, indent=2, default=str) if args.json else render(report))

    if args.strict and report["summary"].get("unsupported_assets", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
