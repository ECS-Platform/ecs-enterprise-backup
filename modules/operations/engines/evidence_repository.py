"""Evidence repository: bulk upload, metadata, hashes, lifecycle, reuse."""

import hashlib
import re
from datetime import datetime, timezone

from app import ecs_state

# Startup profiling for refresh_repository_from_frameworks (instrumentation only).
_REFRESH_PROFILE: dict | None = None


def _prof_add(stage: str, seconds: float, **counters) -> None:
    """Accumulate stage timings/counters while a refresh profile is active."""
    prof = _REFRESH_PROFILE
    if not isinstance(prof, dict):
        return
    stages = prof.setdefault("stages", {})
    bucket = stages.setdefault(stage, {"seconds": 0.0, "calls": 0})
    bucket["seconds"] += float(seconds or 0.0)
    bucket["calls"] += 1
    counts = prof.setdefault("counts", {})
    for key, value in counters.items():
        counts[key] = int(counts.get(key, 0) or 0) + int(value or 0)


evidence_repository = []
upload_tracker = []
evidence_reuse_map = {}
_evidence_counter = 0


def _next_id():
    global _evidence_counter
    if _evidence_counter <= 0:
        _evidence_counter = _max_existing_evidence_seq()
    _evidence_counter += 1
    return f"EVD-{_evidence_counter:05d}"


def _max_existing_evidence_seq() -> int:
    """Highest EVD-NNNNN already known (ops / audit / canonical) so new IDs never collide."""
    import re

    max_n = 0

    def _consider(value: str) -> None:
        nonlocal max_n
        match = re.match(r"^EVD-(\d+)$", str(value or "").strip())
        if match:
            max_n = max(max_n, int(match.group(1)))

    for rec in evidence_repository:
        _consider(str(rec.get("evidence_id") or ""))
    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        for art in ai_repo.all_artifacts():
            _consider(str(getattr(art, "evidence_id", "") or ""))
    except Exception:  # noqa: BLE001
        pass
    try:
        from ecs_platform.repository.repository import EvidenceRepository

        repo = EvidenceRepository()
        try:
            for uid in repo.list_evidence_uids(limit=5000):
                _consider(uid)
        finally:
            repo.close()
    except Exception:  # noqa: BLE001
        pass
    return max_n


def enforce_naming(filename: str, framework: str, application: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    prefix = re.sub(r"\s+", "_", framework.upper())[:12]
    app = re.sub(r"\s+", "_", application.upper())[:10]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    if base.lower().startswith(f"{prefix.lower()}_"):
        return base
    return f"{prefix}_{app}_{ts}_{base}"


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def integrity_check(stored_hash: str, content: bytes) -> dict:
    current = compute_hash(content) if content else stored_hash
    ok = current == stored_hash
    return {
        "stored_hash": stored_hash,
        "current_hash": current,
        "valid": ok,
        "status": "Valid" if ok else "Tamper Detected (simulated)",
    }


def _parse_row_metadata(raw) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            import json

            parsed = json.loads(raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:  # noqa: BLE001
            return {}
    try:
        return dict(raw or {})
    except Exception:  # noqa: BLE001
        return {}


def _ops_record_from_index(indexed: dict, *, sha256: str = "") -> dict:
    """Rebuild a minimal ops upload shape from the PQ content/fingerprint index."""
    meta = {
        "object_key": indexed.get("object_key") or "",
        "content_sha256": indexed.get("sha256") or sha256,
        "canonical_fingerprint": indexed.get("canonical_fingerprint") or "",
        "substantive_content_sha256": indexed.get("canonical_fingerprint") or "",
        "query_id": indexed.get("control_id") or "",
    }
    return {
        "evidence_id": indexed.get("evidence_id") or "",
        "sha256": indexed.get("sha256") or sha256,
        "version": int(indexed.get("evidence_version") or 1),
        "filename": indexed.get("filename") or "",
        "custody_mode": indexed.get("custody_mode") or "",
        "object_uri": indexed.get("object_uri") or "",
        "control": indexed.get("control_id") or "",
        "framework_tags": [indexed["framework"]] if indexed.get("framework") else [],
        "metadata": meta,
        "status": "Uploaded",
        "workflow_status": indexed.get("workflow_status") or "Uploaded",
    }


def _ops_record_from_artifact(art) -> dict:
    """Map an audit EvidenceArtifact into the ops upload shape for dedup receipts."""
    meta = _parse_row_metadata(getattr(art, "metadata", None))
    sha = str(
        getattr(art, "content_hash", "")
        or meta.get("sha256")
        or meta.get("content_sha256")
        or ""
    )
    return {
        "evidence_id": str(getattr(art, "evidence_id", "") or ""),
        "sha256": sha,
        "version": int(getattr(art, "version", 1) or 1),
        "filename": str(getattr(art, "filename", "") or ""),
        "custody_mode": str(getattr(art, "custody_mode", "") or ""),
        "object_uri": str(getattr(art, "object_uri", "") or meta.get("object_uri") or ""),
        "control": str(getattr(art, "control_id", "") or meta.get("control") or ""),
        "framework_tags": list(getattr(art, "frameworks", ()) or []),
        "metadata": {
            **meta,
            "object_key": meta.get("object_key") or "",
            "content_sha256": sha,
            "canonical_fingerprint": meta.get("canonical_fingerprint")
            or meta.get("substantive_content_sha256")
            or "",
            "substantive_content_sha256": meta.get("substantive_content_sha256")
            or meta.get("canonical_fingerprint")
            or "",
        },
        "status": "Uploaded",
        "audit_version": int(getattr(art, "version", 1) or 1),
    }


def _ops_record_from_canonical_row(row: dict) -> dict:
    meta = _parse_row_metadata(row.get("metadata"))
    sha = str(meta.get("sha256") or meta.get("content_hash") or meta.get("content_sha256") or "")
    return {
        "evidence_id": str(row.get("evidence_uid") or ""),
        "sha256": sha,
        "version": int(meta.get("version") or 1),
        "filename": str(meta.get("filename") or row.get("title") or ""),
        "custody_mode": str(meta.get("custody_mode") or ""),
        "object_uri": str(meta.get("object_uri") or row.get("url") or ""),
        "control": str(meta.get("control") or ""),
        "framework_tags": [meta["framework"]] if meta.get("framework") else [],
        "metadata": {
            **meta,
            "content_sha256": sha,
            "canonical_fingerprint": meta.get("canonical_fingerprint")
            or meta.get("substantive_content_sha256")
            or "",
            "substantive_content_sha256": meta.get("substantive_content_sha256")
            or meta.get("canonical_fingerprint")
            or "",
        },
        "status": "Uploaded",
    }


def _find_durable_by_sha256(sha256: str) -> dict | None:
    """Look up identical content in audit memory/SQL and canonical PostgreSQL."""
    if not sha256:
        return None
    import time as _time

    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        _t0 = _time.perf_counter()
        for art in ai_repo.all_artifacts():
            if str(getattr(art, "content_hash", "") or "") == sha256:
                _prof_add("durable_dedup_audit_memory", _time.perf_counter() - _t0, db_reads=0)
                return _ops_record_from_artifact(art)
        _prof_add("durable_dedup_audit_memory", _time.perf_counter() - _t0)
    except Exception:  # noqa: BLE001
        pass
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        _t0 = _time.perf_counter()
        for candidate in get_persistence().list_all_evidence_versions():
            if str(getattr(candidate, "content_hash", "") or "") == sha256:
                _prof_add("durable_dedup_sql_persistence", _time.perf_counter() - _t0, db_reads=1)
                return _ops_record_from_artifact(candidate)
        _prof_add("durable_dedup_sql_persistence", _time.perf_counter() - _t0, db_reads=1)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ecs_platform.repository.repository import EvidenceRepository

        _t0 = _time.perf_counter()
        repo = EvidenceRepository()
        try:
            for row in repo.search_evidence(limit=500):
                meta = _parse_row_metadata(row.get("metadata"))
                if str(meta.get("sha256") or meta.get("content_hash") or meta.get("content_sha256") or "") == sha256:
                    _prof_add("durable_dedup_canonical_pg", _time.perf_counter() - _t0, db_reads=1)
                    return _ops_record_from_canonical_row(row)
            _prof_add("durable_dedup_canonical_pg", _time.perf_counter() - _t0, db_reads=1)
        finally:
            repo.close()
    except Exception:  # noqa: BLE001
        pass
    return None


def _find_durable_by_canonical(canonical_hash: str) -> dict | None:
    """Look up logically identical PQ content across durable stores."""
    if not canonical_hash:
        return None
    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        for art in ai_repo.all_artifacts():
            meta = _parse_row_metadata(getattr(art, "metadata", None))
            if (
                meta.get("canonical_fingerprint") == canonical_hash
                or meta.get("substantive_content_sha256") == canonical_hash
            ):
                return _ops_record_from_artifact(art)
    except Exception:  # noqa: BLE001
        pass
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        for art in get_persistence().list_all_evidence_versions():
            meta = _parse_row_metadata(getattr(art, "metadata", None))
            if (
                meta.get("canonical_fingerprint") == canonical_hash
                or meta.get("substantive_content_sha256") == canonical_hash
            ):
                return _ops_record_from_artifact(art)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ecs_platform.repository.repository import EvidenceRepository

        repo = EvidenceRepository()
        try:
            for row in repo.search_evidence(limit=500):
                meta = _parse_row_metadata(row.get("metadata"))
                if (
                    meta.get("canonical_fingerprint") == canonical_hash
                    or meta.get("substantive_content_sha256") == canonical_hash
                ):
                    return _ops_record_from_canonical_row(row)
        finally:
            repo.close()
    except Exception:  # noqa: BLE001
        pass
    return None


def find_upload_by_sha256(sha256: str) -> dict | None:
    """Return an existing ops-repository upload with the same content hash.

    Checks in-memory ops rows, PQ content index, then durable audit/PostgreSQL
    so identical SHA-256 artifacts are skipped even after process restart.
    """
    if not sha256:
        return None
    for rec in evidence_repository:
        if rec.get("sha256") == sha256:
            return rec
    indexed = ecs_state.predefined_query_content_index.get(sha256)
    if indexed:
        evidence_id = indexed.get("evidence_id")
        if evidence_id:
            for rec in evidence_repository:
                if rec.get("evidence_id") == evidence_id:
                    return rec
        return _ops_record_from_index(indexed, sha256=sha256)
    return _find_durable_by_sha256(sha256)


def find_upload_by_canonical_fingerprint(canonical_hash: str) -> dict | None:
    """Return an existing predefined-query upload for a canonical fingerprint."""
    if not canonical_hash:
        return None
    indexed = ecs_state.predefined_query_fingerprint_index.get(canonical_hash)
    if indexed:
        evidence_id = indexed.get("evidence_id")
        if evidence_id:
            for rec in evidence_repository:
                if rec.get("evidence_id") == evidence_id:
                    return rec
        return _ops_record_from_index(indexed)
    for rec in evidence_repository:
        meta = rec.get("metadata") or {}
        if meta.get("canonical_fingerprint") == canonical_hash:
            return rec
        if meta.get("substantive_content_sha256") == canonical_hash:
            return rec
    return _find_durable_by_canonical(canonical_hash)


def _ops_list_contains(*, sha256: str = "", evidence_id: str = "") -> bool:
    for rec in evidence_repository:
        if sha256 and rec.get("sha256") == sha256:
            return True
        if evidence_id and rec.get("evidence_id") == evidence_id:
            return True
    return False


def _materialize_durable_hit_into_ops(
    existing: dict,
    *,
    content_hash: str,
    uploaded_by: str,
    framework: str,
    application: str,
    control: str,
    source_connector: str,
    source_item_id: str,
    source_url: str,
    environment: str,
    mime_type: str,
    metadata: dict | None,
    custody_mode: str,
    source_modified_at: str,
) -> dict:
    """Append a session-local ops row for a durable-only SHA hit.

    Durable dedup (AI/SQL/canonical) can find content after ops memory was cleared
    (tests/restart). Materialize once into ``evidence_repository`` so ops consumers
    still see the evidence without a second AI/canonical write.
    """
    existing_meta = dict(existing.get("metadata") or {})
    incoming_meta = dict(metadata or {})
    merged_meta = {**existing_meta, **incoming_meta}
    row = {
        "evidence_id": str(existing.get("evidence_id") or "") or _next_id(),
        "filename": str(existing.get("filename") or incoming_meta.get("filename") or ""),
        "original_filename": str(existing.get("original_filename") or existing.get("filename") or ""),
        "framework_tags": list(existing.get("framework_tags") or [])
        or ([framework] if framework else ["Cross-Framework"]),
        "application_tags": [application] if application else list(existing.get("application_tags") or ["Net Banking"]),
        "control": control or str(existing.get("control") or ""),
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "integrity": "Valid",
        "integrity_valid": True,
        "lifecycle": "Draft",
        "summary": "",
        "size_bytes": int(existing.get("size_bytes") or 0),
        "status": "Uploaded",
        "source_connector": source_connector or str(existing.get("source_connector") or ""),
        "source_item_id": source_item_id or str(existing.get("source_item_id") or ""),
        "source_url": source_url or str(existing.get("source_url") or ""),
        "environment": environment or str(existing.get("environment") or ""),
        "mime_type": mime_type or str(existing.get("mime_type") or ""),
        "metadata": merged_meta,
        "source_modified_at": source_modified_at,
        "custody_mode": custody_mode or str(existing.get("custody_mode") or ""),
        "version": int(existing.get("version") or existing.get("audit_version") or 1),
        "sha256": content_hash or str(existing.get("sha256") or ""),
        "object_uri": str(existing.get("object_uri") or ""),
        "audit_repository_synced": True,
        "audit_version": int(existing.get("audit_version") or existing.get("version") or 1),
    }
    evidence_repository.append(row)
    return row


def register_upload(
    filename: str,
    content: bytes,
    uploaded_by: str,
    framework: str = "",
    application: str = "Net Banking",
    control: str = "",
    *,
    source_connector: str = "",
    source_item_id: str = "",
    source_url: str = "",
    environment: str = "",
    mime_type: str = "",
    metadata: dict | None = None,
    source_modified_at: str = "",
    custody_mode: str = "",
    allow_duplicate: bool = False,
):
    import time as _time

    _prof = _REFRESH_PROFILE is not None
    _t_all = _time.perf_counter() if _prof else 0.0
    content_bytes = content or b""
    _t0 = _time.perf_counter() if _prof else 0.0
    content_hash = compute_hash(content_bytes)
    meta_in = dict(metadata or {})
    substantive_hash = meta_in.get("substantive_content_sha256") or meta_in.get("canonical_fingerprint")
    if not allow_duplicate:
        existing = find_upload_by_sha256(content_hash)
        if existing is not None:
            if _prof:
                _prof_add("hash_and_dedup_check", _time.perf_counter() - _t0, register_attempts=1, duplicates_sha=1)
            eid = str(existing.get("evidence_id") or "")
            if not _ops_list_contains(sha256=content_hash, evidence_id=eid):
                # Durable hit only — hydrate ops for this process, keep DUPLICATE
                # semantics (no second brand-new evidence identity). Mirror into AI
                # memory so get_latest() works after ops/AI were cleared.
                materialized = _materialize_durable_hit_into_ops(
                    existing,
                    content_hash=content_hash,
                    uploaded_by=uploaded_by,
                    framework=framework,
                    application=application,
                    control=control,
                    source_connector=source_connector,
                    source_item_id=source_item_id,
                    source_url=source_url,
                    environment=environment,
                    mime_type=mime_type,
                    metadata=meta_in,
                    custody_mode=custody_mode,
                    source_modified_at=source_modified_at,
                )
                _mirror_to_audit_repository(
                    materialized, content_bytes, framework, application, control
                )
                return {
                    **materialized,
                    "status": "DUPLICATE",
                    "duplicate": True,
                    "duplicate_kind": "sha256",
                    "original_evidence_id": materialized.get("evidence_id") or eid,
                    "embedding_skipped": True,
                    "search_index": {
                        "indexed": False,
                        "reason": "embedding_skipped",
                        "embedding_skipped": True,
                    },
                }
            dup = dict(existing)
            dup["status"] = "DUPLICATE"
            dup["duplicate"] = True
            dup["duplicate_kind"] = "sha256"
            dup["original_evidence_id"] = existing.get("evidence_id", "")
            dup["embedding_skipped"] = True
            dup["search_index"] = {
                "indexed": False,
                "reason": "embedding_skipped",
                "embedding_skipped": True,
            }
            return dup
        if substantive_hash:
            logical = find_upload_by_canonical_fingerprint(substantive_hash)
            if logical is not None:
                if _prof:
                    _prof_add("hash_and_dedup_check", _time.perf_counter() - _t0, register_attempts=1, duplicates_sha=0)
                eid = str(logical.get("evidence_id") or "")
                logical_sha = str(logical.get("sha256") or content_hash)
                if not _ops_list_contains(sha256=logical_sha, evidence_id=eid):
                    materialized = _materialize_durable_hit_into_ops(
                        logical,
                        content_hash=logical_sha or content_hash,
                        uploaded_by=uploaded_by,
                        framework=framework,
                        application=application,
                        control=control,
                        source_connector=source_connector,
                        source_item_id=source_item_id,
                        source_url=source_url,
                        environment=environment,
                        mime_type=mime_type,
                        metadata=meta_in,
                        custody_mode=custody_mode,
                        source_modified_at=source_modified_at,
                    )
                    _mirror_to_audit_repository(
                        materialized, content_bytes, framework, application, control
                    )
                    return {
                        **materialized,
                        "status": "DUPLICATE",
                        "duplicate": True,
                        "duplicate_kind": "canonical",
                        "original_evidence_id": materialized.get("evidence_id") or eid,
                        "embedding_skipped": True,
                        "search_index": {
                            "indexed": False,
                            "reason": "embedding_skipped",
                            "embedding_skipped": True,
                        },
                    }
                dup = dict(logical)
                dup["status"] = "DUPLICATE"
                dup["duplicate"] = True
                dup["duplicate_kind"] = "canonical"
                dup["original_evidence_id"] = logical.get("evidence_id", "")
                dup["embedding_skipped"] = True
                dup["search_index"] = {
                    "indexed": False,
                    "reason": "embedding_skipped",
                    "embedding_skipped": True,
                }
                return dup

    std_name = enforce_naming(filename, framework or "GENERAL", application)
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "evidence_id": _next_id(),
        "filename": std_name,
        "original_filename": filename,
        "framework_tags": [framework] if framework else ["Cross-Framework"],
        "application_tags": [application],
        "control": control,
        "uploaded_by": uploaded_by,
        "uploaded_at": now,
        "integrity": "Valid",
        "integrity_valid": True,
        "lifecycle": "Draft",
        "summary": "",
        "size_bytes": len(content) if content else 0,
        "status": "Uploaded",
        "source_connector": source_connector,
        "source_item_id": source_item_id,
        "source_url": source_url,
        "environment": environment,
        "mime_type": mime_type,
        "metadata": dict(metadata or {}),
        "source_modified_at": source_modified_at,
        "custody_mode": custody_mode,
        "version": 1,
    }
    if _prof:
        _prof_add("hash_and_dedup_check", _time.perf_counter() - _t0, register_attempts=1)
        _t0 = _time.perf_counter()
    try:
        from modules.shared.services.evidence_authoritative_reader import _enrich_fcm_mappings

        record["metadata"] = _enrich_fcm_mappings(
            record["metadata"],
            framework=framework or "Cross-Framework",
            control=control,
        )
    except Exception:  # noqa: BLE001
        pass
    if _prof:
        _prof_add("fcm_enrichment", _time.perf_counter() - _t0)
        _t0 = _time.perf_counter()
    custody = _apply_custody(record, content or b"", application, control)
    if _prof:
        _prof_add("custody_object_store", _time.perf_counter() - _t0)
        _t0 = _time.perf_counter()
    file_hash = custody.content_hash
    integrity = integrity_check(file_hash, content or b"")
    record["sha256"] = file_hash
    record["integrity"] = integrity["status"]
    record["integrity_valid"] = integrity["valid"]
    record["custody_mode"] = custody.custody_mode
    record["object_uri"] = custody.object_uri
    record["size_bytes"] = custody.size_bytes
    record["object_stored"] = bool(custody.object_uri) and (
        custody.stored
        or "immutable_exists" in str(custody.reason or "")
        or str(custody.custody_mode or "").upper() == "SNAPSHOT"
    )
    if custody.reason:
        meta_c = dict(record.get("metadata") or {})
        meta_c.setdefault("custody_reason", custody.reason)
        record["metadata"] = meta_c
    record["summary"] = generate_summary(record)
    record["reviewer"] = "Pending Assignment"
    evidence_repository.append(record)
    # Mirror the upload into the audit-intelligence evidence repository so manual /
    # bulk uploads become real evidence for readiness, reuse, dashboards, and
    # integrity — instead of living only in this MVP in-memory list. Best-effort:
    # a bridge failure must never break the primary upload path.
    if _prof:
        _prof_add("record_build_and_append", _time.perf_counter() - _t0)
        _t0 = _time.perf_counter()
    _mirror_to_audit_repository(record, content or b"", framework, application, control)
    if _prof:
        _prof_add("audit_mirror_and_canonical_write", _time.perf_counter() - _t0, db_writes=1)
        _t0 = _time.perf_counter()
    record["search_index"] = _register_search_index(record, content or b"")
    if _prof:
        _prof_add("search_index_hook", _time.perf_counter() - _t0)
        _t0 = _time.perf_counter()
    from modules.shared.services.audit_trail import log_event, record_version

    record_version(
        record["evidence_id"],
        std_name,
        int(record.get("version") or record.get("audit_version") or 1),
        uploaded_by,
    )
    log_event(
        "Evidence Uploaded",
        uploaded_by,
        framework or "Cross-Framework",
        control,
        std_name,
        record["evidence_id"],
    )
    upload_tracker.append(
        {
            "evidence_id": record["evidence_id"],
            "filename": std_name,
            "status": "Complete",
            "uploaded_by": uploaded_by,
            "at": now,
        }
    )
    _link_reuse(record)
    if _prof:
        _prof_add("audit_trail_and_reuse", _time.perf_counter() - _t0)
        _prof_add("register_upload_total", _time.perf_counter() - _t_all, register_accepted=1)
    return record


def _apply_custody(record, content: bytes, application: str, control: str):
    """Resolve evidence custody (REFERENCE_ONLY default). Never raises."""
    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo
        from modules.audit_intelligence.services import evidence_custody as custody

        evidence_key = ai_repo.make_evidence_key(application, control or record.get("filename", "UPLOAD"))
        result = custody.resolve_custody(
            source_connector=record.get("source_connector", ""),
            source_item_id=record.get("source_item_id", ""),
            source_url=record.get("source_url", ""),
            source_modified_at=record.get("source_modified_at", ""),
            filename=record.get("filename", ""),
            mime_type=record.get("mime_type", ""),
            evidence_key=evidence_key,
            version=int(record.get("version", 1) or 1),
            content=content or None,
            custody_mode=record.get("custody_mode") or None,
        )
        if result.reason:
            meta = dict(record.get("metadata") or {})
            meta["custody_reason"] = result.reason
            record["metadata"] = meta
        return result
    except Exception:  # noqa: BLE001
        from modules.audit_intelligence.services.evidence_custody import CustodyResult

        fallback_hash = compute_hash(content or record.get("filename", "").encode())
        return CustodyResult(
            custody_mode="REFERENCE_ONLY",
            content_hash=fallback_hash,
            size_bytes=len(content) if content else 0,
            source_url=record.get("source_url", ""),
            source_item_id=record.get("source_item_id", ""),
            source_modified_at=record.get("source_modified_at", ""),
            object_uri="",
            stored=False,
            reason="custody_fallback",
        )


def _register_search_index(record: dict, content: bytes) -> dict:
    """Register persisted upload for semantic search; skip duplicate content."""
    sha = record.get("sha256") or ""
    if not sha:
        return {"indexed": False, "reason": "missing_hash"}
    meta = dict(record.get("metadata") or {})
    substantive_hash = meta.get("substantive_content_sha256") or meta.get("canonical_fingerprint")
    dup_peers = [
        r for r in evidence_repository[:-1]
        if r.get("sha256") == sha and r.get("evidence_id") != record.get("evidence_id")
    ]
    if dup_peers:
        return {
            "indexed": False,
            "reason": "embedding_skipped",
            "embedding_skipped": True,
            "duplicate_content": True,
            "existing_evidence_id": dup_peers[0].get("evidence_id"),
        }
    if substantive_hash:
        logical_peer = find_upload_by_canonical_fingerprint(substantive_hash)
        if logical_peer and logical_peer.get("evidence_id") != record.get("evidence_id"):
            peer_idx = dict(logical_peer.get("search_index") or {})
            if peer_idx.get("indexed") or peer_idx.get("embedded_chunks", 0) > 0:
                return {
                    "indexed": False,
                    "reason": "embedding_skipped",
                    "embedding_skipped": True,
                    "duplicate_substantive_content": True,
                    "existing_evidence_id": logical_peer.get("evidence_id"),
                }
    if not record.get("audit_repository_synced"):
        return {"indexed": False, "reason": "mirror_failed"}
    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo
        from ecs_platform.evidence_indexing import index_after_persist

        control = record.get("control") or record.get("filename", "UPLOAD")
        app = (record.get("application_tags") or ["Net Banking"])[0]
        key = ai_repo.make_evidence_key(app, control)
        versions = ai_repo.get_versions(key)
        if not versions:
            return {"indexed": False, "reason": "artifact_missing"}
        artifact = versions[-1]
        text = content.decode("utf-8", errors="ignore") if content else ""
        report = index_after_persist(artifact, normalized_text=text)
        indexed = bool(report.get("ok")) and int(report.get("embedded_chunks", 0) or 0) > 0
        reason = str(report.get("reason") or "")
        if report.get("skipped") and reason in {
            "superseded",
            "empty_text",
            "provider_not_configured",
            "startup_seed_no_indexing",
        }:
            indexed = False
        elif reason == "already_indexed" or int(report.get("skipped_unchanged", 0) or 0) > 0:
            # Vectors already present in PGVector — treat as success, not a skip/fail.
            return {
                "indexed": True,
                "reason": "already_indexed",
                "embedding_skipped": True,
                **report,
            }
        out = {"indexed": indexed, **report}
        if report.get("errors"):
            out["reason"] = "index_failed"
        return out
    except Exception as exc:  # noqa: BLE001
        return {"indexed": False, "reason": "index_failed", "errors": [str(exc)]}


def _mirror_to_audit_repository(record, content, framework, application, control):
    """Store an uploaded evidence item into the audit-intelligence repository.

    Reuses the existing ``audit_intelligence.engines.evidence_repository`` (no new
    store): the manual/bulk-uploaded artifact gets a SHA-256 versioned record with
    framework/application tags, so it flows into readiness, reuse, and integrity.
    Technology/control metadata is enriched from the existing control mapping when
    the control id is known. Never raises.
    """
    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        technology = ""
        frameworks: tuple[str, ...] = tuple(t for t in [framework] if t and t != "Cross-Framework")
        if control:
            try:
                from modules.audit_intelligence.engines import technology_control_mapping as mapping

                ref = mapping.get_control(control)
                if ref:
                    technology = ref.technology or ""
                    if ref.frameworks:
                        frameworks = tuple(ref.frameworks)
            except Exception:  # noqa: BLE001 - mapping optional
                pass
        text = content.decode("utf-8", "ignore") if isinstance(content, (bytes, bytearray)) else str(content or "")
        meta = dict(record.get("metadata") or {})
        try:
            from modules.shared.services.evidence_authoritative_reader import _enrich_fcm_mappings

            meta = _enrich_fcm_mappings(
                meta,
                framework=framework or (record.get("framework_tags") or [""])[0],
                control=control or record.get("control") or "",
            )
        except Exception:  # noqa: BLE001
            pass
        # Preserve the pre-standardization name so repository search finds the
        # filename users type (e.g. encryption_evidence.txt) even when the
        # stored ``filename`` is the enforce_naming() variant.
        if record.get("original_filename"):
            meta.setdefault("original_filename", str(record["original_filename"]))
        if record.get("application_tags"):
            meta.setdefault("application", str((record.get("application_tags") or [""])[0]))
        try:
            evidence_quality = float(meta.get("evidence_quality") or 0.0)
        except (TypeError, ValueError):
            evidence_quality = 0.0
        # index=False: PGVector write is owned solely by _register_search_index so
        # publish-time embedding runs once (Phase-1 pipeline). Hydration uses the
        # same flag independently and must not be changed here.
        stored = ai_repo.store_evidence(
            control_id=control or record.get("filename", "UPLOAD"),
            content=text or record.get("summary", ""),
            technology=technology or str(meta.get("technology") or ""),
            asset_id=application or "",
            frameworks=frameworks,
            verdict=str(meta.get("validation_verdict") or meta.get("verdict") or ""),
            control_status=str(meta.get("control_status") or ""),
            evidence_quality=evidence_quality,
            # Prefer connector identity (e.g. common_controls) so collector-sourced
            # rows keep a stable ``source`` label after the single-write lifecycle.
            source=str(record.get("source_connector") or "manual_upload"),
            filename=record.get("filename", ""),
            tags=(f"app:{application}", "source:upload",
                  f"mvp_evidence_id:{record.get('evidence_id', '')}"),
            evidence_id=record.get("evidence_id", ""),
            environment=record.get("environment", ""),
            source_connector=record.get("source_connector", ""),
            source_item_id=record.get("source_item_id", ""),
            source_url=record.get("source_url", ""),
            mime_type=record.get("mime_type", ""),
            metadata=meta,
            custody_mode=record.get("custody_mode", "REFERENCE_ONLY"),
            source_modified_at=record.get("source_modified_at", ""),
            object_uri=record.get("object_uri", ""),
            content_hash_override=record.get("sha256", ""),
            size_bytes_override=int(record.get("size_bytes", 0) or 0),
            index=False,
        )
        record["audit_version"] = stored.version
        # Authoritative version lives on the audit artifact; keep ops in sync.
        record["version"] = int(stored.version or record.get("version") or 1)
        meta_out = dict(record.get("metadata") or {})
        meta_out["audit_version"] = stored.version
        record["metadata"] = meta_out
        record["audit_repository_synced"] = True
        _persist_upload_to_canonical(record, text or record.get("summary", ""), stored)
    except Exception:  # noqa: BLE001 - bridge must never break the primary upload
        record["audit_repository_synced"] = False


def _persist_upload_to_canonical(record: dict, content_text: str, stored) -> None:
    """Best-effort write into ``ecs_platform.repository`` using the upload's Evidence ID.

    Reuses the same upsert shape as the LLM usecase seed path — no new persistence
    service. Never raises. Sets ``canonical_persisted`` on the ops record.
    """
    try:
        from ecs_platform.repository.repository import EvidenceRepository

        evidence_id = str(record.get("evidence_id") or getattr(stored, "evidence_id", "") or "")
        if not evidence_id:
            record["canonical_persisted"] = False
            meta_fail = dict(record.get("metadata") or {})
            meta_fail["canonical_persist_reason"] = "missing_evidence_id"
            record["metadata"] = meta_fail
            return
        meta = dict(record.get("metadata") or {})
        meta.update(
            {
                "evidence_id": evidence_id,
                "filename": str(record.get("filename") or ""),
                "custody_mode": str(record.get("custody_mode") or ""),
                "object_uri": str(record.get("object_uri") or ""),
                "mime_type": str(record.get("mime_type") or ""),
                "source_url": str(record.get("source_url") or ""),
                "source_connector": str(record.get("source_connector") or "upload"),
                "content_hash": str(record.get("sha256") or ""),
                "version": int(
                    getattr(stored, "version", 0)
                    or record.get("audit_version")
                    or record.get("version")
                    or 1
                ),
                "control": str(record.get("control") or ""),
                "framework": str((record.get("framework_tags") or [""])[0] or ""),
                "environment": str(record.get("environment") or ""),
                "sha256": str(record.get("sha256") or ""),
                "canonical_fingerprint": str(
                    meta.get("canonical_fingerprint")
                    or meta.get("substantive_content_sha256")
                    or ""
                ),
                "substantive_content_sha256": str(
                    meta.get("substantive_content_sha256")
                    or meta.get("canonical_fingerprint")
                    or ""
                ),
            }
        )
        application = str((record.get("application_tags") or [""])[0] or "")
        control = str(record.get("control") or "")
        # Prefer FCM control id when enrichment populated it; otherwise keep legacy
        # control string so existing uploads without fcm_control_id behave unchanged.
        mapped_control = str(meta.get("fcm_control_id") or control or "").strip()
        item = {
            "evidence_uid": evidence_id,
            "source_system": str(record.get("source_connector") or "upload"),
            "source_object_id": str(record.get("source_item_id") or evidence_id),
            "object_type": str(record.get("mime_type") or "application/octet-stream"),
            "title": str(record.get("filename") or evidence_id),
            "content": content_text or "",
            "owner": str(record.get("uploaded_by") or "ecs"),
            "url": str(record.get("object_uri") or record.get("source_url") or ""),
            "application": application,
            "metadata": meta,
            "control_mapping": [mapped_control] if mapped_control else [],
            "framework_mapping": [fw for fw in (record.get("framework_tags") or []) if fw],
        }
        repo = EvidenceRepository()
        try:
            repo.upsert_evidence(item)
            durable_uid = str(item.get("evidence_uid") or evidence_id)
            # Source-identity conflict keeps the durable canonical uid — align ops
            # and the just-mirrored audit artifact before PGVector indexing runs.
            if durable_uid and durable_uid != evidence_id:
                record["evidence_id"] = durable_uid
                meta["evidence_id"] = durable_uid
                try:
                    object.__setattr__(stored, "evidence_id", durable_uid)
                except Exception:  # noqa: BLE001
                    pass
            record["canonical_persisted"] = True
            meta_out = dict(record.get("metadata") or {})
            meta_out.update(meta)
            meta_out["canonical_persisted"] = True
            record["metadata"] = meta_out
        finally:
            repo.close()
    except Exception as exc:  # noqa: BLE001 - canonical write must never break upload
        record["canonical_persisted"] = False
        meta_fail = dict(record.get("metadata") or {})
        meta_fail["canonical_persisted"] = False
        meta_fail["canonical_persist_reason"] = f"{type(exc).__name__}:{exc}"
        record["metadata"] = meta_fail


def _link_reuse(record):
    """Simulate vector embedding reuse across controls."""
    key = record["filename"].lower()
    if key in evidence_reuse_map:
        evidence_reuse_map[key]["linked_controls"].append(
            {
                "framework": record["framework_tags"][0],
                "control": record.get("control") or "Shared Control",
            }
        )
        record["reused"] = True
        record["reuse_group"] = evidence_reuse_map[key]["group_id"]
    else:
        group_id = f"REUSE-{len(evidence_reuse_map) + 1:03d}"
        evidence_reuse_map[key] = {
            "group_id": group_id,
            "filename": record["filename"],
            "linked_controls": [
                {
                    "framework": record["framework_tags"][0],
                    "control": record.get("control") or "Primary",
                }
            ],
        }
        if record["framework_tags"][0] != "Cross-Framework":
            evidence_reuse_map[key]["linked_controls"].append(
                {"framework": "DPSC", "control": "Log Monitoring"}
            )
            evidence_reuse_map[key]["linked_controls"].append(
                {"framework": "CSITE", "control": "SIEM Alerts"}
            )
        record["reuse_group"] = group_id
        record["reused"] = False


def _framework_seed_bytes(row: dict, source: str) -> bytes:
    """Deterministic seed payload used by framework-catalog refresh (unchanged)."""
    return f"{row['framework']}|{row['control']}|{row['evidence_name']}|{source}".encode()


def _framework_seed_source_item_id(catalog_evidence_id: str) -> str:
    return f"framework-catalog/{catalog_evidence_id}"


def _collect_present_framework_seed_keys() -> tuple[set[str], set[str], set[str]]:
    """One-shot index of already-seeded catalog entries (ops + durable).

    Returns (content_sha256s, catalog_evidence_ids, source_item_ids).
    Used only to skip register_upload for unchanged seeds — no persistence changes.
    """
    hashes: set[str] = set()
    catalog_ids: set[str] = set()
    source_items: set[str] = set()

    def _ingest_ops_rec(rec: dict) -> None:
        sha = str(rec.get("sha256") or "")
        if sha:
            hashes.add(sha)
        sid = str(rec.get("source_item_id") or "")
        if sid:
            source_items.add(sid)
        meta = rec.get("metadata") or {}
        if isinstance(meta, dict):
            cid = str(meta.get("catalog_evidence_id") or "")
            if cid:
                catalog_ids.add(cid)
            sha2 = str(meta.get("sha256") or meta.get("content_sha256") or meta.get("content_hash") or "")
            if sha2:
                hashes.add(sha2)

    for rec in evidence_repository:
        _ingest_ops_rec(rec)

    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        for art in ai_repo.all_artifacts():
            sha = str(getattr(art, "content_hash", "") or "")
            if sha:
                hashes.add(sha)
            sid = str(getattr(art, "source_item_id", "") or "")
            if sid:
                source_items.add(sid)
            meta = dict(getattr(art, "metadata", ()) or ())
            cid = str(meta.get("catalog_evidence_id") or "")
            if cid:
                catalog_ids.add(cid)
    except Exception:  # noqa: BLE001
        pass

    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        for candidate in get_persistence().list_all_evidence_versions():
            sha = str(getattr(candidate, "content_hash", "") or "")
            if sha:
                hashes.add(sha)
            sid = str(getattr(candidate, "source_item_id", "") or "")
            if sid:
                source_items.add(sid)
            meta = dict(getattr(candidate, "metadata", ()) or ())
            cid = str(meta.get("catalog_evidence_id") or "")
            if cid:
                catalog_ids.add(cid)
        _prof_add("seed_index_sql_persistence", 0.0, db_reads=1)
    except Exception:  # noqa: BLE001
        pass

    try:
        from ecs_platform.repository.repository import EvidenceRepository

        repo = EvidenceRepository()
        try:
            # One scan covers prior startup seeds (catalog ~702); avoids per-row durable lookups.
            for row in repo.search_evidence(limit=5000):
                meta = _parse_row_metadata(row.get("metadata"))
                sha = str(
                    meta.get("sha256")
                    or meta.get("content_hash")
                    or meta.get("content_sha256")
                    or ""
                )
                if sha:
                    hashes.add(sha)
                cid = str(meta.get("catalog_evidence_id") or "")
                if cid:
                    catalog_ids.add(cid)
                sid = str(row.get("source_object_id") or meta.get("source_item_id") or "")
                if sid:
                    source_items.add(sid)
            _prof_add("seed_index_canonical_pg", 0.0, db_reads=1)
        finally:
            repo.close()
    except Exception:  # noqa: BLE001
        pass

    return hashes, catalog_ids, source_items


def refresh_repository_from_frameworks(source: str = "scheduler"):
    """Seed ops repository from the in-memory framework catalog.

    Unchanged catalog seeds are detected before ``register_upload`` via deterministic
    content hash / catalog identity (avoids incompatible EVD-PCI-* vs EVD-00001 checks).
    """
    global _REFRESH_PROFILE
    import time as _time

    from modules.frameworks.engines.framework_catalog import catalog_stats, get_all_evidence_records

    _t_refresh = _time.perf_counter()
    stats = catalog_stats()
    _REFRESH_PROFILE = {
        "source": source,
        "stages": {},
        "counts": {
            "frameworks": int(stats.get("framework_count", 0) or 0),
            "controls": int(stats.get("control_count", 0) or 0),
            "catalog_evidences": int(stats.get("evidence_count", 0) or 0),
            "rows_seen": 0,
            "rows_skipped_exists": 0,
            "rows_register_called": 0,
            "added": 0,
            "db_reads": 0,
            "db_writes": 0,
        },
    }

    _t0 = _time.perf_counter()
    rows = get_all_evidence_records()
    _prof_add("catalog_read_parse_in_memory", _time.perf_counter() - _t0)
    # FRAMEWORK_CATALOG is already constructed in-process (no Excel I/O here).
    _REFRESH_PROFILE["counts"]["rows_seen"] = len(rows)

    _t0 = _time.perf_counter()
    known_hashes, known_catalog_ids, known_source_items = _collect_present_framework_seed_keys()
    _prof_add("seed_presence_index", _time.perf_counter() - _t0)

    added = 0
    for row in rows:
        catalog_id = str(row.get("evidence_id") or "")
        source_item_id = _framework_seed_source_item_id(catalog_id) if catalog_id else ""
        content = _framework_seed_bytes(row, source)
        content_hash = compute_hash(content)

        _t0 = _time.perf_counter()
        already_present = (
            (content_hash and content_hash in known_hashes)
            or (catalog_id and catalog_id in known_catalog_ids)
            or (source_item_id and source_item_id in known_source_items)
            # Legacy incompatible ID compare kept as a harmless extra check.
            or any(r.get("evidence_id") == catalog_id for r in evidence_repository)
        )
        _prof_add("exists_check_in_memory", _time.perf_counter() - _t0)
        if already_present:
            _REFRESH_PROFILE["counts"]["rows_skipped_exists"] += 1
            continue

        _REFRESH_PROFILE["counts"]["rows_register_called"] += 1
        _t0 = _time.perf_counter()
        result = register_upload(
            filename=row["mock_file"],
            content=content,
            uploaded_by=row["uploaded_by"] if source == "startup" else f"Scheduler ({source})",
            framework=row["framework"],
            application=row["application_name"],
            control=row["control"],
            source_connector="framework_catalog",
            source_item_id=source_item_id,
            metadata={
                "catalog_evidence_id": catalog_id,
                "seed_source": "framework_catalog",
                "collection_source": "framework_catalog",
            },
        )
        _prof_add("register_upload_outer", _time.perf_counter() - _t0)
        if result.get("duplicate"):
            # Same as skip: durable/ops already had this seed; do not mutate [-1] or count as added.
            if content_hash:
                known_hashes.add(content_hash)
            _REFRESH_PROFILE["counts"]["rows_skipped_exists"] += 1
            continue
        if evidence_repository:
            evidence_repository[-1]["evidence_status"] = row.get("evidence_status", "Current")
            evidence_repository[-1]["audit_status"] = row.get("audit_status", "Pending")
            evidence_repository[-1]["reviewer"] = row.get("reviewer", "")
            evidence_repository[-1]["comments"] = row.get("comments", "")
            evidence_repository[-1]["expiry_date"] = row.get("expiry_date", "")
            evidence_repository[-1]["server_name"] = row.get("server_name", "")
            # Keep presence index warm for later rows in this same refresh.
            sha = str(evidence_repository[-1].get("sha256") or content_hash)
            if sha:
                known_hashes.add(sha)
            if catalog_id:
                known_catalog_ids.add(catalog_id)
            if source_item_id:
                known_source_items.add(source_item_id)
        added += 1
    _REFRESH_PROFILE["counts"]["added"] = added
    _REFRESH_PROFILE["counts"]["db_reads"] = int((_REFRESH_PROFILE.get("counts") or {}).get("db_reads", 0) or 0)
    _REFRESH_PROFILE["counts"]["db_writes"] = int((_REFRESH_PROFILE.get("counts") or {}).get("db_writes", 0) or 0)
    total_s = _time.perf_counter() - _t_refresh
    _REFRESH_PROFILE["total_seconds"] = total_s

    try:
        from modules.shared.services import ecs_logging as _ecs_log

        stages = sorted(
            ((_REFRESH_PROFILE.get("stages") or {}).items()),
            key=lambda kv: float((kv[1] or {}).get("seconds", 0) or 0),
            reverse=True,
        )
        _ecs_log.info(
            "ECSStartupProfile",
            f"refresh_repository_from_frameworks total={total_s:.3f}s "
            f"frameworks={_REFRESH_PROFILE['counts']['frameworks']} "
            f"controls={_REFRESH_PROFILE['counts']['controls']} "
            f"catalog_evidences={_REFRESH_PROFILE['counts']['catalog_evidences']} "
            f"register_called={_REFRESH_PROFILE['counts']['rows_register_called']} "
            f"skipped_unchanged={_REFRESH_PROFILE['counts']['rows_skipped_exists']} "
            f"added={added} "
            f"db_reads={_REFRESH_PROFILE['counts'].get('db_reads', 0)} "
            f"db_writes={_REFRESH_PROFILE['counts'].get('db_writes', 0)}",
        )
        for name, bucket in stages:
            _ecs_log.info(
                "ECSStartupProfile",
                f"  stage={name} seconds={float(bucket.get('seconds', 0)):.3f} "
                f"calls={int(bucket.get('calls', 0))}",
            )
    except Exception:  # noqa: BLE001
        pass
    finally:
        # Keep last profile available for tests/diagnostics; clear active flag semantics
        # by leaving the dict populated (read-only after return).
        pass
    return added


def _guess_application(framework: str, control: str) -> str:
    for item in ecs_state.PCI_DSS_MOCK_EVIDENCES:
        if item["control"] == control:
            return item["application"]
    for row in ecs_state.scheduler_data:
        if len(row) >= 2 and row[1] == framework:
            return row[0]
    return "Net Banking"


def generate_summary(record: dict) -> str:
    fw = ", ".join(record["framework_tags"])
    app = ", ".join(record["application_tags"])
    return (
        f"AI Summary: {record['filename']} supports {fw} for {app}. "
        f"Integrity {record['integrity']}. Uploaded by {record['uploaded_by']}."
    )


def get_health_dashboard():
    from modules.executive_overview.engines.demo_metrics import HEALTH_METRICS

    rows = []
    for r in evidence_repository:
        rows.append(
            {
                "evidence_id": r["evidence_id"],
                "filename": r["filename"],
                "sha256": r["sha256"][:16] + "...",
                "full_hash": r["sha256"],
                "integrity": r["integrity"],
                "valid": r["integrity_valid"],
                "framework": ", ".join(r["framework_tags"]),
            }
        )
    valid = sum(1 for r in rows if r["valid"])
    total = max(len(rows), HEALTH_METRICS["total_artifacts"] // 100)
    if not rows:
        total = HEALTH_METRICS["total_artifacts"]
        valid = int(total * HEALTH_METRICS["valid_integrity_pct"] / 100)
    return {
        "rows": rows,
        "total": total if rows else HEALTH_METRICS["total_artifacts"],
        "valid_count": valid if rows else int(HEALTH_METRICS["total_artifacts"] * 0.987),
        "tamper_count": HEALTH_METRICS["tamper_alerts"] if not rows else len(rows) - valid,
        "overdue_count": HEALTH_METRICS["overdue_count"],
        "stale_count": HEALTH_METRICS["stale_count"],
        "valid_pct": HEALTH_METRICS["valid_integrity_pct"],
    }


def get_reuse_graph():
    nodes = []
    edges = []
    for key, info in evidence_reuse_map.items():
        nodes.append({"id": info["group_id"], "label": info["filename"][:30]})
        for i, link in enumerate(info["linked_controls"]):
            target = f"{link['framework']}::{link['control']}"
            edges.append({"from": info["group_id"], "to": target, "label": link["framework"]})
    groups = list(evidence_reuse_map.values())
    if not groups:
        groups = [
            {
                "group_id": "REUSE-001",
                "filename": "PCI_DSS_NETBANKING_20260524_db_tde_report.pdf",
                "linked_controls": [
                    {"framework": "PCI DSS", "control": "Req 3.4 — Encryption at Rest"},
                    {"framework": "DPSC", "control": "Log Monitoring"},
                    {"framework": "DB Baselining", "control": "DB Encryption"},
                ],
            },
            {
                "group_id": "REUSE-002",
                "filename": "CSITE_SIEM_alert_export.csv",
                "linked_controls": [
                    {"framework": "CSITE", "control": "SIEM Alerts"},
                    {"framework": "PCI DSS", "control": "Req 10.6 — Log Review"},
                ],
            },
        ]
    return {"nodes": nodes, "edges": edges, "groups": groups}


def where_else_used(filename: str) -> str:
    key = filename.lower()
    for k, info in evidence_reuse_map.items():
        if k in key or filename.lower() in k:
            links = info["linked_controls"]
            parts = [f"{l['framework']} / {l['control']}" for l in links]
            return "Also used in: " + " | ".join(parts)
    return "No reuse mapping found for that evidence (upload or scheduler pull first)."


def get_summaries():
    return [
        {
            "evidence_id": r["evidence_id"],
            "filename": r["filename"],
            "summary": r["summary"],
            "framework": ", ".join(r["framework_tags"]),
        }
        for r in evidence_repository[-20:]
    ]


def publish_evidence(
    filename: str,
    content: bytes,
    uploaded_by: str,
    framework: str = "",
    application: str = "Net Banking",
    control: str = "",
    **kwargs,
):
    """Canonical write entry for upload/connector bridges.

    Delegates to ``register_upload`` (existing ops repository + audit mirror).
    Callers must use this name; do not introduce a second persistence path.
    """
    return register_upload(
        filename,
        content,
        uploaded_by,
        framework,
        application,
        control,
        **kwargs,
    )
