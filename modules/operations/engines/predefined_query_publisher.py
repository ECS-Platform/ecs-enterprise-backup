"""Publish successful predefined-query runs as JSON evidence artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from modules.operations.engines.predefined_query_evidence import (
    prepare_evidence_record,
    store_predefined_evidence,
)
from modules.operations.engines.query_connectors import ConnectorResult


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "unknown")).strip("-")
    return cleaned or "unknown"


def resolve_execution_context(control: dict[str, Any]) -> dict[str, str]:
    application = str(control.get("application") or "").strip()
    environment = str(control.get("environment") or "").strip()
    asset_id = str(control.get("asset_id") or "").strip()
    try:
        from config.environment_loader import active_environment

        if not environment:
            environment = active_environment()
    except Exception:  # noqa: BLE001
        environment = environment or "local"
    if not application:
        application = "Net Banking"
    if not asset_id:
        asset_id = application
    return {"application": application, "environment": environment, "asset_id": asset_id}


def _parse_tabular_output(output: str) -> tuple[list[str], list[list[Any]]]:
    lines = [ln.rstrip() for ln in (output or "").splitlines() if ln.strip()]
    if len(lines) < 2 or " | " not in lines[0]:
        return [], []
    columns = [c.strip() for c in lines[0].split(" | ")]
    rows: list[list[Any]] = []
    for line in lines[2:]:
        if " | " not in line:
            continue
        rows.append([cell.strip() for cell in line.split(" | ")])
    return columns, rows


def build_artifact_json(
    *,
    control: dict[str, Any],
    technology: str,
    query: str,
    result: ConnectorResult,
    user: str,
    execution_id: str = "",
    executed_at: str = "",
) -> dict[str, Any]:
    meta = dict(result.metadata or {})
    ctx = resolve_execution_context(control)
    control_id = str(control.get("control_id") or "")
    columns = list(meta.get("columns") or [])
    rows = list(meta.get("parsed_rows") or meta.get("result") or [])
    if not columns and not rows:
        columns, rows = _parse_tabular_output(result.output or "")
    row_count = int(meta.get("rows_returned", len(rows)))
    artifact: dict[str, Any] = {
        "source_type": "PREDEFINED_QUERY",
        "query_id": control_id,
        "technology": technology,
        "application": ctx["application"],
        "environment": ctx["environment"],
        "asset_id": ctx["asset_id"],
        "control_id": control_id,
        "executed_at": executed_at or _utc_now(),
        "status": "SUCCESS",
        "row_count": row_count,
        "columns": columns,
        "result": rows,
    }
    if control.get("control_name"):
        artifact["control_name"] = control["control_name"]
    if control.get("framework_coverage"):
        artifact["framework_coverage"] = control["framework_coverage"]
    if control.get("frameworks"):
        artifact["frameworks"] = list(control["frameworks"])
    if execution_id:
        artifact["execution_id"] = execution_id
    if user:
        artifact["executed_by"] = user
    artifact["query_reference"] = query
    artifact["duration_ms"] = int(result.duration_ms or 0)
    return artifact


def artifact_object_key(
    *,
    application: str,
    environment: str,
    query_id: str,
    executed_at: str,
) -> str:
    ts = executed_at.replace(":", "").replace("+", "Z").replace(" ", "T")
    ts = ts.replace(".", "")[:17]
    return f"predefined-query/{_slug(application)}/{_slug(environment)}/{_slug(query_id)}/{ts}.json"


def publish_predefined_query_evidence(
    *,
    control: dict[str, Any],
    technology: str,
    query: str,
    result: ConnectorResult,
    user: str,
    execution_id: str = "",
    framework: str = "",
) -> dict[str, Any]:
    executed_at = _utc_now()
    artifact = build_artifact_json(
        control=control,
        technology=technology,
        query=query,
        result=result,
        user=user,
        execution_id=execution_id,
        executed_at=executed_at,
    )
    content = json.dumps(artifact, indent=2, sort_keys=True, default=str).encode("utf-8")
    content_hash = hashlib.sha256(content).hexdigest()
    ctx = resolve_execution_context(control)
    control_id = str(control.get("control_id") or "")
    object_key = artifact_object_key(
        application=ctx["application"],
        environment=ctx["environment"],
        query_id=control_id,
        executed_at=executed_at,
    )
    primary_fw = framework or (control.get("frameworks", [""])[0] if control.get("frameworks") else "")
    filename = f"PREDEFINED_QUERY_{control_id}.json"
    custody_mode = os.environ.get("ECS_PREDEFINED_QUERY_CUSTODY", "").strip() or os.environ.get(
        "ECS_EVIDENCE_DEFAULT_CUSTODY", "SNAPSHOT"
    )
    from modules.operations.engines.evidence_repository import register_upload

    upload = register_upload(
        filename=filename,
        content=content,
        uploaded_by=user,
        framework=primary_fw,
        application=ctx["application"],
        control=control_id,
        source_connector="predefined_query",
        source_item_id=f"predefined-query/{control_id}/{execution_id or executed_at}",
        source_url=f"object://{object_key}",
        environment=ctx["environment"],
        mime_type="application/json",
        metadata={
            "source_type": "PREDEFINED_QUERY",
            "query_id": control_id,
            "technology": technology,
            "object_key": object_key,
            "content_sha256": content_hash,
            "execution_id": execution_id,
            "row_count": artifact["row_count"],
        },
        custody_mode=custody_mode,
    )
    evidence = prepare_evidence_record(
        control_id=control_id,
        result=json.dumps(artifact),
        user=user,
        framework_coverage=control.get("framework_coverage") or "",
    )
    store_predefined_evidence(evidence)
    return {
        **upload,
        "evidence_id": upload.get("evidence_id") or evidence.evidence_id,
        "object_key": object_key,
        "sha256": upload.get("sha256") or content_hash,
        "artifact": artifact,
    }
