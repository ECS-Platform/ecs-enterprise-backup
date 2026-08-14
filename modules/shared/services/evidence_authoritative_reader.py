"""Authoritative Phase-1 evidence read facade — no duplicate persistence.

Consumers (Evidence Search, chatbot queries, repository APIs, audit exports)
must read persisted ECS metadata through this module. Writes continue to flow
via ``operations.evidence_repository.register_upload`` → audit mirror → SQL.
"""

from __future__ import annotations

from typing import Any

from modules.operations.engines import evidence_repository as ops_repo


def _meta_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (list, tuple)):
        return {str(k): str(v) for k, v in value}
    return {}


def _workflow_status(record: dict) -> str:
    from modules.shared.services.common_evidence_queries import _workflow_status as _wf

    return _wf(record)


def _fcm_framework_resolve_candidates(framework: str) -> list[str]:
    """Candidate keys for FCM id/alias resolution (preserves display names)."""
    raw = str(framework or "").strip()
    if not raw:
        return []
    slug = raw.lower().replace(" ", "_").replace("-", "_")
    candidates: list[str] = []
    for key in (raw, slug):
        if key and key not in candidates:
            candidates.append(key)
    # "OS Baselining" → slug os_baselining; FCM id is os_baseline.
    if slug.endswith("_baselining"):
        alt = f"{slug[: -len('baselining')]}baseline"
        if alt not in candidates:
            candidates.append(alt)
    return candidates


def _resolve_fcm_framework_doc(repo: Any, framework: str) -> tuple[str, dict[str, Any] | None]:
    """Resolve framework string to (framework_id, doc); empty when unknown."""
    raw = str(framework or "").strip()
    if not raw:
        return "", None
    for candidate in _fcm_framework_resolve_candidates(raw):
        fw_id = repo.resolve_framework_id(candidate)
        doc = repo.get_framework(fw_id)
        if doc:
            resolved = str((doc.get("framework") or {}).get("id") or fw_id)
            return resolved, doc
    raw_l = raw.lower()
    slug_l = raw_l.replace(" ", "_").replace("-", "_")
    for summary in repo.list_framework_summaries():
        names = {
            str(summary.get("id") or "").lower(),
            str(summary.get("code") or "").lower(),
            str(summary.get("name") or "").lower(),
            str(summary.get("display_name") or "").lower(),
        }
        if raw_l in names or slug_l in names:
            fw_id = str(summary.get("id") or "")
            doc = repo.get_framework(fw_id) if fw_id else None
            if doc:
                return fw_id, doc
    return "", None


def _enrich_fcm_mappings(meta: dict[str, Any], *, framework: str, control: str) -> dict[str, Any]:
    """Best-effort FCM policy / procedure / evidence-requirement tags."""
    if meta.get("fcm_control_id") or meta.get("policy_refs"):
        return meta
    if not framework or not control:
        return meta
    try:
        from modules.frameworks.repositories.framework_control_repository import (
            get_framework_control_repository,
        )

        repo = get_framework_control_repository()
        fw_id, doc = _resolve_fcm_framework_doc(repo, framework)
        if not doc:
            return meta
        controls = doc.get("controls") or []
        match = next(
            (
                c
                for c in controls
                if str(c.get("id") or "") == control
                or control in str(c.get("title") or "")
                or str(c.get("title") or "") in control
            ),
            None,
        )
        if not match:
            return meta
        out = dict(meta)
        out.setdefault("fcm_framework_id", fw_id)
        out.setdefault("fcm_control_id", match.get("id"))
        out.setdefault("policy_refs", list(match.get("policy_refs") or []))
        out.setdefault(
            "procedure_ids",
            [p.get("id") for p in (match.get("procedures") or []) if p.get("id")],
        )
        out.setdefault(
            "evidence_requirement_ids",
            [e.get("id") for e in (match.get("evidence_requirements") or []) if e.get("id")],
        )
        return out
    except Exception:  # noqa: BLE001
        return meta


def _ops_row(rec: dict) -> dict[str, Any]:
    meta = _enrich_fcm_mappings(
        _meta_dict(rec.get("metadata")),
        framework=str((rec.get("framework_tags") or [""])[0]),
        control=str(rec.get("control") or ""),
    )
    framework = str((rec.get("framework_tags") or ["Cross-Framework"])[0])
    application = str((rec.get("application_tags") or ["Net Banking"])[0])
    control = str(rec.get("control") or meta.get("control_id") or "")
    row = dict(rec)
    row["metadata"] = meta
    row["application"] = application
    row["framework"] = framework
    row["control_id"] = control
    # Template + /versions API key by evidence_key (asset::control), not evidence_id.
    row["evidence_key"] = str(
        rec.get("evidence_key")
        or _derive_evidence_key(application, control or str(rec.get("filename") or "UPLOAD"))
    )
    sha = str(rec.get("sha256") or meta.get("sha256") or meta.get("content_sha256") or "")
    row["checksum"] = str(rec.get("checksum") or (sha[:8] if sha else ""))
    # Prefer audit mirror version when present so UI matches version history.
    row["version"] = int(rec.get("audit_version") or rec.get("version") or meta.get("audit_version") or 1)
    if rec.get("display_evidence_id"):
        row["display_evidence_id"] = str(rec.get("display_evidence_id"))
    elif meta.get("display_evidence_id"):
        row["display_evidence_id"] = str(meta.get("display_evidence_id"))
    row["collection_source"] = (
        meta.get("collection_source") or rec.get("source_connector") or meta.get("source_type") or ""
    )
    row["environment"] = str(rec.get("environment") or meta.get("environment") or "")
    row["collected_at"] = str(rec.get("uploaded_at") or meta.get("collected_at") or "")
    row["object_key"] = meta.get("object_key") or rec.get("object_uri") or ""
    row["object_reference"] = row["object_key"] or rec.get("object_uri") or ""
    row["file_location"] = row["object_key"] or rec.get("source_url") or ""
    row["workflow_status"] = _workflow_status(rec)
    row["approval_status"] = meta.get("approval_status") or row["workflow_status"]
    row["review_status"] = meta.get("review_status") or row["workflow_status"]
    row["audit_status"] = rec.get("audit_status") or meta.get("audit_status") or row["workflow_status"]
    row["lifecycle"] = rec.get("lifecycle") or meta.get("lifecycle") or "Draft"
    row["source_type"] = meta.get("source_type") or rec.get("source_connector") or ""
    return row


def _derive_evidence_key(application: str, control: str) -> str:
    """Match audit-repo keying used by register_upload / store_evidence."""
    try:
        from modules.audit_intelligence.engines.evidence_repository import make_evidence_key

        return make_evidence_key(application, control)
    except Exception:  # noqa: BLE001
        asset = (application or "global").strip() or "global"
        return f"{asset}::{control}".strip(":")


def _artifact_row(art) -> dict[str, Any]:
    meta = _enrich_fcm_mappings(
        _meta_dict(getattr(art, "metadata", ()) or ()),
        framework=", ".join(getattr(art, "frameworks", ()) or ()),
        control=str(getattr(art, "control_id", "") or ""),
    )
    frameworks = list(getattr(art, "frameworks", ()) or ())
    framework = frameworks[0] if frameworks else str(meta.get("framework") or "Cross-Framework")
    application = str(getattr(art, "asset_id", "") or meta.get("application") or "Net Banking")
    evidence_id = str(getattr(art, "evidence_id", "") or "")
    control = str(getattr(art, "control_id", "") or meta.get("control_id") or "")
    evidence_key = str(
        getattr(art, "evidence_key", "")
        or _derive_evidence_key(application, control or str(getattr(art, "filename", "") or "UPLOAD"))
    )
    content_hash = str(getattr(art, "content_hash", "") or meta.get("content_sha256") or "")
    checksum = str(getattr(art, "checksum", "") or (content_hash[:8] if content_hash else ""))
    workflow_status = str(
        meta.get("workflow_status") or meta.get("validation_verdict") or "Collected"
    )
    display_id = str(meta.get("display_evidence_id") or "")
    row = {
        "evidence_id": evidence_id,
        "evidence_key": evidence_key,
        "filename": str(getattr(art, "filename", "") or evidence_id),
        "original_filename": meta.get("original_filename") or getattr(art, "filename", ""),
        "framework_tags": frameworks or [framework],
        "application_tags": [application],
        "framework": framework,
        "application": application,
        "control": control,
        "control_id": control,
        "technology": str(getattr(art, "technology", "") or meta.get("technology") or ""),
        "verdict": str(getattr(art, "verdict", "") or meta.get("verdict") or ""),
        "uploaded_by": meta.get("uploaded_by") or meta.get("collected_by") or "System",
        "uploaded_at": str(getattr(art, "collected_at", "") or ""),
        "collected_at": str(getattr(art, "collected_at", "") or ""),
        "sha256": content_hash,
        "checksum": checksum,
        "version": int(getattr(art, "version", 1) or 1),
        "custody_mode": str(getattr(art, "custody_mode", "") or meta.get("custody_mode") or ""),
        "object_uri": str(getattr(art, "object_uri", "") or meta.get("object_uri") or ""),
        "object_key": str(meta.get("object_key") or getattr(art, "object_uri", "") or ""),
        "object_reference": str(meta.get("object_key") or getattr(art, "object_uri", "") or ""),
        "file_location": str(meta.get("object_key") or getattr(art, "object_uri") or getattr(art, "source_url", "") or ""),
        "source_connector": str(getattr(art, "source_connector", "") or meta.get("source_connector") or ""),
        "source_url": str(getattr(art, "source_url", "") or meta.get("web_url") or ""),
        "source_item_id": str(getattr(art, "source_item_id", "") or ""),
        "environment": str(getattr(art, "environment", "") or meta.get("environment") or ""),
        "mime_type": str(getattr(art, "mime_type", "") or meta.get("mime_type") or ""),
        "metadata": meta,
        "collection_source": meta.get("collection_source") or getattr(art, "source_connector", "") or getattr(art, "source", ""),
        "audit_repository_synced": True,
        "integrity_valid": True,
        "lifecycle": meta.get("lifecycle") or "Collected",
        "status": workflow_status,
        "workflow_status": workflow_status,
        "approval_status": meta.get("approval_status") or workflow_status,
        "review_status": meta.get("review_status") or workflow_status,
        "audit_status": meta.get("audit_status") or workflow_status,
        "tags": list(getattr(art, "tags", ()) or ()),
    }
    if display_id:
        row["display_evidence_id"] = display_id
    row["workflow_status"] = _workflow_status(row)
    row["approval_status"] = meta.get("approval_status") or row["workflow_status"]
    row["review_status"] = meta.get("review_status") or row["workflow_status"]
    row["audit_status"] = meta.get("audit_status") or row["workflow_status"]
    return row


def collect_authoritative_evidence_rows(*, latest_only: bool = True) -> list[dict[str, Any]]:
    """Merge ops uploads with audit-repository artifacts (hydrated SQL/canonical)."""
    by_id: dict[str, dict[str, Any]] = {}
    for rec in ops_repo.evidence_repository:
        row = _ops_row(rec)
        eid = str(row.get("evidence_id") or "")
        if eid:
            by_id[eid] = row

    try:
        from modules.audit_intelligence.engines import evidence_repository as ai_repo

        artifacts = ai_repo.search(latest_only=latest_only)
    except Exception:  # noqa: BLE001
        artifacts = []

    for art in artifacts:
        eid = str(getattr(art, "evidence_id", "") or "")
        if not eid:
            continue
        existing = by_id.get(eid)
        if existing is None:
            by_id[eid] = _artifact_row(art)
            continue
        merged = dict(existing)
        art_row = _artifact_row(art)
        merged["version"] = max(
            int(merged.get("version") or 1),
            int(art_row.get("version") or 1),
        )
        for key in (
            "evidence_key",
            "checksum",
            "technology",
            "verdict",
            "custody_mode",
            "object_uri",
            "object_key",
            "object_reference",
            "file_location",
            "sha256",
            "collected_at",
            "display_evidence_id",
            "mime_type",
            "source_url",
            "source_connector",
            # Ops upload records carry framework_tags/application_tags but never a
            # flat ``tags`` list — that only exists on the audit artifact. Without
            # this the merged row drops tags entirely and the repository detail
            # modal renders an empty Tags field for every manual/bulk upload.
            "tags",
        ):
            if not merged.get(key) and art_row.get(key):
                merged[key] = art_row[key]
        merged["audit_repository_synced"] = True
        # Ops metadata wins on conflict; fill gaps from audit artifact.
        meta = {**_meta_dict(art_row.get("metadata")), **_meta_dict(merged.get("metadata"))}
        merged["metadata"] = meta
        by_id[eid] = merged

    return list(by_id.values())


def get_authoritative_evidence(evidence_id: str) -> dict[str, Any] | None:
    needle = str(evidence_id or "").strip()
    if not needle:
        return None
    for row in collect_authoritative_evidence_rows():
        if str(row.get("evidence_id") or "") == needle:
            return row
        if str(row.get("display_evidence_id") or "") == needle:
            return row
        if str(row.get("repository_id") or "") == needle:
            return row
        meta = _meta_dict(row.get("metadata"))
        if str(meta.get("display_evidence_id") or "") == needle:
            return row
        if str(meta.get("evidence_id") or "") == needle:
            return row
    return None


def repository_stats() -> dict[str, Any]:
    rows = collect_authoritative_evidence_rows()
    indexed = sum(1 for r in rows if (r.get("search_index") or {}).get("indexed"))
    duplicates = sum(1 for r in rows if str(r.get("status", "")).upper() == "DUPLICATE")
    return {
        "total_records": len(rows),
        "indexed_for_search": indexed,
        "duplicate_records": duplicates,
        "with_object_storage": sum(1 for r in rows if r.get("object_uri") or r.get("object_key")),
        "frameworks": len({r.get("framework") for r in rows if r.get("framework")}),
        "applications": len({r.get("application") for r in rows if r.get("application")}),
    }
