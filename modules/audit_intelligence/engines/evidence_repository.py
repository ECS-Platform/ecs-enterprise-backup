"""Evidence Repository (Milestone 3).

Durable-shaped metadata store for collected evidence, with:
  * versioning (each re-collection of the same evidence key bumps the version),
  * content hash (SHA-256) + short checksum,
  * rich metadata + tags,
  * an evidence timeline (chronological events per key), and
  * search/filter.

Stores METADATA ONLY — never credentials/secrets. The actual evidence artifact
(file/output) is captured elsewhere (the predefined-query engine's evidence
upload); here we keep a hash/checksum + descriptive metadata for audit trails and
pack assembly. Backing store is in-memory (swap for a DB later without changing the
public API).
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from modules.audit_intelligence.models import EvidenceArtifact

# evidence_key -> list of versions (ascending). timeline is a flat event log.
_STORE: dict[str, list[EvidenceArtifact]] = {}
_TIMELINE: list[dict[str, Any]] = []

#: Safety caps to bound in-memory growth (durable persistence lifts these).
MAX_VERSIONS_PER_KEY = 50   # keep the most recent N versions of each evidence key
MAX_TIMELINE_EVENTS = 5000  # keep the most recent N timeline events


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _invalidate_dashboard_cache() -> None:
    """Best-effort: drop cached dashboard payloads after a repository change.

    Kept dependency-light and failure-proof (a caching helper must never break a
    write) via a lazy, guarded import. Caching is a pure optimisation — if this is
    ever a no-op, correctness is preserved by the dashboard cache's short TTL.
    """
    try:
        from modules.audit_intelligence.services import dashboard_service

        dashboard_service.invalidate_dashboard_cache()
    except Exception:  # noqa: BLE001 - cache invalidation must never raise
        pass


def reset_repository() -> None:
    global _last_canonical_failure_at, _last_canonical_success_at
    _STORE.clear()
    _TIMELINE.clear()
    _HYDRATED_CANONICAL_UIDS.clear()
    _last_canonical_failure_at = 0.0
    _last_canonical_success_at = 0.0
    _invalidate_dashboard_cache()


def _evidence_persistence_enabled() -> bool:
    """True when the SQL audit persistence backend is installed (startup flag)."""
    return str(os.environ.get("AUDIT_WORKFLOW_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _hash_content(content: str) -> tuple[str, str, int]:
    raw = (content or "").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return digest, digest[:8], len(raw)


def _metadata_tuple(value: Any) -> tuple[tuple[str, str], ...]:
    if not value:
        return ()
    if isinstance(value, dict):
        return tuple(sorted((str(k), str(v)) for k, v in value.items()))
    return ()


def _persist_artifact(artifact: EvidenceArtifact) -> None:
    """Best-effort durable write; never raises."""
    if not _evidence_persistence_enabled():
        return
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        get_persistence().append_evidence_version(artifact)
    except Exception:  # noqa: BLE001 - persistence must never break a store
        pass


def _index_artifact(artifact: EvidenceArtifact, *, normalized_text: str = "") -> None:
    """Best-effort vector indexing after persistence; never raises."""
    try:
        from ecs_platform.evidence_indexing import index_after_persist

        index_after_persist(artifact, normalized_text=normalized_text)
    except Exception:  # noqa: BLE001 - indexing must never break a store
        pass


def _find_in_memory_duplicate(source_item_id: str, content_hash: str) -> EvidenceArtifact | None:
    if not source_item_id or not content_hash:
        return None
    for versions in _STORE.values():
        for art in versions:
            if art.source_item_id == source_item_id and art.content_hash == content_hash:
                return art
    return None


def _next_version(key: str) -> int:
    versions = list(_STORE.get(key, []))
    if _evidence_persistence_enabled():
        try:
            from modules.audit_intelligence.services.persistence import get_persistence

            seen = {(a.evidence_key, a.version) for a in versions}
            for art in get_persistence().get_evidence_versions(key):
                if (art.evidence_key, art.version) not in seen:
                    versions.append(art)
        except Exception:  # noqa: BLE001
            pass
    return (max(v.version for v in versions) + 1) if versions else 1


def _find_persisted_duplicate(source_item_id: str, content_hash: str) -> EvidenceArtifact | None:
    if not _evidence_persistence_enabled():
        return None
    if not source_item_id or not content_hash:
        return None
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        return get_persistence().find_evidence_by_source_hash(source_item_id, content_hash)
    except Exception:  # noqa: BLE001
        return None


def _merge_into_store(artifact: EvidenceArtifact) -> bool:
    """Insert into the in-memory facade when (evidence_key, version) is absent."""
    versions = _STORE.setdefault(artifact.evidence_key, [])
    if any(v.version == artifact.version for v in versions):
        return False
    versions.append(artifact)
    versions.sort(key=lambda a: a.version)
    if len(versions) > MAX_VERSIONS_PER_KEY:
        del versions[: len(versions) - MAX_VERSIONS_PER_KEY]
    return True


def hydrate_from_persistence() -> int:
    """Reload persisted evidence versions into the in-memory facade.

    Existing in-memory entries are never overwritten (memory wins for the current
    process). Returns the number of versions hydrated. No-op when SQL persistence is
    disabled. Never raises.
    """
    if not _evidence_persistence_enabled():
        return 0
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        artifacts = get_persistence().list_all_evidence_versions()
    except Exception:  # noqa: BLE001 - hydration must never block startup
        return 0
    hydrated = 0
    for artifact in artifacts:
        if _merge_into_store(artifact):
            hydrated += 1
    if hydrated:
        _invalidate_dashboard_cache()
    return hydrated


def make_evidence_key(asset_id: str, control_id: str) -> str:
    """Stable identity for an evidence stream across versions."""
    asset = (asset_id or "global").strip() or "global"
    return f"{asset}::{control_id}".strip(":")


# --------------------------------------------------------------------------- #
# Canonical PostgreSQL -> in-memory hydration bridge
# --------------------------------------------------------------------------- #
#: evidence_uid values already merged in this process (covers both hydration
#: and same-process ``_mirror_to_audit_repository`` writes) so repeated
#: hydration calls never duplicate or re-version canonical rows.
_HYDRATED_CANONICAL_UIDS: set[str] = set()

#: Process-local refresh guard so ``search()``/``stats()`` (called on every
#: request) don't open a PostgreSQL connection every time. A successful
#: hydration is considered fresh for ``_CANONICAL_REFRESH_INTERVAL_S``; a
#: failed/unreachable attempt is throttled for the shorter
#: ``_CANONICAL_FAILURE_THROTTLE_S`` so a dead database isn't retried on every
#: request either. ``force=True`` (startup) bypasses both.
_CANONICAL_REFRESH_INTERVAL_S = 5.0
_CANONICAL_FAILURE_THROTTLE_S = 5.0
_last_canonical_success_at: float = 0.0
_last_canonical_failure_at: float = 0.0


def _canonical_metadata_dict(meta: Any) -> dict[str, Any]:
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        try:
            import json

            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _canonical_row_to_kwargs(row: dict[str, Any]) -> dict[str, Any]:
    """Map one ``ecs_platform.repository.EvidenceRepository`` row to
    :func:`store_evidence` kwargs, per the field mapping in this bridge's spec."""
    meta = _canonical_metadata_dict(row.get("metadata"))
    application = row.get("application") or meta.get("application") or ""
    control = meta.get("control") or row.get("title") or ""
    title = row.get("title") or ""

    technology = ""
    try:
        from modules.audit_intelligence.engines import technology_control_mapping as mapping

        ref = mapping.get_control(control) if control else None
        if ref:
            technology = ref.technology or ""
    except Exception:  # noqa: BLE001 - mapping optional
        pass

    frameworks: tuple[str, ...] = ()
    fw = meta.get("framework")
    if fw:
        frameworks = (fw,) if isinstance(fw, str) else tuple(fw)

    source_system = row.get("source_system") or ""
    evidence_uid = row.get("evidence_uid") or ""
    filename = meta.get("original_filename") or title

    return dict(
        evidence_key=make_evidence_key(application, control or title),
        control_id=control or title,
        content=str(row.get("content") or ""),
        technology=technology,
        asset_id=application,
        frameworks=frameworks,
        source="connector" if source_system else "",
        filename=filename,
        evidence_id=evidence_uid,
        environment=meta.get("environment", ""),
        source_connector=meta.get("source_connector") or source_system,
        source_item_id=row.get("source_object_id") or "",
        source_url=meta.get("web_url") or row.get("url") or "",
        mime_type=meta.get("mime_type", ""),
        metadata=meta,
        custody_mode=meta.get("custody_mode") or "REFERENCE_ONLY",
        source_modified_at=meta.get("modified_datetime", ""),
        object_uri=meta.get("object_uri", ""),
        content_hash_override=meta.get("sha256") or row.get("content_hash") or "",
    )


def _find_by_evidence_id(evidence_id: str) -> EvidenceArtifact | None:
    if not evidence_id:
        return None
    for versions in _STORE.values():
        for art in versions:
            if art.evidence_id == evidence_id:
                return art
    return None


def hydrate_from_canonical_repository(*, limit: int = 1000, force: bool = False) -> int:
    """Best-effort bridge: merge canonical PostgreSQL evidence into ``_STORE``.

    Reads through :class:`ecs_platform.repository.EvidenceRepository` (the DAL —
    no direct psycopg2 calls here) and stores each canonical row as an
    :class:`EvidenceArtifact` version, using the existing ``store_evidence``
    versioning/dedup semantics. Idempotent: a canonical ``evidence_uid`` already
    hydrated (or already mirrored in-process) is skipped on subsequent calls, so
    repeated hydration never creates new versions or duplicates counts. Existing
    ``_STORE`` entries (baseline/demo) are never cleared or overwritten. Never
    raises — a missing/unreachable PostgreSQL is a silent no-op.

    Process-local refresh guard: unless ``force=True`` (used at startup), this
    is a no-op within ``_CANONICAL_REFRESH_INTERVAL_S`` of the last successful
    hydration, or within ``_CANONICAL_FAILURE_THROTTLE_S`` of the last failed
    attempt — so ``search()``/``stats()`` calling this on every request never
    opens a PostgreSQL connection per request.
    """
    global _last_canonical_failure_at, _last_canonical_success_at
    import time as _time

    # Throttle BEFORE any repository import/construction/DAL call.
    if not force:
        now = _time.monotonic()
        if _last_canonical_success_at > 0.0 and (now - _last_canonical_success_at) < _CANONICAL_REFRESH_INTERVAL_S:
            return 0
        if _last_canonical_failure_at > 0.0 and (now - _last_canonical_failure_at) < _CANONICAL_FAILURE_THROTTLE_S:
            return 0

    try:
        from ecs_platform.repository import EvidenceRepository
    except Exception:  # noqa: BLE001 - repository module unavailable
        _last_canonical_failure_at = _time.monotonic()
        return 0

    repo = None
    try:
        repo = EvidenceRepository()
        rows = repo.search_evidence(limit=limit)
        # Stamp immediately so re-entrant search()/stats() during merge are throttled.
        _last_canonical_success_at = _time.monotonic()
    except Exception:  # noqa: BLE001 - PostgreSQL unreachable/misconfigured
        _last_canonical_failure_at = _time.monotonic()
        return 0
    finally:
        if repo is not None:
            try:
                repo.close()
            except Exception:  # noqa: BLE001
                pass

    hydrated = 0
    for row in rows:
        uid = row.get("evidence_uid") or ""
        if not uid or uid in _HYDRATED_CANONICAL_UIDS:
            continue
        if _find_by_evidence_id(uid) is not None:
            # Already present via _mirror_to_audit_repository() in this process
            # (same evidence_id/evidence_uid) — mark hydrated, don't re-store.
            _HYDRATED_CANONICAL_UIDS.add(uid)
            continue
        try:
            store_evidence(**_canonical_row_to_kwargs(row))
        except Exception:  # noqa: BLE001 - one bad row must never break hydration
            continue
        _HYDRATED_CANONICAL_UIDS.add(uid)
        hydrated += 1
    if hydrated:
        _invalidate_dashboard_cache()
    # Refresh stamp when the attempt completes so a slow merge cannot expire the
    # success window before the next force=False caller.
    _last_canonical_success_at = _time.monotonic()
    return hydrated


# --------------------------------------------------------------------------- #
# Store / version
# --------------------------------------------------------------------------- #
def store_evidence(
    *,
    control_id: str,
    content: str = "",
    technology: str = "",
    asset_id: str = "",
    frameworks: tuple[str, ...] = (),
    run_id: str = "",
    verdict: str = "",
    control_status: str = "",
    evidence_quality: float = 0.0,
    source: str = "",
    filename: str = "",
    tags: tuple[str, ...] = (),
    evidence_key: str = "",
    evidence_id: str = "",
    environment: str = "",
    source_connector: str = "",
    source_item_id: str = "",
    source_url: str = "",
    mime_type: str = "",
    metadata: dict[str, Any] | None = None,
    custody_mode: str = "REFERENCE_ONLY",
    source_modified_at: str = "",
    object_uri: str = "",
    content_hash_override: str = "",
    size_bytes_override: int = 0,
) -> EvidenceArtifact:
    """Store a new evidence version. Returns the created :class:`EvidenceArtifact`.

    Versioning is automatic: the first store for a key is v1; each subsequent store
    increments. The content hash lets callers detect unchanged evidence. When
    ``source_item_id`` is supplied, writes are idempotent for the same content hash.
    """
    key = evidence_key or make_evidence_key(asset_id, control_id)
    if content_hash_override:
        content_hash = content_hash_override
        checksum = content_hash[:8]
        size = int(size_bytes_override or len((content or "").encode("utf-8")))
    else:
        content_hash, checksum, size = _hash_content(content)

    duplicate = (
        _find_in_memory_duplicate(source_item_id, content_hash)
        or _find_persisted_duplicate(source_item_id, content_hash)
    )
    if duplicate is not None:
        # Allow an upgrade path from REFERENCE_ONLY -> SNAPSHOT for the same
        # source object/hash when immutable bytes are now available. Without this,
        # dedupe would keep returning the earlier reference-only version forever.
        wants_snapshot = (custody_mode or "").strip().upper() == "SNAPSHOT" and bool(object_uri)
        duplicate_is_reference = (duplicate.custody_mode or "").strip().upper() != "SNAPSHOT" or not duplicate.object_uri
        if wants_snapshot and duplicate_is_reference:
            duplicate = None
    if duplicate is not None:
        _merge_into_store(duplicate)
        return duplicate

    version = _next_version(key)

    artifact = EvidenceArtifact(
        evidence_key=key,
        version=version,
        control_id=control_id,
        technology=technology,
        asset_id=asset_id,
        frameworks=tuple(frameworks),
        run_id=run_id,
        verdict=verdict,
        control_status=control_status,
        evidence_quality=evidence_quality,
        content_hash=content_hash,
        checksum=checksum,
        size_bytes=size,
        source=source,
        filename=filename,
        collected_at=_now(),
        tags=tuple(tags),
        evidence_id=evidence_id,
        environment=environment,
        source_connector=source_connector,
        source_item_id=source_item_id,
        source_url=source_url,
        mime_type=mime_type,
        metadata=_metadata_tuple(metadata),
        custody_mode=custody_mode or "REFERENCE_ONLY",
        source_modified_at=source_modified_at,
        object_uri=object_uri,
    )
    versions = _STORE.setdefault(key, [])
    versions.append(artifact)
    if len(versions) > MAX_VERSIONS_PER_KEY:  # keep most recent N (version numbers still monotonic)
        del versions[: len(versions) - MAX_VERSIONS_PER_KEY]
    _TIMELINE.append(
        {
            "at": artifact.collected_at,
            "evidence_key": key,
            "version": version,
            "control_id": control_id,
            "asset_id": asset_id,
            "verdict": verdict,
            "content_hash": content_hash,
            "event": "stored",
        }
    )
    if len(_TIMELINE) > MAX_TIMELINE_EVENTS:
        del _TIMELINE[: len(_TIMELINE) - MAX_TIMELINE_EVENTS]
    _persist_artifact(artifact)
    _index_artifact(artifact, normalized_text=content or "")
    _invalidate_dashboard_cache()
    return artifact


def store_from_run(run: Any, *, results_by_control: dict[str, Any] | None = None) -> list[EvidenceArtifact]:
    """Convenience: persist evidence metadata for every completed record in a run.

    ``run`` is an ``EvidenceRun``; ``results_by_control`` optionally maps control_id
    -> ValidationResult (dict or object) to enrich verdict/status/quality.
    """
    results_by_control = results_by_control or {}
    out: list[EvidenceArtifact] = []
    for record in getattr(run, "records", []):
        if not record.ok:
            continue
        vr = results_by_control.get(record.control_id)
        verdict = _attr(vr, "verdict", "")
        control_status = _attr(vr, "control_status", "")
        quality = _attr(vr, "evidence_quality", 0.0) or 0.0
        out.append(
            store_evidence(
                control_id=record.control_id,
                content=record.output_excerpt,
                technology=record.technology,
                asset_id=record.asset_id,
                frameworks=tuple(record.frameworks),
                run_id=run.run_id,
                verdict=verdict,
                control_status=control_status,
                evidence_quality=quality,
                source="evidence_run",
                filename=record.evidence_filename,
            )
        )
    return out


def _attr(obj: Any, name: str, default: Any) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# --------------------------------------------------------------------------- #
# Read / version access
# --------------------------------------------------------------------------- #
def get_versions(evidence_key: str) -> list[EvidenceArtifact]:
    return list(_STORE.get(evidence_key, []))


def get_latest(evidence_key: str) -> EvidenceArtifact | None:
    versions = _STORE.get(evidence_key)
    return versions[-1] if versions else None


def all_latest() -> list[EvidenceArtifact]:
    """Latest version of every evidence key."""
    return [versions[-1] for versions in _STORE.values() if versions]


def all_artifacts() -> list[EvidenceArtifact]:
    """Every version of every evidence key (flat)."""
    return [a for versions in _STORE.values() for a in versions]


def timeline(evidence_key: str = "") -> list[dict[str, Any]]:
    """Chronological event log, optionally filtered to one evidence key."""
    events = [e for e in _TIMELINE if not evidence_key or e["evidence_key"] == evidence_key]
    return sorted(events, key=lambda e: e["at"])


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
def _artifact_matches_query(artifact: EvidenceArtifact, q: str) -> bool:
    """True when free-text ``q`` matches any of the repository's searchable fields.

    Covers the Evidence Repository UI fields: evidence id/uid, title/filename,
    application (asset_id), source/connector, framework, control, and object_uri.
    Also scans tags and metadata values (e.g. original_filename from connectors).
    """
    if not q:
        return True
    haystacks = (
        artifact.control_id,
        artifact.technology,
        artifact.asset_id,
        artifact.evidence_key,
        artifact.filename,
        artifact.evidence_id,
        artifact.source_connector,
        artifact.source,
        artifact.object_uri,
        artifact.source_item_id,
        artifact.source_url,
        artifact.custody_mode,
        " ".join(artifact.frameworks),
        " ".join(artifact.tags),
        " ".join(v for _, v in (artifact.metadata or ())),
        " ".join(k for k, _ in (artifact.metadata or ())),
    )
    return any(q in (h or "").lower() for h in haystacks)


def search(
    *,
    query: str = "",
    technology: str = "",
    framework: str = "",
    asset_id: str = "",
    verdict: str = "",
    tag: str = "",
    latest_only: bool = True,
) -> list[EvidenceArtifact]:
    """Filter stored evidence (latest version by default)."""
    # Keep the in-memory facade aligned with durable audit persistence so the UI
    # lists connector/scheduler/upload evidence written in other workers or after
    # restart. Memory still wins for keys already present (existing merge rules).
    hydrate_from_persistence()
    hydrate_from_canonical_repository()
    items = all_latest() if latest_only else all_artifacts()
    q = query.strip().lower()
    if technology:
        items = [a for a in items if a.technology == technology]
    if framework:
        items = [a for a in items if framework in a.frameworks]
    if asset_id:
        items = [a for a in items if a.asset_id == asset_id]
    if verdict:
        items = [a for a in items if a.verdict == verdict]
    if tag:
        items = [a for a in items if tag in a.tags]
    if q:
        items = [a for a in items if _artifact_matches_query(a, q)]
    return items


def stats() -> dict[str, Any]:
    hydrate_from_persistence()
    hydrate_from_canonical_repository()
    latest = all_latest()
    # Unique non-empty technology values only — blank is not a technology, and the
    # synthetic "Unknown" label used in by_technology charts must not inflate the KPI.
    real_technologies = {
        (a.technology or "").strip()
        for a in latest
        if (a.technology or "").strip()
    }
    return {
        "evidence_keys": len(_STORE),
        "total_versions": sum(len(v) for v in _STORE.values()),
        "latest_count": len(latest),
        "technologies": len(real_technologies),
        "by_technology": _count(latest, lambda a: a.technology or "Unknown"),
        "by_verdict": _count(latest, lambda a: a.verdict or "Unassessed"),
        "timeline_events": len(_TIMELINE),
    }


def _count(items: list[EvidenceArtifact], key) -> dict[str, int]:
    out: dict[str, int] = {}
    for a in items:
        out[key(a)] = out.get(key(a), 0) + 1
    return dict(sorted(out.items()))
