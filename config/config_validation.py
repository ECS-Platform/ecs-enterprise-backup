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

import os
import re
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
# DR mirrors prod, so it is strict too.
_STRICT_ENVS = {"sit", "uat", "prod", "dr"}

# Environments where pointing at localhost/loopback is a hard error (a real
# remote environment must never resolve to the local machine).
_NO_LOCALHOST_ENVS = {"uat", "prod", "dr"}

_LOCALHOST_TOKENS = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal")

# Field-name fragments that identify a URL/endpoint value worth validating.
_URL_FIELD_HINTS = ("url", "endpoint", "base_url", "public_url", "authority")

# Fields whose value NAMES an env var that must hold a secret (checked non-blank
# in strict envs). These are the *_env pointer conventions used across the YAML.
_SECRET_ENV_SUFFIX = "_env"


def _looks_like_url(field_name: str) -> bool:
    fn = field_name.lower()
    return any(h in fn for h in _URL_FIELD_HINTS)


def _contains_localhost(value: str) -> bool:
    low = str(value).lower()
    return any(tok in low for tok in _LOCALHOST_TOKENS)


def mask_secret(value: Any) -> str:
    """Return a masked representation of a secret — never the raw value.

    Empty -> 'MISSING'; otherwise the first 2 chars + fixed asterisks so logs and
    validation output never reveal a credential.
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return "MISSING"
    s = str(value)
    return f"{s[:2]}****" if len(s) > 2 else "****"

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


def validate_environment(
    env: str | None = None, *, check_secrets: bool | None = None
) -> ValidationReport:
    """Validate one environment. Never raises — returns a structured report.

    A failure to even load the YAML is captured as a single fatal error.

    :param check_secrets: when True, ``*_env`` secret pointers must resolve to a
        non-empty environment variable (a *deployment* gate — run with the target
        env's secrets loaded). When False (the default for structural / CI config
        validation) secret presence is reported as a warning only, so config files
        can be validated without real credentials. Defaults to the value of
        ``ECS_VALIDATE_SECRETS`` (truthy) else False.
    """
    if check_secrets is None:
        check_secrets = _as_bool(os.environ.get("ECS_VALIDATE_SECRETS"))
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

    # --- application bind/public config (deployment portability) --------------
    app = cfg.get("application") or {}
    if app:
        rep.checks_run += 1
        port = app.get("port")
        if not _is_blank(port) and not _valid_port(port):
            rep.error(f"application.port is not a valid port: '{port}'")
        for url_field in ("public_url", "base_url"):
            val = app.get(url_field)
            if _is_blank(val):
                continue
            rep.checks_run += 1
            if not _valid_url(val):
                rep.error(f"application.{url_field} is not a valid URL: '{val}'")

    # --- no localhost/loopback in remote environments -------------------------
    if name in _NO_LOCALHOST_ENVS:
        for path, value in _iter_url_like(cfg):
            rep.checks_run += 1
            if _contains_localhost(value):
                rep.error(
                    f"{path} points at localhost/loopback ('{value}') which is "
                    f"invalid for environment '{name}'"
                )

    # --- URL / port shape checks (all environments) ---------------------------
    for path, value in _iter_url_like(cfg):
        rep.checks_run += 1
        if not _valid_url(value):
            rep.warn(f"{path} does not look like a valid URL: '{value}'")

    # --- required secrets present in strict environments ----------------------
    # Only enforced as ERRORS when check_secrets is on (a deployment gate run with
    # the target env's secrets loaded). Otherwise reported as warnings so config
    # files validate structurally in CI without real credentials.
    if strict:
        for path, env_var in _iter_secret_env_pointers(cfg):
            rep.checks_run += 1
            if _is_blank(os.environ.get(env_var)):
                msg = (
                    f"{path} -> environment variable '{env_var}' is empty "
                    f"(required secret in '{name}'); value: {mask_secret(os.environ.get(env_var))}"
                )
                if check_secrets:
                    rep.error(msg)
                else:
                    rep.warn(msg + " [set ECS_VALIDATE_SECRETS=1 to enforce]")

    # --- SSL/TLS expectations in remote environments --------------------------
    if name in _NO_LOCALHOST_ENVS:
        rep.checks_run += 1
        sec = cfg.get("security") or {}
        if "force_https" in sec and not _as_bool(sec.get("force_https")):
            rep.warn(f"security.force_https is false in '{name}' (TLS recommended)")

    # --- production/DR hardening expectations ----------------------------------
    if name in ("prod", "dr"):
        rep.checks_run += 1
        if not bool((((cfg.get("authentication") or {}).get("sso")) or {}).get("enabled")):
            rep.warn(f"authentication.sso.enabled is false in '{name}'")
        rep.checks_run += 1
        if not bool((((cfg.get("storage") or {}).get("object_store")) or {}).get("secure")):
            rep.warn(f"storage.object_store.secure is false in '{name}'")

    return rep


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _valid_port(value: Any) -> bool:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    return 1 <= n <= 65535


_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s]+$")


def _valid_url(value: Any) -> bool:
    """True for a http(s)/scheme URL OR a bare host[:port] (both are used in YAML)."""
    s = str(value).strip()
    if not s or s.startswith("${"):
        return True  # unresolved placeholder — not this validator's concern
    if _URL_RE.match(s):
        return True
    # Accept bare host or host:port (e.g. object-store endpoint "minio:9000").
    return bool(re.match(r"^[A-Za-z0-9._\-]+(:\d{1,5})?$", s))


def _iter_url_like(cfg: dict[str, Any], _prefix: str = ""):
    """Yield (dotted_path, value) for every string field that looks like a URL/endpoint."""
    for key, val in cfg.items():
        path = f"{_prefix}.{key}" if _prefix else str(key)
        if isinstance(val, dict):
            yield from _iter_url_like(val, path)
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, dict):
                    yield from _iter_url_like(item, f"{path}[{i}]")
        elif isinstance(val, str) and val.strip() and _looks_like_url(str(key)):
            yield path, val


def _iter_secret_env_pointers(cfg: dict[str, Any], _prefix: str = ""):
    """Yield (dotted_path, env_var_name) for every ``*_env`` secret pointer."""
    for key, val in cfg.items():
        path = f"{_prefix}.{key}" if _prefix else str(key)
        if isinstance(val, dict):
            yield from _iter_secret_env_pointers(val, path)
        elif (
            isinstance(key, str)
            and key.endswith(_SECRET_ENV_SUFFIX)
            and isinstance(val, str)
            and val.strip()
        ):
            yield path, val.strip()


def validate_or_raise(env: str | None = None, *, check_secrets: bool | None = None) -> ValidationReport:
    """Validate and raise :class:`EnvironmentConfigError` if any errors are found."""
    rep = validate_environment(env, check_secrets=check_secrets)
    if not rep.ok:
        bullet = "\n  - ".join(rep.errors)
        raise EnvironmentConfigError(
            f"ECS configuration for environment '{rep.environment}' is invalid:\n  - {bullet}"
        )
    return rep


def validate_all(*, check_secrets: bool | None = None) -> dict[str, ValidationReport]:
    """Validate every environment that has a YAML file present."""
    return {
        env: validate_environment(env, check_secrets=check_secrets)
        for env in available_environments()
    }


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
    check_secrets = "--check-secrets" in argv
    if "--all" in argv:
        reports = validate_all(check_secrets=check_secrets)
        print("\n".join(_format(r) for r in reports.values()))
        return 0 if all(r.ok for r in reports.values()) else 1
    env = next((a for a in argv if not a.startswith("-")), None)
    rep = validate_environment(env, check_secrets=check_secrets)
    print(_format(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
