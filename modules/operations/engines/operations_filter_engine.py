"""Operations filter engine — apply filters, aggregate KPIs, paginate."""

from __future__ import annotations

from typing import Any


def normalize_filters(filters: dict[str, str] | None) -> dict[str, str]:
    if not filters:
        return {}
    return {k: (v or "").strip() for k, v in filters.items()}


def matches_filters(row: dict[str, Any], filters: dict[str, str]) -> bool:
    fw = filters.get("framework", "")
    if fw and not fw.startswith("All ") and row.get("framework") != fw:
        return False
    app = filters.get("application", "")
    if app and not app.startswith("All ") and row.get("application") != app:
        return False
    owner = filters.get("owner", "")
    if owner and not owner.startswith("All ") and row.get("owner") != owner:
        return False
    risk = filters.get("risk", "")
    if risk and not risk.startswith("All "):
        rr = row.get("risk", "")
        if risk == "High":
            if rr not in ("High", "Critical"):
                return False
        elif rr != risk:
            return False
    status = filters.get("status", "")
    if status and not status.startswith("All "):
        candidates = [
            str(row.get("status", "")),
            str(row.get("health", "")),
        ]
        if row.get("sync_status"):
            candidates.append(str(row["sync_status"]))
        if not any(status.lower() in c.lower() or c.lower() == status.lower() for c in candidates if c):
            return False
    return True


def apply_filters(rows: list[dict], filters: dict[str, str] | None) -> list[dict]:
    f = normalize_filters(filters)
    if not f:
        return list(rows)
    return [r for r in rows if matches_filters(r, f)]


def aggregate_kpis(rows: list[dict], definitions: list[dict]) -> list[dict]:
    """definitions: [{label, tone, field|compute}]"""
    out = []
    for d in definitions:
        field = d.get("field")
        if field:
            val = sum(1 for r in rows if r.get(field))
        elif d.get("sum_field"):
            val = sum(int(r.get(d["sum_field"], 0) or 0) for r in rows)
        elif d.get("count_if"):
            cond = d["count_if"]
            val = sum(1 for r in rows if r.get(cond["field"]) == cond.get("equals") or (
                cond.get("in") and r.get(cond["field"]) in cond["in"]
            ))
        else:
            val = len(rows)
        if d.get("format") == "pct" and rows:
            val = round(val / len(rows) * 100, 1)
        out.append({"label": d["label"], "value": val, "tone": d.get("tone", "primary")})
    return out
