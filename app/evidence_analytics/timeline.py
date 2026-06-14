"""Evidence Timeline Engine (Capability A, Phase 5.5).

Reconstructs a deterministic chronological timeline for an evidence item or
observation from data ECS already records (audit trail entries, workflow history
entries, version chain, observation close/reopen records). Determines current
state, previous state, and full change history, and flags approval reversals and
declining quality.

  * READ-ONLY, NO-LLM. FLAG-GATED by EVIDENCE_TIMELINE_ENABLED (default off).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.evidence_analytics._common import flag_enabled, load_policy, merge_block, parse_dt
from app.evidence_analytics.models import EvidenceTimeline, EventType, TimelineEvent

_DEFAULTS = {
    "event_priority": {
        "evidence_created": 0, "evidence_updated": 1, "evidence_submitted": 2,
        "evidence_approved": 3, "evidence_rejected": 3, "evidence_reopened": 4,
        "observation_closed": 5, "observation_reopened": 6,
    },
    "quality_decline_threshold": 10,
}

# Map common workflow action strings to canonical event types.
_ACTION_MAP = {
    "create": EventType.EVIDENCE_CREATED, "created": EventType.EVIDENCE_CREATED,
    "upload": EventType.EVIDENCE_CREATED, "uploaded": EventType.EVIDENCE_CREATED,
    "update": EventType.EVIDENCE_UPDATED, "updated": EventType.EVIDENCE_UPDATED,
    "revise": EventType.EVIDENCE_UPDATED, "revised": EventType.EVIDENCE_UPDATED,
    "submit": EventType.EVIDENCE_SUBMITTED, "submitted": EventType.EVIDENCE_SUBMITTED,
    "evidence.submit": EventType.EVIDENCE_SUBMITTED,
    "approve": EventType.EVIDENCE_APPROVED, "approved": EventType.EVIDENCE_APPROVED,
    "evidence.approve": EventType.EVIDENCE_APPROVED,
    "reject": EventType.EVIDENCE_REJECTED, "rejected": EventType.EVIDENCE_REJECTED,
    "evidence.reject": EventType.EVIDENCE_REJECTED,
    "reopen": EventType.EVIDENCE_REOPENED, "reopened": EventType.EVIDENCE_REOPENED,
    "send_back": EventType.EVIDENCE_REOPENED,
    "observation.close": EventType.OBSERVATION_CLOSED, "close": EventType.OBSERVATION_CLOSED,
    "closed": EventType.OBSERVATION_CLOSED,
    "observation.reopen": EventType.OBSERVATION_REOPENED,
}

_APPROVE = EventType.EVIDENCE_APPROVED
_REJECT = EventType.EVIDENCE_REJECTED


def timeline_enabled() -> bool:
    return flag_enabled("EVIDENCE_TIMELINE_ENABLED", "timeline_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"timeline": load_policy().get("timeline", {})}, "timeline")


def _classify(action: str) -> EventType | None:
    key = str(action or "").strip().lower()
    if key in _ACTION_MAP:
        return _ACTION_MAP[key]
    for token, et in _ACTION_MAP.items():
        if token in key:
            return et
    return None


def _event_from_entry(entry: Mapping[str, Any], source: str) -> TimelineEvent | None:
    action = entry.get("action") or entry.get("event") or entry.get("event_type") or ""
    et = _classify(str(action))
    if et is None:
        return None
    ts = (entry.get("timestamp") or entry.get("created_at") or entry.get("ts")
          or entry.get("approved_at") or entry.get("rejected_at") or entry.get("submitted_at")
          or entry.get("uploaded_at") or entry.get("closed_at") or "")
    return TimelineEvent(
        event_type=et.value, timestamp=str(ts),
        actor=str(entry.get("actor") or entry.get("user") or entry.get("by") or ""),
        previous_state=str(entry.get("previous_status") or entry.get("previous_state") or ""),
        new_state=str(entry.get("new_status") or entry.get("new_state") or ""),
        detail=str(entry.get("detail") or entry.get("comments") or ""), source=source)


def build_timeline(subject: str, *,
                   audit_entries: Sequence[Mapping[str, Any]] | None = None,
                   workflow_history: Sequence[Mapping[str, Any]] | None = None,
                   version_history: Any = None,
                   observation_events: Sequence[Mapping[str, Any]] | None = None,
                   quality_by_version: Mapping[int, float] | None = None,
                   force: bool = False) -> EvidenceTimeline:
    """Reconstruct a chronological timeline for an evidence item / observation.

    All inputs are optional and tolerated when missing. Never raises.
    """
    if not force and not timeline_enabled():
        return EvidenceTimeline(subject=subject, enabled=False,
                                note="timeline disabled (EVIDENCE_TIMELINE_ENABLED=false)")
    try:
        policy = _policy()
        priority = policy.get("event_priority", _DEFAULTS["event_priority"])
        events: list[TimelineEvent] = []

        for entry in (audit_entries or []):
            if isinstance(entry, Mapping):
                e = _event_from_entry(entry, "audit_log")
                if e:
                    events.append(e)
        for entry in (workflow_history or []):
            if isinstance(entry, Mapping):
                e = _event_from_entry(entry, "workflow_history")
                if e:
                    events.append(e)
        for entry in (observation_events or []):
            if isinstance(entry, Mapping):
                e = _event_from_entry(entry, "observation")
                if e:
                    events.append(e)

        # Version chain -> created/updated events.
        versions = getattr(version_history, "versions", None) or []
        for v in versions:
            vnum = getattr(v, "version_number", 1)
            et = EventType.EVIDENCE_CREATED if vnum == 1 else EventType.EVIDENCE_UPDATED
            events.append(TimelineEvent(
                event_type=et.value, timestamp=str(getattr(v, "created_at", "")),
                actor=str(getattr(v, "created_by", "")),
                detail=str(getattr(v, "change_reason", "")), source="version"))

        # Deterministic sort: by timestamp, then by canonical event priority.
        def _sort_key(e: TimelineEvent):
            dt = parse_dt(e.timestamp)
            return (1 if dt is None else 0,
                    dt.timestamp() if dt else 0.0,
                    int(priority.get(e.event_type, 99)))

        events.sort(key=_sort_key)

        # Current / previous state from terminal events.
        state_events = [e for e in events]
        current_state = state_events[-1].event_type if state_events else ""
        previous_state = state_events[-2].event_type if len(state_events) >= 2 else ""

        # Approval reversal: an APPROVED followed later by a REJECTED/REOPENED.
        approval_reversed = False
        seen_approved = False
        for e in events:
            if e.event_type == _APPROVE.value:
                seen_approved = True
            elif seen_approved and e.event_type in (_REJECT.value,
                                                    EventType.EVIDENCE_REOPENED.value):
                approval_reversed = True
                break

        # Declining quality across versions.
        quality_declining = False
        if quality_by_version:
            ordered = [quality_by_version[k] for k in sorted(quality_by_version)]
            threshold = float(policy.get("quality_decline_threshold", 10))
            for i in range(1, len(ordered)):
                if ordered[i - 1] - ordered[i] >= threshold:
                    quality_declining = True
                    break

        return EvidenceTimeline(
            subject=subject, enabled=True, current_state=current_state,
            previous_state=previous_state, events=events,
            approval_reversed=approval_reversed, quality_declining=quality_declining)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return EvidenceTimeline(subject=subject, enabled=False,
                                note=f"timeline error (ignored): {type(exc).__name__}")


def detect_approval_reversal(timeline: EvidenceTimeline) -> bool:
    return timeline.approval_reversed


def detect_quality_decline(timeline: EvidenceTimeline) -> bool:
    return timeline.quality_declining
