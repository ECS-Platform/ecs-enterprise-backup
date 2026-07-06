#!/usr/bin/env python3
"""ECS Audit Intelligence report (Milestone 1) — read-only, offline.

Inspect the Technology -> Control -> Framework mapping and (optionally) the asset
inventory produced by the audit-intelligence layer, without a browser or any live
Docker / DB / network. Useful for onboarding, demos, and CI smoke checks.

Sections:
  * mapping   — technology/control/framework coverage derived from the 167-control
                predefined-query catalog.
  * assets    — unified asset inventory + fingerprints from the SAFE offline sources
                (docker-compose parse and/or the existing enterprise-GRC CMDB).

Usage:
    python scripts/audit_intelligence_report.py
    python scripts/audit_intelligence_report.py --section mapping --technology NGINX
    python scripts/audit_intelligence_report.py --section assets --docker-compose --enterprise-grc
    python scripts/audit_intelligence_report.py --json

Notes:
  * Never makes network calls. ServiceNow discovery is intentionally NOT wired here
    (it needs an injected/live transport); this CLI only uses offline sources.
  * Read-only: prints derived views; changes nothing.
Exit code is always 0 on success (this is a reporting tool).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_mapping_section(args) -> dict[str, Any]:
    from modules.audit_intelligence.services import mapping_service

    if args.technology:
        detail = mapping_service.technology_detail(args.technology)
        return {"kind": "technology_detail", "query": args.technology, "detail": detail}
    if args.framework:
        detail = mapping_service.framework_detail(args.framework)
        return {"kind": "framework_detail", "query": args.framework, "detail": detail}
    return {
        "kind": "mapping_overview",
        "stats": mapping_service.stats(),
        "technologies": mapping_service.technologies(),
        "frameworks": mapping_service.frameworks(),
    }


def build_assets_section(args) -> dict[str, Any]:
    from modules.audit_intelligence.services import asset_service

    # SAFE offline sources only. Default to docker-compose if neither is chosen so
    # the section is never empty when a developer just runs `--section assets`.
    include_compose = args.docker_compose or not args.enterprise_grc
    assets = asset_service.discover_assets(
        include_docker_compose=include_compose,
        include_enterprise_grc=args.enterprise_grc,
    )
    return {
        "kind": "asset_inventory",
        "sources": {
            "docker_compose": include_compose,
            "enterprise_grc": bool(args.enterprise_grc),
        },
        "coverage": asset_service.coverage_summary(assets),
        "technology_inventory": asset_service.technology_inventory(assets),
        "fingerprint_report": asset_service.fingerprint_report(assets),
    }


def build_report(args) -> dict[str, Any]:
    report: dict[str, Any] = {"repository": str(ROOT), "section": args.section}
    if args.section in ("mapping", "all"):
        report["mapping"] = build_mapping_section(args)
    if args.section in ("assets", "all"):
        report["assets"] = build_assets_section(args)
    return report


def _render_mapping(m: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    kind = m.get("kind")
    if kind == "mapping_overview":
        s = m["stats"]
        lines += [
            "Technology -> Control -> Framework mapping",
            "-----------------------------------------",
            f"  Technologies: {s['technologies']}   Controls: {s['controls']}   "
            f"Frameworks: {s['frameworks']}",
            f"  Executable controls: {s['executable_controls']}   "
            f"Controls without framework: {s['controls_without_framework']}",
            "",
            "  Technologies (control_count / framework_count):",
        ]
        for t in m["technologies"]:
            lines.append(
                f"    {t['name']:32} {t['control_count']:>3} controls  "
                f"{t['framework_count']:>2} frameworks"
            )
        lines.append("")
        lines.append("  Frameworks (control_count / technology_count):")
        for f in m["frameworks"]:
            lines.append(
                f"    {f['name']:32} {f['control_count']:>3} controls  "
                f"{f['technology_count']:>2} technologies"
            )
    elif kind == "technology_detail":
        d = m.get("detail")
        if not d:
            lines.append(f"  Technology not found: {m['query']}")
        else:
            lines += [
                f"Technology: {d['name']}",
                f"  Controls: {d['control_count']}   Frameworks: {', '.join(d['frameworks'])}",
                "  Controls:",
            ]
            for c in d["controls"]:
                lines.append(
                    f"    {c['control_id']:10} {c['control_name'][:48]:48} "
                    f"[{', '.join(c['frameworks'])}]"
                )
    elif kind == "framework_detail":
        d = m.get("detail")
        if not d:
            lines.append(f"  Framework not found: {m['query']}")
        else:
            lines += [
                f"Framework: {d['name']}",
                f"  Controls: {d['control_count']}   Technologies: {', '.join(d['technologies'])}",
            ]
    return lines


def _render_assets(a: dict[str, Any]) -> list[str]:
    cov = a["coverage"]
    lines = [
        "Asset inventory & fingerprints",
        "------------------------------",
        f"  Sources: docker_compose={a['sources']['docker_compose']}  "
        f"enterprise_grc={a['sources']['enterprise_grc']}",
        f"  Total assets: {cov['total_assets']}   Identified: {cov['identified_assets']}   "
        f"Unidentified: {cov['unidentified_assets']}",
        f"  Identification rate: {cov['identification_rate']:.0%}   "
        f"In query catalog: {cov['assets_in_query_catalog']}",
        f"  Applicable frameworks: {len(cov['applicable_frameworks'])}   "
        f"Applicable controls: {cov['applicable_control_count']}",
        "",
        "  Technology inventory:",
    ]
    for r in a["technology_inventory"]:
        lines.append(
            f"    {r['technology']:32} {r['asset_count']:>3} assets  "
            f"conf={r['avg_confidence']:.2f}  in_catalog={r['in_catalog']}"
        )
    band = a["fingerprint_report"]["confidence_banding"]
    lines += [
        "",
        f"  Confidence banding: high={band['high']} medium={band['medium']} "
        f"low={band['low']} none={band['none']}",
    ]
    return lines


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ECS Audit Intelligence Report (Milestone 1)",
        "===========================================",
        f"Repository: {report['repository']}",
        "",
    ]
    if "mapping" in report:
        lines += _render_mapping(report["mapping"])
        lines.append("")
    if "assets" in report:
        lines += _render_assets(report["assets"])
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ECS Audit Intelligence report (read-only, offline).",
    )
    parser.add_argument(
        "--section", choices=["all", "mapping", "assets"], default="all",
        help="Which section(s) to print (default: all).",
    )
    parser.add_argument("--technology", default="", help="Show detail for one technology (mapping).")
    parser.add_argument("--framework", default="", help="Show detail for one framework (mapping).")
    parser.add_argument("--docker-compose", action="store_true",
                        help="Include docker-compose services as assets (offline parse).")
    parser.add_argument("--enterprise-grc", action="store_true",
                        help="Include the existing enterprise-GRC CMDB inventory as assets.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
