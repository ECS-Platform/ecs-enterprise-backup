"""Asset service facade (Milestone 1, Module 2).

Serialization-friendly layer over the asset-discovery and fingerprint engines.
Produces the inventory, a technology inventory (roll-up), a fingerprint report,
and a coverage summary that ties assets back to the control/framework mapping
(Module 1). Returns plain dicts/lists for stable API/UI/test contracts.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from modules.audit_intelligence.engines import asset_discovery
from modules.audit_intelligence.models import Asset


def discover_assets(
    *,
    manual_records: Iterable[dict[str, Any]] | None = None,
    servicenow_transport: Callable[..., dict] | None = None,
    servicenow_client: Any | None = None,
    include_docker_compose: bool = False,
    include_enterprise_grc: bool = False,
    compose_path: str | None = None,
    role: str = "owner",
) -> list[Asset]:
    """Run discovery and return unified :class:`Asset` objects (unserialized)."""
    return asset_discovery.discover(
        manual_records=manual_records,
        servicenow_transport=servicenow_transport,
        servicenow_client=servicenow_client,
        include_docker_compose=include_docker_compose,
        include_enterprise_grc=include_enterprise_grc,
        compose_path=compose_path,
        role=role,
    )


def inventory(assets: list[Asset]) -> list[dict[str, Any]]:
    """Serialize an asset list to the unified inventory shape."""
    return [a.to_dict() for a in assets]


def technology_inventory(assets: list[Asset]) -> list[dict[str, Any]]:
    """Roll assets up by technology (count, environments, avg confidence)."""
    by_tech: dict[str, list[Asset]] = {}
    for a in assets:
        key = a.technology or "Unknown"
        by_tech.setdefault(key, []).append(a)

    rows: list[dict[str, Any]] = []
    for tech, group in by_tech.items():
        confidences = [a.confidence_score for a in group]
        rows.append(
            {
                "technology": tech,
                "asset_count": len(group),
                "environments": sorted({a.environment for a in group if a.environment}),
                "sources": sorted({a.source for a in group if a.source}),
                "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
                "in_catalog": bool(group and group[0].fingerprint and group[0].fingerprint.matched_catalog_technology),
                "applicable_frameworks": sorted(
                    {fw for a in group for fw in a.applicable_frameworks}
                ),
            }
        )
    rows.sort(key=lambda r: (-r["asset_count"], r["technology"].lower()))
    return rows


def fingerprint_report(assets: list[Asset]) -> dict[str, Any]:
    """Per-asset fingerprint detail plus confidence banding."""
    def band(score: float) -> str:
        if score >= 0.8:
            return "high"
        if score >= 0.5:
            return "medium"
        if score > 0.0:
            return "low"
        return "none"

    rows = []
    banding = {"high": 0, "medium": 0, "low": 0, "none": 0}
    for a in assets:
        b = band(a.confidence_score)
        banding[b] += 1
        rows.append(
            {
                "asset_id": a.asset_id,
                "hostname": a.hostname,
                "source": a.source,
                "technology": a.technology or "Unknown",
                "version": a.version,
                "confidence_score": round(a.confidence_score, 3),
                "confidence_band": b,
                "matched_catalog_technology": bool(
                    a.fingerprint and a.fingerprint.matched_catalog_technology
                ),
                "signals": list(a.fingerprint.signals) if a.fingerprint else [],
            }
        )
    return {"assets": rows, "confidence_banding": banding, "total": len(assets)}


def coverage_summary(assets: list[Asset]) -> dict[str, Any]:
    """How much of the inventory maps to known technologies/controls/frameworks."""
    total = len(assets)
    identified = [a for a in assets if a.technology and a.technology != "Unknown"]
    in_catalog = [
        a for a in assets
        if a.fingerprint and a.fingerprint.matched_catalog_technology
    ]
    frameworks = sorted({fw for a in assets for fw in a.applicable_frameworks})
    control_ids = {cid for a in assets for cid in a.applicable_control_ids}
    return {
        "total_assets": total,
        "identified_assets": len(identified),
        "unidentified_assets": total - len(identified),
        "assets_in_query_catalog": len(in_catalog),
        "identification_rate": round(len(identified) / total, 3) if total else 0.0,
        "catalog_coverage_rate": round(len(in_catalog) / total, 3) if total else 0.0,
        "applicable_frameworks": frameworks,
        "applicable_control_count": len(control_ids),
        "by_source": _count_by(assets, lambda a: a.source or "unknown"),
        "by_criticality": _count_by(assets, lambda a: a.criticality or "unspecified"),
        "by_environment": _count_by(assets, lambda a: a.environment or "unspecified"),
    }


def _count_by(assets: list[Asset], key: Callable[[Asset], str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for a in assets:
        out[key(a)] = out.get(key(a), 0) + 1
    return dict(sorted(out.items()))
