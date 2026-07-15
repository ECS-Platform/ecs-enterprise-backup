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


# --------------------------------------------------------------------------- #
# Milestone 2 — Evidence collection orchestrator
# --------------------------------------------------------------------------- #

#: Execution statuses used across jobs and runs.
STATUS_QUEUED = "Queued"
STATUS_RUNNING = "Running"
STATUS_COMPLETED = "Completed"
STATUS_FAILED = "Failed"
STATUS_PARTIAL = "Partially Completed"
STATUS_CONNECTOR_MISSING = "Connector Missing"
STATUS_CONFIG_REQUIRED = "Configuration Required"
STATUS_RETRY = "Retry"
STATUS_CANCELLED = "Cancelled"

ALL_STATUSES = (
    STATUS_QUEUED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED,
    STATUS_PARTIAL, STATUS_CONNECTOR_MISSING, STATUS_CONFIG_REQUIRED,
    STATUS_RETRY, STATUS_CANCELLED,
)


@dataclass
class EvidenceRecord:
    """Metadata captured for a single control execution within a run.

    Mutable (a run mutates its records as execution proceeds). Never stores
    credentials; ``output_excerpt`` is a truncated, non-secret preview only.
    """

    control_id: str
    technology: str = ""
    status: str = STATUS_QUEUED
    frameworks: tuple[str, ...] = ()
    asset_id: str = ""
    ok: bool = False
    error_type: str = ""
    message: str = ""
    rows_returned: int = 0
    duration_ms: int = 0
    evidence_id: str = ""
    evidence_filename: str = ""
    output_excerpt: str = ""
    attempts: int = 0
    executable: bool = False
    # Populated by the validation engine (Milestone 2, part 2).
    validation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frameworks"] = list(self.frameworks)
        return d


@dataclass
class EvidenceRun:
    """A collection run over a set of controls (one asset/app/env/framework/tech/bank)."""

    run_id: str
    scope_kind: str = ""          # asset | application | environment | framework | technology | all
    scope_value: str = ""
    requested_by: str = ""
    status: str = STATUS_QUEUED
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    records: list[EvidenceRecord] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scope_kind": self.scope_kind,
            "scope_value": self.scope_value,
            "requested_by": self.requested_by,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "summary": self.summary(),
            "records": [r.to_dict() for r in self.records],
            "audit_trail": list(self.audit_trail),
        }

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for r in self.records:
            counts[r.status] = counts.get(r.status, 0) + 1
        total = len(self.records)
        completed = counts.get(STATUS_COMPLETED, 0)
        return {
            "total": total,
            "completed": completed,
            "failed": counts.get(STATUS_FAILED, 0),
            "connector_missing": counts.get(STATUS_CONNECTOR_MISSING, 0),
            "config_required": counts.get(STATUS_CONFIG_REQUIRED, 0),
            "cancelled": counts.get(STATUS_CANCELLED, 0),
            "by_status": counts,
            "completion_rate": round(completed / total, 3) if total else 0.0,
        }


# --------------------------------------------------------------------------- #
# Milestone 2 — Evidence validation
# --------------------------------------------------------------------------- #

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_WARNING = "WARNING"
VERDICT_NOT_APPLICABLE = "NOT APPLICABLE"

CONTROL_STATUS_COMPLIANT = "Compliant"
CONTROL_STATUS_NON_COMPLIANT = "Non-Compliant"
CONTROL_STATUS_NEEDS_REVIEW = "Needs Review"
CONTROL_STATUS_NOT_ASSESSED = "Not Assessed"


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one control's evidence."""

    control_id: str
    technology: str = ""
    verdict: str = VERDICT_NOT_APPLICABLE
    control_status: str = CONTROL_STATUS_NOT_ASSESSED
    evidence_quality: float = 0.0     # 0.0 .. 1.0
    rule_id: str = ""
    rationale: str = ""
    frameworks: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frameworks"] = list(self.frameworks)
        d["evidence_quality"] = round(self.evidence_quality, 3)
        return d


# --------------------------------------------------------------------------- #
# Milestone 3 — Observations
# --------------------------------------------------------------------------- #

SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"
SEVERITY_INFO = "Informational"

OBS_STATUS_DRAFT = "Draft"
OBS_STATUS_SUBMITTED = "Submitted"
OBS_STATUS_APPROVED = "Approved"
OBS_STATUS_REJECTED = "Rejected"
OBS_STATUS_REMEDIATED = "Remediated"
OBS_STATUS_CLOSED = "Closed"

OBS_WORKFLOW = (
    OBS_STATUS_DRAFT, OBS_STATUS_SUBMITTED, OBS_STATUS_APPROVED,
    OBS_STATUS_REJECTED, OBS_STATUS_REMEDIATED, OBS_STATUS_CLOSED,
)


@dataclass
class Observation:
    """An audit observation generated from a failed/warning validation."""

    observation_id: str
    technology: str = ""
    asset_id: str = ""
    control_id: str = ""
    frameworks: tuple[str, ...] = ()
    severity: str = SEVERITY_MEDIUM
    observation: str = ""
    impact: str = ""
    recommendation: str = ""
    evidence_reference: str = ""
    owner: str = ""
    status: str = OBS_STATUS_DRAFT
    created_at: str = ""
    updated_at: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frameworks"] = list(self.frameworks)
        return d


# --------------------------------------------------------------------------- #
# Milestone 3 — Evidence repository
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class EvidenceArtifact:
    """A versioned evidence metadata record stored in the repository.

    Stores METADATA + a content hash/checksum — never credentials. ``content_hash``
    is a SHA-256 over the captured (non-secret) evidence content.
    """

    evidence_key: str            # stable identity across versions (e.g. asset+control)
    version: int = 1
    control_id: str = ""
    technology: str = ""
    asset_id: str = ""
    frameworks: tuple[str, ...] = ()
    run_id: str = ""
    verdict: str = ""
    control_status: str = ""
    evidence_quality: float = 0.0
    content_hash: str = ""       # sha256 hex
    checksum: str = ""           # short crc-like checksum (first 8 of hash)
    size_bytes: int = 0
    source: str = ""
    filename: str = ""
    collected_at: str = ""
    tags: tuple[str, ...] = ()
    evidence_id: str = ""
    environment: str = ""
    source_connector: str = ""
    source_item_id: str = ""
    source_url: str = ""
    mime_type: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    custody_mode: str = "REFERENCE_ONLY"
    source_modified_at: str = ""
    object_uri: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frameworks"] = list(self.frameworks)
        d["tags"] = list(self.tags)
        d["evidence_quality"] = round(self.evidence_quality, 3)
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        else:
            d.pop("metadata", None)
        return d
