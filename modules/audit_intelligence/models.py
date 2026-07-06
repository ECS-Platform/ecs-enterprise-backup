"""Serializable data models for the ECS audit-intelligence layer (Milestone 1).

All models are frozen dataclasses with a ``to_dict()`` for stable JSON/UI/test
surfaces. They intentionally mirror (and normalize) the shapes already produced
by the predefined-query engine and the asset sources, rather than inventing a
parallel schema. Nothing here holds credentials, IPs, or secrets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# --------------------------------------------------------------------------- #
# Module 1 — Technology -> Control -> Framework mapping
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ControlRef:
    """A predefined-query control, normalized for the mapping/audit layer.

    Derived from ``predefined_queries_engine.get_all_controls()`` records; this is
    a read-only projection (we never write back to the engine).
    """

    control_id: str
    control_name: str
    technology: str
    frameworks: tuple[str, ...] = ()
    category: str = ""
    description: str = ""
    evidence_type: str = ""
    query: str = ""
    predefined: bool = False
    executable: bool = False
    status: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frameworks"] = list(self.frameworks)
        return d


@dataclass(frozen=True)
class TechnologyRef:
    """A technology present in the predefined-query catalog with coverage counts."""

    name: str
    control_count: int = 0
    framework_count: int = 0
    executable_control_count: int = 0
    control_ids: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["control_ids"] = list(self.control_ids)
        d["frameworks"] = list(self.frameworks)
        return d


@dataclass(frozen=True)
class FrameworkRef:
    """A compliance framework (e.g. RBI, PCI DSS, ITPP) with coverage counts."""

    name: str
    control_count: int = 0
    technology_count: int = 0
    control_ids: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["control_ids"] = list(self.control_ids)
        d["technologies"] = list(self.technologies)
        return d


@dataclass(frozen=True)
class MappingRow:
    """One flattened Technology -> Control -> Frameworks mapping row (for tables/search)."""

    technology: str
    control_id: str
    control_name: str
    frameworks: tuple[str, ...] = ()
    category: str = ""
    executable: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frameworks"] = list(self.frameworks)
        return d


# --------------------------------------------------------------------------- #
# Module 2 — Asset discovery & technology fingerprinting
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TechnologyFingerprint:
    """Deterministic inference of a technology (+ optional version) for an asset."""

    technology: str
    confidence: float = 0.0  # 0.0 .. 1.0
    version: str = ""
    signals: tuple[str, ...] = ()  # human-readable reasons the tech was inferred
    matched_catalog_technology: bool = False  # tech exists in the query catalog

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["signals"] = list(self.signals)
        d["confidence"] = round(self.confidence, 3)
        return d


@dataclass(frozen=True)
class Asset:
    """Unified asset record normalized from any discovery source.

    Sources: ServiceNow CMDB skeleton, manual import, docker-compose demo, and the
    existing enterprise-GRC CMDB. Credential/secret fields are never carried here.
    """

    asset_id: str
    hostname: str = ""
    environment: str = ""
    application: str = ""
    owner: str = ""
    technology: str = ""
    version: str = ""
    operating_system: str = ""
    cloud: str = ""
    criticality: str = ""
    confidence_score: float = 0.0  # 0.0 .. 1.0 (overall discovery/fingerprint confidence)
    source: str = ""
    fingerprint: TechnologyFingerprint | None = None
    # Cross-link to Module 1: controls/frameworks applicable to this asset's tech.
    applicable_control_ids: tuple[str, ...] = ()
    applicable_frameworks: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)  # original source fields (non-secret)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["confidence_score"] = round(self.confidence_score, 3)
        d["applicable_control_ids"] = list(self.applicable_control_ids)
        d["applicable_frameworks"] = list(self.applicable_frameworks)
        d["fingerprint"] = self.fingerprint.to_dict() if self.fingerprint else None
        return d
