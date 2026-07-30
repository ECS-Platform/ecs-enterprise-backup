"""Reusable Phase-2 technology adapters — fixture-backed, application-agnostic.

Adapters are keyed by technology + common-control slug only. Application
identity is never encoded here; callers stamp it from portfolio config.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_ROOT = _REPO_ROOT / "data" / "phase2-reusability" / "fixtures"

# Canonical evidence fields expected by Phase-1 CommonControls validation rules.
_AT_REST_FIELDS = ("encryption_at_rest", "encrypted_datastores_pct")
_IN_TRANSIT_FIELDS = ("tls_enabled", "min_protocol")
_SECURE_CONFIG_FIELDS = ("hardening_score",)
_LEAST_PRIVILEGE_FIELDS = ("privileged_accounts_reviewed", "mfa_enabled")


def fixture_root() -> Path:
    import os

    override = os.environ.get("ECS_PHASE2_FIXTURE_ROOT", "").strip()
    return Path(override) if override else DEFAULT_FIXTURE_ROOT


def fixture_exists(technology: str, control_slug: str) -> bool:
    tech = str(technology or "").strip()
    slug = str(control_slug or "").strip()
    if not tech or not slug:
        return False
    return (fixture_root() / tech / f"{slug}.json").is_file()


def load_technology_fixture(technology: str, control_slug: str) -> dict[str, Any]:
    """Load deterministic mock evidence for a technology × control pair."""
    tech = str(technology or "").strip()
    slug = str(control_slug or "").strip()
    if not tech or not slug:
        raise ValueError("technology and control_slug are required")
    path = fixture_root() / tech / f"{slug}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Phase-2 fixture: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_control_payload(slug, payload, technology=tech)


def normalize_control_payload(
    control_slug: str,
    payload: dict[str, Any],
    *,
    technology: str = "",
) -> dict[str, Any]:
    """Normalize adapter output to canonical fields used by CommonControls validation."""
    out = dict(payload or {})
    out.setdefault("collector", "phase2_tech_adapter")
    if technology:
        out.setdefault("technology", technology)
    if control_slug == "encryption-at-rest":
        if "encryption_at_rest" not in out and "tde_enabled" in out:
            out["encryption_at_rest"] = bool(out["tde_enabled"])
        if "encrypted_datastores_pct" not in out and out.get("encryption_at_rest") is True:
            out["encrypted_datastores_pct"] = 100
        for key in _AT_REST_FIELDS:
            out.setdefault(key, False if key == "encryption_at_rest" else 0)
    elif control_slug == "encryption-in-transit":
        if "tls_enabled" not in out and out.get("ssl_enabled") is not None:
            out["tls_enabled"] = bool(out["ssl_enabled"])
        if "min_protocol" not in out and out.get("tls_protocol"):
            out["min_protocol"] = str(out["tls_protocol"])
        out.setdefault("tls_enabled", False)
        out.setdefault("min_protocol", "TLS1.2")
        for key in _IN_TRANSIT_FIELDS:
            out.setdefault(key, False if key == "tls_enabled" else "TLS1.2")
    elif control_slug == "secure-configuration":
        if "hardening_score" not in out and out.get("cis_score") is not None:
            out["hardening_score"] = int(out["cis_score"])
        out.setdefault("hardening_score", 0)
        for key in _SECURE_CONFIG_FIELDS:
            out.setdefault(key, 0)
    elif control_slug == "identity-privileged-access":
        if "privileged_accounts_reviewed" not in out and out.get("access_review_complete") is not None:
            out["privileged_accounts_reviewed"] = bool(out["access_review_complete"])
        if "mfa_enabled" not in out and out.get("mfa") is not None:
            out["mfa_enabled"] = bool(out["mfa"])
        out.setdefault("privileged_accounts_reviewed", False)
        out.setdefault("mfa_enabled", False)
        for key in _LEAST_PRIVILEGE_FIELDS:
            out.setdefault(key, False)
    return out


def fixture_bytes(technology: str, control_slug: str) -> bytes:
    payload = load_technology_fixture(technology, control_slug)
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _register(*names: str) -> dict[str, Callable[..., dict[str, Any]]]:
    return {name: load_technology_fixture for name in names}


# Thin aliases — same loader, named for readability in orchestration/tests.
ADAPTERS: dict[str, Callable[..., dict[str, Any]]] = _register(
    "aurora_mysql",
    "mysql",
    "yugabyte",
    "postgresql",
    "aerospike",
    "nginx",
    "tomcat",
    "linux_rhel",
    "linux",
    "kubernetes",
)


def adapt_control_evidence(technology: str, control_slug: str) -> dict[str, Any]:
    """Return fixture payload via the technology adapter (no app branching)."""
    tech = str(technology or "").strip()
    adapter = ADAPTERS.get(tech)
    if adapter is None:
        raise KeyError(f"No Phase-2 adapter registered for technology={tech!r}")
    return adapter(tech, control_slug)


def list_registered_adapters() -> list[str]:
    return sorted(ADAPTERS)
