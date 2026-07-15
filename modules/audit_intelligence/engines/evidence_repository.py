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
    _STORE.clear()
    _TIMELINE.clear()
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
        items = [
            a for a in items
            if q in a.control_id.lower()
            or q in a.technology.lower()
            or q in a.asset_id.lower()
            or q in a.evidence_key.lower()
        ]
    return items


def stats() -> dict[str, Any]:
    latest = all_latest()
    return {
        "evidence_keys": len(_STORE),
        "total_versions": sum(len(v) for v in _STORE.values()),
        "latest_count": len(latest),
        "by_technology": _count(latest, lambda a: a.technology or "Unknown"),
        "by_verdict": _count(latest, lambda a: a.verdict or "Unassessed"),
        "timeline_events": len(_TIMELINE),
    }


def _count(items: list[EvidenceArtifact], key) -> dict[str, int]:
    out: dict[str, int] = {}
    for a in items:
        out[key(a)] = out.get(key(a), 0) + 1
    return dict(sorted(out.items()))
