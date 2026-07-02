"""Evidence Difference Engine (Capability B, Phase 5.5).

Deterministic, non-LLM comparison of evidence version N vs N-1. This is a thin
adapter that COMPOSES Phase 5.4:
  * app.evidence_intel.versioning  — to build/select the version chain, and
  * app.evidence_intel.change      — to classify the field-level differences
    (metadata, control mapping, framework mapping, owner, status, approval,
    application).

It REUSES the Phase 5.4 flag EVIDENCE_CHANGE_DETECTION_ENABLED (no new flag).
Read-only, fail-safe.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.evidence_analytics.models import VersionDifference


def diff_enabled() -> bool:
    """Reuses the Phase 5.4 change-detection flag."""
    try:
        from app.evidence_intel.change import change_detection_enabled
        return change_detection_enabled()
    except Exception:  # noqa: BLE001
        from app.evidence_analytics._common import flag_enabled
        return flag_enabled("EVIDENCE_CHANGE_DETECTION_ENABLED", "change_detection_enabled")


def diff_snapshots(old: Mapping[str, Any], new: Mapping[str, Any], *,
                   evidence_id: str = "", from_version: int | None = None,
                   to_version: int | None = None, force: bool = False) -> VersionDifference:
    """Diff two evidence snapshots via the 5.4 change engine. Never raises."""
    if not evidence_id and isinstance(new, Mapping):
        evidence_id = str(new.get("evidence_id") or new.get("id") or "")
    if not force and not diff_enabled():
        return VersionDifference(
            evidence_id=evidence_id, enabled=False,
            note="difference disabled (EVIDENCE_CHANGE_DETECTION_ENABLED=false)")
    try:
        from app.evidence_intel.change import assess_change

        assessment = assess_change(old, new, evidence_id=evidence_id, force=True)
        return VersionDifference(
            evidence_id=evidence_id, enabled=True,
            from_version=from_version, to_version=to_version,
            change_class=assessment.change_class,
            changed_fields=[c.field_name for c in assessment.changes],
            summary=assessment.summary,
            changes=[c.to_dict() for c in assessment.changes])
    except Exception as exc:  # noqa: BLE001 - fail safe
        return VersionDifference(evidence_id=evidence_id, enabled=False,
                                 note=f"difference error (ignored): {type(exc).__name__}")


def diff_latest_versions(evidence_id: str, snapshots: Sequence[Mapping[str, Any]], *,
                         force: bool = False) -> VersionDifference:
    """Build the version chain and diff the latest version (N) vs the prior (N-1).

    ``snapshots`` are ordered upload snapshots (same input as
    evidence_intel.versioning.build_version_history). Never raises.
    """
    if not force and not diff_enabled():
        return VersionDifference(
            evidence_id=evidence_id, enabled=False,
            note="difference disabled (EVIDENCE_CHANGE_DETECTION_ENABLED=false)")
    try:
        from app.evidence_intel.versioning import build_version_history

        history = build_version_history(evidence_id, snapshots, force=True)
        versions = history.versions
        if len(versions) < 2:
            return VersionDifference(
                evidence_id=evidence_id, enabled=True,
                from_version=versions[0].version_number if versions else None,
                to_version=versions[0].version_number if versions else None,
                change_class="None", summary="no prior version to compare")
        # Re-associate each version with its originating snapshot for field diff.
        # Snapshots collapse on identical hash, so map by order of distinct hashes.
        distinct: list[Mapping[str, Any]] = []
        last_hash = None
        for snap in snapshots:
            if not isinstance(snap, Mapping):
                continue
            from app.evidence_intel.versioning import _snapshot_hash  # type: ignore
            h = _snapshot_hash(snap)
            if distinct and h and h == last_hash:
                continue
            distinct.append(snap)
            last_hash = h
        if len(distinct) < 2:
            return VersionDifference(evidence_id=evidence_id, enabled=True,
                                     change_class="None", summary="no distinct prior version")
        prev_snap, last_snap = distinct[-2], distinct[-1]
        return diff_snapshots(prev_snap, last_snap, evidence_id=evidence_id,
                              from_version=versions[-2].version_number,
                              to_version=versions[-1].version_number, force=True)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return VersionDifference(evidence_id=evidence_id, enabled=False,
                                 note=f"difference error (ignored): {type(exc).__name__}")
