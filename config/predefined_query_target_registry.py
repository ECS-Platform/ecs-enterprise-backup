"""ECS Predefined-Query Target Registry loader.

Loads the operator-facing named-target registry files
(``config/predefined_query_targets.<env>.yaml``) that enumerate the concrete
systems the predefined-query module assesses per environment. This COMPLEMENTS
(does not replace) the connector-level ``predefined_query_targets`` blocks in
``config/environments/*.yaml`` — those define *how* to connect per technology;
the registry lists *which named targets* to run against.

Design
------
* Read-only, dependency-light (reuses ``ecs_platform.config.loader`` for
  ``${VAR}`` substitution). Never raises on a missing file — returns an empty
  registry so callers/tests degrade gracefully.
* ``localhost``/loopback is allowed ONLY in the ``local`` registry; the validator
  flags it as an error for uat/prod/dr (a real remote target must not resolve to
  the local machine).
* Secrets are never stored here — targets reference credentials by
  ``credential_ref`` (vault path / env var name).

CLI::

    python -m config.predefined_query_target_registry local
    python -m config.predefined_query_target_registry --all
    python -m config.predefined_query_target_registry uat --validate
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VALID_ENVIRONMENTS: tuple[str, ...] = ("local", "uat", "prod", "dr")

#: Environments where a target must NOT resolve to localhost/loopback.
_NO_LOCALHOST_ENVS = {"uat", "prod", "dr"}
_LOCALHOST_TOKENS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")

#: Fields every target entry should declare.
REQUIRED_TARGET_FIELDS = (
    "target_id", "technology", "hostname", "port", "environment",
    "connector_ref", "execution_method", "enabled",
)


def _config_dir() -> Path:
    try:
        from ecs_platform.config.loader import config_dir

        return config_dir()
    except Exception:  # noqa: BLE001 - fall back to repo-root/config
        return Path(__file__).resolve().parent


def registry_path(env: str) -> Path:
    return _config_dir() / f"predefined_query_targets.{env}.yaml"


def available_registries() -> list[str]:
    return [e for e in VALID_ENVIRONMENTS if registry_path(e).is_file()]


def load_registry(env: str) -> dict[str, Any]:
    """Load one env's target registry (env-resolved). Returns {} if absent/invalid."""
    path = registry_path(env)
    if not path.is_file():
        return {"environment": env, "targets": []}
    try:
        from ecs_platform.config.loader import _read_yaml  # substitutes ${VAR}

        data = _read_yaml(path)
    except Exception:  # noqa: BLE001
        try:
            import yaml

            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception:  # noqa: BLE001
            return {"environment": env, "targets": []}
    if not isinstance(data, dict):
        return {"environment": env, "targets": []}
    data.setdefault("environment", env)
    data.setdefault("targets", [])
    return data


def get_targets(env: str, *, enabled_only: bool = False) -> list[dict[str, Any]]:
    targets = list(load_registry(env).get("targets") or [])
    if enabled_only:
        targets = [t for t in targets if _truthy(t.get("enabled"))]
    return targets


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _contains_localhost(value: Any) -> bool:
    low = str(value or "").lower()
    return any(tok in low for tok in _LOCALHOST_TOKENS)


@dataclass
class RegistryValidation:
    environment: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    target_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment, "ok": self.ok,
            "target_count": self.target_count,
            "errors": list(self.errors), "warnings": list(self.warnings),
        }


def validate_registry(env: str) -> RegistryValidation:
    """Validate a target registry. Never raises — returns a structured report."""
    rep = RegistryValidation(environment=env)
    reg = load_registry(env)
    targets = reg.get("targets") or []
    rep.target_count = len(targets)

    if not registry_path(env).is_file():
        rep.warnings.append(f"registry file predefined_query_targets.{env}.yaml is absent")
        return rep

    seen_ids: set[str] = set()
    for i, t in enumerate(targets):
        if not isinstance(t, dict):
            rep.errors.append(f"target[{i}] is not a mapping")
            continue
        tid = str(t.get("target_id") or "")
        for f in REQUIRED_TARGET_FIELDS:
            if t.get(f) in (None, ""):
                rep.errors.append(f"target '{tid or i}' missing required field '{f}'")
        if tid:
            if tid in seen_ids:
                rep.errors.append(f"duplicate target_id '{tid}'")
            seen_ids.add(tid)
        # localhost policy
        if env in _NO_LOCALHOST_ENVS:
            for host_field in ("hostname", "ip"):
                if _contains_localhost(t.get(host_field)):
                    rep.errors.append(
                        f"target '{tid or i}'.{host_field} points at localhost/loopback "
                        f"('{t.get(host_field)}') which is invalid for '{env}'")
        # environment field should match
        if str(t.get("environment") or "") not in ("", env):
            rep.warnings.append(
                f"target '{tid or i}'.environment='{t.get('environment')}' != registry env '{env}'")
    return rep


def validate_all() -> dict[str, RegistryValidation]:
    return {e: validate_registry(e) for e in available_registries()}


def _fmt(rep: RegistryValidation) -> str:
    status = "PASS" if rep.ok else "FAIL"
    lines = [f"[{status}] predefined_query_targets.{rep.environment} "
             f"({rep.target_count} targets, {len(rep.errors)} errors, {len(rep.warnings)} warnings)"]
    for e in rep.errors:
        lines.append(f"   x ERROR: {e}")
    for w in rep.warnings:
        lines.append(f"   ! warn:  {w}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    do_validate = "--validate" in argv or "--all" in argv
    if "--all" in argv:
        reps = validate_all()
        print("\n".join(_fmt(r) for r in reps.values()))
        return 0 if all(r.ok for r in reps.values()) else 1
    env = next((a for a in argv if not a.startswith("-")), "local")
    if do_validate:
        rep = validate_registry(env)
        print(_fmt(rep))
        return 0 if rep.ok else 1
    reg = load_registry(env)
    print(f"predefined_query_targets.{env}: {len(reg.get('targets') or [])} target(s)")
    for t in reg.get("targets") or []:
        print(f"  - {t.get('target_id')}  [{t.get('technology')}]  "
              f"{t.get('hostname')}:{t.get('port')}  enabled={t.get('enabled')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
