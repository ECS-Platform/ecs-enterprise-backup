"""Evidence repository: bulk upload, metadata, hashes, lifecycle, reuse."""

import hashlib
import re
from datetime import datetime, timezone

from app import ecs_state

evidence_repository = []
upload_tracker = []
evidence_reuse_map = {}
_evidence_counter = 0


def _next_id():
    global _evidence_counter
    _evidence_counter += 1
    return f"EVD-{_evidence_counter:05d}"


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


def find_upload_by_sha256(sha256: str) -> dict | None:
    """Return an existing ops-repository upload with the same content hash."""
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
    return None


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
    for rec in evidence_repository:
        meta = rec.get("metadata") or {}
        if meta.get("canonical_fingerprint") == canonical_hash:
            return rec
    return None


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
    content_bytes = content or b""
    content_hash = compute_hash(content_bytes)
    if not allow_duplicate:
        existing = find_upload_by_sha256(content_hash)
        if existing is not None:
            dup = dict(existing)
            dup["status"] = "DUPLICATE"
            dup["duplicate"] = True
            dup["duplicate_kind"] = "sha256"
            dup["original_evidence_id"] = existing.get("evidence_id", "")
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
    try:
        from modules.shared.services.evidence_authoritative_reader import _enrich_fcm_mappings

        record["metadata"] = _enrich_fcm_mappings(
            record["metadata"],
            framework=framework or "Cross-Framework",
            control=control,
        )
    except Exception:  # noqa: BLE001
        pass
    custody = _apply_custody(record, content or b"", application, control)
    file_hash = custody.content_hash
    integrity = integrity_check(file_hash, content or b"")
    record["sha256"] = file_hash
    record["integrity"] = integrity["status"]
    record["integrity_valid"] = integrity["valid"]
    record["custody_mode"] = custody.custody_mode
    record["object_uri"] = custody.object_uri
    record["size_bytes"] = custody.size_bytes
    record["summary"] = generate_summary(record)
    record["reviewer"] = "Pending Assignment"
    evidence_repository.append(record)
    # Mirror the upload into the audit-intelligence evidence repository so manual /
    # bulk uploads become real evidence for readiness, reuse, dashboards, and
    # integrity — instead of living only in this MVP in-memory list. Best-effort:
    # a bridge failure must never break the primary upload path.
    _mirror_to_audit_repository(record, content or b"", framework, application, control)
    record["search_index"] = _register_search_index(record, content or b"")
    from modules.shared.services.audit_trail import log_event, record_version

    record_version(record["evidence_id"], std_name, 1, uploaded_by)
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
    dup_peers = [
        r for r in evidence_repository[:-1]
        if r.get("sha256") == sha and r.get("evidence_id") != record.get("evidence_id")
    ]
    if dup_peers:
        return {
            "indexed": False,
            "reason": "duplicate_content",
            "existing_evidence_id": dup_peers[0].get("evidence_id"),
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
        return {"indexed": bool(report.get("ok")), **report}
    except Exception as exc:  # noqa: BLE001
        return {"indexed": False, "reason": str(exc)}


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
        ai_repo.store_evidence(
            control_id=control or record.get("filename", "UPLOAD"),
            content=text or record.get("summary", ""),
            technology=technology,
            asset_id=application or "",
            frameworks=frameworks,
            verdict="",                       # manual uploads are unassessed until validated
            control_status="",
            source="manual_upload" if not record.get("source_connector") else "connector",
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
        )
        record["audit_repository_synced"] = True
    except Exception:  # noqa: BLE001 - bridge must never break the primary upload
        record["audit_repository_synced"] = False


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


def refresh_repository_from_frameworks(source: str = "scheduler"):
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
