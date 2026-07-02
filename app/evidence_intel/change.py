"""Evidence change detection (Phase 6 of 5.4).

Deterministically classifies the difference between two snapshots of an evidence
item as Minor / Moderate / Major, based on which fields changed: metadata, file
hash, approval status, owner, and control mapping.

  * NO file-content AI analysis. Pure field-level diffing.
  * READ-ONLY, NO-LLM. FLAG-GATED by EVIDENCE_CHANGE_DETECTION_ENABLED (default off).
"""

from __future__ import annotations

from typing import Any, Mapping

from app.evidence_intel._common import flag_enabled, load_policy, merge_block
from app.evidence_intel.models import ChangeClass, EvidenceChangeAssessment, FieldChange

_DEFAULTS = {
    "field_severity": {
        "content_hash": "major", "approval_status": "major",
        "control_mapping": "moderate", "framework_mapping": "moderate", "owner": "moderate",
        "metadata": "minor", "title": "minor", "url": "minor",
    },
    "moderate_to_major_count": 3,
}

# Canonical field -> the snapshot keys that represent it (first present wins).
_FIELD_KEYS = {
    "content_hash": ["content_hash", "hash", "sha256"],
    "approval_status": ["review_status", "status", "evidence_status", "approval_status"],
    "control_mapping": ["control_mapping", "controls", "control", "control_id"],
    "framework_mapping": ["framework_mapping", "frameworks", "framework"],
    "owner": ["owner", "remediation_owner"],
    "metadata": ["metadata"],
    "title": ["title", "upload_filename", "filename"],
    "url": ["url"],
}

_SEVERITY_RANK = {ChangeClass.NONE: 0, ChangeClass.MINOR: 1,
                  ChangeClass.MODERATE: 2, ChangeClass.MAJOR: 3}
_RANK_TO_CLASS = {v: k for k, v in _SEVERITY_RANK.items()}


def change_detection_enabled() -> bool:
    return flag_enabled("EVIDENCE_CHANGE_DETECTION_ENABLED", "change_detection_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"change": load_policy().get("change", {})}, "change")


def _get(snapshot: Mapping[str, Any], field: str) -> Any:
    for k in _FIELD_KEYS.get(field, [field]):
        if k in snapshot:
            return snapshot.get(k)
    return None


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, (list, tuple, set)):
        return sorted(str(v).strip().lower() for v in value if v is not None)
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items())}
    return value


def assess_change(old: Mapping[str, Any], new: Mapping[str, Any], *,
                  evidence_id: str = "", force: bool = False) -> EvidenceChangeAssessment:
    """Classify the change between two evidence snapshots. Never raises."""
    if not evidence_id and isinstance(new, Mapping):
        evidence_id = str(new.get("evidence_id") or new.get("id") or "")

    if not force and not change_detection_enabled():
        return EvidenceChangeAssessment(
            evidence_id=evidence_id, enabled=False,
            note="change detection disabled (EVIDENCE_CHANGE_DETECTION_ENABLED=false)")
    try:
        if not isinstance(old, Mapping) or not isinstance(new, Mapping):
            raise TypeError("old and new must be mappings")
        policy = _policy()
        sev_map = policy["field_severity"]
        changes: list[FieldChange] = []

        for field in _FIELD_KEYS:
            ov, nv = _get(old, field), _get(new, field)
            if _normalize(ov) != _normalize(nv):
                sev = str(sev_map.get(field, "minor")).capitalize()
                changes.append(FieldChange(field_name=field, old_value=ov, new_value=nv,
                                           severity=sev))

        if not changes:
            return EvidenceChangeAssessment(
                evidence_id=evidence_id, enabled=True,
                change_class=ChangeClass.NONE.value, changes=[],
                summary="no changes detected")

        max_rank = 0
        moderate_count = 0
        for c in changes:
            cls = {"minor": ChangeClass.MINOR, "moderate": ChangeClass.MODERATE,
                   "major": ChangeClass.MAJOR}.get(c.severity.lower(), ChangeClass.MINOR)
            max_rank = max(max_rank, _SEVERITY_RANK[cls])
            if cls == ChangeClass.MODERATE:
                moderate_count += 1

        # Accumulated moderate changes escalate to major.
        threshold = int(policy.get("moderate_to_major_count", 3))
        if moderate_count >= threshold:
            max_rank = max(max_rank, _SEVERITY_RANK[ChangeClass.MAJOR])

        change_class = _RANK_TO_CLASS[max_rank]
        fields = ", ".join(c.field_name for c in changes)
        summary = f"{change_class.value} change in {len(changes)} field(s): {fields}"

        return EvidenceChangeAssessment(
            evidence_id=evidence_id, enabled=True, change_class=change_class.value,
            changes=changes, summary=summary)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return EvidenceChangeAssessment(
            evidence_id=evidence_id, enabled=False,
            note=f"change detection error (ignored): {type(exc).__name__}")
