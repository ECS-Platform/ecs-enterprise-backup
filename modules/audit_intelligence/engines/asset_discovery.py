"""Asset discovery engine (Milestone 1, Module 2).

Normalizes assets from multiple sources into a single unified :class:`Asset`
inventory, applies deterministic technology fingerprinting, and cross-links each
asset to the controls/frameworks applicable to its technology (via Module 1).

Sources (all offline / mockable — no live network or Docker required):
  * ``servicenow``     — the ServiceNow CMDB skeleton client (inject a mock
                          transport in tests; never calls a real instance).
  * ``manual``         — a caller-supplied list of asset dicts (manual import).
  * ``docker_compose`` — parses ``docker-compose.yml`` service definitions
                          (image / container_name) to enumerate demo assets.
  * ``enterprise_grc`` — reuses the existing enterprise-GRC CMDB inventory.

Nothing here stores credentials/secrets; only non-secret descriptive metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.engines import technology_fingerprint as fp
from modules.audit_intelligence.models import Asset

_REPO_ROOT = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------- #
# Normalization helpers
# --------------------------------------------------------------------------- #


def _clean(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _link_controls(technology: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Applicable control_ids + frameworks for a technology (from Module 1)."""
    if not technology:
        return (), ()
    controls = mapping.controls_for_technology(technology)
    control_ids = tuple(sorted(c.control_id for c in controls))
    frameworks = tuple(mapping.frameworks_for_technology(technology))
    return control_ids, frameworks


def _finalize(
    *,
    asset_id: str,
    source: str,
    hostname: str = "",
    environment: str = "",
    application: str = "",
    owner: str = "",
    operating_system: str = "",
    cloud: str = "",
    criticality: str = "",
    raw: dict[str, Any] | None = None,
    fingerprint_hints: dict[str, Any] | None = None,
) -> Asset:
    """Build a fully-populated :class:`Asset` incl. fingerprint + control links."""
    hints = dict(fingerprint_hints or {})
    # Common signals used by the fingerprinter.
    hints.setdefault("name", hostname or application)
    hints.setdefault("environment", environment)
    fingerprint = fp.fingerprint_asset(hints)

    technology = fingerprint.technology if fingerprint.technology != "Unknown" else ""
    control_ids, frameworks = _link_controls(technology)

    return Asset(
        asset_id=asset_id or hostname or application or "UNKNOWN",
        hostname=hostname,
        environment=environment,
        application=application,
        owner=owner,
        technology=technology,
        version=fingerprint.version,
        operating_system=operating_system,
        cloud=cloud,
        criticality=criticality,
        confidence_score=fingerprint.confidence,
        source=source,
        fingerprint=fingerprint,
        applicable_control_ids=control_ids,
        applicable_frameworks=frameworks,
        raw=dict(raw or {}),
    )


# --------------------------------------------------------------------------- #
# Source: manual import
# --------------------------------------------------------------------------- #


def discover_from_manual(records: Iterable[dict[str, Any]]) -> list[Asset]:
    """Normalize a caller-supplied list of asset dicts (manual import).

    Recognized keys (all optional): asset_id, hostname/name, environment,
    application/app, owner, technology, version, os/operating_system, cloud,
    criticality, image, ports.
    """
    assets: list[Asset] = []
    for rec in records or []:
        rec = dict(rec)
        hostname = _clean(rec.get("hostname") or rec.get("name"))
        hints: dict[str, Any] = {
            "name": hostname or _clean(rec.get("application") or rec.get("app")),
            "technology": _clean(rec.get("technology")),
            "image": _clean(rec.get("image")),
            "ports": rec.get("ports") or [],
            "version": _clean(rec.get("version")),
            "operating_system": _clean(rec.get("os") or rec.get("operating_system")),
        }
        assets.append(
            _finalize(
                asset_id=_clean(rec.get("asset_id")),
                source="manual",
                hostname=hostname,
                environment=_clean(rec.get("environment")),
                application=_clean(rec.get("application") or rec.get("app")),
                owner=_clean(rec.get("owner")),
                operating_system=_clean(rec.get("os") or rec.get("operating_system")),
                cloud=_clean(rec.get("cloud")),
                criticality=_clean(rec.get("criticality")),
                raw=rec,
                fingerprint_hints=hints,
            )
        )
    return assets


# --------------------------------------------------------------------------- #
# Source: ServiceNow CMDB skeleton
# --------------------------------------------------------------------------- #


def discover_from_servicenow(
    *,
    transport: Callable[..., dict] | None = None,
    limit: int = 100,
    client: Any | None = None,
) -> list[Asset]:
    """Fetch + normalize assets from the ServiceNow CMDB skeleton.

    A mock ``transport`` (or a pre-built ``client``) MUST be supplied in tests —
    the skeleton refuses real calls, so this never touches a live instance.
    Returns [] gracefully if the integration is not configured.
    """
    from modules.operations.integrations.servicenow_cmdb import (
        IntegrationNotConfigured,
        ServiceNowCmdbClient,
    )

    if client is None:
        client = ServiceNowCmdbClient(transport=transport)
    try:
        raw_assets = client.fetch_assets(limit=limit)
    except IntegrationNotConfigured:
        return []

    assets: list[Asset] = []
    for rec in raw_assets:
        rec = dict(rec)
        hostname = _clean(rec.get("name"))
        hints = {
            "name": hostname,
            "asset_class": _clean(rec.get("asset_class")),
            "operating_system": _clean(rec.get("os") or rec.get("operating_system")),
        }
        assets.append(
            _finalize(
                asset_id=_clean(rec.get("asset_id")) or hostname,
                source="servicenow_cmdb",
                hostname=hostname,
                environment=_clean(rec.get("environment")),
                application=_clean(rec.get("application")),
                owner=_clean(rec.get("owner")),
                operating_system=_clean(rec.get("operating_system") or rec.get("os")),
                cloud=_clean(rec.get("cloud")),
                criticality=_clean(rec.get("criticality")),
                raw=rec,
                fingerprint_hints=hints,
            )
        )
    return assets


# --------------------------------------------------------------------------- #
# Source: docker-compose (offline parse)
# --------------------------------------------------------------------------- #


def _compose_path() -> Path:
    return _REPO_ROOT / "docker-compose.yml"


def discover_from_docker_compose(compose_path: str | Path | None = None) -> list[Asset]:
    """Enumerate demo assets by parsing docker-compose.yml service definitions.

    Offline only — reads the YAML file; does NOT talk to the Docker daemon.
    Each service becomes an asset fingerprinted from its image/name.
    """
    path = Path(compose_path) if compose_path else _compose_path()
    if not path.is_file():
        return []
    try:
        import yaml

        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001 - malformed/missing compose -> no assets
        return []

    services = data.get("services") or {}
    assets: list[Asset] = []
    for svc_name, svc in services.items():
        svc = svc or {}
        image = _clean(svc.get("image"))
        container = _clean(svc.get("container_name")) or _clean(svc_name)
        ports = svc.get("ports") or []
        hints = {
            "name": container or svc_name,
            "service": _clean(svc_name),
            "image": image,
            "ports": ports,
        }
        assets.append(
            _finalize(
                asset_id=container or _clean(svc_name),
                source="docker_compose",
                hostname=container or _clean(svc_name),
                environment="Local Demo",
                raw={"service": svc_name, "image": image, "container_name": container},
                fingerprint_hints=hints,
            )
        )
    assets.sort(key=lambda a: a.asset_id)
    return assets


# --------------------------------------------------------------------------- #
# Source: existing enterprise-GRC CMDB inventory
# --------------------------------------------------------------------------- #


def discover_from_enterprise_grc(role: str = "owner") -> list[Asset]:
    """Reuse the existing enterprise-GRC CMDB inventory as a discovery source."""
    try:
        from modules.enterprise_grc.engines.enterprise_grc import build_cmdb_inventory
    except Exception:  # noqa: BLE001 - optional dependency; never break discovery
        return []

    inventory = build_cmdb_inventory(role=role) or {}
    rows = inventory.get("rows") or []
    assets: list[Asset] = []
    for rec in rows:
        rec = dict(rec)
        hostname = _clean(rec.get("name"))
        asset_type = _clean(rec.get("type"))
        hints = {
            "name": hostname,
            "asset_type": asset_type,
        }
        assets.append(
            _finalize(
                asset_id=_clean(rec.get("asset_id")) or hostname,
                source="enterprise_grc_cmdb",
                hostname=hostname,
                environment=_clean(rec.get("environment")),
                application=hostname if asset_type == "Application" else "",
                owner=_clean(rec.get("owner")),
                criticality=_clean(rec.get("criticality")),
                raw=rec,
                fingerprint_hints=hints,
            )
        )
    return assets


# --------------------------------------------------------------------------- #
# Aggregate discovery
# --------------------------------------------------------------------------- #

_SOURCE_LABELS = {
    "manual": "Manual Import",
    "servicenow": "ServiceNow CMDB",
    "docker_compose": "Docker Demo",
    "enterprise_grc": "Enterprise GRC CMDB",
}


def discover(
    *,
    manual_records: Iterable[dict[str, Any]] | None = None,
    servicenow_transport: Callable[..., dict] | None = None,
    servicenow_client: Any | None = None,
    include_docker_compose: bool = False,
    include_enterprise_grc: bool = False,
    compose_path: str | Path | None = None,
    role: str = "owner",
) -> list[Asset]:
    """Run the requested discovery sources and return a merged asset inventory.

    Only sources that are explicitly provided/enabled run — so a plain call is a
    no-op (safe default). De-duplicates by ``asset_id`` (first source wins).
    """
    collected: list[Asset] = []
    if manual_records is not None:
        collected += discover_from_manual(manual_records)
    if servicenow_transport is not None or servicenow_client is not None:
        collected += discover_from_servicenow(
            transport=servicenow_transport, client=servicenow_client
        )
    if include_docker_compose:
        collected += discover_from_docker_compose(compose_path)
    if include_enterprise_grc:
        collected += discover_from_enterprise_grc(role=role)

    # De-duplicate by asset_id, preserving first occurrence (source priority order).
    seen: set[str] = set()
    merged: list[Asset] = []
    for asset in collected:
        key = asset.asset_id
        if key in seen:
            continue
        seen.add(key)
        merged.append(asset)
    return merged
