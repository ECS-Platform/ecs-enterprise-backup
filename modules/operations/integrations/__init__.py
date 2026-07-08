"""ECS enterprise integration adapters (config-driven; no real calls in tests).

Ships credential-externalised adapter *skeletons* for (see ``ADAPTER_MODULES``):
  servicenow_cmdb, archer, sharepoint_graph, teams_graph, outlook_graph, jira,
  confluence, sonarqube, checkmarx, prisma_cloud, tripwire, aws_connector,
  gcp_connector, azure_connector, nessus, qualys.

Every adapter:
  * reads config from env / YAML only (never hard-coded, never logged),
  * exposes a consistent interface — ``get_config()``, ``is_configured()``,
    ``masked_config()``, ``health_check()``, ``fetch_*()``, ``normalize_*()``,
  * accepts an injectable transport so unit tests supply mocked responses with no
    network access, and
  * returns the standard ``{ok, source, status, items, errors}`` shape (see
    ``_base``).
"""

from __future__ import annotations

import importlib
from typing import Any

#: YAML sections that may hold integration config, in priority order.
_INTEGRATION_SECTIONS = ("connectors", "integrations")


def lookup_yaml_config(keys: tuple[str, ...]) -> dict[str, Any]:
    """Find an integration's config block from the active environment YAML.

    Backward compatible: searches BOTH the ``connectors`` and ``integrations``
    sections for ANY of the given block keys (in priority order), so old and new
    config layouts both resolve. Never raises — returns ``{}`` on any failure.
    """
    try:
        from config.environment_loader import get_section
    except Exception:  # noqa: BLE001 - env layer unavailable -> env-only config
        return {}
    for section_name in _INTEGRATION_SECTIONS:
        try:
            section = get_section(section_name) or {}
        except Exception:  # noqa: BLE001
            section = {}
        for key in keys:
            block = section.get(key)
            if isinstance(block, dict) and block:
                return dict(block)
    return {}


# --------------------------------------------------------------------------- #
# Adapter registry
# --------------------------------------------------------------------------- #
#: Registered adapter modules, in a stable display order.
ADAPTER_MODULES = (
    "servicenow_cmdb",
    "archer",
    "sharepoint_graph",
    "teams_graph",
    "outlook_graph",
    "jira",
    "confluence",
    "sonarqube",
    "checkmarx",
    "prisma_cloud",
    "tripwire",
    # Cloud posture + vulnerability scanners (config-driven; safe-by-default).
    "aws_connector",
    "gcp_connector",
    "azure_connector",
    "nessus",
    "qualys",
)


def _adapter(name: str):
    return importlib.import_module(f"modules.operations.integrations.{name}")


def list_adapters() -> list[str]:
    """Names of all registered integration adapters."""
    return list(ADAPTER_MODULES)


def masked_config_all() -> dict[str, Any]:
    """Secret-safe config view for every adapter (never reveals secret values)."""
    out: dict[str, Any] = {}
    for name in ADAPTER_MODULES:
        try:
            out[name] = _adapter(name).masked_config()
        except Exception as exc:  # noqa: BLE001 - one bad adapter must not break the rest
            out[name] = {"integration": name, "error": type(exc).__name__}
    return out


def build_http_transport(*, verify_ssl: bool = True, max_retries: int = 1):
    """Re-export of :func:`_base.build_http_transport` (real HTTP transport).

    Opt-in production transport for live collection; never an adapter default.
    """
    from modules.operations.integrations._base import build_http_transport as _b
    return _b(verify_ssl=verify_ssl, max_retries=max_retries)


def health_check_all() -> dict[str, Any]:
    """Run every adapter's config-based health check (no live calls in the skeleton)."""
    results: dict[str, Any] = {}
    for name in ADAPTER_MODULES:
        try:
            results[name] = _adapter(name).health_check()
        except Exception as exc:  # noqa: BLE001
            results[name] = {"ok": False, "source": name, "status": "adapter_error",
                             "items": [], "errors": [type(exc).__name__]}
    configured = sum(1 for r in results.values() if r.get("configured"))
    return {
        "adapters": results,
        "total": len(ADAPTER_MODULES),
        "configured": configured,
        "not_configured": len(ADAPTER_MODULES) - configured,
    }
