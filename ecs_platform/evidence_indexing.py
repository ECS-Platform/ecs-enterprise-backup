"""Version-aware evidence indexing into PGVector.

Triggered immediately after durable evidence persistence. Reuses existing text
extraction (repository normalized text), deterministic chunking, and the
configured embedding provider. Never raises to callers on the post-persist hook.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from ecs_platform.vectorstore.base import Chunk, VectorStore, chunk_text


def _text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def bytes_to_text(data: bytes, *, mime_type: str = "", filename: str = "") -> str:
    """Decode evidence bytes the same way the repository mirror does."""
    if not data:
        return ""
    if (mime_type or "").lower() == "application/json":
        try:
            import json

            parsed = json.loads(data.decode("utf-8"))
            return json.dumps(parsed, indent=2, sort_keys=True, default=str)
        except Exception:  # noqa: BLE001
            pass
    return data.decode("utf-8", errors="ignore")


def _metadata_fallback_text(artifact: Any) -> str:
    frameworks = ", ".join(getattr(artifact, "frameworks", ()) or ())
    meta = dict(getattr(artifact, "metadata", ()) or ())
    parts = [
        getattr(artifact, "filename", ""),
        getattr(artifact, "control_id", ""),
        getattr(artifact, "asset_id", ""),
        getattr(artifact, "environment", ""),
        frameworks,
        getattr(artifact, "source_connector", ""),
        getattr(artifact, "verdict", ""),
        getattr(artifact, "source", ""),
    ]
    for key, value in sorted(meta.items()):
        parts.append(f"{key}: {value}")
    return "\n".join(part for part in parts if part)


def _load_snapshot_bytes(artifact: Any) -> bytes | None:
    if getattr(artifact, "custody_mode", "") != "SNAPSHOT":
        return None
    try:
        from ecs_platform.storage import get_object_store, object_key_for_evidence

        store = get_object_store()
        key = object_key_for_evidence(
            source_connector=getattr(artifact, "source_connector", "") or "unknown",
            evidence_key=getattr(artifact, "evidence_key", ""),
            version=int(getattr(artifact, "version", 1) or 1),
            content_hash=getattr(artifact, "content_hash", ""),
            filename=getattr(artifact, "filename", ""),
        )
        return store.get_bytes(key)
    except Exception:  # noqa: BLE001
        return None


def resolve_indexable_text(
    artifact: Any,
    *,
    normalized_text: str = "",
    snapshot_bytes: bytes | None = None,
) -> tuple[str, str]:
    """Resolve indexable text: SNAPSHOT bytes, normalized text, metadata fallback."""
    if getattr(artifact, "custody_mode", "") == "SNAPSHOT":
        body = snapshot_bytes if snapshot_bytes is not None else _load_snapshot_bytes(artifact)
        if body:
            return (
                bytes_to_text(
                    body,
                    mime_type=getattr(artifact, "mime_type", ""),
                    filename=getattr(artifact, "filename", ""),
                ),
                "snapshot",
            )
    text = (normalized_text or "").strip()
    if text:
        return text, "normalized"
    return _metadata_fallback_text(artifact), "metadata"


def _evidence_uid(artifact: Any) -> str:
    eid = (getattr(artifact, "evidence_id", "") or "").strip()
    if eid:
        return eid
    return f"{getattr(artifact, 'evidence_key', 'unknown')}:v{getattr(artifact, 'version', 1)}"


def _chunk_id(artifact: Any, idx: int, piece_hash: str) -> str:
    return f"{_evidence_uid(artifact)}:v{int(getattr(artifact, 'version', 1))}:{idx}:{piece_hash}"


def build_chunk_metadata(artifact: Any, *, text_source: str, piece_hash: str, is_latest: bool) -> dict[str, Any]:
    frameworks = list(getattr(artifact, "frameworks", ()) or ())
    return {
        "evidence_id": getattr(artifact, "evidence_id", ""),
        "evidence_key": getattr(artifact, "evidence_key", ""),
        "version": int(getattr(artifact, "version", 1) or 1),
        "application": getattr(artifact, "asset_id", ""),
        "environment": getattr(artifact, "environment", ""),
        "framework": frameworks[0] if frameworks else "",
        "frameworks": frameworks,
        "control": getattr(artifact, "control_id", ""),
        "connector": getattr(artifact, "source_connector", ""),
        "filename": getattr(artifact, "filename", ""),
        "content_hash": getattr(artifact, "content_hash", ""),
        "custody_mode": getattr(artifact, "custody_mode", "REFERENCE_ONLY"),
        "text_source": text_source,
        "chunk_content_hash": piece_hash,
        "is_latest": is_latest,
        "doc_kind": "evidence_version",
    }


def _is_latest_version(artifact: Any) -> bool:
    try:
        from modules.audit_intelligence.engines import evidence_repository as repo

        latest = repo.get_latest(getattr(artifact, "evidence_key", ""))
        return latest is None or latest.version == getattr(artifact, "version", 1)
    except Exception:  # noqa: BLE001
        return True


def _existing_chunk_hashes(store: VectorStore) -> dict[str, str]:
    try:
        with store._connect().cursor() as cur:  # noqa: SLF001
            cur.execute(
                f"SELECT chunk_id, metadata->>'chunk_content_hash' FROM {store._table}"  # noqa: SLF001
            )
            return {row[0]: (row[1] or "") for row in cur.fetchall()}
    except Exception:  # noqa: BLE001
        return {}


def _indexing_allowed(provider: Any) -> tuple[bool, str]:
    demo = str(os.environ.get("DEMO_MODE", "")).strip().lower() in {"1", "true", "yes", "on"}
    configured = bool(getattr(provider, "configured", lambda: False)())
    if configured:
        return True, ""
    if demo:
        return False, "demo_mode_no_provider"
    return False, "provider_not_configured"


def index_evidence_version(
    artifact: Any,
    *,
    normalized_text: str = "",
    snapshot_bytes: bytes | None = None,
    skip_if_superseded: bool = True,
    force: bool = False,
    provider: Any = None,
    store: VectorStore | None = None,
) -> dict[str, Any]:
    """Index one evidence version into PGVector. Idempotent unless ``force``."""
    from ecs_platform.config import load_vectorstore_config
    from ecs_platform.llm_engine.provider import get_provider
    from ecs_platform.vectorstore import get_vector_store

    report: dict[str, Any] = {
        "ok": False,
        "skipped": False,
        "reason": "",
        "evidence_key": getattr(artifact, "evidence_key", ""),
        "version": int(getattr(artifact, "version", 1) or 1),
        "text_source": "",
        "candidate_chunks": 0,
        "embedded_chunks": 0,
        "skipped_unchanged": 0,
        "errors": [],
    }

    if skip_if_superseded and not _is_latest_version(artifact):
        report.update({"ok": True, "skipped": True, "reason": "superseded"})
        return report

    text, text_source = resolve_indexable_text(
        artifact, normalized_text=normalized_text, snapshot_bytes=snapshot_bytes,
    )
    report["text_source"] = text_source
    if not (text or "").strip():
        report.update({"ok": True, "skipped": True, "reason": "empty_text"})
        return report

    provider = provider or get_provider()
    allowed, allow_reason = _indexing_allowed(provider)
    if not allowed:
        report.update({"ok": True, "skipped": True, "reason": allow_reason})
        return report

    try:
        chunk_cfg = (load_vectorstore_config().get("vectorstore", {}) or {}).get("chunking", {})
    except Exception:  # noqa: BLE001
        chunk_cfg = {}
    size = int(chunk_cfg.get("chunk_size", 1000))
    overlap = int(chunk_cfg.get("chunk_overlap", 150))
    pieces = chunk_text(text, chunk_size=size, overlap=overlap) or [text.strip()]

    store = store or get_vector_store()

    is_latest = _is_latest_version(artifact)
    existing = {} if force else _existing_chunk_hashes(store)
    uid = _evidence_uid(artifact)

    candidates: list[tuple[Chunk, str]] = []
    for idx, piece in enumerate(pieces):
        piece_hash = _text_hash(piece)
        chunk = Chunk(
            chunk_id=_chunk_id(artifact, idx, piece_hash),
            evidence_uid=uid,
            text=piece,
            metadata=build_chunk_metadata(
                artifact, text_source=text_source, piece_hash=piece_hash, is_latest=is_latest,
            ),
        )
        candidates.append((chunk, piece))

    report["candidate_chunks"] = len(candidates)
    to_embed = [
        (chunk, piece)
        for chunk, piece in candidates
        if force or existing.get(chunk.chunk_id) != chunk.metadata["chunk_content_hash"]
    ]
    report["skipped_unchanged"] = len(candidates) - len(to_embed)
    if not to_embed:
        report["ok"] = True
        return report

    try:
        store.init_store()
        embeddings = provider.embed([piece for _chunk, piece in to_embed])
        out_chunks: list[Chunk] = []
        for (chunk, _piece), embedding in zip(to_embed, embeddings):
            chunk.embedding = embedding
            out_chunks.append(chunk)
        store.upsert(out_chunks)
        report["embedded_chunks"] = len(out_chunks)
        report["ok"] = True
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(str(exc))
    return report


def index_after_persist(
    artifact: Any,
    *,
    normalized_text: str = "",
    snapshot_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Best-effort post-persist hook. Skips superseded versions by default."""
    try:
        return index_evidence_version(
            artifact,
            normalized_text=normalized_text,
            snapshot_bytes=snapshot_bytes,
            skip_if_superseded=True,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "skipped": False,
            "reason": "index_failed",
            "errors": [str(exc)],
            "evidence_key": getattr(artifact, "evidence_key", ""),
            "version": int(getattr(artifact, "version", 1) or 1),
        }


def retry_index_evidence(
    evidence_key: str,
    version: int,
    *,
    normalized_text: str = "",
    snapshot_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Force re-embed one persisted version."""
    from modules.audit_intelligence.engines import evidence_repository as repo

    versions = repo.get_versions(evidence_key)
    artifact = next((v for v in versions if v.version == version), None)
    if artifact is None:
        return {"ok": False, "errors": [f"version not found: {evidence_key} v{version}"]}
    return index_evidence_version(
        artifact,
        normalized_text=normalized_text,
        snapshot_bytes=snapshot_bytes,
        skip_if_superseded=False,
        force=True,
    )


def reindex_evidence_versions(
    *,
    evidence_key: str = "",
    include_superseded: bool = False,
    force: bool = False,
    limit: int = 5000,
) -> dict[str, Any]:
    """Bulk reindex persisted evidence versions (latest-only by default)."""
    from modules.audit_intelligence.engines import evidence_repository as repo
    from modules.audit_intelligence.services.persistence import get_persistence

    report: dict[str, Any] = {
        "ok": True,
        "indexed": 0,
        "skipped": 0,
        "errors": [],
        "versions": [],
    }

    try:
        if evidence_key:
            artifacts = repo.get_versions(evidence_key)
        else:
            artifacts = repo.all_artifacts()
            if not artifacts:
                backend = get_persistence()
                list_all = getattr(backend, "list_all_evidence_versions", None)
                if callable(list_all):
                    artifacts = list_all()
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["errors"].append(str(exc))
        return report

    if not include_superseded:
        latest_by_key: dict[str, Any] = {}
        for art in artifacts:
            key = getattr(art, "evidence_key", "")
            if not key:
                continue
            current = latest_by_key.get(key)
            if current is None or art.version > current.version:
                latest_by_key[key] = art
        artifacts = list(latest_by_key.values())

    for art in artifacts[: max(0, limit)]:
        result = index_evidence_version(
            art,
            skip_if_superseded=not include_superseded,
            force=force,
        )
        report["versions"].append(result)
        if result.get("skipped"):
            report["skipped"] += 1
        elif result.get("ok"):
            report["indexed"] += 1
        else:
            report["errors"].extend(result.get("errors", []))
    report["ok"] = not report["errors"]
    return report
