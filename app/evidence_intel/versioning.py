"""Evidence versioning foundation (Phase 1 of 5.4).

Builds an immutable EvidenceVersion chain from a sequence of uploads/snapshots,
WITHOUT changing any existing upload flow or schema. The version model is computed
in memory from data ECS already captures (uploaded_at, uploaded_by, hash,
status). Historical versions are immutable; the latest is easily retrievable.

  * READ-ONLY, NO-LLM, NO schema change, NO write to ECS state.
  * FLAG-GATED by EVIDENCE_VERSIONING_ENABLED (default off). When disabled,
    build_version_history() returns an empty, disabled history.
  * BACKWARD COMPATIBLE: callers that never enable the flag are unaffected.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from app.evidence_intel._common import flag_enabled
from app.evidence_intel.models import (
    EvidenceStatus,
    EvidenceVersion,
    EvidenceVersionHistory,
)


def versioning_enabled() -> bool:
    return flag_enabled("EVIDENCE_VERSIONING_ENABLED", "versioning_enabled")


def compute_hash(content: Any) -> str:
    """Stable SHA-256 hex of a snapshot's content/identity. Empty -> ''."""
    if content is None:
        return ""
    if isinstance(content, (dict, list, tuple)):
        text = repr(content)
    else:
        text = str(content)
    if text == "":
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _snapshot_hash(snap: Mapping[str, Any]) -> str:
    # Prefer an explicit hash; else derive from filename + content + key metadata.
    for key in ("hash", "sha256", "content_hash"):
        h = snap.get(key)
        if isinstance(h, str) and h.strip():
            return h.strip()
    basis = "|".join(str(snap.get(k, "")) for k in
                     ("upload_filename", "filename", "content", "title"))
    return compute_hash(basis) if basis.strip("|") else ""


def build_version_history(evidence_id: str, snapshots: Sequence[Mapping[str, Any]], *,
                          force: bool = False) -> EvidenceVersionHistory:
    """Build an immutable version chain from ordered upload snapshots.

    Each snapshot is a mapping that may carry: uploaded_at/created_at,
    uploaded_by/created_by, hash/sha256/content_hash, status/evidence_status,
    change_reason. Consecutive snapshots with an identical hash are collapsed
    (no new version is created when nothing changed). Never raises.
    """
    if not force and not versioning_enabled():
        return EvidenceVersionHistory(evidence_id=evidence_id, versions=[])

    try:
        versions: list[EvidenceVersion] = []
        last_hash = None
        for snap in snapshots or []:
            if not isinstance(snap, Mapping):
                continue
            h = _snapshot_hash(snap)
            if versions and h and h == last_hash:
                # Identical content -> not a new version (idempotent re-upload).
                continue
            num = len(versions) + 1
            status = (snap.get("evidence_status") or snap.get("status")
                      or EvidenceStatus.COLLECTED.value)
            version = EvidenceVersion(
                evidence_id=evidence_id,
                version_number=num,
                created_at=str(snap.get("uploaded_at") or snap.get("created_at") or ""),
                created_by=str(snap.get("uploaded_by") or snap.get("created_by") or ""),
                hash=h,
                previous_version=(num - 1) if num > 1 else None,
                change_reason=str(snap.get("change_reason") or snap.get("upload_comments") or ""),
                evidence_status=str(status),
                metadata=dict(snap.get("metadata") or {}),
            )
            versions.append(version)
            last_hash = h

        # Link supersession: every prior version is superseded by the next.
        for i in range(len(versions) - 1):
            versions[i].superseded_by = versions[i + 1].version_number
            if versions[i].evidence_status not in (EvidenceStatus.REJECTED.value,):
                versions[i].evidence_status = EvidenceStatus.SUPERSEDED.value

        return EvidenceVersionHistory(evidence_id=evidence_id, versions=versions)
    except Exception:  # noqa: BLE001 - fail safe
        return EvidenceVersionHistory(evidence_id=evidence_id, versions=[])


def latest_version(history: EvidenceVersionHistory) -> EvidenceVersion | None:
    """Return the latest (current) version, or None when there is no history."""
    return history.latest


def get_version(history: EvidenceVersionHistory, version_number: int) -> EvidenceVersion | None:
    for v in history.versions:
        if v.version_number == version_number:
            return v
    return None


def next_version(history: EvidenceVersionHistory, snapshot: Mapping[str, Any], *,
                 force: bool = False) -> EvidenceVersion | None:
    """Compute (without persisting) the next version that an upload would create.

    Returns None if the snapshot's hash equals the latest version's hash (no
    change -> no new version), or when versioning is disabled.
    """
    if not force and not versioning_enabled():
        return None
    try:
        latest = history.latest
        h = _snapshot_hash(snapshot)
        if latest is not None and h and h == latest.hash:
            return None
        num = (latest.version_number + 1) if latest else 1
        return EvidenceVersion(
            evidence_id=history.evidence_id, version_number=num,
            created_at=str(snapshot.get("uploaded_at") or snapshot.get("created_at") or ""),
            created_by=str(snapshot.get("uploaded_by") or snapshot.get("created_by") or ""),
            hash=h, previous_version=(num - 1) if num > 1 else None,
            change_reason=str(snapshot.get("change_reason") or ""),
            evidence_status=str(snapshot.get("evidence_status")
                                or snapshot.get("status") or EvidenceStatus.COLLECTED.value),
            metadata=dict(snapshot.get("metadata") or {}))
    except Exception:  # noqa: BLE001
        return None
