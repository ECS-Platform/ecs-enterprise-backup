"""Instrumentation-only patch for refresh_repository_from_frameworks profiling."""
from pathlib import Path

path = Path("modules/operations/engines/evidence_repository.py")
text = path.read_text(encoding="utf-8")

# --- insert profile helpers after imports ---
marker = "from app import ecs_state\n\nevidence_repository = []\n"
helper = '''from app import ecs_state

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
'''

if marker not in text:
    raise SystemExit("import marker not found")
if "_REFRESH_PROFILE" not in text:
    text = text.replace(marker, helper, 1)

# --- instrument _find_durable_by_sha256 DB paths ---
old_durable = '''def _find_durable_by_sha256(sha256: str) -> dict | None:
    """Look up identical content in audit memory/SQL and canonical PostgreSQL."""
    if not sha256:
        return None
    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        for art in ai_repo.all_artifacts():
            if str(getattr(art, "content_hash", "") or "") == sha256:
                return _ops_record_from_artifact(art)
    except Exception:  # noqa: BLE001
        pass
    try:
        from modules.audit_intelligence.services.persistence import get_persistence

        for candidate in get_persistence().list_all_evidence_versions():
            if str(getattr(candidate, "content_hash", "") or "") == sha256:
                return _ops_record_from_artifact(candidate)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ecs_platform.repository.repository import EvidenceRepository

        repo = EvidenceRepository()
        try:
            for row in repo.search_evidence(limit=500):
                meta = _parse_row_metadata(row.get("metadata"))
                if str(meta.get("sha256") or meta.get("content_hash") or meta.get("content_sha256") or "") == sha256:
                    return _ops_record_from_canonical_row(row)
        finally:
            repo.close()
    except Exception:  # noqa: BLE001
        pass
    return None
'''

new_durable = '''def _find_durable_by_sha256(sha256: str) -> dict | None:
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
'''

if old_durable not in text:
    raise SystemExit("durable block not found")
text = text.replace(old_durable, new_durable, 1)

# --- instrument register_upload stages (only when profile active) ---
old_reg_start = '''    content_bytes = content or b""
    content_hash = compute_hash(content_bytes)
    meta_in = dict(metadata or {})
    substantive_hash = meta_in.get("substantive_content_sha256") or meta_in.get("canonical_fingerprint")
    if not allow_duplicate:
        existing = find_upload_by_sha256(content_hash)
'''

new_reg_start = '''    import time as _time

    _prof = _REFRESH_PROFILE is not None
    _t_all = _time.perf_counter() if _prof else 0.0
    content_bytes = content or b""
    _t0 = _time.perf_counter() if _prof else 0.0
    content_hash = compute_hash(content_bytes)
    meta_in = dict(metadata or {})
    substantive_hash = meta_in.get("substantive_content_sha256") or meta_in.get("canonical_fingerprint")
    if not allow_duplicate:
        existing = find_upload_by_sha256(content_hash)
'''

if old_reg_start not in text:
    raise SystemExit("register_upload start not found")
text = text.replace(old_reg_start, new_reg_start, 1)

# After first early return for duplicate - add profiling before returns is hard.
# Instead wrap the major mid-function stages.

old_enrich = '''    try:
        from modules.shared.services.evidence_authoritative_reader import _enrich_fcm_mappings

        record["metadata"] = _enrich_fcm_mappings(
            record["metadata"],
            framework=framework or "Cross-Framework",
            control=control,
        )
    except Exception:  # noqa: BLE001
        pass
    custody = _apply_custody(record, content or b"", application, control)
'''

new_enrich = '''    if _prof:
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
'''

if old_enrich not in text:
    raise SystemExit("enrich/custody block not found")
text = text.replace(old_enrich, new_enrich, 1)

old_mirror = '''    evidence_repository.append(record)
    # Mirror the upload into the audit-intelligence evidence repository so manual /
    # bulk uploads become real evidence for readiness, reuse, dashboards, and
    # integrity — instead of living only in this MVP in-memory list. Best-effort:
    # a bridge failure must never break the primary upload path.
    _mirror_to_audit_repository(record, content or b"", framework, application, control)
    record["search_index"] = _register_search_index(record, content or b"")
'''

new_mirror = '''    evidence_repository.append(record)
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
'''

if old_mirror not in text:
    raise SystemExit("mirror block not found")
text = text.replace(old_mirror, new_mirror, 1)

old_return = '''    _link_reuse(record)
    return record


def _apply_custody(record, content: bytes, application: str, control: str):
'''

new_return = '''    _link_reuse(record)
    if _prof:
        _prof_add("audit_trail_and_reuse", _time.perf_counter() - _t0)
        _prof_add("register_upload_total", _time.perf_counter() - _t_all, register_accepted=1)
    return record


def _apply_custody(record, content: bytes, application: str, control: str):
'''

if old_return not in text:
    raise SystemExit("return/link_reuse block not found")
text = text.replace(old_return, new_return, 1)

# Profile early duplicate returns in register_upload
old_dup1 = '''        if existing is not None:
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
'''

new_dup1 = '''        if existing is not None:
            if _prof:
                _prof_add("hash_and_dedup_check", _time.perf_counter() - _t0, register_attempts=1, duplicates_sha=1)
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
'''

if old_dup1 not in text:
    raise SystemExit("dup sha block not found")
text = text.replace(old_dup1, new_dup1, 1)

# --- replace refresh_repository_from_frameworks ---
old_refresh = '''def refresh_repository_from_frameworks(source: str = "scheduler"):
    from modules.frameworks.engines.framework_catalog import get_all_evidence_records

    added = 0
    for row in get_all_evidence_records():
        exists = any(r.get("evidence_id") == row["evidence_id"] for r in evidence_repository)
        if exists:
            continue
        content = f"{row['framework']}|{row['control']}|{row['evidence_name']}|{source}".encode()
        register_upload(
            filename=row["mock_file"],
            content=content,
            uploaded_by=row["uploaded_by"] if source == "startup" else f"Scheduler ({source})",
            framework=row["framework"],
            application=row["application_name"],
            control=row["control"],
        )
        if evidence_repository:
            evidence_repository[-1]["evidence_status"] = row.get("evidence_status", "Current")
            evidence_repository[-1]["audit_status"] = row.get("audit_status", "Pending")
            evidence_repository[-1]["reviewer"] = row.get("reviewer", "")
            evidence_repository[-1]["comments"] = row.get("comments", "")
            evidence_repository[-1]["expiry_date"] = row.get("expiry_date", "")
            evidence_repository[-1]["server_name"] = row.get("server_name", "")
        added += 1
    return added
'''

new_refresh = '''def refresh_repository_from_frameworks(source: str = "scheduler"):
    """Seed ops repository from the in-memory framework catalog.

    Instrumentation: when called, emits a stage timing breakdown via ecs_logging
    (no behavior change).
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

    added = 0
    for row in rows:
        _t0 = _time.perf_counter()
        exists = any(r.get("evidence_id") == row["evidence_id"] for r in evidence_repository)
        _prof_add("exists_check_in_memory", _time.perf_counter() - _t0)
        if exists:
            _REFRESH_PROFILE["counts"]["rows_skipped_exists"] += 1
            continue
        content = f"{row['framework']}|{row['control']}|{row['evidence_name']}|{source}".encode()
        _REFRESH_PROFILE["counts"]["rows_register_called"] += 1
        _t0 = _time.perf_counter()
        register_upload(
            filename=row["mock_file"],
            content=content,
            uploaded_by=row["uploaded_by"] if source == "startup" else f"Scheduler ({source})",
            framework=row["framework"],
            application=row["application_name"],
            control=row["control"],
        )
        _prof_add("register_upload_outer", _time.perf_counter() - _t0)
        if evidence_repository:
            evidence_repository[-1]["evidence_status"] = row.get("evidence_status", "Current")
            evidence_repository[-1]["audit_status"] = row.get("audit_status", "Pending")
            evidence_repository[-1]["reviewer"] = row.get("reviewer", "")
            evidence_repository[-1]["comments"] = row.get("comments", "")
            evidence_repository[-1]["expiry_date"] = row.get("expiry_date", "")
            evidence_repository[-1]["server_name"] = row.get("server_name", "")
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
'''

if old_refresh not in text:
    raise SystemExit("refresh function not found")
text = text.replace(old_refresh, new_refresh, 1)

path.write_text(text, encoding="utf-8")
print("instrumentation applied")
