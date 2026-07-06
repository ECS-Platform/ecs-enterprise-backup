"""Mapping service facade (Milestone 1, Module 1).

A thin, serialization-friendly layer over
:mod:`modules.audit_intelligence.engines.technology_control_mapping`. Returns
plain dicts/lists (via each model's ``to_dict``) so future REST APIs and UI
templates have a stable contract without importing the engine directly.

No business logic beyond shaping/serialization lives here.

Caching
-------
The mapping catalog is a *pure, deterministic projection* over the static
predefined-query catalog (it never changes at runtime), so the argument-free
derivations (:func:`technologies`, :func:`frameworks`, :func:`controls`,
:func:`graph`, :func:`stats`, :func:`filter_options`) are memoised in a
process-local TTL cache. This keeps the executive dashboard and mapping pages
cheap under repeated hits without introducing Redis. Call :func:`reset_cache`
(or the shared ``reset_all_caches``) after force-reloading the catalog / in
tests.
"""

from __future__ import annotations

from typing import Any

from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.shared.utils.simple_cache import cached

#: Catalog derivations are static per process; a long TTL is safe and bounds
#: staleness if the underlying catalog is ever hot-reloaded.
_CATALOG_TTL_SECONDS = 600


@cached(ttl_seconds=_CATALOG_TTL_SECONDS, maxsize=1)
def technologies() -> list[dict[str, Any]]:
    """All technologies with coverage counts (serialized)."""
    return [t.to_dict() for t in mapping.list_technologies()]


@cached(ttl_seconds=_CATALOG_TTL_SECONDS, maxsize=1)
def frameworks() -> list[dict[str, Any]]:
    """All frameworks with coverage counts (serialized)."""
    return [f.to_dict() for f in mapping.list_frameworks()]


@cached(ttl_seconds=_CATALOG_TTL_SECONDS, maxsize=1)
def controls() -> list[dict[str, Any]]:
    """All controls, normalized (serialized)."""
    return [c.to_dict() for c in mapping.all_controls()]


def technology_detail(technology: str) -> dict[str, Any] | None:
    """A single technology plus its controls and frameworks (for a detail view)."""
    ref = mapping.get_technology(technology)
    if ref is None:
        return None
    detail = ref.to_dict()
    detail["controls"] = [c.to_dict() for c in mapping.controls_for_technology(technology)]
    return detail


def framework_detail(framework: str) -> dict[str, Any] | None:
    """A single framework plus its controls and technologies (for a detail view)."""
    ref = mapping.get_framework(framework)
    if ref is None:
        return None
    detail = ref.to_dict()
    detail["controls"] = [c.to_dict() for c in mapping.controls_for_framework(framework)]
    return detail


def control_detail(control_id: str) -> dict[str, Any] | None:
    """A single control with its technology + frameworks (for a detail view)."""
    ref = mapping.get_control(control_id)
    return ref.to_dict() if ref else None


@cached(ttl_seconds=_CATALOG_TTL_SECONDS, maxsize=1)
def graph() -> dict[str, Any]:
    """The full Technology -> Controls -> Frameworks graph + stats."""
    return mapping.build_mapping_graph()


def search(
    *,
    query: str = "",
    technology: str = "",
    framework: str = "",
) -> list[dict[str, Any]]:
    """Filtered flattened mapping rows (serialized)."""
    return [
        row.to_dict()
        for row in mapping.search_mappings(
            query=query, technology=technology, framework=framework
        )
    ]


@cached(ttl_seconds=_CATALOG_TTL_SECONDS, maxsize=1)
def stats() -> dict[str, Any]:
    """Coverage summary across the mapping graph."""
    return mapping.mapping_stats()


@cached(ttl_seconds=_CATALOG_TTL_SECONDS, maxsize=1)
def filter_options() -> dict[str, list[str]]:
    """Dropdown options for a future mapping UI (technologies + frameworks)."""
    return {
        "technologies": ["All Technologies"] + mapping.technology_names(),
        "frameworks": ["All Frameworks"] + mapping.framework_names(),
    }


def reset_cache() -> None:
    """Clear this service's memoised catalog derivations and the engine cache.

    Use after force-reloading the predefined-query catalog or in tests. Safe to
    call anytime; it only drops caches (correctness is unaffected).
    """
    for fn in (technologies, frameworks, controls, graph, stats, filter_options):
        fn.cache_clear()  # type: ignore[attr-defined]
    mapping.reset_cache()
