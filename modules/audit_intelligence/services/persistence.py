"""Durable persistence foundation for ECS Audit Intelligence.

The audit-intelligence engines keep their working state in module-level in-memory
stores (fast, dependency-free, ideal for the demo and tests). This module adds a
**DB-ready persistence foundation** *alongside* that behavior — it does not
replace or disable the in-memory engines. It provides:

  * :class:`AuditPersistence` — an abstract repository interface covering every
    durable audit-intelligence entity;
  * :class:`InMemoryAuditPersistence` — a reference implementation (used by tests
    and as the default), semantically identical to the engine stores;
  * serialization / deserialization helpers that round-trip the frozen/mutable
    dataclasses in :mod:`modules.audit_intelligence.models` through plain JSON-safe
    dicts (so any backend can store them as JSON or normalized columns);
  * a pluggable provider (:func:`get_persistence` / :func:`set_persistence`) so an
    operator can swap in the SQL backend without touching call sites.

Entities covered (the seven durable surfaces):
  1. evidence runs            (EvidenceRun)
  2. evidence results         (EvidenceRecord, per run)
  3. validation results       (ValidationResult)
  4. observations             (Observation)
  5. evidence versions        (EvidenceArtifact, versioned per evidence_key)
  6. evidence packs           (pack manifests — plain dicts)
  7. scheduler history        (scheduler event dicts)

Safety: nothing here stores credentials/secrets. Content bodies are never stored
(the engines only ever hold hashes + non-secret excerpts). No live database is
required — the default backend is in-memory and the SQL backend defaults to
SQLite (see :mod:`modules.audit_intelligence.services.sql_persistence`).
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Optional

from modules.audit_intelligence.models import (
    EvidenceArtifact,
    EvidenceRecord,
    EvidenceRun,
    Observation,
    ValidationResult,
)

# --------------------------------------------------------------------------- #
# Serialization / deserialization helpers
# --------------------------------------------------------------------------- #
# The models expose ``to_dict()`` (JSON-safe). For durability we also need the
# inverse. These helpers are tolerant: unknown keys are ignored and missing keys
# fall back to the dataclass defaults, so a schema that grows over time stays
# backward/forward compatible.


def _tuple(value: Any) -> tuple:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def record_to_dict(record: EvidenceRecord) -> dict[str, Any]:
    return record.to_dict()


def record_from_dict(data: dict[str, Any]) -> EvidenceRecord:
    return EvidenceRecord(
        control_id=data.get("control_id", ""),
        technology=data.get("technology", ""),
        status=data.get("status", ""),
        frameworks=_tuple(data.get("frameworks")),
        asset_id=data.get("asset_id", ""),
        ok=bool(data.get("ok", False)),
        error_type=data.get("error_type", ""),
        message=data.get("message", ""),
        rows_returned=int(data.get("rows_returned", 0) or 0),
        duration_ms=int(data.get("duration_ms", 0) or 0),
        evidence_id=data.get("evidence_id", ""),
        evidence_filename=data.get("evidence_filename", ""),
        output_excerpt=data.get("output_excerpt", ""),
        attempts=int(data.get("attempts", 0) or 0),
        executable=bool(data.get("executable", False)),
        validation=data.get("validation"),
    )


def run_to_dict(run: EvidenceRun) -> dict[str, Any]:
    """Full, round-trippable dict for a run (includes raw records + audit trail)."""
    return {
        "run_id": run.run_id,
        "scope_kind": run.scope_kind,
        "scope_value": run.scope_value,
        "requested_by": run.requested_by,
        "status": run.status,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "records": [record_to_dict(r) for r in run.records],
        "audit_trail": list(run.audit_trail),
    }


def run_from_dict(data: dict[str, Any]) -> EvidenceRun:
    run = EvidenceRun(
        run_id=data.get("run_id", ""),
        scope_kind=data.get("scope_kind", ""),
        scope_value=data.get("scope_value", ""),
        requested_by=data.get("requested_by", ""),
        status=data.get("status", ""),
        created_at=data.get("created_at", ""),
        started_at=data.get("started_at", ""),
        finished_at=data.get("finished_at", ""),
    )
    run.records = [record_from_dict(r) for r in data.get("records", []) or []]
    run.audit_trail = list(data.get("audit_trail", []) or [])
    return run


def validation_to_dict(result: ValidationResult) -> dict[str, Any]:
    return result.to_dict()


def validation_from_dict(data: dict[str, Any]) -> ValidationResult:
    return ValidationResult(
        control_id=data.get("control_id", ""),
        technology=data.get("technology", ""),
        verdict=data.get("verdict", ""),
        control_status=data.get("control_status", ""),
        evidence_quality=float(data.get("evidence_quality", 0.0) or 0.0),
        rule_id=data.get("rule_id", ""),
        rationale=data.get("rationale", ""),
        frameworks=_tuple(data.get("frameworks")),
    )


def observation_to_dict(obs: Observation) -> dict[str, Any]:
    return obs.to_dict()


def observation_from_dict(data: dict[str, Any]) -> Observation:
    obs = Observation(
        observation_id=data.get("observation_id", ""),
        technology=data.get("technology", ""),
        asset_id=data.get("asset_id", ""),
        control_id=data.get("control_id", ""),
        frameworks=_tuple(data.get("frameworks")),
        severity=data.get("severity", ""),
        observation=data.get("observation", ""),
        impact=data.get("impact", ""),
        recommendation=data.get("recommendation", ""),
        evidence_reference=data.get("evidence_reference", ""),
        owner=data.get("owner", ""),
        status=data.get("status", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )
    obs.history = list(data.get("history", []) or [])
    return obs


def artifact_to_dict(artifact: EvidenceArtifact) -> dict[str, Any]:
    return artifact.to_dict()


def _metadata_tuple(value: Any) -> tuple[tuple[str, str], ...]:
    if not value:
        return ()
    if isinstance(value, dict):
        return tuple(sorted((str(k), str(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        pairs: list[tuple[str, str]] = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                pairs.append((str(item[0]), str(item[1])))
        return tuple(sorted(pairs))
    return ()


def artifact_from_dict(data: dict[str, Any]) -> EvidenceArtifact:
    return EvidenceArtifact(
        evidence_key=data.get("evidence_key", ""),
        version=int(data.get("version", 1) or 1),
        control_id=data.get("control_id", ""),
        technology=data.get("technology", ""),
        asset_id=data.get("asset_id", ""),
        frameworks=_tuple(data.get("frameworks")),
        run_id=data.get("run_id", ""),
        verdict=data.get("verdict", ""),
        control_status=data.get("control_status", ""),
        evidence_quality=float(data.get("evidence_quality", 0.0) or 0.0),
        content_hash=data.get("content_hash", ""),
        checksum=data.get("checksum", ""),
        size_bytes=int(data.get("size_bytes", 0) or 0),
        source=data.get("source", ""),
        filename=data.get("filename", ""),
        collected_at=data.get("collected_at", ""),
        tags=_tuple(data.get("tags")),
        evidence_id=data.get("evidence_id", ""),
        environment=data.get("environment", ""),
        source_connector=data.get("source_connector", ""),
        source_item_id=data.get("source_item_id", ""),
        source_url=data.get("source_url", ""),
        mime_type=data.get("mime_type", ""),
        metadata=_metadata_tuple(data.get("metadata")),
        custody_mode=data.get("custody_mode", "REFERENCE_ONLY"),
        source_modified_at=data.get("source_modified_at", ""),
        object_uri=data.get("object_uri", ""),
    )


# --------------------------------------------------------------------------- #
# Persistence interface
# --------------------------------------------------------------------------- #
class AuditPersistence(ABC):
    """Abstract durable store for audit-intelligence entities.

    Implementations must be safe to call from the request path and must never
    raise for a missing key (return ``None`` / ``[]`` instead). All inputs/outputs
    are model instances; backends serialize via the helpers above.
    """

    # ---- lifecycle -------------------------------------------------------- #
    @abstractmethod
    def initialize(self) -> None:
        """Create/verify backing structures (idempotent)."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all persisted data (used by tests / re-seeding)."""

    # ---- 1) evidence runs  +  2) evidence results ------------------------- #
    @abstractmethod
    def save_run(self, run: EvidenceRun) -> EvidenceRun:
        """Insert or update a run (records/results are saved with it)."""

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[EvidenceRun]:
        ...

    @abstractmethod
    def list_runs(self) -> list[EvidenceRun]:
        """Runs, newest first (by created_at)."""

    @abstractmethod
    def get_run_results(self, run_id: str) -> list[EvidenceRecord]:
        """The per-control evidence results for a run (empty if unknown)."""

    # ---- 3) validation results -------------------------------------------- #
    @abstractmethod
    def save_validation_results(self, run_id: str, results: list[ValidationResult]) -> None:
        ...

    @abstractmethod
    def get_validation_results(self, run_id: str) -> list[ValidationResult]:
        ...

    # ---- 4) observations -------------------------------------------------- #
    @abstractmethod
    def save_observation(self, observation: Observation) -> Observation:
        ...

    @abstractmethod
    def get_observation(self, observation_id: str) -> Optional[Observation]:
        ...

    @abstractmethod
    def list_observations(self) -> list[Observation]:
        ...

    # ---- 5) evidence versions --------------------------------------------- #
    @abstractmethod
    def append_evidence_version(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        """Append a new version for the artifact's evidence_key."""

    @abstractmethod
    def get_evidence_versions(self, evidence_key: str) -> list[EvidenceArtifact]:
        """All versions for a key, ascending by version (empty if unknown)."""

    @abstractmethod
    def list_evidence_latest(self) -> list[EvidenceArtifact]:
        """Latest version of every evidence key."""

    @abstractmethod
    def find_evidence_by_source_hash(
        self, source_item_id: str, content_hash: str,
    ) -> Optional[EvidenceArtifact]:
        """Return an existing version for an idempotent (source_item_id, hash) pair."""

    @abstractmethod
    def list_all_evidence_versions(self) -> list[EvidenceArtifact]:
        """Every persisted evidence version (ascending by key, then version)."""

    # ---- 6) evidence packs ------------------------------------------------ #
    @abstractmethod
    def save_pack(self, pack_id: str, manifest: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get_pack(self, pack_id: str) -> Optional[dict[str, Any]]:
        ...

    @abstractmethod
    def list_packs(self) -> list[dict[str, Any]]:
        ...

    # ---- 7) scheduler history --------------------------------------------- #
    @abstractmethod
    def record_scheduler_event(self, event: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get_scheduler_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Most-recent-first scheduler events (bounded by ``limit``)."""

    # ---- summary ---------------------------------------------------------- #
    def counts(self) -> dict[str, int]:
        """Entity counts (default derives from the list/read methods)."""
        return {
            "runs": len(self.list_runs()),
            "observations": len(self.list_observations()),
            "evidence_keys": len(self.list_evidence_latest()),
            "packs": len(self.list_packs()),
            "scheduler_events": len(self.get_scheduler_history(limit=10_000)),
        }


# --------------------------------------------------------------------------- #
# In-memory reference implementation
# --------------------------------------------------------------------------- #
class InMemoryAuditPersistence(AuditPersistence):
    """Thread-safe, dependency-free reference implementation.

    Mirrors the semantics of the engine stores (newest-first run listing,
    ascending evidence versions, bounded scheduler history). Suitable as the
    production default until a SQL backend is wired, and used by tests.
    """

    def __init__(self, *, max_scheduler_events: int = 5000) -> None:
        self._lock = threading.RLock()
        self._max_scheduler_events = max_scheduler_events
        self._runs: dict[str, EvidenceRun] = {}
        self._validation: dict[str, list[ValidationResult]] = {}
        self._observations: dict[str, Observation] = {}
        self._evidence: dict[str, list[EvidenceArtifact]] = {}
        self._packs: dict[str, dict[str, Any]] = {}
        self._scheduler: list[dict[str, Any]] = []

    def initialize(self) -> None:  # nothing to create for in-memory
        return None

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()
            self._validation.clear()
            self._observations.clear()
            self._evidence.clear()
            self._packs.clear()
            self._scheduler.clear()

    # ---- runs + results --------------------------------------------------- #
    def save_run(self, run: EvidenceRun) -> EvidenceRun:
        with self._lock:
            # Deep-copy via serialization so external mutation can't corrupt state.
            self._runs[run.run_id] = run_from_dict(run_to_dict(run))
        return run

    def get_run(self, run_id: str) -> Optional[EvidenceRun]:
        with self._lock:
            stored = self._runs.get(run_id)
            return run_from_dict(run_to_dict(stored)) if stored else None

    def list_runs(self) -> list[EvidenceRun]:
        with self._lock:
            runs = [run_from_dict(run_to_dict(r)) for r in self._runs.values()]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    def get_run_results(self, run_id: str) -> list[EvidenceRecord]:
        with self._lock:
            stored = self._runs.get(run_id)
            if not stored:
                return []
            return [record_from_dict(record_to_dict(rec)) for rec in stored.records]

    # ---- validation ------------------------------------------------------- #
    def save_validation_results(self, run_id: str, results: list[ValidationResult]) -> None:
        with self._lock:
            self._validation[run_id] = [
                validation_from_dict(validation_to_dict(r)) for r in results
            ]

    def get_validation_results(self, run_id: str) -> list[ValidationResult]:
        with self._lock:
            return list(self._validation.get(run_id, []))

    # ---- observations ----------------------------------------------------- #
    def save_observation(self, observation: Observation) -> Observation:
        with self._lock:
            self._observations[observation.observation_id] = observation_from_dict(
                observation_to_dict(observation)
            )
        return observation

    def get_observation(self, observation_id: str) -> Optional[Observation]:
        with self._lock:
            stored = self._observations.get(observation_id)
            return observation_from_dict(observation_to_dict(stored)) if stored else None

    def list_observations(self) -> list[Observation]:
        with self._lock:
            return [observation_from_dict(observation_to_dict(o))
                    for o in self._observations.values()]

    # ---- evidence versions ------------------------------------------------ #
    def append_evidence_version(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        with self._lock:
            versions = self._evidence.setdefault(artifact.evidence_key, [])
            versions.append(artifact_from_dict(artifact_to_dict(artifact)))
            versions.sort(key=lambda a: a.version)
        return artifact

    def get_evidence_versions(self, evidence_key: str) -> list[EvidenceArtifact]:
        with self._lock:
            return list(self._evidence.get(evidence_key, []))

    def list_evidence_latest(self) -> list[EvidenceArtifact]:
        with self._lock:
            return [versions[-1] for versions in self._evidence.values() if versions]

    def find_evidence_by_source_hash(
        self, source_item_id: str, content_hash: str,
    ) -> Optional[EvidenceArtifact]:
        if not source_item_id or not content_hash:
            return None
        with self._lock:
            for versions in self._evidence.values():
                for art in versions:
                    if art.source_item_id == source_item_id and art.content_hash == content_hash:
                        return art
        return None

    def list_all_evidence_versions(self) -> list[EvidenceArtifact]:
        with self._lock:
            items = [a for versions in self._evidence.values() for a in versions]
        return sorted(items, key=lambda a: (a.evidence_key, a.version))

    # ---- packs ------------------------------------------------------------ #
    def save_pack(self, pack_id: str, manifest: dict[str, Any]) -> None:
        with self._lock:
            self._packs[pack_id] = dict(manifest)

    def get_pack(self, pack_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            manifest = self._packs.get(pack_id)
            return dict(manifest) if manifest is not None else None

    def list_packs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(m) for m in self._packs.values()]

    # ---- scheduler -------------------------------------------------------- #
    def record_scheduler_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._scheduler.append(dict(event))
            if len(self._scheduler) > self._max_scheduler_events:
                del self._scheduler[: len(self._scheduler) - self._max_scheduler_events]

    def get_scheduler_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            events = list(reversed(self._scheduler))  # newest first
        return events[: max(0, limit)]


# --------------------------------------------------------------------------- #
# Pluggable provider
# --------------------------------------------------------------------------- #
_DEFAULT: Optional[AuditPersistence] = None
_PROVIDER_LOCK = threading.RLock()


def get_persistence() -> AuditPersistence:
    """Return the process-wide persistence backend (in-memory by default).

    The default is created lazily and initialized once. Operators swap the backend
    via :func:`set_persistence` (e.g. to the SQL backend) at startup.
    """
    global _DEFAULT
    with _PROVIDER_LOCK:
        if _DEFAULT is None:
            _DEFAULT = InMemoryAuditPersistence()
            _DEFAULT.initialize()
        return _DEFAULT


def set_persistence(backend: Optional[AuditPersistence]) -> None:
    """Install a persistence backend (call at startup). ``None`` resets to default."""
    global _DEFAULT
    with _PROVIDER_LOCK:
        if backend is not None:
            backend.initialize()
        _DEFAULT = backend


def reset_persistence() -> None:
    """Clear the current backend's data and drop the cached default (tests)."""
    global _DEFAULT
    with _PROVIDER_LOCK:
        if _DEFAULT is not None:
            try:
                _DEFAULT.clear()
            except Exception:  # noqa: BLE001 - reset must never raise
                pass
        _DEFAULT = None
