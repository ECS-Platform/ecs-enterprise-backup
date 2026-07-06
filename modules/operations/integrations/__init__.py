"""ECS enterprise integration skeletons (config-driven; no real calls in tests).

Currently ships integration *skeletons* only:
  * servicenow_cmdb — ServiceNow CMDB asset/CI fetch interface + mapping stubs.
  * archer          — Archer control/framework fetch interface + mapping stubs.

Both are credential-externalised, never log secrets, and accept an injectable
transport so unit tests can supply mocked responses without any network access.
"""

from __future__ import annotations

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
