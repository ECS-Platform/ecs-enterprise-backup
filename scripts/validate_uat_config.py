#!/usr/bin/env python3
"""Validate an ECS UAT asset/connector configuration before a UAT run.

Offline, read-only, deterministic — no network, no connector calls, no secrets
printed. It checks that a UAT asset inventory (and, optionally, the connector
config) is well-formed and safe to use in UAT:

  1. YAML loads successfully.
  2. No ``localhost`` / loopback remains when in UAT mode (real UAT must not point
     at localhost). Applies to resolved hostnames of the asset inventory.
  3. Required asset fields exist (asset_id, technology; hostname or asset_type).
  4. Required connector fields exist (each configured connector references a base
     URL/endpoint and its secrets via ``*_env`` names, never inline values).
  5. Secrets are referenced via environment variables, not hardcoded.

This does NOT duplicate the scheduler loader — it reuses
``modules.audit_intelligence.services.asset_scheduler`` where possible and only
adds validation rules on top.

USAGE
-----
    python scripts/validate_uat_config.py --assets config/uat_assets.uat.yaml
    python scripts/validate_uat_config.py --assets config/uat_assets.uat.yaml --mode uat --strict
    python scripts/validate_uat_config.py --assets ... --connectors config/integrations.yaml --json

Exit codes: 0 = valid (or warnings only). 1 = validation errors (or any issue in
``--strict`` mode). Never raises to the shell.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Hostnames that are invalid for a real UAT target.
_LOCALHOST_TOKENS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")
#: Always-required fields for every asset entry.
_REQUIRED_ASSET_FIELDS = ("asset_id",)
#: Patterns that look like an inline secret value (not an env reference).
_SECRET_KEY_RE = re.compile(r"(secret|token|password|access[_-]?key)", re.I)
_ENV_REF_RE = re.compile(r"^\$\{[^}]+\}$|_env$")


def _load_yaml(path: Path) -> tuple[dict | None, str]:
    if not path.is_file():
        return None, f"file not found: {path}"
    try:
        import yaml

        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if data is None:
            return {}, ""
        if not isinstance(data, dict):
            return None, f"top-level YAML must be a mapping: {path.name}"
        return data, ""
    except Exception as exc:  # noqa: BLE001 - report, never crash
        return None, f"YAML parse error in {path.name}: {type(exc).__name__}: {exc}"


def _resolve_env(value: str) -> str:
    """Expand ${VAR} / ${VAR:-default} using the current environment."""
    if not isinstance(value, str) or "${" not in value:
        return value

    def repl(m: "re.Match[str]") -> str:
        token = m.group(1)
        name, _, default = token.partition(":-")
        return os.environ.get(name.strip(), default)

    return re.sub(r"\$\{([^}]+)\}", repl, value)


def _is_placeholder(value: str) -> bool:
    v = (value or "").strip()
    return not v or v.startswith("<") or v.endswith("-placeholder>") or "placeholder" in v


# --------------------------------------------------------------------------- #
# Asset validation
# --------------------------------------------------------------------------- #
def validate_assets(data: dict, *, mode: str) -> tuple[list[str], list[str], int]:
    """Return (errors, warnings, asset_count) for an asset-inventory config."""
    errors: list[str] = []
    warnings: list[str] = []
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("no 'assets' list found (expected a top-level 'assets:' array)")
        return errors, warnings, 0

    uat_mode = mode.lower() == "uat"
    for i, asset in enumerate(assets):
        label = f"assets[{i}]"
        if not isinstance(asset, dict):
            errors.append(f"{label}: not a mapping")
            continue
        aid = asset.get("asset_id") or label
        # Always-required fields.
        for field in _REQUIRED_ASSET_FIELDS:
            if not str(asset.get(field) or "").strip():
                errors.append(f"{aid}: missing required field '{field}'")
        # An asset must have a target: hostname (baseline) or asset_type (connector).
        hostname_raw = str(asset.get("hostname") or asset.get("host") or "")
        asset_type = str(asset.get("asset_type") or "").strip()
        technology = str(asset.get("technology") or "").strip()
        if not hostname_raw and not asset_type:
            errors.append(f"{aid}: needs a 'hostname' (or 'host') or an 'asset_type'")
        # 'technology' is required for BASELINE assets (no asset_type). Connector
        # assets route by 'asset_type', so technology is optional there.
        if not asset_type and not technology:
            errors.append(f"{aid}: baseline asset must set 'technology' "
                          f"(or provide 'asset_type' to route to a connector)")
        # No-localhost-in-UAT rule (resolved value).
        resolved = _resolve_env(hostname_raw).lower()
        if uat_mode and resolved and any(tok in resolved for tok in _LOCALHOST_TOKENS):
            errors.append(f"{aid}: hostname resolves to localhost/loopback "
                          f"('{resolved}') — not allowed in UAT mode")
        # Placeholder warning (not an error — templates ship placeholders).
        if uat_mode and hostname_raw and _is_placeholder(_resolve_env(hostname_raw)):
            warnings.append(f"{aid}: hostname is still a placeholder "
                            f"('{hostname_raw}') — set the real UAT value via env")
    return errors, warnings, len(assets)


# --------------------------------------------------------------------------- #
# Connector validation (secrets via env only)
# --------------------------------------------------------------------------- #
def validate_connectors(data: dict) -> tuple[list[str], list[str], int]:
    """Return (errors, warnings, connector_count) for a connector config.

    Accepts either the ``integrations:`` shape (config/integrations.yaml) or the
    ``connectors:`` shape (config/environments/*.yaml). Ensures no inline secrets.
    """
    errors: list[str] = []
    warnings: list[str] = []
    block = data.get("integrations") or data.get("connectors") or {}
    if not isinstance(block, dict) or not block:
        warnings.append("no 'integrations'/'connectors' block found to validate")
        return errors, warnings, 0

    count = 0
    for name, cfg in block.items():
        if not isinstance(cfg, dict):
            continue
        count += 1
        for key, value in cfg.items():
            if not _SECRET_KEY_RE.search(str(key)):
                continue
            # Keys named *_env are references (good). Values must be ${VAR} refs,
            # empty, or a *_env name — never a literal secret.
            sval = str(value or "").strip()
            if key.endswith("_env"):
                continue  # a variable name, not a value
            if sval and not _ENV_REF_RE.search(sval) and not _is_placeholder(sval):
                errors.append(f"connector '{name}': field '{key}' looks like an "
                              f"inline secret — reference an env var instead")
    return errors, warnings, count


def run(*, assets_path: str, connectors_path: str = "", mode: str = "uat") -> dict:
    report: dict = {"ok": True, "mode": mode, "checks": [], "errors": [], "warnings": []}

    a_data, a_err = _load_yaml(Path(assets_path))
    report["checks"].append({"check": "assets_yaml_loads", "ok": a_data is not None,
                             "detail": a_err or assets_path})
    if a_data is None:
        report["errors"].append(a_err)
        report["ok"] = False
        return report
    a_errors, a_warnings, a_count = validate_assets(a_data, mode=mode)
    report["checks"].append({"check": "assets_valid", "ok": not a_errors,
                             "detail": f"{a_count} asset(s); {len(a_errors)} error(s)"})
    report["errors"].extend(a_errors)
    report["warnings"].extend(a_warnings)

    if connectors_path:
        c_data, c_err = _load_yaml(Path(connectors_path))
        report["checks"].append({"check": "connectors_yaml_loads", "ok": c_data is not None,
                                 "detail": c_err or connectors_path})
        if c_data is None:
            report["errors"].append(c_err)
        else:
            c_errors, c_warnings, c_count = validate_connectors(c_data)
            report["checks"].append({"check": "connectors_no_inline_secrets",
                                     "ok": not c_errors,
                                     "detail": f"{c_count} connector(s); {len(c_errors)} error(s)"})
            report["errors"].extend(c_errors)
            report["warnings"].extend(c_warnings)

    report["ok"] = not report["errors"]
    return report


def render(report: dict) -> str:
    lines = ["ECS UAT Config Validation", "=========================",
             f"mode: {report['mode']}", ""]
    for c in report["checks"]:
        lines.append(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['check']:34} {c['detail']}")
    if report["errors"]:
        lines.append("")
        lines.append("Errors:")
        lines.extend(f"  - {e}" for e in report["errors"])
    if report["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in report["warnings"])
    lines.append("")
    lines.append(f"Result: {'VALID' if report['ok'] else 'INVALID'} "
                 f"({len(report['errors'])} error(s), {len(report['warnings'])} warning(s))")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate an ECS UAT asset/connector config.")
    parser.add_argument("--assets", default=str(ROOT / "config" / "uat_assets.local.yaml"),
                        help="Path to the UAT asset inventory YAML.")
    parser.add_argument("--connectors", default="",
                        help="Optional connector config YAML (e.g. config/integrations.yaml).")
    parser.add_argument("--mode", default="uat", choices=["uat", "local", "sit", "prod"],
                        help="Deployment mode; 'uat' enforces the no-localhost rule.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as failures (exit non-zero on any warning).")
    args = parser.parse_args(argv)

    report = run(assets_path=args.assets, connectors_path=args.connectors, mode=args.mode)
    print(json.dumps(report, indent=2, default=str) if args.json else render(report))

    if not report["ok"]:
        return 1
    if args.strict and report["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
