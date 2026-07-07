#!/usr/bin/env python3
"""ECS UAT connector health harness — safe checks for external integrations.

Runs config-presence and (optionally) live health checks for the ECS enterprise
integration adapters (ServiceNow, Archer, SharePoint/Graph, Jira, Confluence,
SonarQube, Checkmarx, Prisma Cloud, Tripwire).

SAFETY MODEL
------------
* By default NO live network call is made. A live call happens ONLY when an
  adapter is configured AND ``--live`` is explicitly passed.
* ``--no-network`` forces config-only mode (validate presence + masking) even if
  ``--live`` is given — useful in CI / locked-down UAT jump hosts.
* Secrets are NEVER printed. Config is shown masked (SET/MISSING) exactly as the
  adapters expose it; the raw values never leave the process.

USAGE
-----
    python scripts/run_uat_connector_health.py --adapter all
    python scripts/run_uat_connector_health.py --adapter jira --json
    python scripts/run_uat_connector_health.py --adapter all --strict
    python scripts/run_uat_connector_health.py --adapter graph --live      # live probe if configured
    python scripts/run_uat_connector_health.py --adapter all --no-network  # config-only

Exit codes: 0 = OK. With ``--strict``, exit 1 if any *configured* adapter is not
healthy (unconfigured adapters never fail strict mode — "not configured" is a
valid UAT state until credentials are provisioned).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Offline-safe defaults; never turn these on implicitly for live systems.
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Friendly CLI alias -> adapter module name under modules.operations.integrations.
ADAPTER_ALIASES: dict[str, str] = {
    "servicenow": "servicenow_cmdb",
    "archer": "archer",
    "graph": "sharepoint_graph",
    "sharepoint": "sharepoint_graph",
    "jira": "jira",
    "confluence": "confluence",
    "sonarqube": "sonarqube",
    "checkmarx": "checkmarx",
    "prisma": "prisma_cloud",
    "tripwire": "tripwire",
}

#: Per-adapter remediation hints (which env vars to set). No secrets, no IPs.
REMEDIATION: dict[str, str] = {
    "servicenow_cmdb": "Set ECS_SERVICENOW_BASE_URL, ECS_SERVICENOW_CLIENT_ID, ECS_SERVICENOW_CLIENT_SECRET.",
    "archer": "Set ECS_ARCHER_BASE_URL and ECS_ARCHER_API_TOKEN.",
    "sharepoint_graph": "Set ECS_GRAPH_TENANT_ID, ECS_GRAPH_CLIENT_ID, ECS_GRAPH_CLIENT_SECRET, ECS_GRAPH_SITE_ID.",
    "jira": "Set ECS_JIRA_BASE_URL, ECS_JIRA_USERNAME, ECS_JIRA_API_TOKEN.",
    "confluence": "Set ECS_CONFLUENCE_BASE_URL, ECS_CONFLUENCE_USERNAME, ECS_CONFLUENCE_API_TOKEN.",
    "sonarqube": "Set ECS_SONARQUBE_BASE_URL and ECS_SONARQUBE_TOKEN.",
    "checkmarx": "Set ECS_CHECKMARX_BASE_URL, ECS_CHECKMARX_CLIENT_ID, ECS_CHECKMARX_CLIENT_SECRET.",
    "prisma_cloud": "Set ECS_PRISMA_CLOUD_BASE_URL, ECS_PRISMA_CLOUD_ACCESS_KEY, ECS_PRISMA_CLOUD_SECRET_KEY.",
    "tripwire": "Set ECS_TRIPWIRE_BASE_URL, ECS_TRIPWIRE_USERNAME, ECS_TRIPWIRE_PASSWORD.",
}

#: Statuses that indicate a *reachable, authenticated* adapter.
_HEALTHY_STATUSES = frozenset({"ok"})


def resolve_adapters(selection: str) -> list[str]:
    """Map a CLI selection ('all' or a friendly alias) to module names."""
    sel = (selection or "all").strip().lower()
    if sel == "all":
        # Preserve the registry's stable display order.
        try:
            from modules.operations import integrations

            return list(integrations.list_adapters())
        except Exception:  # noqa: BLE001 - fall back to the alias values
            seen: list[str] = []
            for mod in ADAPTER_ALIASES.values():
                if mod not in seen:
                    seen.append(mod)
            return seen
    if sel in ADAPTER_ALIASES:
        return [ADAPTER_ALIASES[sel]]
    # Allow passing the full module name directly too.
    if sel in set(ADAPTER_ALIASES.values()):
        return [sel]
    raise SystemExit(
        f"Unknown adapter: {selection!r}. Choose 'all' or one of: "
        + ", ".join(sorted(ADAPTER_ALIASES))
    )


def _import_adapter(module_name: str):
    import importlib

    return importlib.import_module(f"modules.operations.integrations.{module_name}")


def check_adapter(module_name: str, *, live: bool, no_network: bool) -> dict:
    """Return a secret-safe health record for one adapter. Never raises."""
    record: dict = {
        "adapter": module_name,
        "configured": False,
        "masked_config": {},
        "status": "unknown",
        "ok": False,
        "errors": [],
        "remediation": REMEDIATION.get(module_name, ""),
        "mode": "config-only",
    }
    try:
        mod = _import_adapter(module_name)
    except Exception as exc:  # noqa: BLE001
        record["status"] = "adapter_error"
        record["errors"] = [f"import failed: {type(exc).__name__}"]
        return record

    # Config presence + masking (never a live call).
    try:
        record["configured"] = bool(mod.is_configured())
    except Exception as exc:  # noqa: BLE001
        record["errors"].append(f"is_configured: {type(exc).__name__}")
    try:
        record["masked_config"] = mod.masked_config()
    except Exception as exc:  # noqa: BLE001
        record["errors"].append(f"masked_config: {type(exc).__name__}")

    do_live = bool(live) and not no_network and record["configured"]
    if not do_live:
        # Config-only: report readiness from config, no probe.
        if record["configured"]:
            record["status"] = "configured"
            record["ok"] = True
            if not live:
                record["remediation"] = "Configured. Re-run with --live to probe the endpoint."
            elif no_network:
                record["remediation"] = "Configured. --no-network set: live probe skipped."
        else:
            record["status"] = "not_configured"
            record["ok"] = False
        return record

    # Live probe (adapter is configured and --live requested).
    record["mode"] = "live"
    try:
        health = mod.health_check()
    except Exception as exc:  # noqa: BLE001 - health must never crash the harness
        record["status"] = "health_error"
        record["errors"].append(f"health_check: {type(exc).__name__}")
        return record
    record["status"] = str(health.get("status", "unknown"))
    record["ok"] = bool(health.get("ok")) and record["status"] in _HEALTHY_STATUSES
    if health.get("errors"):
        # Only surface error *types/messages* the adapter already deemed safe.
        record["errors"].extend(list(health.get("errors") or []))
    if health.get("masked_config"):
        record["masked_config"] = health["masked_config"]
    if not record["ok"]:
        record["remediation"] = _live_remediation(record["status"], module_name)
    return record


def _live_remediation(status: str, module_name: str) -> str:
    hints = {
        "auth_error": "Authentication failed — verify the credential/token and its scope.",
        "timeout": "Timed out — check VPN/routing and the endpoint URL; raise the timeout if needed.",
        "connection_error": "Cannot connect — confirm host reachability and firewall/port rules.",
        "http_error": "Endpoint returned an HTTP error — verify the base URL and API path.",
        "not_configured": REMEDIATION.get(module_name, "Provide the required configuration."),
    }
    return hints.get(status, "Investigate the adapter health error (see errors).")


def run(selection: str, *, live: bool, no_network: bool) -> dict:
    adapters = resolve_adapters(selection)
    results = [check_adapter(m, live=live, no_network=no_network) for m in adapters]
    configured = [r for r in results if r["configured"]]
    unhealthy_configured = [r for r in configured if not r["ok"]]
    return {
        "results": results,
        "total": len(results),
        "configured": len(configured),
        "not_configured": len(results) - len(configured),
        "healthy": sum(1 for r in results if r["ok"]),
        "unhealthy_configured": len(unhealthy_configured),
        "mode": "live" if (live and not no_network) else "config-only",
    }


def render(report: dict) -> str:
    lines = ["ECS UAT Connector Health", "========================",
             f"mode: {report['mode']}", ""]
    for r in report["results"]:
        mark = "OK " if r["ok"] else ("-- " if r["status"] == "not_configured" else "!! ")
        lines.append(f"  [{mark}] {r['adapter']:20} configured={str(r['configured']):5} "
                     f"status={r['status']}")
        # masked_config is safe to print (SET/MISSING only).
        mc = r.get("masked_config") or {}
        if mc:
            compact = ", ".join(f"{k}={v}" for k, v in mc.items()
                                if k not in ("integration",))
            lines.append(f"        config: {compact}")
        if r.get("errors"):
            lines.append(f"        errors: {'; '.join(str(e) for e in r['errors'])}")
        if r.get("remediation") and not r["ok"]:
            lines.append(f"        hint:   {r['remediation']}")
    lines.append("")
    lines.append(
        f"Summary: {report['configured']}/{report['total']} configured, "
        f"{report['healthy']} healthy, {report['unhealthy_configured']} configured-but-unhealthy."
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run safe health checks for ECS external integration adapters.")
    parser.add_argument("--adapter", default="all",
                        help="'all' or one of: " + ", ".join(sorted(ADAPTER_ALIASES)))
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero if any CONFIGURED adapter is unhealthy.")
    parser.add_argument("--live", action="store_true",
                        help="Perform a live health probe for configured adapters.")
    parser.add_argument("--no-network", action="store_true",
                        help="Force config-only mode (never probe), overriding --live.")
    args = parser.parse_args(argv)

    report = run(args.adapter, live=args.live, no_network=args.no_network)
    print(json.dumps(report, indent=2, default=str) if args.json else render(report))

    if args.strict and report["unhealthy_configured"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
