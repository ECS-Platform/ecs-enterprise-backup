"""Normalize predefined-query execution results into rule-evaluable evidence.

The predefined-query engine returns connector-shaped payloads (tabular text for
SQL connectors, raw stdout for shell/CLI/scanner connectors). The Common-Control
rule engine needs named fields. This module is the single translation point and
adds no execution logic of its own — it only reshapes what
``predefined_queries_engine.run_predefined_query`` already returned.

Output document::

    NormalizedEvidence(
        query_id, technology, ok, status, source,
        columns=[...], rows=[{col: val}, ...], row_count,
        output="<raw text>",
        fields={"ssl": "on", "row_count": 3, "line_count": 12, "output": "..."},
        error, error_type, reason_code, evidence_id,
    )

Field derivation is deterministic and generic:
  * ``row_count`` / ``line_count`` / ``output`` are always present,
  * a name/value shaped result (``name|setting``, ``Variable_name|Value``,
    ``name|value``) becomes one field per row,
  * a single-row result becomes one field per column,
  * every column remains addressable row-wise for aggregated rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.operations.engines.common_control_rule_engine import (
    REASON_CONNECTIVITY_PENDING,
    REASON_EVIDENCE_MISSING,
)

#: Engine error types that mean "we could not reach / use the target", as opposed
#: to "the control genuinely failed". These must surface as UNKNOWN, never as a
#: control failure.
CONNECTIVITY_ERROR_TYPES: frozenset[str] = frozenset({
    "connection_error",
    "connection_failure",
    "connector_unavailable",
    "missing_connector",
    "configuration_required",
    "config_required",
    "timeout",
})

#: Error types that mean the platform cannot execute this query at all.
NOT_EXECUTABLE_ERROR_TYPES: frozenset[str] = frozenset({
    "unsupported_control",
    "unsupported_technology",
    "unsupported_query",
    "deferred_control",
    "missing_control",
    "missing_query",
    "missing_framework",
})

STATUS_SUCCESS = "SUCCESS"
STATUS_CONNECTIVITY_PENDING = "CONNECTIVITY_PENDING"
STATUS_NOT_EXECUTABLE = "NOT_EXECUTABLE"
STATUS_EXECUTION_FAILED = "EXECUTION_FAILED"
STATUS_NOT_EXECUTED = "NOT_EXECUTED"

#: Column-name pairs that identify a "setting name / setting value" result.
_NAME_COLUMNS = frozenset({"name", "variable_name", "parameter", "parameter_name", "setting_name", "key"})
_VALUE_COLUMNS = frozenset({"value", "setting", "val", "current_value"})


@dataclass
class NormalizedEvidence:
    """Rule-evaluable view of one predefined-query execution."""

    query_id: str = ""
    technology: str = ""
    ok: bool = False
    status: str = STATUS_NOT_EXECUTED
    source: str = "live"                # live | fixture | none
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    output: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    error_type: str = ""
    reason_code: str = ""
    evidence_id: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "technology": self.technology,
            "ok": self.ok,
            "status": self.status,
            "source": self.source,
            "columns": list(self.columns),
            "row_count": self.row_count,
            "fields": dict(self.fields),
            "error": self.error,
            "error_type": self.error_type,
            "reason_code": self.reason_code,
            "evidence_id": self.evidence_id,
            "duration_ms": self.duration_ms,
            "output_excerpt": (self.output or "")[:500],
        }


def _parse_tabular(output: str) -> tuple[list[str], list[list[str]]]:
    """Parse the ``col | col`` / ``---`` / ``val | val`` shape SQL connectors emit."""
    try:
        from modules.operations.engines.predefined_query_publisher import _parse_tabular_output

        return _parse_tabular_output(output)
    except Exception:  # noqa: BLE001 - keep normalization working standalone
        import re as _re

        lines = [ln.rstrip() for ln in (output or "").splitlines() if ln.strip()]
        if len(lines) < 2 or not _re.match(r"^-+$", lines[1]):
            return [], []
        columns = [c.strip() for c in lines[0].split(" | ")] if " | " in lines[0] else [lines[0].strip()]
        rows = [
            [cell.strip() for cell in line.split(" | ")] if " | " in line else [line.strip()]
            for line in lines[2:]
        ]
        return columns, rows


def _line_count(output: str) -> int:
    return sum(1 for ln in (output or "").splitlines() if ln.strip())


def _derive_fields(columns: list[str], rows: list[dict[str, Any]], output: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "row_count": len(rows),
        "line_count": _line_count(output),
        "output": output or "",
    }
    if not columns:
        return fields

    lowered = [c.strip().lower() for c in columns]
    # name/value shaped result (any column count, e.g. "profile, resource_name,
    # limit") -> one field per row, keyed by the name column's value. Extra
    # columns (e.g. "profile") are carried in the row but not exploded into
    # fields — rules address the settings by name, not by their container.
    name_idx = next((i for i, c in enumerate(lowered) if c in _NAME_COLUMNS), None)
    value_idx = next((i for i, c in enumerate(lowered) if c in _VALUE_COLUMNS), None)
    if name_idx is not None and value_idx is not None and name_idx != value_idx:
        name_col, value_col = columns[name_idx], columns[value_idx]
        for row in rows:
            key = str(row.get(name_col, "")).strip()
            if key:
                fields.setdefault(key, row.get(value_col))
        return fields

    # Single-row result -> one field per column.
    if len(rows) == 1:
        for col in columns:
            fields.setdefault(col, rows[0].get(col))
    return fields


def normalize_execution_result(
    result: dict[str, Any] | None,
    *,
    query_id: str = "",
    technology: str = "",
    execution_mode: str = "",
    source: str = "live",
    parse: str = "",
) -> NormalizedEvidence:
    """Turn a ``run_predefined_query`` payload into a :class:`NormalizedEvidence`.

    ``execution_mode`` comes from the predefined-query catalog (``sql``, ``shell``,
    ``cli``, ``rest_api``, ``scanner``) and selects tabular vs text parsing.
    ``parse`` (``text`` / ``rows`` / ``auto``) overrides it when a rule needs to.
    """
    ev = NormalizedEvidence(query_id=query_id, technology=technology, source=source)

    if not result:
        ev.status = STATUS_NOT_EXECUTED
        ev.reason_code = REASON_EVIDENCE_MISSING
        ev.error = "Predefined query was not executed."
        ev.fields = _derive_fields([], [], "")
        return ev

    ev.evidence_id = str(result.get("evidence_id") or "")
    ev.duration_ms = int(result.get("duration_ms") or 0)
    ev.output = str(result.get("output") or "")

    if not result.get("ok"):
        ev.error = str(result.get("error") or "Execution failed")
        ev.error_type = str(result.get("error_type") or "execution_failure")
        if ev.error_type in CONNECTIVITY_ERROR_TYPES:
            ev.status = STATUS_CONNECTIVITY_PENDING
            ev.reason_code = REASON_CONNECTIVITY_PENDING
        elif ev.error_type in NOT_EXECUTABLE_ERROR_TYPES:
            ev.status = STATUS_NOT_EXECUTABLE
            ev.reason_code = REASON_EVIDENCE_MISSING
        else:
            ev.status = STATUS_EXECUTION_FAILED
            ev.reason_code = REASON_EVIDENCE_MISSING
        ev.fields = _derive_fields([], [], ev.output)
        return ev

    ev.ok = True
    ev.status = STATUS_SUCCESS

    mode = (parse or "").strip().lower()
    if mode not in ("text", "rows", "auto", ""):
        mode = "auto"
    if not mode or mode == "auto":
        mode = "rows" if (execution_mode or "").strip().lower() == "sql" else "text"

    columns: list[str] = []
    raw_rows: list[list[str]] = []
    if mode == "rows":
        columns, raw_rows = _parse_tabular(ev.output)

    ev.columns = columns
    ev.rows = [
        {col: (row[i] if i < len(row) else "") for i, col in enumerate(columns)}
        for row in raw_rows
    ]
    ev.row_count = len(ev.rows) or int(result.get("rows_returned") or 0)
    ev.fields = _derive_fields(columns, ev.rows, ev.output)
    ev.fields["row_count"] = ev.row_count
    return ev


def normalize_raw_output(
    output: str,
    *,
    query_id: str = "",
    technology: str = "",
    execution_mode: str = "",
    source: str = "fixture",
    parse: str = "",
) -> NormalizedEvidence:
    """Normalize raw connector output directly (used for offline PQ fixtures)."""
    return normalize_execution_result(
        {"ok": True, "output": output},
        query_id=query_id,
        technology=technology,
        execution_mode=execution_mode,
        source=source,
        parse=parse,
    )


def unavailable_evidence(
    *,
    query_id: str = "",
    technology: str = "",
    reason: str = "Target not reachable — connectivity pending.",
    reason_code: str = REASON_CONNECTIVITY_PENDING,
    status: str = STATUS_CONNECTIVITY_PENDING,
) -> NormalizedEvidence:
    """Evidence placeholder for a control that could not be checked at all."""
    ev = NormalizedEvidence(
        query_id=query_id,
        technology=technology,
        ok=False,
        status=status,
        source="none",
        error=reason,
        reason_code=reason_code,
    )
    ev.fields = _derive_fields([], [], "")
    return ev
