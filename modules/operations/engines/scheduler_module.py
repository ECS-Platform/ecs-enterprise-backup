"""Automated scheduled evidence pull simulation."""

import os
import threading
import time
from datetime import datetime, timezone

from app import ecs_state
from app.env_bootstrap import demo_mode_enabled
from modules.executive_overview.engines.demo_metrics import SCHEDULER_METRICS
from modules.shared.services.audit_trail import log_event

_scheduler_status = {
    "enabled": True,
    "paused": False,
    "last_pull_at": SCHEDULER_METRICS["last_pull_at"],
    "last_pull_status": SCHEDULER_METRICS["last_pull_status"],
    "pulls_completed": SCHEDULER_METRICS["pulls_completed"],
    "next_scheduled": "Every 6 hours (02:00 / 08:00 / 14:00 / 20:00 IST)",
    "records_last_pull": SCHEDULER_METRICS["records_last_pull"],
    "success_rate_pct": SCHEDULER_METRICS["success_rate_pct"],
    "avg_duration_sec": SCHEDULER_METRICS["avg_duration_sec"],
    "jobs": [
        {
            "source": "SharePoint Evidence Library",
            "framework": "PCI DSS",
            "status": "Synced",
            "last_run": "2026-05-24 06:00 UTC",
            "records": 128,
        },
        {
            "source": "ServiceNow GRC",
            "framework": "DPSC",
            "status": "Synced",
            "last_run": "2026-05-24 06:01 UTC",
            "records": 96,
        },
        {
            "source": "SIEM Export Pipeline",
            "framework": "CSITE",
            "status": "Synced",
            "last_run": "2026-05-24 06:02 UTC",
            "records": 188,
        },
        {
            "source": "CMDB Baselining Agent",
            "framework": "OS Baselining",
            "status": "Ready",
            "last_run": "2026-05-23 20:00 UTC",
            "records": 74,
        },
    ],
}

_execution_history: list[dict] = []
_collection_seq = 0
_run_progress: dict[str, dict] = {}


def get_run_progress(run_id: str) -> dict | None:
    return _run_progress.get(run_id)


_SUMMARY_INT_KEYS = (
    "files_discovered",
    "new_evidence",
    "duplicates_skipped",
    "failures",
    "postgresql_count",
    "object_storage_count",
    "pgvector_count",
    "sources_executed",
    "versions_created",
    "connector_ingested",
)

_TERMINAL_RUN_STATUSES = frozenset({"success", "completed", "partial", "failed"})


def _normalize_run_id(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _coerce_run_summary(raw, *, run_id: str = "", applications=None, frameworks=None) -> dict:
    """Ensure summary is a dict with required numeric fields (never a list/None)."""
    base = raw if isinstance(raw, dict) else {}
    apps = base.get("selected_applications")
    if not isinstance(apps, list):
        apps = base.get("applications")
    if not isinstance(apps, list):
        apps = list(applications or [])
    fws = base.get("selected_frameworks")
    if not isinstance(fws, list):
        fws = base.get("frameworks")
    if not isinstance(fws, list):
        fws = list(frameworks or [])
    rid = _normalize_run_id(base.get("run_id") or run_id)
    out = {
        "run_id": rid,
        "selected_applications": [str(a) for a in apps],
        "selected_frameworks": [str(f) for f in fws],
        "applications": [str(a) for a in apps],
        "frameworks": [str(f) for f in fws],
    }
    for key in _SUMMARY_INT_KEYS:
        try:
            out[key] = int(base.get(key, 0) or 0)
        except (TypeError, ValueError):
            out[key] = 0
    for key in (
        "source_breakdown",
        "source_totals",
        "pgvector_detail",
        "pq_zero_reason",
        "collection_mode",
        "environment_flags",
    ):
        if key in base:
            out[key] = base[key]
    return out


def _summary_is_complete(summary) -> bool:
    """True when summary is a real completion object (not missing/list/empty placeholder)."""
    if not isinstance(summary, dict) or not summary:
        return False
    if not _normalize_run_id(summary.get("run_id")):
        return False
    # Placeholder {} / pre-start summaries lack selection keys that the builder always sets.
    if "selected_applications" not in summary and "applications" not in summary:
        return False
    required = (
        "files_discovered",
        "new_evidence",
        "duplicates_skipped",
        "failures",
        "postgresql_count",
        "object_storage_count",
        "pgvector_count",
    )
    return all(key in summary for key in required)


def get_run_status(run_id: str) -> dict | None:
    """Live or completed run status for polling clients."""
    rid = _normalize_run_id(run_id)
    live = _run_progress.get(rid) or _run_progress.get(run_id)
    if live:
        raw_status = live.get("status")
        # Never invent "completed" when status is missing/undefined.
        status = str(raw_status).strip().lower() if raw_status not in (None, "") else "running"
        raw_summary = live.get("summary")
        summary = (
            _coerce_run_summary(raw_summary, run_id=rid)
            if isinstance(raw_summary, dict) and raw_summary
            else {}
        )
        # Terminal success/partial require a real summary; failed may omit counters.
        if status in {"success", "completed", "partial"} and not _summary_is_complete(summary):
            status = "running"
        return {
            "ok": True,
            "run_id": rid,
            "status": status,
            "progress_events": live.get("progress_events") or live.get("progress") or [],
            "summary": summary if _summary_is_complete(summary) or status == "failed" else {},
            "active_step": live.get("active_step") or "",
            "error": live.get("error"),
        }
    for hist in _execution_history:
        if _normalize_run_id(hist.get("run_id")) == rid:
            raw_status = hist.get("status")
            status = str(raw_status).strip().lower() if raw_status not in (None, "") else ""
            if not status:
                # History rows without an explicit status are not treated as completed.
                status = "running"
            raw_summary = hist.get("summary")
            summary = (
                _coerce_run_summary(raw_summary, run_id=rid)
                if isinstance(raw_summary, dict) and raw_summary
                else {}
            )
            if status in {"success", "completed", "partial"} and not _summary_is_complete(summary):
                status = "running"
            return {
                "ok": True,
                "run_id": rid,
                "status": status,
                "progress_events": hist.get("progress_events") or [],
                "summary": summary if _summary_is_complete(summary) or status == "failed" else {},
                "active_step": "",
                "error": hist.get("error"),
            }
    return None


def _publish_run_progress(
    run_id: str,
    progress,
    *,
    status: str = "running",
    summary: dict | None = None,
    active_step: str = "",
    error: str = "",
) -> None:
    if isinstance(progress, list):
        events = progress
        active = active_step
    elif hasattr(progress, "to_list"):
        events = progress.to_list()
        active = active_step or progress.active_step()
    else:
        events = []
        active = active_step
    payload = {
        "run_id": run_id,
        "status": status,
        "progress_events": events,
        "summary": summary if summary is not None else (_run_progress.get(run_id, {}).get("summary") or {}),
        "active_step": active,
    }
    if error:
        payload["error"] = error
    _run_progress[run_id] = payload


def start_scheduler_collection_async(
    *,
    user: str = "System",
    applications=None,
    frameworks=None,
    connector_transport=None,
) -> dict:
    """Start a collection run in the background and return run_id immediately."""
    global _collection_seq
    started_utc = datetime.now(timezone.utc)
    _collection_seq += 1
    run_id = f"COLL-{started_utc.strftime('%Y%m%d-%H%M%S')}-{_collection_seq:03d}"
    _run_progress[run_id] = {
        "run_id": run_id,
        "status": "running",
        "progress_events": [],
        "summary": {},
        "active_step": "plan built",
    }

    def _worker() -> None:
        try:
            run_scheduler_collection(
                user=user,
                applications=applications,
                frameworks=frameworks,
                connector_transport=connector_transport,
                run_id=run_id,
            )
        except Exception as exc:  # noqa: BLE001
            _run_progress[run_id] = {
                "run_id": run_id,
                "status": "failed",
                "progress_events": _run_progress.get(run_id, {}).get("progress_events") or [],
                "summary": _run_progress.get(run_id, {}).get("summary") or {},
                "error": str(exc),
            }

    threading.Thread(target=_worker, daemon=True).start()
    return {"ok": True, "run_id": run_id, "status": "running"}


def _merge_run_summary(*parts: dict) -> dict:
    totals = {
        "files_discovered": 0,
        "new_evidence": 0,
        "duplicates_skipped": 0,
        "versions_created": 0,
        "failures": 0,
        "postgresql_count": 0,
        "object_storage_count": 0,
        "pgvector_count": 0,
        "sources_executed": 0,
        "connector_ingested": 0,
    }
    for block in parts:
        if not isinstance(block, dict):
            continue
        for key in totals:
            totals[key] += int(block.get(key, 0) or 0)
    return totals


def _classify_pgvector_status(search_index: dict | None) -> dict[str, str]:
    """Map repository search_index payload to indexed/queued/skipped/failed/unavailable."""
    idx = dict(search_index or {})
    if idx.get("indexed"):
        return {"status": "indexed", "reason": str(idx.get("reason") or "ok")}
    reason = str(idx.get("reason") or idx.get("errors", [""])[0] if idx.get("errors") else "not_indexed")
    if reason in {"provider_not_configured", "provider_unavailable"}:
        return {"status": "provider_unavailable", "reason": reason}
    if reason in {"duplicate_content", "superseded", "empty_text", "artifact_missing", "mirror_failed", "missing_hash"}:
        return {"status": "skipped", "reason": reason}
    if reason in {"index_failed"} or idx.get("errors"):
        return {"status": "failed", "reason": reason}
    if reason in {"queued", "index_queued"}:
        return {"status": "queued", "reason": reason}
    return {"status": "skipped", "reason": reason}


def _normalize_source_type(*, source_connector: str = "", meta: dict | None = None) -> str:
    meta = dict(meta or {})
    raw = str(meta.get("source_type") or source_connector or meta.get("collection_source") or "").strip()
    aliases = {
        "PREDEFINED_QUERY": "predefined_query",
        "predefined_query": "predefined_query",
        "common_control": "common_controls",
        "CommonControls": "common_controls",
        "mock_evidence": "mock_evidence",
        "sharepoint": "sharepoint_graph",
        "connector": str(source_connector or "connector"),
    }
    if raw in aliases:
        return aliases[raw]
    if raw.lower() in {"predefined_query", "mock_evidence", "common_controls", "sharepoint_graph"}:
        return raw.lower()
    return raw or "unknown"


def _source_row(
    source: str,
    *,
    planned: int = 0,
    executed: int = 0,
    discovered: int = 0,
    persisted: int = 0,
    duplicates: int = 0,
    failed: int = 0,
    metadata_count: int = 0,
    object_storage_count: int = 0,
    pgvector_indexed: int = 0,
    pgvector_queued: int = 0,
    pgvector_skipped: int = 0,
    pgvector_failed: int = 0,
    pgvector_unavailable: int = 0,
    status: str = "",
    skip_reason: str = "",
    **extra,
) -> dict:
    row = {
        "source": source,
        "planned": int(planned or 0),
        "executed": int(executed or 0),
        "discovered": int(discovered or 0),
        "persisted": int(persisted or 0),
        "duplicates": int(duplicates or 0),
        "failed": int(failed or 0),
        "metadata_count": int(metadata_count or 0),
        "object_storage_count": int(object_storage_count or 0),
        "pgvector_indexed": int(pgvector_indexed or 0),
        "pgvector_queued": int(pgvector_queued or 0),
        "pgvector_skipped": int(pgvector_skipped or 0),
        "pgvector_failed": int(pgvector_failed or 0),
        "pgvector_provider_unavailable": int(pgvector_unavailable or 0),
        "status": status or ("completed" if persisted else ("skipped" if skip_reason else "empty")),
        "skip_reason": skip_reason,
        "failure_reason": skip_reason if status == "failed" else "",
    }
    row.update(extra)
    return row


def _aggregate_pgvector_counts(rows: list[dict]) -> dict:
    totals = {
        "indexed": 0,
        "queued": 0,
        "skipped": 0,
        "failed": 0,
        "provider_unavailable": 0,
    }
    for row in rows:
        totals["indexed"] += int(row.get("pgvector_indexed", 0) or 0)
        totals["queued"] += int(row.get("pgvector_queued", 0) or 0)
        totals["skipped"] += int(row.get("pgvector_skipped", 0) or 0)
        totals["failed"] += int(row.get("pgvector_failed", 0) or 0)
        totals["provider_unavailable"] += int(row.get("pgvector_provider_unavailable", 0) or 0)
    if not any(totals.values()):
        totals["status"] = "provider_unavailable"
        totals["reason"] = "No embeddings indexed — PGVector provider not configured or indexing skipped"
    else:
        totals["status"] = "indexed" if totals["indexed"] else "skipped"
        totals["reason"] = ""
    return totals


def _pq_zero_reason(pq_result: dict) -> str:
    if not isinstance(pq_result, dict):
        return "predefined_query_collection_failed"
    if pq_result.get("enabled") is False:
        return str(pq_result.get("skip_reason") or "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED=false")
    if int(pq_result.get("persisted", 0) or 0) > 0:
        return ""
    if pq_result.get("error"):
        return str(pq_result["error"])
    reasons: list[str] = []
    for row in pq_result.get("results") or []:
        if row.get("evidence_persisted"):
            continue
        if row.get("skip_reason"):
            reasons.append(str(row["skip_reason"]))
        elif row.get("error_type"):
            reasons.append(str(row["error_type"]))
        elif row.get("error"):
            reasons.append(str(row["error"]))
    if reasons:
        return "; ".join(dict.fromkeys(reasons))
    if not pq_result.get("controls"):
        return "no_matching_queries"
    return "execution_did_not_persist"


def _diagnose_predefined_query(control_id: str) -> dict:
    from modules.operations.engines.predefined_queries_engine import (
        assess_execution_capability,
        get_control_by_id,
        is_live_execution_enabled,
    )

    control = get_control_by_id(control_id)
    if not control:
        return {"executable": False, "skip_reason": "missing_control", "detail": "Control not found"}
    capability = assess_execution_capability(control)
    if not is_live_execution_enabled(control):
        return {
            "executable": False,
            "skip_reason": capability.get("status", "unsupported_control"),
            "detail": capability.get("reason") or "Live execution is not enabled for this control",
            "error_type": "unsupported_control",
        }
    return {"executable": True, "skip_reason": "", "detail": capability.get("reason", "")}


def _pgvector_counts_from_receipts(receipts: list[dict]) -> dict[str, int]:
    counts = {"indexed": 0, "queued": 0, "skipped": 0, "failed": 0, "provider_unavailable": 0}
    for receipt in receipts:
        idx = receipt.get("search_index") if isinstance(receipt.get("search_index"), dict) else {}
        if not idx and receipt.get("evidence_id"):
            try:
                from modules.operations.engines import evidence_repository as ops_repo

                rec = next((r for r in ops_repo.evidence_repository if r.get("evidence_id") == receipt["evidence_id"]), None)
                idx = (rec or {}).get("search_index") or {}
            except Exception:  # noqa: BLE001
                idx = {}
        bucket = _classify_pgvector_status(idx)
        key = bucket["status"]
        if key == "provider_unavailable":
            counts["provider_unavailable"] += 1
        elif key in counts:
            counts[key] += 1
        else:
            counts["skipped"] += 1
    return counts


def build_connector_source_summary(
    *,
    planned_jobs: int,
    live: bool,
    mode: str,
    job_results: list[dict],
) -> dict:
    connector_jobs = [r for r in job_results if isinstance(r, dict)]
    if not live:
        reason = f"{mode}: ECS_CONNECTOR_EXECUTION_ENABLED is not set and no transport injected"
        return _source_row(
            "connectors",
            planned=planned_jobs,
            status="skipped",
            skip_reason=reason,
            connector_ids=sorted({str(r.get("connector") or "") for r in connector_jobs if r.get("connector")}),
        )
    discovered = sum(int(r.get("objects_fetched", 0) or 0) for r in connector_jobs)
    persisted = sum(int(r.get("ingested", 0) or 0) for r in connector_jobs)
    failed = sum(1 for r in connector_jobs if r.get("ok") is False or int(r.get("ingested", 0) or 0) == 0)
    receipts: list[dict] = []
    for row in connector_jobs:
        receipts.extend(row.get("receipts") or [])
    pg = _pgvector_counts_from_receipts(receipts)
    skip = ""
    status = "completed"
    if planned_jobs and not persisted and failed:
        status = "failed"
        skip = "; ".join(
            dict.fromkeys(
                str(r.get("reason") or r.get("status") or "connector_run_failed")
                for r in connector_jobs
                if int(r.get("ingested", 0) or 0) == 0
            )
        )
    elif planned_jobs and not persisted:
        status = "empty"
        skip = "connectors ran but persisted zero evidence"
    return _source_row(
        "connectors",
        planned=planned_jobs,
        executed=len(connector_jobs),
        discovered=discovered,
        persisted=persisted,
        failed=failed,
        metadata_count=persisted,
        object_storage_count=persisted,
        pgvector_indexed=pg["indexed"],
        pgvector_queued=pg["queued"],
        pgvector_skipped=pg["skipped"],
        pgvector_failed=pg["failed"],
        pgvector_unavailable=pg["provider_unavailable"],
        status=status,
        skip_reason=skip,
        connector_ids=sorted({str(r.get("connector") or "") for r in connector_jobs if r.get("connector")}),
    )


def build_mock_source_summary(*, mock_summary: dict, enabled: bool, demo_mode: bool) -> dict:
    if not demo_mode:
        return _source_row(
            "mock_evidence",
            status="skipped",
            skip_reason="DEMO_MODE=false — mock evidence path disabled",
        )
    if not enabled:
        return _source_row(
            "mock_evidence",
            status="skipped",
            skip_reason="ECS_MOCK_EVIDENCE_COLLECTION_ENABLED=false",
        )
    if not mock_summary:
        return _source_row("mock_evidence", status="skipped", skip_reason="no mock folders matched selection")
    pg = _pgvector_counts_from_receipts(mock_summary.get("receipts") or [])
    return _source_row(
        "mock_evidence",
        planned=int(mock_summary.get("files_discovered", 0) or 0),
        executed=int(mock_summary.get("sources_executed", 0) or 0),
        discovered=int(mock_summary.get("files_discovered", 0) or 0),
        persisted=int(mock_summary.get("new_evidence", 0) or 0),
        duplicates=int(mock_summary.get("duplicates_skipped", 0) or 0),
        failed=int(mock_summary.get("failures", 0) or 0),
        metadata_count=int(mock_summary.get("postgresql_count", 0) or 0),
        object_storage_count=int(mock_summary.get("object_storage_count", 0) or 0),
        pgvector_indexed=pg["indexed"] or int(mock_summary.get("pgvector_count", 0) or 0),
        pgvector_queued=pg["queued"],
        pgvector_skipped=pg["skipped"],
        pgvector_failed=pg["failed"],
        pgvector_unavailable=pg["provider_unavailable"],
        status="completed" if int(mock_summary.get("new_evidence", 0) or 0) else "empty",
        skip_reason="" if int(mock_summary.get("new_evidence", 0) or 0) else "mock folders discovered but nothing persisted",
    )


def build_common_controls_source_summary(*, cc_result: dict, enabled: bool) -> dict:
    if not enabled:
        return _source_row(
            "common_controls",
            status="skipped",
            skip_reason="ECS_COMMON_CONTROLS_COLLECTION_ENABLED=false",
        )
    if cc_result.get("error"):
        return _source_row(
            "common_controls",
            status="failed",
            skip_reason=str(cc_result["error"]),
        )
    pg = _pgvector_counts_from_receipts(cc_result.get("receipts") or [])
    persisted = int(cc_result.get("collected", cc_result.get("new_evidence", 0)) or 0)
    return _source_row(
        "common_controls",
        planned=int(cc_result.get("folders_discovered", cc_result.get("files_discovered", 0)) or 0),
        executed=int(cc_result.get("folders_discovered", 0) or 0),
        discovered=int(cc_result.get("folders_discovered", cc_result.get("files_discovered", 0)) or 0),
        persisted=persisted,
        failed=int(cc_result.get("failures", 0) or 0),
        metadata_count=int(cc_result.get("postgresql_count", 0) or 0),
        object_storage_count=int(cc_result.get("object_storage_count", 0) or 0),
        pgvector_indexed=pg["indexed"],
        pgvector_queued=pg["queued"],
        pgvector_skipped=pg["skipped"],
        pgvector_failed=pg["failed"],
        pgvector_unavailable=pg["provider_unavailable"],
        status="completed" if persisted else "empty",
    )


def build_predefined_query_source_summary(*, pq_result: dict, enabled: bool) -> dict:
    if not enabled:
        return _source_row(
            "predefined_query",
            status="skipped",
            skip_reason=str(pq_result.get("skip_reason") or "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED=false"),
            persist_flag=False,
        )
    controls = pq_result.get("controls") or []
    results = pq_result.get("results") or []
    executed = sum(1 for row in results if row.get("ok") is not False or row.get("error_type"))
    persisted = int(pq_result.get("persisted", 0) or 0)
    duplicates = sum(1 for row in results if row.get("duplicate"))
    failed = int(pq_result.get("failures", 0) or 0)
    pg = {"indexed": 0, "queued": 0, "skipped": 0, "failed": 0, "provider_unavailable": 0}
    for row in results:
        upload = row.get("upload") if isinstance(row.get("upload"), dict) else {}
        idx = upload.get("search_index") if isinstance(upload.get("search_index"), dict) else {}
        if idx.get("indexed"):
            pg["indexed"] += 1
        elif upload.get("evidence_id"):
            bucket = _classify_pgvector_status(idx)
            key = bucket["status"]
            if key == "provider_unavailable":
                pg["provider_unavailable"] += 1
            elif key in pg:
                pg[key] += 1
    skip = _pq_zero_reason(pq_result) if persisted == 0 else ""
    status = "completed" if persisted else ("skipped" if skip else "empty")
    return _source_row(
        "predefined_query",
        planned=len(controls),
        executed=max(executed, len(results)),
        discovered=len(controls),
        persisted=persisted,
        duplicates=duplicates,
        failed=failed,
        metadata_count=int(pq_result.get("postgresql_count", 0) or 0),
        object_storage_count=int(pq_result.get("object_storage_count", 0) or 0),
        pgvector_indexed=pg["indexed"] or int(pq_result.get("pgvector_count", 0) or 0),
        pgvector_queued=pg["queued"],
        pgvector_skipped=pg["skipped"],
        pgvector_failed=pg["failed"],
        pgvector_unavailable=pg["provider_unavailable"],
        status=status,
        skip_reason=skip,
        persist_flag=bool(pq_result.get("persist_flag", True)),
        control_ids=controls,
        demo_mode=bool(pq_result.get("demo_mode")),
        environment_flags=pq_result.get("environment_flags") or {},
    )


def build_sharepoint_source_summary(*, sp_result: dict, enabled: bool) -> dict:
    if not enabled:
        return _source_row(
            "sharepoint_graph",
            status="skipped",
            skip_reason=str(sp_result.get("skip_reason") or "ECS_SHAREPOINT_ENABLED=false"),
            sharepoint_mode=sp_result.get("sharepoint_mode", ""),
        )
    if sp_result.get("error") or sp_result.get("status") == "failed":
        return _source_row(
            "sharepoint_graph",
            status="failed",
            skip_reason=str(sp_result.get("skip_reason") or sp_result.get("error") or "sharepoint_failed"),
            sharepoint_mode=sp_result.get("sharepoint_mode", ""),
            failed=int(sp_result.get("failed", 1) or 1),
        )
    pg = _pgvector_counts_from_receipts(sp_result.get("receipts") or [])
    persisted = int(sp_result.get("ingested", 0) or 0)
    return _source_row(
        "sharepoint_graph",
        planned=int(sp_result.get("discovered", 0) or 0),
        executed=1,
        discovered=int(sp_result.get("discovered", 0) or 0),
        persisted=persisted,
        duplicates=int(sp_result.get("duplicates", 0) or 0),
        failed=int(sp_result.get("failed", 0) or 0),
        metadata_count=int(sp_result.get("postgresql_count", persisted) or 0),
        object_storage_count=int(sp_result.get("object_storage_count", 0) or 0),
        pgvector_indexed=pg["indexed"] or int(sp_result.get("pgvector_count", 0) or 0),
        pgvector_queued=pg["queued"],
        pgvector_skipped=pg["skipped"],
        pgvector_failed=pg["failed"],
        pgvector_unavailable=pg["provider_unavailable"],
        status="completed" if persisted else ("skipped" if sp_result.get("skip_reason") else "empty"),
        skip_reason=str(sp_result.get("skip_reason") or ""),
        sharepoint_mode=sp_result.get("sharepoint_mode", ""),
        downloaded=int(sp_result.get("downloaded", 0) or 0),
    )


def build_run_source_breakdown(
    *,
    connector_summary: dict,
    mock_summary: dict,
    cc_result: dict,
    pq_result: dict,
    sp_result: dict,
    mock_enabled: bool,
    cc_enabled: bool,
    pq_enabled: bool,
    sp_enabled: bool,
    demo_mode: bool,
) -> tuple[list[dict], dict, str]:
    rows = [
        build_predefined_query_source_summary(pq_result=pq_result, enabled=pq_enabled),
        build_sharepoint_source_summary(sp_result=sp_result, enabled=sp_enabled),
        connector_summary,
        build_common_controls_source_summary(cc_result=cc_result, enabled=cc_enabled),
        build_mock_source_summary(mock_summary=mock_summary, enabled=mock_enabled, demo_mode=demo_mode),
    ]
    totals = {
        "planned": sum(r["planned"] for r in rows),
        "executed": sum(r["executed"] for r in rows),
        "discovered": sum(r["discovered"] for r in rows),
        "persisted": sum(r["persisted"] for r in rows),
        "duplicates": sum(r["duplicates"] for r in rows),
        "failed": sum(r["failed"] for r in rows),
        "metadata_count": sum(r["metadata_count"] for r in rows),
        "object_storage_count": sum(r["object_storage_count"] for r in rows),
    }
    totals["pgvector_detail"] = _aggregate_pgvector_counts(rows)
    pq_zero = _pq_zero_reason(pq_result if pq_enabled else {"enabled": False, "skip_reason": pq_result.get("skip_reason", "")})
    return rows, totals, pq_zero


def get_scheduler_selection_catalog(role: str = "") -> dict[str, list[str]]:
    """Canonical, deduplicated application/framework options for scheduler UI (RBAC-scoped)."""
    from modules.operations.engines.scheduler_intelligence import APPLICATIONS, FRAMEWORKS
    from modules.shared.services.role_filter_scope import ROLE_FRAMEWORKS, apps_for_role, normalize_role

    apps: list[str] = list(APPLICATIONS)
    for label in SCHEDULER_APPLICATION_MAP:
        display = label.title() if label.islower() and " " in label else label
        if display not in apps:
            apps.append(display)
    seen: set[str] = set()
    deduped_apps: list[str] = []
    for app in apps:
        key = _norm_scheduler_key(app)
        if key and key not in seen:
            seen.add(key)
            deduped_apps.append(app)
    role_key = normalize_role(role) if role else ""
    allowed_apps = apps_for_role(role_key) if role_key else None
    if allowed_apps is not None:
        deduped_apps = [
            app for app in deduped_apps
            if app in allowed_apps or any(part in app for part in allowed_apps)
        ]
    frameworks = list(FRAMEWORKS)
    allowed_fws = ROLE_FRAMEWORKS.get(role_key) if role_key else None
    if allowed_fws is not None:
        frameworks = [fw for fw in frameworks if fw in allowed_fws]
    return {"applications": deduped_apps, "frameworks": frameworks}


def _enrich_fetched_evidence_row(
    *,
    evidence_id: str,
    collected_at: str,
    source_connector: str,
    meta: dict,
    filename: str,
    application: str,
    environment: str,
    framework: str,
    control: str,
    run_id: str,
    workflow_status: str,
    sha256: str,
    version: int,
    duplicate: bool,
    object_key: str,
    search_index: dict | None,
    artifact_type: str = "json",
) -> dict:
    source_type = _normalize_source_type(source_connector=source_connector, meta=meta)
    pg = _classify_pgvector_status(search_index)
    query_or_connector = str(
        meta.get("query_id") or meta.get("connector_id") or source_connector or meta.get("common_control_slug") or ""
    )
    return {
        "evidence_id": evidence_id,
        "collected_at": collected_at,
        "source": source_connector or source_type,
        "source_type": source_type,
        "source_name": str(meta.get("source_name") or meta.get("collection_source") or source_type),
        "evidence_name": filename or evidence_id,
        "application": application,
        "environment": environment,
        "framework": framework,
        "control": control,
        "framework_control": " / ".join(x for x in (framework, control) if x),
        "query_id": str(meta.get("query_id") or ""),
        "connector_id": str(meta.get("connector_id") or source_connector or ""),
        "query_or_connector": query_or_connector,
        "run_id": run_id,
        "status": workflow_status,
        "workflow_status": workflow_status,
        "metadata_status": "persisted" if evidence_id else "missing",
        "object_ref": object_key,
        "object_key": object_key,
        "artifact_type": str(meta.get("artifact_type") or artifact_type),
        "sha256": sha256,
        "duplicate_state": "duplicate" if duplicate else "accepted",
        "version": version,
        "pgvector_status": pg["status"],
        "pgvector_reason": pg["reason"],
        "custody_mode": str(meta.get("custody_mode") or ""),
        "view_url": f"/mvp/scheduler/fetched-evidence/view?evidence_id={evidence_id}",
        "download_url": f"/mvp/scheduler/fetched-evidence/view?evidence_id={evidence_id}&raw=true",
    }


def _artifact_row(art) -> dict:
    meta = dict(getattr(art, "metadata", ()) or ())
    source = str(getattr(art, "source", "") or "")
    source_connector = str(getattr(art, "source_connector", "") or "")
    framework = ", ".join(getattr(art, "frameworks", ()) or ())
    control = str(getattr(art, "control_id", "") or "")
    evidence_id = str(getattr(art, "evidence_id", "") or "")
    run_id = _normalize_run_id(meta.get("scheduler_run_id") or meta.get("run_id") or "")
    duplicate = bool(meta.get("duplicate")) or str(meta.get("duplicate_state", "")).lower() == "duplicate"
    search_index: dict = {}
    workflow_status = str(meta.get("workflow_status") or meta.get("validation_verdict") or "Collected")
    try:
        from modules.operations.engines import evidence_repository as ops_repo

        ops = next((r for r in ops_repo.evidence_repository if r.get("evidence_id") == evidence_id), None)
        if ops:
            run_id = run_id or _normalize_run_id((ops.get("metadata") or {}).get("scheduler_run_id") or "")
            search_index = dict(ops.get("search_index") or {})
            duplicate = duplicate or str(ops.get("status", "")).upper() == "DUPLICATE"
            workflow_status = str(
                (ops.get("metadata") or {}).get("workflow_status") or ops.get("status") or workflow_status
            )
            meta = {**meta, **dict(ops.get("metadata") or {})}
            source_connector = source_connector or str(ops.get("source_connector") or "")
    except Exception:  # noqa: BLE001
        pass
    return _enrich_fetched_evidence_row(
        evidence_id=evidence_id,
        collected_at=str(getattr(art, "collected_at", "") or ""),
        source_connector=source_connector or str(meta.get("source", "") or source),
        meta=meta,
        filename=str(getattr(art, "filename", "") or evidence_id),
        application=str(getattr(art, "asset_id", "") or meta.get("application") or ""),
        environment=str(getattr(art, "environment", "") or meta.get("environment") or ""),
        framework=framework,
        control=control,
        run_id=run_id,
        workflow_status=workflow_status,
        sha256=str(getattr(art, "content_hash", "") or meta.get("content_sha256") or ""),
        version=int(getattr(art, "version", 1) or 1),
        duplicate=duplicate,
        object_key=str(meta.get("object_key") or getattr(art, "object_uri", "") or ""),
        search_index=search_index,
        artifact_type=str(meta.get("artifact_type") or getattr(art, "mime_type", "") or "json"),
    )


_SCHEDULER_SOURCES = frozenset({
    "manual_upload",
    "connector_executor",
    "asset_scheduler",
    "common_controls",
    "mock_evidence",
    "predefined_query",
    "PREDEFINED_QUERY",
})
_SCHEDULER_CONNECTORS = frozenset({
    "mock_evidence",
    "common_controls",
    "PREDEFINED_QUERY",
    "predefined_query",
    "sharepoint_graph",
    "sharepoint",
    "connector",
})
_SCHEDULER_COLLECTION_SOURCES = frozenset({
    "mock_evidence",
    "CommonControls",
    "PREDEFINED_QUERY",
    "predefined_query",
    "connector",
})


def _is_scheduler_sourced(*, source: str, connector_name: str, meta: dict) -> bool:
    if source in _SCHEDULER_SOURCES:
        if source == "manual_upload":
            return bool(
                connector_name in _SCHEDULER_CONNECTORS
                or meta.get("collection_source") in _SCHEDULER_COLLECTION_SOURCES
                or meta.get("source_type") in _SCHEDULER_COLLECTION_SOURCES
                or _normalize_run_id(meta.get("scheduler_run_id") or "")
            )
        return True
    if connector_name in _SCHEDULER_CONNECTORS:
        return True
    if meta.get("collection_source") in _SCHEDULER_COLLECTION_SOURCES:
        return True
    if meta.get("source_type") in _SCHEDULER_COLLECTION_SOURCES:
        return True
    return bool(_normalize_run_id(meta.get("scheduler_run_id") or ""))


def _scheduler_fetched_evidence(limit: int = 200, *, run_id: str = "") -> list[dict]:
    """Latest persisted evidence collected by scheduler runs across all sources."""
    want = _normalize_run_id(run_id)
    artifacts = []
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        artifacts = get_persistence().list_all_evidence_versions()
    except Exception:  # noqa: BLE001
        artifacts = []
    if not artifacts:
        try:
            from modules.audit_intelligence.engines import evidence_repository as ai_repo

            artifacts = ai_repo.all_artifacts()
        except Exception:  # noqa: BLE001
            artifacts = []

    rows: list[dict] = []
    for art in artifacts:
        source = str(getattr(art, "source", "") or "")
        source_connector = str(getattr(art, "source_connector", "") or "")
        if source == "llm_usecase_demo":
            continue
        if str(getattr(art, "evidence_id", "")).startswith("EV-DEMO-") or str(getattr(art, "evidence_id", "")) == "EV-LLM-ENC-001":
            continue
        meta = dict(getattr(art, "metadata", ()) or {})
        if str(meta.get("demo", "")).strip().lower() == "llm_usecase":
            continue
        connector_name = source_connector or str(meta.get("source", "") or "")
        if not _is_scheduler_sourced(source=source, connector_name=connector_name, meta=meta):
            continue
        row = _artifact_row(art)
        if not row.get("evidence_id"):
            continue
        if want and _normalize_run_id(row.get("run_id")) != want:
            continue
        rows.append(row)
    rows.sort(key=lambda r: r.get("collected_at", ""), reverse=True)
    seen = {r.get("evidence_id") for r in rows}
    try:
        from modules.operations.engines import evidence_repository as ops_repo

        for rec in ops_repo.evidence_repository:
            meta = dict(rec.get("metadata") or {})
            eid = str(rec.get("evidence_id") or "")
            if not eid or eid in seen:
                continue
            rid = _normalize_run_id(meta.get("scheduler_run_id") or "")
            src = str(rec.get("source_connector") or meta.get("collection_source") or meta.get("source_type") or "")
            if not _is_scheduler_sourced(source="manual_upload", connector_name=src, meta=meta):
                continue
            if want and rid != want:
                continue
            rows.append(
                _enrich_fetched_evidence_row(
                    evidence_id=eid,
                    collected_at=str(rec.get("uploaded_at") or ""),
                    source_connector=src or "scheduler",
                    meta=meta,
                    filename=str(rec.get("filename") or eid),
                    application=str((rec.get("application_tags") or [""])[0]),
                    environment=str(meta.get("environment") or rec.get("environment") or ""),
                    framework=str((rec.get("framework_tags") or [""])[0]),
                    control=str(rec.get("control") or ""),
                    run_id=rid,
                    workflow_status=str((meta.get("workflow_status") or rec.get("status") or "Uploaded")),
                    sha256=str(rec.get("sha256") or ""),
                    version=int(rec.get("version") or 1),
                    duplicate=str(rec.get("status", "")).upper() == "DUPLICATE",
                    object_key=str(meta.get("object_key") or rec.get("object_uri") or ""),
                    search_index=dict(rec.get("search_index") or {}),
                    artifact_type=str(meta.get("artifact_type") or rec.get("mime_type") or "json"),
                )
            )
            seen.add(eid)
    except Exception:  # noqa: BLE001
        pass
    rows.sort(key=lambda r: r.get("collected_at", ""), reverse=True)
    return rows[: max(0, int(limit or 0))]


def _repository_count():
    from modules.operations.engines.evidence_repository import evidence_repository

    return len(evidence_repository)


def get_scheduler_dashboard(*, run_id: str = ""):
    rows = []
    for row in ecs_state.scheduler_data:
        rows.append(
            {
                "application": row[0],
                "framework": row[1],
                "status": row[2],
                "owner": row[3] if len(row) > 3 else "—",
                "last_sync": row[4] if len(row) > 4 else "—",
            }
        )
    latest = _execution_history[0] if _execution_history else {}
    return {
        "status": _scheduler_status.copy(),
        "scheduler_rows": rows,
        "scheduler_data": ecs_state.scheduler_data,
        "repository_count": max(_repository_count(), SCHEDULER_METRICS["records_last_pull"] // 3),
        "execution_history": _execution_history,
        "fetched_evidence": _scheduler_fetched_evidence(run_id=run_id),
        "latest_run_id": latest.get("run_id", ""),
        "latest_run_summary": latest.get("summary", {}),
        "selection_catalog": get_scheduler_selection_catalog(),
    }


def run_scheduled_pull(user: str = "System") -> dict:
    from modules.operations.engines.evidence_repository import refresh_repository_from_frameworks

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    added = refresh_repository_from_frameworks(source="scheduler")
    observations_scanned = 18 + (added % 6)
    new_findings = max(1, added // 3)
    _scheduler_status["last_pull_at"] = now
    _scheduler_status["last_pull_status"] = "Success"
    _scheduler_status["pulls_completed"] += 1
    _scheduler_status["records_last_pull"] = 412 + (added * 3)
    run_id = f"RUN-{now.replace(' ', '-').replace(':', '')[:15]}"
    _execution_history.insert(
        0,
        {
            "run_id": run_id,
            "timestamp": now,
            "status": "Success",
            "records": _scheduler_status["records_last_pull"],
            "duration_sec": 40,
            "triggered_by": f"Manual ({user})" if user != "System" else "Manual",
            "observations_scanned": observations_scanned,
            "new_findings": new_findings,
        },
    )
    for job in _scheduler_status["jobs"]:
        job["status"] = "Synced"
        job["last_run"] = now
    for i, row in enumerate(ecs_state.scheduler_data):
        app, fw, status, owner, _ = row[:5]
        ecs_state.scheduler_data[i] = (app, fw, "Implemented", owner, now)
    log_event(
        "Scheduled Pull",
        user or "ECS Scheduler",
        "",
        "",
        f"Scanned {observations_scanned} observations; {new_findings} new findings; {added} artefacts added",
    )
    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler("Evidence sync completed", f"{observations_scanned} observations; {new_findings} findings; {added} artefacts", user=user)
    except Exception:
        pass
    return {
        "timestamp": now,
        "added": added,
        "run_id": run_id,
        "observations_scanned": observations_scanned,
        "new_findings": new_findings,
        "records": _scheduler_status["records_last_pull"],
    }


def retry_failed_observation(failure_id: str, user: str = "System") -> dict:
    """Reprocess a failed scheduler observation — updates failure queue and logs."""
    from modules.operations.engines.scheduler_intelligence import _seed_scheduler_failures

    failures = _seed_scheduler_failures()
    target = next((f for f in failures if f.get("failure_id") == failure_id), None)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if not target:
        return {"ok": False, "message": f"Failure {failure_id} not found.", "status": "Failed"}

    target["retry_status"] = "Retrying"
    target["last_retry_at"] = ts
    target["retry_count"] = target.get("retry_count", 0) + 1
    ecs_state.scheduler_retry_log.insert(0, {
        "failure_id": failure_id,
        "timestamp": ts,
        "actor": user,
        "status": "Retrying",
        "detail": f"Reprocessing {target.get('source', 'integration')} pull",
    })

    import random
    success = random.Random(failure_id + ts).random() > 0.15
    if success:
        target["retry_status"] = "Completed"
        target["resolved_at"] = ts
        if target in ecs_state.scheduler_failures:
            ecs_state.scheduler_failures.remove(target)
        ecs_state.scheduler_retry_log[0]["status"] = "Completed"
        msg = f"Observation reprocessed successfully — {failure_id} removed from failed queue."
        log_event("Scheduler Retry", user, "", failure_id, msg)
    else:
        target["retry_status"] = "Failed Again"
        ecs_state.scheduler_retry_log[0]["status"] = "Failed Again"
        msg = f"Retry failed for {failure_id} — queued for next scheduler window."
        log_event("Scheduler Retry Failed", user, "", failure_id, msg)

    return {"ok": success, "message": msg, "status": target["retry_status"], "failure_id": failure_id}


def pause_scheduler(user: str = "") -> str:
    _scheduler_status["paused"] = True
    log_event("Scheduler Paused", user or "System", "", "", "Non-critical collection jobs paused")
    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler("Scheduler paused", user=user)
    except Exception:
        pass
    return "Scheduler paused — non-critical evidence collection jobs suspended."


def resume_scheduler(user: str = "") -> str:
    _scheduler_status["paused"] = False
    log_event("Scheduler Resumed", user or "System", "", "", "Collection jobs resumed")
    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler("Scheduler resumed", user=user)
    except Exception:
        pass
    return "Scheduler resumed — all collection jobs active."


def is_scheduler_paused() -> bool:
    return bool(_scheduler_status.get("paused"))


def _common_controls_collection_enabled() -> bool:
    return str(os.environ.get("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "true")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _predefined_query_scheduler_enabled() -> bool:
    return str(os.environ.get("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "true")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _mock_evidence_collection_enabled() -> bool:
    return demo_mode_enabled() and str(
        os.environ.get("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "true")
    ).strip().lower() in {"1", "true", "yes", "on"}


def collect_scheduled_predefined_queries(
    *,
    user: str = "scheduler",
    control_ids: list[str] | None = None,
    run_id: str = "",
) -> dict:
    """Run configured predefined queries and persist JSON evidence in one pass."""
    pq_enabled = _predefined_query_scheduler_enabled()
    demo_mode = demo_mode_enabled()
    env_flags = {
        "DEMO_MODE": demo_mode,
        "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED": pq_enabled,
        "ECS_PREDEFINED_QUERY_SCHEDULER_CONTROL": os.environ.get("ECS_PREDEFINED_QUERY_SCHEDULER_CONTROL", "PGX-001"),
    }
    if not pq_enabled:
        return {
            "enabled": False,
            "status": "skipped",
            "skip_reason": "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED=false",
            "persist_flag": False,
            "controls": [],
            "results": [],
            "persisted": 0,
            "discovered": 0,
            "files_discovered": 0,
            "new_evidence": 0,
            "postgresql_count": 0,
            "object_storage_count": 0,
            "pgvector_count": 0,
            "failures": 0,
            "demo_mode": demo_mode,
            "environment_flags": env_flags,
        }

    from modules.operations.engines.predefined_queries_engine import run_predefined_query

    raw = control_ids or [os.environ.get("ECS_PREDEFINED_QUERY_SCHEDULER_CONTROL", "PGX-001")]
    ids = [str(cid).strip() for cid in raw if str(cid).strip()]
    results: list[dict] = []
    discovered = len(ids)
    postgresql_count = 0
    object_storage_count = 0
    pgvector_count = 0
    failures = 0
    from modules.operations.engines.predefined_query_publisher import (
        reset_active_scheduler_run_id,
        set_active_scheduler_run_id,
    )

    run_token = set_active_scheduler_run_id(run_id)
    try:
        for cid in ids:
            diagnosis = _diagnose_predefined_query(cid)
            try:
                outcome = run_predefined_query(cid, user, scheduled=True)
            except Exception as exc:  # noqa: BLE001
                outcome = {
                    "ok": False,
                    "control_id": cid,
                    "error": str(exc),
                    "error_type": "execution_error",
                    "evidence_persisted": False,
                }
                failures += 1
            outcome = dict(outcome or {})
            outcome.setdefault("control_id", cid)
            outcome["persist_flag"] = True
            outcome["scheduled"] = True
            if not diagnosis.get("executable") and not outcome.get("evidence_persisted"):
                outcome.setdefault("error_type", diagnosis.get("error_type", "unsupported_control"))
                outcome.setdefault("error", diagnosis.get("detail"))
                outcome["skip_reason"] = diagnosis.get("skip_reason") or diagnosis.get("detail")
            if outcome.get("evidence_persisted"):
                upload = outcome.get("upload") if isinstance(outcome.get("upload"), dict) else {}
                eid = upload.get("evidence_id") if upload else outcome.get("evidence_id")
                if run_id and eid:
                    try:
                        from modules.operations.engines import evidence_repository as ops_repo

                        rec = next((r for r in ops_repo.evidence_repository if r.get("evidence_id") == eid), None)
                        if rec is not None:
                            meta = dict(rec.get("metadata") or {})
                            meta["scheduler_run_id"] = run_id
                            meta.setdefault("source_type", "predefined_query")
                            meta.setdefault("query_id", cid)
                            rec["metadata"] = meta
                            if upload:
                                upload["metadata"] = meta
                                upload["search_index"] = rec.get("search_index") or {}
                    except Exception:  # noqa: BLE001
                        pass
                postgresql_count += 1
                upload = outcome.get("upload") or {}
                if upload.get("object_uri") or (upload.get("metadata") or {}).get("object_key"):
                    object_storage_count += 1
                idx = upload.get("search_index") or {}
                if idx.get("indexed"):
                    pgvector_count += 1
            elif outcome.get("ok") is False:
                failures += 1
            results.append({"control_id": cid, **outcome})
    finally:
        reset_active_scheduler_run_id(run_token)
    persisted = sum(1 for row in results if row.get("evidence_persisted"))
    return {
        "enabled": True,
        "status": "completed" if persisted else "empty",
        "controls": ids,
        "results": results,
        "persisted": persisted,
        "discovered": discovered,
        "files_discovered": discovered,
        "new_evidence": persisted,
        "postgresql_count": postgresql_count,
        "object_storage_count": object_storage_count,
        "pgvector_count": pgvector_count,
        "failures": failures,
        "persist_flag": True,
        "demo_mode": demo_mode,
        "environment_flags": env_flags,
    }

def _norm_scheduler_key(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


# UI / scheduler-intelligence application labels -> canonical asset keys
# (``application`` field + ``asset_id`` from the asset config). Exact match only.
SCHEDULER_APPLICATION_MAP: dict[str, frozenset[str]] = {
    "net banking": frozenset({"evidence library (mock)", "local-sharepoint-evidence"}),
    "mobile banking": frozenset({"ecs appsec demo", "local-sonarqube"}),
    "payments": frozenset({"change management (mock)", "local-jira-project"}),
    "loan origination": frozenset({"change management (mock)", "local-jira-project"}),
    "internet banking": frozenset({"evidence library (mock)", "local-sharepoint-evidence"}),
    # Pass-through for asset-config application labels (local/UAT YAML).
    "ecs demo": frozenset({
        "ecs demo",
        "local-postgres",
        "local-nginx",
        "local-redis",
        "local-linux-host",
    }),
    "ecs appsec demo": frozenset({"ecs appsec demo", "local-sonarqube"}),
    "evidence library (mock)": frozenset({
        "evidence library (mock)",
        "local-sharepoint-evidence",
    }),
    "change management (mock)": frozenset({
        "change management (mock)",
        "local-jira-project",
    }),
    "cmdb (mock)": frozenset({"cmdb (mock)", "local-servicenow-cmdb"}),
}

# UI framework labels -> canonical framework names on planned jobs (exact, lowercased).
SCHEDULER_FRAMEWORK_ALIASES: dict[str, frozenset[str]] = {
    "pci dss": frozenset({"pci dss"}),
    "pci-dss": frozenset({"pci dss"}),
    "dpsc": frozenset({"dpsc"}),
    "itpp": frozenset({"itpp"}),
    "appsec": frozenset({"appsec"}),
    "csite": frozenset({"csite"}),
    "c-site": frozenset({"csite"}),
    "c site": frozenset({"csite"}),
    "vapt": frozenset({"vapt"}),
    "os baselining": frozenset({"os baselining"}),
    "db baselining": frozenset({"db baselining"}),
}


def _job_canonical_keys(job) -> frozenset[str]:
    keys: set[str] = set()
    for field in ("application", "asset_id"):
        val = _norm_scheduler_key(getattr(job, field, "") or "")
        if val:
            keys.add(val)
    return frozenset(keys)


def normalize_scheduler_applications(applications) -> frozenset[str] | None:
    """Map UI application labels to canonical asset keys.

    Returns ``None`` when the selection is empty (= all jobs). Returns an empty
    set when every selected label is unknown (= zero jobs).
    """
    selected = [_norm_scheduler_key(a) for a in (applications or []) if _norm_scheduler_key(a)]
    if not selected:
        return None
    canonical: set[str] = set()
    unknown_count = 0
    for label in selected:
        mapped = SCHEDULER_APPLICATION_MAP.get(label)
        if mapped is not None:
            canonical.update(mapped)
        else:
            unknown_count += 1
    # Mixed known+unknown UI labels (e.g. enterprise app scans + mapped demo apps)
    # should not over-restrict planning to only the mapped subset.
    if canonical and unknown_count:
        return None
    return frozenset(canonical)


def normalize_scheduler_frameworks(frameworks) -> frozenset[str] | None:
    """Map UI framework labels to canonical framework names on planned jobs."""
    selected = [_norm_scheduler_key(f) for f in (frameworks or []) if _norm_scheduler_key(f)]
    if not selected:
        return None
    canonical: set[str] = set()
    for label in selected:
        mapped = SCHEDULER_FRAMEWORK_ALIASES.get(label)
        if mapped is not None:
            canonical.update(mapped)
    return frozenset(canonical)


def _job_matches_selection(job, applications, frameworks) -> bool:
    """True when a planned job is in scope of the selected apps/frameworks.

    Empty selections mean "all" (no filtering). Unknown labels yield zero jobs.
    Matching is exact on canonical application/asset keys and framework names.
    """
    app_keys = normalize_scheduler_applications(applications)
    if app_keys is not None:
        if not app_keys or not (_job_canonical_keys(job) & app_keys):
            return False
    fw_keys = normalize_scheduler_frameworks(frameworks)
    if fw_keys is not None:
        if not fw_keys:
            return False
        job_fws = {
            _norm_scheduler_key(f)
            for f in (getattr(job, "frameworks", ()) or ())
            if _norm_scheduler_key(f)
        }
        # Connector jobs (e.g. SharePoint/Jira/ServiceNow) carry no predefined
        # framework tags — only baseline/technology jobs do. Don't let framework
        # selection zero out an otherwise-matched connector job for that reason.
        if job_fws and not (job_fws & fw_keys):
            return False
    return True


def run_scheduler_collection(
    *,
    user: str = "System",
    applications=None,
    frameworks=None,
    connector_transport=None,
    run_id: str = "",
) -> dict:
    started_perf = time.perf_counter()
    started_utc = datetime.now(timezone.utc)
    """Run evidence collection via the REAL asset-scheduler / connector-executor.

    Reuses the existing services (no new orchestration, connectors, or
    persistence):
      * ``asset_scheduler`` loads the existing asset config, classifies + plans
        jobs, and (dry-run) reports what *would* run;
      * ``connector_executor`` performs live evidence ingestion into the EXISTING
        repository — but only when ``ECS_CONNECTOR_EXECUTION_ENABLED=true`` (or a
        ``connector_transport`` is injected for tests);
      * ``mock_evidence_collector`` ingests ``data/mock-evidence`` in DEMO_MODE.

    Safe by default: with the flag off and no injected transport this is a
    **dry-run** — the planner runs, but no connector call and no network happen.
    Returns a JSON-safe result carrying the real plan/execution outcome (no
    fabricated counters or log lines).
    """
    from modules.audit_intelligence.services import asset_scheduler
    from modules.audit_intelligence.services import connector_executor
    from modules.operations.engines.mock_evidence_collector import collect_mock_evidence
    from modules.operations.engines.scheduler_progress import SchedulerProgressLog

    apps = [a for a in (applications or []) if str(a).strip()]
    fws = [f for f in (frameworks or []) if str(f).strip()]

    global _collection_seq
    if not run_id:
        _collection_seq += 1
        run_id = f"COLL-{started_utc.strftime('%Y%m%d-%H%M%S')}-{_collection_seq:03d}"

    def _on_progress(_rid: str, events: list, active: str) -> None:
        _publish_run_progress(_rid, events, status="running", active_step=active)

    progress = SchedulerProgressLog(run_id, on_update=_on_progress)
    _publish_run_progress(run_id, progress, status="running", active_step="plan built")
    progress.append("plan built", "Running", detail=f"apps={len(apps) or 'all'} frameworks={len(fws) or 'all'}")

    assets = asset_scheduler.load_assets()
    plan = asset_scheduler.plan_evidence(assets)
    plan.jobs = [j for j in plan.jobs if _job_matches_selection(j, apps, fws)]

    live = connector_transport is not None or connector_executor.execution_enabled()
    mode = "live" if live else "dry-run"
    if not live and demo_mode_enabled() and _mock_evidence_collection_enabled():
        mode = "demo-mock"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    plan_summary = plan.to_dict()["summary"]
    connector_plan_summary = {
        "planned_jobs": plan_summary.get("planned_jobs", 0),
        "by_route": plan_summary.get("by_route", {}),
    }
    progress.append(
        "plan built",
        "Completed",
        detail=f"planned_jobs={connector_plan_summary.get('planned_jobs', 0)} mode={mode}",
    )

    results: list[dict] = []
    ingested = 0
    if live:
        progress.append("source scanned", "Running", detail="connector plan")
        connector_plan = asset_scheduler.EvidencePlan(
            jobs=[j for j in plan.jobs if getattr(j, "connector", "")],
            unsupported=[],
        )
        connector_plan_summary = connector_plan.to_dict()["summary"]
        results = asset_scheduler.execute_plan(
            connector_plan, run_connectors=True, connector_transport=connector_transport,
            requested_by=user or "scheduler", run_id=run_id,
        )
        ingested = sum(int(r.get("ingested", 0) or 0) for r in results if isinstance(r, dict))
        progress.append("source scanned", "Completed", detail=f"connectors={len(results)}")
        for row in results:
            step = f"connector {row.get('connector') or row.get('kind') or 'job'}"
            ok = row.get("ok", True) is not False and int(row.get("ingested", 0) or 0) >= 0
            progress.append(
                step,
                "Completed" if ok else "Failed",
                detail=f"ingested={row.get('ingested', 0)}",
            )
    elif demo_mode_enabled() and _mock_evidence_collection_enabled():
        progress.append("source scanned", "Running", detail="mock-evidence tree")
    else:
        progress.append("source scanned", "Skipped", detail="dry-run without DEMO_MODE mock path")

    mock_summary = {}
    if _mock_evidence_collection_enabled():
        mock_summary = collect_mock_evidence(
            user=user or "scheduler",
            run_id=run_id,
            applications=apps,
            frameworks=fws,
            progress=progress,
            dry_run=False,
        ).to_dict()
        ingested += int(mock_summary.get("new_evidence", 0) or 0)

    duration_sec = max(0, int(round(time.perf_counter() - started_perf)))
    completed_utc = datetime.now(timezone.utc)
    job_results = [r for r in results if isinstance(r, dict)]
    zero_or_failed = [
        r for r in job_results
        if (int(r.get("ingested", 0) or 0) == 0) or (r.get("ok") is False)
    ]
    status = "Success"
    if job_results and zero_or_failed:
        status = "Partial"
    if live and connector_plan_summary.get("planned_jobs", 0) and not job_results:
        status = "Failed"
    if int(mock_summary.get("failures", 0) or 0) and not int(mock_summary.get("new_evidence", 0) or 0):
        status = "Failed"

    cc_collected = 0
    cc_observations = 0
    cc_result: dict = {}
    if _common_controls_collection_enabled():
        try:
            from modules.operations.engines.common_controls_collector import collect_all_common_controls

            progress.append("common controls", "Running")
            cc_run = collect_all_common_controls(user=user or "scheduler", run_id=run_id)
            cc_result = cc_run.to_dict()
            cc_collected = cc_run.collected
            cc_observations = cc_run.observations
            ingested += cc_collected
            progress.append(
                "common controls",
                "Completed",
                detail=f"collected={cc_collected} observations={cc_observations}",
            )
        except Exception:  # noqa: BLE001
            cc_result = {"error": "common_controls_collection_failed"}
            progress.append("common controls", "Failed")

    pq_result: dict = {}
    pq_persisted = 0
    pq_enabled = _predefined_query_scheduler_enabled()
    if pq_enabled:
        try:
            progress.append("predefined queries", "Running", detail="persist=true (scheduled)")
            pq_result = collect_scheduled_predefined_queries(user=user or "scheduler", run_id=run_id)
            pq_persisted = int(pq_result.get("persisted", 0))
            ingested += pq_persisted
            if pq_persisted:
                progress.append("predefined queries", "Completed", detail=f"persisted={pq_persisted}")
            else:
                reason = _pq_zero_reason(pq_result)
                progress.append("predefined queries", "Skipped", detail=reason or "persisted=0")
        except Exception as exc:  # noqa: BLE001
            pq_result = {"error": "predefined_query_collection_failed", "detail": str(exc)}
            progress.append("predefined queries", "Failed", detail=str(exc))
    else:
        pq_result = {
            "enabled": False,
            "skip_reason": "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED=false",
            "persist_flag": False,
        }
        progress.append("predefined queries", "Skipped", detail=pq_result["skip_reason"])

    connector_summary = build_connector_source_summary(
        planned_jobs=connector_plan_summary.get("planned_jobs", 0),
        live=live,
        mode=mode,
        job_results=job_results,
    )
    source_breakdown, source_totals, pq_zero_reason = build_run_source_breakdown(
        connector_summary=connector_summary,
        mock_summary=mock_summary if isinstance(mock_summary, dict) else {},
        cc_result=cc_result if isinstance(cc_result, dict) else {},
        pq_result=pq_result if isinstance(pq_result, dict) else {},
        sp_result={},
        mock_enabled=_mock_evidence_collection_enabled(),
        cc_enabled=_common_controls_collection_enabled(),
        pq_enabled=pq_enabled,
        sp_enabled=False,
        demo_mode=demo_mode_enabled(),
    )
    pgvector_detail = source_totals.get("pgvector_detail") or _aggregate_pgvector_counts(source_breakdown)

    merged_counts = _merge_run_summary(mock_summary, cc_result, pq_result)
    summary = _coerce_run_summary(
        {
            "run_id": run_id,
            "applications": apps,
            "frameworks": fws,
            "sources_executed": merged_counts["sources_executed"] + len(job_results),
            "files_discovered": merged_counts["files_discovered"],
            "new_evidence": merged_counts["new_evidence"],
            "duplicates_skipped": merged_counts["duplicates_skipped"],
            "versions_created": merged_counts["versions_created"],
            "failures": merged_counts["failures"],
            "postgresql_count": merged_counts["postgresql_count"],
            "object_storage_count": merged_counts["object_storage_count"],
            "pgvector_count": merged_counts["pgvector_count"],
            "connector_ingested": sum(int(r.get("ingested", 0) or 0) for r in job_results),
            "source_breakdown": source_breakdown,
            "source_totals": source_totals,
            "pgvector_detail": pgvector_detail,
            "pq_zero_reason": pq_zero_reason,
            "collection_mode": mode,
            "environment_flags": {
                "DEMO_MODE": demo_mode_enabled(),
                "ECS_CONNECTOR_EXECUTION_ENABLED": live,
                "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED": pq_enabled,
                "ECS_COMMON_CONTROLS_COLLECTION_ENABLED": _common_controls_collection_enabled(),
                "ECS_MOCK_EVIDENCE_COLLECTION_ENABLED": _mock_evidence_collection_enabled(),
            },
        },
        run_id=run_id,
        applications=apps,
        frameworks=fws,
    )
    if not progress.events or progress.events[-1].get("step") != "completed":
        progress.append("completed", "Completed", detail=f"status={status}")

    history_row = {
        "run_id": run_id,
        "trigger_type": "Manual",
        "started": started_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "completed": completed_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "duration_sec": duration_sec,
        "apps_covered": len(apps) or len({j.application for j in plan.jobs if getattr(j, "application", "")}),
        "evidence_count": ingested,
        "status": status,
        "initiated_by": user or "System",
        "log_preview": [f"{e['timestamp']} | {e['step']} | {e['status']}" + (f" — {e['detail']}" if e.get('detail') else "") for e in progress.to_list()],
        "progress_events": progress.to_list(),
        "summary": summary,
        "job_results": job_results,
        "mode": mode,
    }
    _execution_history.insert(0, history_row)
    _run_progress[run_id] = {
        "run_id": run_id,
        "status": status.lower(),
        "progress_events": progress.to_list(),
        "summary": summary,
        "result": {
            "ok": True,
            "run_id": run_id,
            "status": status,
            "ingested": ingested,
            "progress": progress.to_list(),
            "summary": summary,
        },
    }

    try:
        from modules.shared.services.ecs_logging import log_scheduler
        log_scheduler(
            f"Evidence collection {mode}",
            f"planned_jobs={connector_plan_summary.get('planned_jobs', 0)}; ingested={ingested}; run_id={run_id}",
            user=user,
        )
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "run_id": run_id,
        "status": status,
        "duration_sec": duration_sec,
        "mode": mode,
        "timestamp": now,
        "applications": apps,
        "frameworks": fws,
        "planned_jobs": connector_plan_summary.get("planned_jobs", 0),
        "by_route": connector_plan_summary.get("by_route", {}),
        "connectors": sorted({j.connector for j in plan.jobs if j.connector}),
        "ingested": ingested,
        "results": results,
        "common_controls": cc_result,
        "common_controls_collected": cc_collected,
        "common_controls_observations": cc_observations,
        "predefined_queries": pq_result,
        "predefined_queries_persisted": pq_persisted,
        "progress": progress.to_list(),
        "summary": summary,
        "mock_evidence": mock_summary,
    }
