"""Generic, reusable assertion engine. Every assertion raises AssertionError with a diagnosable message.

Assertions are deliberately domain-agnostic: domain helpers (evidence/audit/dashboard...) fetch data and pass
plain values/records in here.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

from .api_client import ApiResponse


def _fmt(msg: str | None, default: str) -> str:
    return f"{msg}: {default}" if msg else default


# ---- HTTP / response ---------------------------------------------------------------------------
def assert_status(resp: ApiResponse, expected: int | Iterable[int], msg: str | None = None) -> ApiResponse:
    allowed = {expected} if isinstance(expected, int) else set(expected)
    assert resp.status in allowed, _fmt(
        msg, f"{resp.method} {resp.url} -> {resp.status}, expected {sorted(allowed)} "
             f"(request_id={resp.request_id}) body={resp.text[:300]!r}")
    return resp


def assert_success(resp: ApiResponse, msg: str | None = None) -> ApiResponse:
    """2xx/3xx and, for ECS JSON envelopes, ``ok``/``status`` not signalling an error."""
    assert resp.ok, _fmt(msg, f"{resp.method} {resp.url} -> {resp.status} (request_id={resp.request_id}) {resp.text[:300]!r}")
    if resp.is_json:
        body = resp.json()
        if isinstance(body, dict):
            assert body.get("ok", True) is not False, _fmt(msg, f"ECS envelope ok=false: {str(body)[:300]}")
            assert str(body.get("status", "")).lower() not in {"error", "failed", "failure"}, _fmt(
                msg, f"ECS envelope status=error: {str(body)[:300]}")
    return resp


def assert_failure(resp: ApiResponse, status: int | Iterable[int] | None = None, msg: str | None = None) -> ApiResponse:
    """Request was rejected: 4xx/5xx, or an ECS JSON envelope with ok=false / status=error."""
    envelope_err = False
    if resp.is_json:
        try:
            body = resp.json()
            envelope_err = isinstance(body, dict) and (body.get("ok") is False or
                                                       str(body.get("status", "")).lower() in {"error", "failed", "failure"})
        except AssertionError:
            pass
    assert resp.status >= 400 or envelope_err, _fmt(msg, f"expected failure but got {resp.status} {resp.text[:200]!r}")
    if status is not None:
        assert_status(resp, status, msg)
    return resp


def assert_denied(resp: ApiResponse, msg: str | None = None) -> ApiResponse:
    """Access denied the way ECS does it: 401/403, or a redirect/JSON carrying an 'Access denied' notice."""
    text = (resp.notice or resp.error_message or resp.text[:400]).lower()
    denied = resp.status in (401, 403) or "access denied" in text or "not permitted" in text or "permission" in text
    assert denied, _fmt(msg, f"expected access denied, got {resp.status} notice={resp.notice!r} body={resp.text[:200]!r}")
    return resp


def assert_json_field(body: Any, path: str, expected: Any = ..., msg: str | None = None) -> Any:
    """Dotted/indexed path lookup (``a.b.0.c``). With ``expected`` compares equality, else only presence."""
    cur = body
    for part in path.split("."):
        if isinstance(cur, Mapping) and part in cur:
            cur = cur[part]
        elif isinstance(cur, Sequence) and not isinstance(cur, (str, bytes)) and part.lstrip("-").isdigit() \
                and -len(cur) <= int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise AssertionError(_fmt(msg, f"JSON path '{path}' not found (stopped at '{part}') in {str(body)[:300]}"))
    if expected is not ...:
        assert cur == expected, _fmt(msg, f"JSON '{path}' = {cur!r}, expected {expected!r}")
    return cur


def assert_schema(body: Any, schema: Mapping[str, Any], msg: str | None = None) -> None:
    """Lightweight response-shape check (no jsonschema dependency).

    ``schema`` maps key -> type | tuple(types) | nested schema dict | list-of-schema ``[schema]`` (each item).
    Extra keys in ``body`` are allowed (ECS envelopes carry optional fields).
    """
    assert isinstance(body, Mapping), _fmt(msg, f"expected object, got {type(body).__name__}")
    for key, spec in schema.items():
        assert key in body, _fmt(msg, f"missing key '{key}' in {sorted(body)[:20]}")
        val = body[key]
        if isinstance(spec, dict):
            assert_schema(val, spec, msg)
        elif isinstance(spec, list) and spec:
            assert isinstance(val, list), _fmt(msg, f"'{key}' expected list, got {type(val).__name__}")
            for item in val[:25]:
                assert_schema(item, spec[0], msg) if isinstance(spec[0], dict) else None
        else:
            assert isinstance(val, spec), _fmt(msg, f"'{key}' expected {spec}, got {type(val).__name__}")


# ---- generic value assertions ---------------------------------------------------------------------
def assert_equal(actual: Any, expected: Any, msg: str | None = None) -> None:
    assert actual == expected, _fmt(msg, f"{actual!r} != {expected!r}")


def assert_not_equal(actual: Any, unexpected: Any, msg: str | None = None) -> None:
    assert actual != unexpected, _fmt(msg, f"value unexpectedly equals {unexpected!r}")


def assert_contains(container: Any, item: Any, msg: str | None = None) -> None:
    assert item in container, _fmt(msg, f"{item!r} not found in {str(container)[:300]}")


def assert_not_contains(container: Any, item: Any, msg: str | None = None) -> None:
    assert item not in container, _fmt(msg, f"{item!r} unexpectedly found in {str(container)[:300]}")


def assert_exists(value: Any, msg: str | None = None) -> Any:
    assert value not in (None, "", [], {}), _fmt(msg, "expected a value/record to exist but got an empty result")
    return value


def assert_not_exists(value: Any, msg: str | None = None) -> None:
    assert value in (None, "", [], {}), _fmt(msg, f"expected nothing but found {str(value)[:200]}")


def assert_matches(text: str, pattern: str, msg: str | None = None) -> re.Match:
    m = re.search(pattern, text or "", re.I | re.S)
    assert m, _fmt(msg, f"pattern {pattern!r} not found in {text[:300]!r}")
    return m


def assert_within_ms(elapsed_ms: float, limit_ms: float | None, msg: str | None = None) -> None:
    assert limit_ms is not None, "no SLA threshold configured (config/thresholds.yaml)"
    assert elapsed_ms <= limit_ms, _fmt(msg, f"{elapsed_ms:.0f}ms exceeded SLA {limit_ms}ms")


# ---- records / counts (DB rows, API lists) ----------------------------------------------------------
def assert_record_exists(rows: Sequence[Any] | Any, msg: str | None = None) -> Any:
    rows = rows if isinstance(rows, (list, tuple)) else ([rows] if rows else [])
    assert len(rows) >= 1, _fmt(msg, "expected at least one matching record, found none")
    return rows[0]


def assert_record_count(rows: Sequence[Any], expected: int | None = None, *, minimum: int | None = None,
                        maximum: int | None = None, msg: str | None = None) -> int:
    n = len(rows)
    if expected is not None:
        assert n == expected, _fmt(msg, f"record count {n} != {expected}")
    if minimum is not None:
        assert n >= minimum, _fmt(msg, f"record count {n} < {minimum}")
    if maximum is not None:
        assert n <= maximum, _fmt(msg, f"record count {n} > {maximum}")
    return n


def assert_metadata(record: Mapping[str, Any], expected: Mapping[str, Any], *, case_insensitive: bool = True,
                    msg: str | None = None) -> None:
    """Every expected key must be present in ``record`` (or its nested ``metadata`` dict) with an equal value."""
    nested = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    for key, want in expected.items():
        have = record.get(key, nested.get(key, None))
        assert have is not None, _fmt(msg, f"metadata field '{key}' missing in {sorted(record)[:25]}")
        a, b = (str(have).lower(), str(want).lower()) if case_insensitive else (have, want)
        assert a == b, _fmt(msg, f"metadata '{key}' = {have!r}, expected {want!r}")


def assert_hash(content: bytes | str, expected_sha256: str, msg: str | None = None) -> str:
    data = content.encode() if isinstance(content, str) else content
    digest = hashlib.sha256(data).hexdigest()
    assert digest.lower() == (expected_sha256 or "").lower(), _fmt(msg, f"sha256 {digest} != stored {expected_sha256}")
    return digest


def assert_hash_changed(before: str, after: str, msg: str | None = None) -> None:
    assert before and after and before != after, _fmt(msg, f"hash did not change ({before!r} -> {after!r})")


def assert_version(versions: Sequence[Mapping[str, Any]], *, expected_latest: int | None = None,
                   minimum_count: int | None = None, key: str = "version", msg: str | None = None) -> int:
    nums = sorted(int(v.get(key, 0)) for v in versions)
    if minimum_count is not None:
        assert len(nums) >= minimum_count, _fmt(msg, f"{len(nums)} version(s) < {minimum_count}")
    assert nums, _fmt(msg, "no versions returned")
    assert nums == sorted(set(nums)), _fmt(msg, f"duplicate version numbers: {nums}")
    if expected_latest is not None:
        assert nums[-1] == expected_latest, _fmt(msg, f"latest version {nums[-1]} != {expected_latest}")
    return nums[-1]


# ---- domain-level but generic ------------------------------------------------------------------------
def assert_audit_record(records: Sequence[Mapping[str, Any]], *, action: str | None = None, actor: str | None = None,
                        resource: str | None = None, request_id: str | None = None,
                        detail_contains: str | None = None, msg: str | None = None) -> Mapping[str, Any]:
    """At least one audit record matches every given criterion (substring, case-insensitive; request_id exact)."""
    def ok(r: Mapping[str, Any]) -> bool:
        blob = str(r).lower()
        return ((action is None or action.lower() in str(r.get("action", r.get("event", ""))).lower() or action.lower() in blob)
                and (actor is None or actor.lower() in str(r.get("actor", r.get("user", ""))).lower())
                and (resource is None or resource.lower() in str(r.get("resource", "")).lower() or resource.lower() in blob)
                and (request_id is None or str(r.get("request_id", "")) == request_id)
                and (detail_contains is None or detail_contains.lower() in blob))

    hit = [r for r in records if ok(r)]
    assert hit, _fmt(msg, f"no audit record matched action={action!r} actor={actor!r} resource={resource!r} "
                          f"request_id={request_id!r} among {len(records)} record(s)")
    return hit[0]


def assert_role_access(results: Mapping[str, ApiResponse], *, allowed: Iterable[str], denied: Iterable[str],
                       msg: str | None = None) -> None:
    """``results`` maps persona -> response. Allowed personas succeed; denied personas are rejected the ECS way."""
    for p in allowed:
        r = results[p]
        assert r.status < 400 and not _looks_denied(r), _fmt(msg, f"persona '{p}' should be allowed but got {r.status} "
                                                                  f"notice={r.notice!r} {r.text[:120]!r}")
    for p in denied:
        assert_denied(results[p], f"persona '{p}' should be denied")


def _looks_denied(r: ApiResponse) -> bool:
    return "access denied" in (r.notice or r.error_message or "").lower()


def assert_notification(items: Sequence[Any], *, contains: str, msg: str | None = None) -> Any:
    hit = [i for i in items if contains.lower() in str(i).lower()]
    assert hit, _fmt(msg, f"no notification containing {contains!r} among {len(items)} item(s)")
    return hit[0]


def assert_dashboard_value(body: Mapping[str, Any], path: str, expected: Any = ..., *, tolerance: float = 0.0,
                           msg: str | None = None) -> Any:
    val = assert_json_field(body, path, msg=msg)
    if expected is not ...:
        if isinstance(val, (int, float)) and isinstance(expected, (int, float)):
            assert abs(val - expected) <= tolerance, _fmt(msg, f"dashboard '{path}' = {val}, expected {expected} ±{tolerance}")
        else:
            assert val == expected, _fmt(msg, f"dashboard '{path}' = {val!r}, expected {expected!r}")
    return val


def assert_reconciles(parts: Iterable[float], total: float, *, tolerance: float = 0.0, msg: str | None = None) -> None:
    s = sum(parts)
    assert abs(s - total) <= tolerance, _fmt(msg, f"sum of parts {s} != reported total {total} (±{tolerance})")


def assert_report_value(report: Mapping[str, Any] | str, expected: Any, *, path: str | None = None,
                        msg: str | None = None) -> None:
    if path and isinstance(report, Mapping):
        assert_json_field(report, path, expected, msg)
    else:
        assert str(expected) in str(report), _fmt(msg, f"{expected!r} not present in report")


def assert_traceability(record: Mapping[str, Any], required_keys: Iterable[str] = ("source", "evidence_id"),
                        msg: str | None = None) -> None:
    """Evidence/report row links back to its origin. Accepts the alias keys ECS uses across modules."""
    aliases = {"source": ("source", "source_system", "source_connector", "connector", "origin"),
               "evidence_id": ("evidence_id", "evidence_uid", "evidence_key", "id"),
               "application": ("application", "app", "app_slug", "application_id"),
               "control": ("control", "control_id"), "framework": ("framework", "framework_id", "framework_code"),
               "hash": ("hash", "sha256", "content_hash", "stored_hash")}
    blob_keys = {k.lower() for k in record}
    nested = record.get("metadata")
    if isinstance(nested, Mapping):
        blob_keys |= {k.lower() for k in nested}
    for key in required_keys:
        assert blob_keys & set(aliases.get(key, (key,))), _fmt(msg, f"traceability field '{key}' missing in {sorted(blob_keys)[:30]}")


def assert_compliance_mapping(record: Mapping[str, Any], *, framework: str | None = None, control: str | None = None,
                              msg: str | None = None) -> None:
    text = str(record).lower()
    if framework:
        assert framework.lower() in text, _fmt(msg, f"framework {framework!r} not linked in {text[:200]}")
    if control:
        assert control.lower() in text, _fmt(msg, f"control {control!r} not linked in {text[:200]}")
    assert framework or control, "assert_compliance_mapping needs a framework and/or control"


def assert_retention_state(record: Mapping[str, Any], *, expected_status: str | None = None,
                           require_valid_until: bool = False, msg: str | None = None) -> None:
    """Lifecycle row (evidence_reviews: status, valid_until) reflects the retention policy state."""
    if expected_status:
        have = str(record.get("status") or record.get("lifecycle_status") or "")
        assert have.lower() == expected_status.lower(), _fmt(msg, f"retention/lifecycle status {have!r} != {expected_status!r}")
    if require_valid_until:
        assert record.get("valid_until") or record.get("expires") or record.get("retention_until"), _fmt(
            msg, "no valid_until / retention date on the record")


def assert_eventually(predicate: Callable[[], Any], *, timeout: float = 10.0, interval: float = 0.5, what: str = "condition") -> Any:
    from .wait import wait_until

    return wait_until(predicate, timeout=timeout, interval=interval, what=what)
