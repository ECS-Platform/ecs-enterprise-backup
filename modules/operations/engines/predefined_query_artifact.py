"""Build deterministic JSON artifacts for predefined-query evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
QUERY_VERSION = "1.0"

_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|secret|token|api[_-]?key|connection[_-]?string)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_path_component(value: str, *, fallback: str = "unknown") -> str:
    raw = str(value or "").strip() or fallback
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
    return safe.strip("._-") or fallback


def redact_secrets(text: str) -> str:
    out = str(text or "")
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(r"\1=***REDACTED***", out)
    return out


def _parse_result_payload(raw_output: str) -> tuple[list[str], list[Any], dict[str, Any]]:
    text = redact_secrets(raw_output or "")
    if not text.strip():
        return [], [], {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return ["value"], parsed[:50], {"result_type": "array"}
        if isinstance(parsed, dict):
            cols = [str(k) for k in parsed.keys()]
            return cols, [parsed], {"result_type": "object"}
    except json.JSONDecodeError:
        pass
    lines = [ln for ln in text.splitlines() if ln.strip()][:50]
    return ["line"], lines, {"result_type": "text"}


def build_artifact_filename(
    *,
    application: str,
    environment: str,
    technology: str,
    control_id: str,
    query_id: str,
    executed_at: str,
    content_hash: str,
) -> str:
    ts = sanitize_path_component(executed_at.replace(":", "").replace("+", ""), fallback="ts")
    prefix = content_hash[:12] if content_hash else "nohash"
    parts = [
        "predefined-query",
        sanitize_path_component(application, fallback="app"),
        sanitize_path_component(environment, fallback="env"),
        sanitize_path_component(technology, fallback="tech"),
        sanitize_path_component(control_id, fallback="control"),
        sanitize_path_component(query_id, fallback="query"),
        f"{ts}_{prefix}.json",
    ]
    return "/".join(parts)


def build_success_artifact(
    *,
    control: dict[str, Any],
    technology: str,
    query: str,
    raw_output: str,
    duration_ms: int,
    row_count: int,
    user: str,
    application: str = "ECS Demo",
    environment: str = "local",
    asset_id: str = "",
    execution_id: str = "",
    compliance_status: str = "UNKNOWN",
    expected_value: Any = None,
    observed_value: Any = None,
    scheduler_job_id: str = "",
    scheduler_run_id: str = "",
    execution_mode: str = "ON_DEMAND",
) -> dict[str, Any]:
    executed_at = _utc_now()
    cols, result_rows, parse_meta = _parse_result_payload(raw_output)
    frameworks = list(control.get("frameworks") or [])
    if not frameworks and control.get("framework_coverage"):
        frameworks = [x.strip() for x in str(control["framework_coverage"]).split(",") if x.strip()]
    control_id = str(control.get("control_id") or "")
    return {
        "schema_version": SCHEMA_VERSION,
        "source_type": "PREDEFINED_QUERY",
        "query_id": control_id,
        "query_name": str(control.get("control_name") or control_id),
        "query_version": QUERY_VERSION,
        "technology": technology,
        "application": application,
        "environment": environment,
        "asset_id": asset_id or application,
        "frameworks": frameworks,
        "control_ids": [control_id] if control_id else [],
        "executed_at": executed_at,
        "execution_status": "SUCCESS",
        "duration_ms": int(duration_ms or 0),
        "row_count": int(row_count or 0),
        "columns": cols,
        "result": result_rows,
        "compliance_status": compliance_status,
        "expected_value": expected_value,
        "observed_value": observed_value,
        "error": None,
        "execution_id": execution_id,
        "executed_by": user,
        "scheduler_job_id": scheduler_job_id,
        "scheduler_run_id": scheduler_run_id,
        "execution_mode": execution_mode,
        "parse_meta": parse_meta,
    }


def build_failure_record(
    *,
    control: dict[str, Any],
    technology: str,
    query: str,
    error_message: str,
    error_code: str,
    user: str,
    duration_ms: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_type": "PREDEFINED_QUERY",
        "query_id": str(control.get("control_id") or ""),
        "query_name": str(control.get("control_name") or ""),
        "technology": technology,
        "executed_at": _utc_now(),
        "execution_status": "FAILED",
        "duration_ms": int(duration_ms or 0),
        "executed_by": user,
        "command_or_query_reference": query,
        "error_code": error_code,
        "error": redact_secrets(error_message),
    }


def artifact_bytes(artifact: dict[str, Any]) -> bytes:
    return json.dumps(artifact, indent=2, sort_keys=True, default=str).encode("utf-8")


def artifact_sha256(artifact: dict[str, Any]) -> str:
    return hashlib.sha256(artifact_bytes(artifact)).hexdigest()
