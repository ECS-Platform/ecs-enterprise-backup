"""Technology -> Control -> Framework mapping engine (Milestone 1, Module 1).

Derives the audit-readiness relationship graph:

    Technology  ->  Predefined Queries (Controls)  ->  Frameworks

purely by READING the existing predefined-query catalog
(``predefined_queries_engine.get_all_controls()``). It adds NO new catalog and
mutates nothing — it is a deterministic projection/aggregation over the 167
controls already in the platform.

Example chain (NGINX):
    NGINX -> {NGX-001, NGX-002, ...} -> {TLS controls} -> {RBI, PCI DSS, ITPP} -> Evidence

Everything here is offline and deterministic (safe for unit tests). Results are
returned as the frozen dataclasses in :mod:`modules.audit_intelligence.models`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from modules.audit_intelligence.models import (
    ControlRef,
    FrameworkRef,
    MappingRow,
    TechnologyRef,
)

# --------------------------------------------------------------------------- #
# Source access (read-only over the predefined-query engine)
# --------------------------------------------------------------------------- #


def _raw_controls() -> list[dict[str, Any]]:
    """Fetch all controls from the predefined-query engine (read-only)."""
    from modules.operations.engines import predefined_queries_engine as engine

    return engine.get_all_controls()


def _control_ref_from_raw(raw: dict[str, Any]) -> ControlRef:
    frameworks = tuple(
        fw for fw in (raw.get("frameworks") or []) if str(fw).strip()
    )
    return ControlRef(
        control_id=str(raw.get("control_id") or "").strip(),
        control_name=str(raw.get("control_name") or "").strip(),
        technology=str(raw.get("technology") or "").strip() or "Unknown",
        frameworks=frameworks,
        category=str(raw.get("category") or "").strip(),
        description=str(raw.get("description") or "").strip(),
        evidence_type=str(raw.get("evidence_type") or "").strip(),
        query=str(raw.get("query") or "").strip(),
        predefined=bool(raw.get("predefined")),
        executable=bool(raw.get("executable")),
        status=str(raw.get("status") or "").strip(),
    )


@lru_cache(maxsize=1)
def _all_control_refs() -> tuple[ControlRef, ...]:
    """All controls as normalized :class:`ControlRef` (cached; deterministic)."""
    refs = [
        _control_ref_from_raw(raw)
        for raw in _raw_controls()
        if str(raw.get("control_id") or "").strip()
    ]
    refs.sort(key=lambda c: c.control_id)
    return tuple(refs)


def reset_cache() -> None:
    """Clear the memoized control projection (use after force-reloading the catalog)."""
    _all_control_refs.cache_clear()


# --------------------------------------------------------------------------- #
# Controls
# --------------------------------------------------------------------------- #


def all_controls() -> list[ControlRef]:
    """Every control in the catalog as a :class:`ControlRef`."""
    return list(_all_control_refs())


def get_control(control_id: str) -> ControlRef | None:
    cid = (control_id or "").strip()
    for ref in _all_control_refs():
        if ref.control_id == cid:
            return ref
    return None


def controls_for_technology(technology: str) -> list[ControlRef]:
    tech = (technology or "").strip().lower()
    return [c for c in _all_control_refs() if c.technology.lower() == tech]


def controls_for_framework(framework: str) -> list[ControlRef]:
    fw = (framework or "").strip().lower()
    return [
        c for c in _all_control_refs()
        if any(f.lower() == fw for f in c.frameworks)
    ]


# --------------------------------------------------------------------------- #
# Technologies
# --------------------------------------------------------------------------- #


def _distinct_sorted(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({v for v in values if v}))


def list_technologies() -> list[TechnologyRef]:
    """All technologies present in the catalog, with coverage counts."""
    by_tech: dict[str, list[ControlRef]] = {}
    for c in _all_control_refs():
        by_tech.setdefault(c.technology, []).append(c)

    result: list[TechnologyRef] = []
    for tech, controls in by_tech.items():
        frameworks = _distinct_sorted(fw for c in controls for fw in c.frameworks)
        result.append(
            TechnologyRef(
                name=tech,
                control_count=len(controls),
                framework_count=len(frameworks),
                executable_control_count=sum(1 for c in controls if c.executable),
                control_ids=tuple(sorted(c.control_id for c in controls)),
                frameworks=frameworks,
            )
        )
    result.sort(key=lambda t: t.name.lower())
    return result


def get_technology(technology: str) -> TechnologyRef | None:
    tech = (technology or "").strip().lower()
    for ref in list_technologies():
        if ref.name.lower() == tech:
            return ref
    return None


def technology_names() -> list[str]:
    return [t.name for t in list_technologies()]


def frameworks_for_technology(technology: str) -> list[str]:
    controls = controls_for_technology(technology)
    return list(_distinct_sorted(fw for c in controls for fw in c.frameworks))


# --------------------------------------------------------------------------- #
# Frameworks
# --------------------------------------------------------------------------- #


def list_frameworks() -> list[FrameworkRef]:
    """All frameworks referenced by any control, with coverage counts."""
    by_fw_controls: dict[str, list[str]] = {}
    by_fw_techs: dict[str, set[str]] = {}
    for c in _all_control_refs():
        for fw in c.frameworks:
            by_fw_controls.setdefault(fw, []).append(c.control_id)
            by_fw_techs.setdefault(fw, set()).add(c.technology)

    result: list[FrameworkRef] = []
    for fw, control_ids in by_fw_controls.items():
        techs = _distinct_sorted(by_fw_techs.get(fw, set()))
        result.append(
            FrameworkRef(
                name=fw,
                control_count=len(control_ids),
                technology_count=len(techs),
                control_ids=tuple(sorted(control_ids)),
                technologies=techs,
            )
        )
    result.sort(key=lambda f: f.name.lower())
    return result


def get_framework(framework: str) -> FrameworkRef | None:
    fw = (framework or "").strip().lower()
    for ref in list_frameworks():
        if ref.name.lower() == fw:
            return ref
    return None


def framework_names() -> list[str]:
    return [f.name for f in list_frameworks()]


def technologies_for_framework(framework: str) -> list[str]:
    controls = controls_for_framework(framework)
    return list(_distinct_sorted(c.technology for c in controls))


def frameworks_for_control(control_id: str) -> list[str]:
    ref = get_control(control_id)
    return list(ref.frameworks) if ref else []


def technology_for_control(control_id: str) -> str | None:
    ref = get_control(control_id)
    return ref.technology if ref else None


# --------------------------------------------------------------------------- #
# Graph + flattened rows + search
# --------------------------------------------------------------------------- #


def build_mapping_graph() -> dict[str, Any]:
    """Normalized Technology -> Controls -> Frameworks graph.

    Shape::

        {
          "technologies": [
            {"technology": "NGINX", "framework_count": 3, "controls": [
                {"control_id": "NGX-001", "control_name": "...",
                 "frameworks": ["RBI", "PCI DSS"], "category": "...",
                 "executable": true},
                ...
            ]},
            ...
          ],
          "stats": {...}
        }
    """
    techs: list[dict[str, Any]] = []
    for tech in list_technologies():
        controls = controls_for_technology(tech.name)
        techs.append(
            {
                "technology": tech.name,
                "control_count": tech.control_count,
                "framework_count": tech.framework_count,
                "executable_control_count": tech.executable_control_count,
                "frameworks": list(tech.frameworks),
                "controls": [
                    {
                        "control_id": c.control_id,
                        "control_name": c.control_name,
                        "category": c.category,
                        "frameworks": list(c.frameworks),
                        "executable": c.executable,
                    }
                    for c in controls
                ],
            }
        )
    return {"technologies": techs, "stats": mapping_stats()}


def mapping_rows() -> list[MappingRow]:
    """Flattened one-row-per-control mapping (Technology -> Control -> Frameworks)."""
    return [
        MappingRow(
            technology=c.technology,
            control_id=c.control_id,
            control_name=c.control_name,
            frameworks=c.frameworks,
            category=c.category,
            executable=c.executable,
        )
        for c in _all_control_refs()
    ]


def search_mappings(
    *,
    query: str = "",
    technology: str = "",
    framework: str = "",
) -> list[MappingRow]:
    """Filter the flattened mapping rows by free text / technology / framework."""
    rows = mapping_rows()
    tech = (technology or "").strip().lower()
    fw = (framework or "").strip().lower()
    q = (query or "").strip().lower()

    if tech and tech not in ("all", "all technologies"):
        rows = [r for r in rows if r.technology.lower() == tech]
    if fw and fw not in ("all", "all frameworks"):
        rows = [r for r in rows if any(f.lower() == fw for f in r.frameworks)]
    if q:
        rows = [
            r
            for r in rows
            if q in r.control_id.lower()
            or q in r.control_name.lower()
            or q in r.technology.lower()
            or q in r.category.lower()
            or any(q in f.lower() for f in r.frameworks)
        ]
    return rows


def mapping_stats() -> dict[str, Any]:
    """Coverage summary across the mapping graph."""
    controls = _all_control_refs()
    techs = list_technologies()
    fws = list_frameworks()
    return {
        "technologies": len(techs),
        "controls": len(controls),
        "frameworks": len(fws),
        "executable_controls": sum(1 for c in controls if c.executable),
        "controls_without_framework": sum(1 for c in controls if not c.frameworks),
        "technologies_with_executable": sum(
            1 for t in techs if t.executable_control_count > 0
        ),
    }
