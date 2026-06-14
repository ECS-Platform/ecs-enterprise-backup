"""Advanced evidence query engine (Phase 7 of 5.4).

Deterministic querying over an in-memory list of evidence/observation rows:
filtering, aggregation, and timeline. NO NLP, NO AI, NO vector search — exact /
membership field matching only.

Examples (filters dict): {"framework": "RBI", "application": "Payments",
"status": "Rejected", "owner": "John", "year": "2025", "control": "CIS-7"}

  * READ-ONLY, NO-LLM. FLAG-GATED by EVIDENCE_QUERY_ENABLED (default off).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.evidence_intel._common import flag_enabled, load_policy, merge_block, parse_dt
from app.evidence_intel.models import QueryResult

_DEFAULTS = {
    "max_results": 1000,
    "filterable_fields": ["framework", "application", "status", "owner", "control",
                          "object_type", "source_system", "year"],
    "groupable_fields": ["framework", "application", "status", "owner", "control",
                         "object_type", "year"],
}

# Map a logical filter field to the candidate row keys it can match.
_FIELD_KEYS = {
    "framework": ["framework", "framework_mapping", "frameworks", "framework_tags"],
    "application": ["application", "application_id", "application_tags"],
    "observation": ["observation", "observation_id", "obs_id"],
    "status": ["status", "review_status", "evidence_status"],
    "approval_status": ["approval_status", "review_status", "status", "evidence_status"],
    "owner": ["owner", "remediation_owner", "uploaded_by", "created_by"],
    "control": ["control", "control_id", "control_mapping", "controls"],
    "object_type": ["object_type", "evidence_type", "evidence_category", "type"],
    "evidence_type": ["evidence_type", "object_type", "evidence_category", "type"],
    "source_system": ["source_system"],
    "year": ["year"],
    "audit_year": ["audit_year", "year"],
    # upload_date matches an exact YYYY-MM-DD against any upload/collection date.
    "upload_date": ["upload_date", "uploaded_at", "collected_timestamp", "created_at"],
}

# Fields whose values are dates we normalize to YYYY-MM-DD for exact matching.
_DATE_FIELDS = {"upload_date"}
# Fields whose values we reduce to a 4-digit year.
_YEAR_FIELDS = {"year", "audit_year"}


def query_enabled() -> bool:
    return flag_enabled("EVIDENCE_QUERY_ENABLED", "query_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"query": load_policy().get("query", {})}, "query")


def _row_values(row: Mapping[str, Any], field: str) -> set[str]:
    """All string values a row exposes for a logical field (lowercased)."""
    out: set[str] = set()

    # Year fields: reduce any matched value/timestamp to a 4-digit year.
    if field in _YEAR_FIELDS:
        for key in _FIELD_KEYS.get(field, [field]):
            v = row.get(key)
            if v is None or str(v).strip() == "":
                continue
            dt = parse_dt(v)
            if dt:
                out.add(str(dt.year))
            else:
                token = str(v).strip()
                out.add(token[:4] if len(token) >= 4 and token[:4].isdigit() else token)
        if not out:
            for tk in ("collected_timestamp", "uploaded_at", "upload_date",
                       "created_at", "reviewed_at"):
                dt = parse_dt(row.get(tk))
                if dt:
                    out.add(str(dt.year))
                    break
        return out

    # Date fields: normalize to YYYY-MM-DD for exact-day matching.
    if field in _DATE_FIELDS:
        for key in _FIELD_KEYS.get(field, [field]):
            v = row.get(key)
            if v is None or str(v).strip() == "":
                continue
            dt = parse_dt(v)
            out.add(dt.strftime("%Y-%m-%d") if dt else str(v).strip().lower())
        return out

    for key in _FIELD_KEYS.get(field, [field]):
        if key not in row:
            continue
        v = row.get(key)
        if isinstance(v, str) and v.strip():
            out.add(v.strip().lower())
        elif isinstance(v, (list, tuple, set)):
            for x in v:
                if x is not None and str(x).strip():
                    out.add(str(x).strip().lower())
        elif isinstance(v, int):
            out.add(str(v))
    return out


def _matches(row: Mapping[str, Any], field: str, wanted: Any) -> bool:
    values = _row_values(row, field)
    if not values:
        return False
    if isinstance(wanted, (list, tuple, set)):
        wanted_set = {str(w).strip().lower() for w in wanted if str(w).strip()}
        return bool(values & wanted_set)
    target = str(wanted).strip().lower()
    # framework/control allow base-prefix match (e.g. "rbi" matches "rbi-csf-x").
    if field in ("framework", "control"):
        return any(v == target or v.startswith(target) or target in v for v in values)
    return target in values


def query_evidence(rows: Iterable[Mapping[str, Any]],
                   filters: Mapping[str, Any] | None = None, *,
                   group_by: str | None = None,
                   timeline_field: str = "collected_timestamp",
                   force: bool = False) -> QueryResult:
    """Filter + (optionally) aggregate + build a timeline over rows. Never raises."""
    if not force and not query_enabled():
        return QueryResult(enabled=False,
                           note="query engine disabled (EVIDENCE_QUERY_ENABLED=false)")
    try:
        policy = _policy()
        max_results = int(policy.get("max_results", 1000))
        filterable = set(policy.get("filterable_fields", []))
        groupable = set(policy.get("groupable_fields", []))
        filters = {k: v for k, v in (filters or {}).items() if k in filterable}

        all_rows = [r for r in rows if isinstance(r, Mapping)]
        matched = [r for r in all_rows
                   if all(_matches(r, f, val) for f, val in filters.items())]
        total = len(matched)
        limited = [dict(r) for r in matched[:max_results]]

        aggregations: dict[str, dict[str, int]] = {}
        if group_by and group_by in groupable:
            bucket: dict[str, int] = {}
            for r in matched:
                vals = _row_values(r, group_by) or {"(none)"}
                for v in vals:
                    bucket[v] = bucket.get(v, 0) + 1
            aggregations[group_by] = dict(sorted(bucket.items(),
                                                 key=lambda kv: (-kv[1], kv[0])))

        timeline: list[dict[str, Any]] = []
        by_year: dict[str, int] = {}
        for r in matched:
            dt = parse_dt(r.get(timeline_field) or r.get("uploaded_at") or r.get("created_at"))
            if dt:
                key = dt.strftime("%Y-%m")
                by_year[key] = by_year.get(key, 0) + 1
        for period in sorted(by_year):
            timeline.append({"period": period, "count": by_year[period]})

        return QueryResult(enabled=True, total=total, rows=limited,
                           aggregations=aggregations, timeline=timeline,
                           filters=dict(filters))
    except Exception as exc:  # noqa: BLE001 - fail safe
        return QueryResult(enabled=False,
                           note=f"query error (ignored): {type(exc).__name__}")


def aggregate(rows: Iterable[Mapping[str, Any]], group_by: str, *,
              filters: Mapping[str, Any] | None = None,
              force: bool = False) -> dict[str, int]:
    """Convenience: return just the aggregation bucket for a field."""
    res = query_evidence(rows, filters, group_by=group_by, force=force)
    return res.aggregations.get(group_by, {})
