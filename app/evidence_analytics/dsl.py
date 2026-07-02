"""Evidence Search DSL (Capability E, Phase 5.5).

A small, deterministic, injection-safe query language for auditors, e.g.:

    framework=SOC2 AND status=approved AND age>90
    application="Payments API" AND reused=true
    source_system=sonarqube AND quality>=80

Grammar (case-insensitive keywords):
    query      := condition (AND condition)*
    condition  := field operator value
    operator   := = | != | > | < | >= | <=
    value      := bareword | "quoted string" | number | true/false

Parsing is a hand-written tokenizer + recursive reader (NO eval, NO regex-based
code execution). Fields and operators are allow-listed from config. Execution is
delegated to the Phase 5.4 query engine (evidence_intel.query); numeric pseudo
fields (age, quality) and booleans (approved, reused) are evaluated in-process.

NEW FLAG: EVIDENCE_SEARCH_DSL_ENABLED (default off). Execution additionally
requires the Phase 5.4 EVIDENCE_QUERY_ENABLED flag.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from app.evidence_analytics._common import age_days, flag_enabled, load_policy, merge_block
from app.evidence_analytics.models import DSLCondition, DSLQuery, DSLResult

_DEFAULTS = {
    "allowed_fields": [
        "framework", "application", "observation", "control", "owner", "status",
        "approval_status", "evidence_type", "source_system", "year", "audit_year",
        "upload_date", "age", "quality", "approved", "reused",
    ],
    "operators": ["=", "!=", ">", "<", ">=", "<="],
    "max_conditions": 20,
}

_NUMERIC_FIELDS = {"age", "quality", "year", "audit_year"}
_BOOL_FIELDS = {"approved", "reused"}
_RANGE_OPS = {">", "<", ">=", "<="}
_TWO_CHAR_OPS = (">=", "<=", "!=")
_ONE_CHAR_OPS = ("=", ">", "<")


def search_dsl_enabled() -> bool:
    return flag_enabled("EVIDENCE_SEARCH_DSL_ENABLED", "search_dsl_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"dsl": load_policy().get("dsl", {})}, "dsl")


# --------------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------------- #

def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            buf = []
            while j < n and text[j] != quote:
                buf.append(text[j])
                j += 1
            if j >= n:
                raise ValueError("unterminated quoted string")
            tokens.append('"' + "".join(buf) + '"')  # keep quote marker
            i = j + 1
            continue
        two = text[i:i + 2]
        if two in _TWO_CHAR_OPS:
            tokens.append(two)
            i += 2
            continue
        if ch in _ONE_CHAR_OPS:
            tokens.append(ch)
            i += 1
            continue
        # bareword (until whitespace or operator char)
        j = i
        buf = []
        while j < n and not text[j].isspace() and text[j] not in "=<>!\"'":
            buf.append(text[j])
            j += 1
        tokens.append("".join(buf))
        i = j
    return tokens


def _coerce_value(field_name: str, raw: str) -> Any:
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if field_name in _BOOL_FIELDS:
        return raw.strip().lower() in ("true", "1", "yes")
    if field_name in _NUMERIC_FIELDS:
        try:
            return float(raw) if "." in raw else int(raw)
        except ValueError:
            raise ValueError(f"field '{field_name}' expects a number, got '{raw}'")
    return raw


def parse(text: str) -> DSLQuery:
    """Parse a DSL string into a validated DSLQuery. Never raises."""
    query = DSLQuery(raw=str(text or ""))
    try:
        policy = _policy()
        allowed = {str(f).lower() for f in policy.get("allowed_fields", [])}
        operators = set(policy.get("operators", _DEFAULTS["operators"]))
        max_conditions = int(policy.get("max_conditions", 20))

        tokens = _tokenize(query.raw)
        if not tokens:
            query.errors.append("empty query")
            return query

        # Read: field op value (AND field op value)*
        idx = 0
        expect_condition = True
        while idx < len(tokens):
            if not expect_condition:
                if tokens[idx].upper() != "AND":
                    query.errors.append(f"expected 'AND', got '{tokens[idx]}'")
                    return query
                idx += 1
                expect_condition = True
                continue
            if idx + 2 > len(tokens) - 1:
                query.errors.append("incomplete condition (expected field op value)")
                return query
            field_name, op, raw_val = tokens[idx], tokens[idx + 1], tokens[idx + 2]
            fkey = field_name.lower()
            if fkey not in allowed:
                query.errors.append(f"unknown field '{field_name}'")
                return query
            if op not in operators:
                query.errors.append(f"unknown operator '{op}'")
                return query
            if op in _RANGE_OPS and fkey not in _NUMERIC_FIELDS:
                query.errors.append(f"operator '{op}' only valid for numeric fields")
                return query
            value = _coerce_value(fkey, raw_val)
            query.conditions.append(DSLCondition(field_name=fkey, operator=op, value=value))
            idx += 3
            expect_condition = False

        if expect_condition and not query.conditions:
            query.errors.append("no conditions parsed")
            return query
        if expect_condition and query.conditions:
            query.errors.append("trailing 'AND' with no condition")
            return query
        if len(query.conditions) > max_conditions:
            query.errors.append(f"too many conditions (> {max_conditions})")
            return query

        query.valid = True
        return query
    except ValueError as exc:
        query.errors.append(str(exc))
        return query
    except Exception as exc:  # noqa: BLE001 - fail safe
        query.errors.append(f"parse error: {type(exc).__name__}")
        return query


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #

def _row_field(row: Mapping[str, Any], field_name: str, now: datetime) -> Any:
    if field_name == "age":
        for key in ("collected_timestamp", "collected_at", "upload_date",
                    "uploaded_at", "created_at", "timestamp"):
            if row.get(key):
                d = age_days(row.get(key), now=now)
                if d is not None:
                    return d
        return None
    if field_name == "quality":
        q = row.get("quality")
        if q is None:
            q = row.get("quality_score")
        try:
            return float(q) if q is not None else None
        except (TypeError, ValueError):
            return None
    if field_name == "approved":
        status = str(row.get("approval_status") or row.get("status") or "").lower()
        return status in ("approved", "approve", "accepted")
    if field_name == "reused":
        val = row.get("reused")
        if val is None:
            controls = row.get("submitted_controls") or row.get("controls") or []
            return len(controls) > 1 if isinstance(controls, (list, tuple)) else False
        return bool(val)
    if field_name in ("year", "audit_year"):
        for key in ("audit_year", "year", "collected_timestamp", "upload_date", "created_at"):
            v = row.get(key)
            if isinstance(v, int):
                return v
            if isinstance(v, str) and v[:4].isdigit():
                return int(v[:4])
        return None
    return row.get(field_name)


def _match(row: Mapping[str, Any], cond: DSLCondition, now: datetime) -> bool:
    actual = _row_field(row, cond.field_name, now)
    expected = cond.value
    if cond.operator in _RANGE_OPS:
        if actual is None:
            return False
        try:
            a, e = float(actual), float(expected)
        except (TypeError, ValueError):
            return False
        return {">": a > e, "<": a < e, ">=": a >= e, "<=": a <= e}[cond.operator]
    # equality / inequality (case-insensitive for strings, exact for bool/number)
    if isinstance(expected, bool):
        eq = bool(actual) == expected
    elif isinstance(expected, (int, float)):
        try:
            eq = float(actual) == float(expected)
        except (TypeError, ValueError):
            eq = False
    else:
        eq = str(actual or "").strip().lower() == str(expected).strip().lower()
    return eq if cond.operator == "=" else (not eq)


def execute(text: str, rows: Sequence[Mapping[str, Any]], *,
            now: datetime | None = None, force: bool = False) -> DSLResult:
    """Parse then evaluate the DSL against in-memory rows. Never raises."""
    if not force and not search_dsl_enabled():
        return DSLResult(enabled=False, query=parse(text),
                         note="search DSL disabled (EVIDENCE_SEARCH_DSL_ENABLED=false)")
    try:
        now = now or datetime.now(timezone.utc)
        query = parse(text)
        if not query.valid:
            return DSLResult(enabled=True, query=query, total=0,
                             note="invalid query: " + "; ".join(query.errors))
        matched = [dict(r) for r in rows
                   if isinstance(r, Mapping)
                   and all(_match(r, c, now) for c in query.conditions)]
        return DSLResult(enabled=True, query=query, total=len(matched), rows=matched)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return DSLResult(enabled=False, query=DSLQuery(raw=str(text or "")),
                         note=f"dsl execute error (ignored): {type(exc).__name__}")
