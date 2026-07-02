"""ECS Environment Configuration Validation (Phase 9).

Validates a resolved environment configuration and fails startup with clear,
actionable errors. Severity is environment-aware: integration gaps that are
expected on a developer laptop (``local``) are WARNINGS, but the same gaps in
``uat`` / ``prod`` are ERRORS.

Programmatic use
----------------
    from config.config_validation import validate_or_raise, validate_environment
    report = validate_environment("uat")          # structured report, never raises
    validate_or_raise()                            # raises on the ACTIVE env if invalid

CLI use
-------
    python -m config.config_validation            # validate the active env (ECS_ENV)
    python -m config.config_validation --all      # validate every env file present
    python -m config.config_validation uat        # validate a named env
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from config.environment_loader import (
    VALID_ENVIRONMENTS,
    EnvironmentConfigError,
    available_environments,
    get_environment_config,
)

# Environments where missing real integration targets is a hard error.
_STRICT_ENVS = {"sit", "uat", "prod"}

_REQUIRED_SECTIONS = (
    "applications",
    "databases",
    "connectors",
    "framework_targets",
    "predefined_query_targets",
    "storage",
    "reporting",
)


@dataclass
class ValidationReport:
    environment: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks_run: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checks_run": self.checks_run,
        }


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def validate_environment(env: str | None = None) -> ValidationReport:
    """Validate one environment. Never raises — returns a structured report.

    A failure to even load the YAML is captured as a single fatal error.
    """
    target = (env or "").strip().lower() or None
    rep = ValidationReport(environment=target or "active")

    try:
        cfg = get_environment_config(env=target)
    except EnvironmentConfigError as exc:
        rep.error(str(exc))
        return rep
    except Exception as exc:  # noqa: BLE001 - surface any load problem as a clean error
        rep.error(f"Unexpected error loading configuration: {exc}")
        return rep

    name = str(cfg.get("environment") or target or "active")
    rep.environment = name
    strict = name in _STRICT_ENVS

    # --- environment identifier ------------------------------------------------
    rep.checks_run += 1
    if name not in VALID_ENVIRONMENTS:
        rep.error(f"environment '{name}' is not one of {', '.join(VALID_ENVIRONMENTS)}")

    # --- required top-level sections ------------------------------------------
    for section in _REQUIRED_SECTIONS:
        rep.checks_run += 1
        if not isinstance(cfg.get(section), dict):
            rep.error(f"missing or invalid section: '{section}'")

    # --- databases.postgres (evidence repository — always required) -----------
    pg = (cfg.get("databases") or {}).get("postgres") or {}
    for key in ("host", "port", "database", "user"):
        rep.checks_run += 1
        if _is_blank(pg.get(key)):
            rep.error(f"databases.postgres.{key} is empty (required for the evidence repository)")
    rep.checks_run += 1
    if not _is_blank(pg.get("port")) and not str(pg.get("port")).isdigit():
        rep.error(f"databases.postgres.port must be numeric, got '{pg.get('port')}'")

    # --- connectors: enabled connectors must have a URL -----------------------
    for cname, cval in (cfg.get("connectors") or {}).items():
        if not isinstance(cval, dict):
            continue
        if bool(cval.get("enabled")):
            rep.checks_run += 1
            if _is_blank(cval.get("url")):
                rep.error(f"connector '{cname}' is enabled but has no url")

    # --- framework_targets reference valid target groups ----------------------
    target_keys = set((cfg.get("predefined_query_targets") or {}).keys())
    for fname, fval in (cfg.get("framework_targets") or {}).items():
        if not isinstance(fval, dict) or not fval.get("enabled"):
            continue
        for group in fval.get("target_groups", []) or []:
            rep.checks_run += 1
            if group not in target_keys:
                rep.error(
                    f"framework_targets.{fname} references unknown target group '{group}'"
                )

    # --- predefined query target server lists ---------------------------------
    pqt = cfg.get("predefined_query_targets") or {}
    for group in ("os_servers", "db_servers"):
        rep.checks_run += 1
        servers = pqt.get(group)
        if not isinstance(servers, list) or not servers:
            msg = f"predefined_query_targets.{group} is empty"
            if strict:
                rep.error(msg + " (required for live control validation in this environment)")
            else:
                rep.warn(msg + " (ok for local/demo — live demo connectors are used instead)")

    # --- reporting.export_path -------------------------------------------------
    rep.checks_run += 1
    if _is_blank((cfg.get("reporting") or {}).get("export_path")):
        rep.error("reporting.export_path is empty")

    # --- production hardening expectations -------------------------------------
    if name == "prod":
        rep.checks_run += 1
        if not bool((((cfg.get("authentication") or {}).get("sso")) or {}).get("enabled")):
            rep.warn("authentication.sso.enabled is false in production")
        rep.checks_run += 1
        if not bool((((cfg.get("storage") or {}).get("object_store")) or {}).get("secure")):
            rep.warn("storage.object_store.secure is false in production")

    return rep


def validate_or_raise(env: str | None = None) -> ValidationReport:
    """Validate and raise :class:`EnvironmentConfigError` if any errors are found."""
    rep = validate_environment(env)
    if not rep.ok:
        bullet = "\n  - ".join(rep.errors)
        raise EnvironmentConfigError(
            f"ECS configuration for environment '{rep.environment}' is invalid:\n  - {bullet}"
        )
    return rep


def validate_all() -> dict[str, ValidationReport]:
    """Validate every environment that has a YAML file present."""
    return {env: validate_environment(env) for env in available_environments()}


def _format(rep: ValidationReport) -> str:
    status = "PASS" if rep.ok else "FAIL"
    lines = [f"[{status}] {rep.environment}  ({rep.checks_run} checks, "
             f"{len(rep.errors)} errors, {len(rep.warnings)} warnings)"]
    for err in rep.errors:
        lines.append(f"   ✗ ERROR: {err}")
    for warn in rep.warnings:
        lines.append(f"   ! warn:  {warn}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--all" in argv:
        reports = validate_all()
        print("\n".join(_format(r) for r in reports.values()))
        return 0 if all(r.ok for r in reports.values()) else 1
    env = next((a for a in argv if not a.startswith("-")), None)
    rep = validate_environment(env)
    print(_format(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
