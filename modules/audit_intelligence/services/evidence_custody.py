"""Evidence content custody — REFERENCE_ONLY (default) and SNAPSHOT modes.

Metadata + version history stay in SQL; immutable bytes are stored in the ECS object
store (MinIO/S3-compatible or local fallback). Never raises to callers.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional

CUSTODY_REFERENCE_ONLY = "REFERENCE_ONLY"
CUSTODY_SNAPSHOT = "SNAPSHOT"

ContentFetcher = Callable[[], bytes | None]


@dataclass(frozen=True)
class CustodyResult:
    custody_mode: str
    content_hash: str
    size_bytes: int
    source_url: str
    source_item_id: str
    source_modified_at: str
    object_uri: str
    stored: bool
    reason: str = ""


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def default_custody_mode() -> str:
    cfg = _custody_config()
    mode = str(
        os.environ.get(
            "ECS_EVIDENCE_CUSTODY_MODE",
            str(cfg.get("mode", CUSTODY_REFERENCE_ONLY)),
        ),
    ).strip().upper()
    return mode if mode in (CUSTODY_REFERENCE_ONLY, CUSTODY_SNAPSHOT) else CUSTODY_REFERENCE_ONLY


def snapshot_enabled() -> bool:
    cfg = _custody_config()
    return _truthy(os.environ.get("ECS_EVIDENCE_SNAPSHOT_ENABLED", str(cfg.get("snapshot_enabled", False))))


def _custody_config() -> dict[str, Any]:
    try:
        from ecs_platform.config import load_repository_config

        repo = load_repository_config().get("repository", {}) or {}
        return dict(repo.get("custody", {}) or {})
    except Exception:  # noqa: BLE001
        return {}


def max_bytes() -> int:
    cfg = _custody_config()
    raw = os.environ.get("ECS_EVIDENCE_MAX_BYTES", str(cfg.get("max_bytes", 52_428_800)))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 52_428_800


def allowed_mime_types() -> set[str]:
    cfg = _custody_config()
    raw = os.environ.get(
        "ECS_EVIDENCE_ALLOWED_MIME_TYPES",
        str(cfg.get(
            "allowed_mime_types",
            "application/pdf,application/json,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
            "text/plain,text/csv,image/png,image/jpeg",
        )),
    )
    return {m.strip().lower() for m in str(raw).split(",") if m.strip()}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reference_fingerprint(
    *,
    source_item_id: str,
    source_url: str,
    source_modified_at: str,
) -> bytes:
    payload = {
        "source_item_id": source_item_id,
        "source_url": source_url,
        "source_modified_at": source_modified_at,
    }
    return json.dumps(payload, sort_keys=True, default=str).encode("utf-8")


def _mime_allowed(mime_type: str, filename: str) -> bool:
    allowed = allowed_mime_types()
    if not allowed:
        return True
    mime = (mime_type or "").strip().lower()
    if mime and mime in allowed:
        return True
    ext = ""
    if "." in (filename or ""):
        ext = filename.rsplit(".", 1)[-1].lower()
    ext_map = {
        "pdf": "application/pdf",
        "json": "application/json",
        "txt": "text/plain",
        "csv": "text/csv",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return ext_map.get(ext, "") in allowed


def resolve_custody(
    *,
    source_connector: str,
    source_item_id: str,
    source_url: str,
    source_modified_at: str,
    filename: str,
    mime_type: str,
    evidence_key: str,
    version: int,
    content: bytes | None = None,
    content_fetcher: Optional[ContentFetcher] = None,
    custody_mode: str | None = None,
) -> CustodyResult:
    """Apply custody policy. Defaults to REFERENCE_ONLY; SNAPSHOT is opt-in."""
    mode = (custody_mode or default_custody_mode()).strip().upper()
    if mode == CUSTODY_SNAPSHOT and not snapshot_enabled():
        mode = CUSTODY_REFERENCE_ONLY

    if mode == CUSTODY_SNAPSHOT:
        body = content
        if body is None and content_fetcher is not None:
            try:
                body = content_fetcher()
            except Exception:  # noqa: BLE001
                body = None
        if not body:
            return _reference_result(
                source_item_id=source_item_id,
                source_url=source_url,
                source_modified_at=source_modified_at,
                reason="snapshot_unavailable",
            )
        if len(body) > max_bytes():
            return _reference_result(
                source_item_id=source_item_id,
                source_url=source_url,
                source_modified_at=source_modified_at,
                content=body,
                reason="size_limit_exceeded",
            )
        if not _mime_allowed(mime_type, filename):
            return _reference_result(
                source_item_id=source_item_id,
                source_url=source_url,
                source_modified_at=source_modified_at,
                content=body,
                reason="mime_type_not_allowed",
            )
        digest = _sha256(body)
        try:
            from ecs_platform.storage import get_object_store, object_key_for_evidence

            store = get_object_store()
            key = object_key_for_evidence(
                source_connector=source_connector or "unknown",
                evidence_key=evidence_key,
                version=version,
                content_hash=digest,
                filename=filename,
            )
            if store.exists(key):
                return CustodyResult(
                    custody_mode=CUSTODY_SNAPSHOT,
                    content_hash=digest,
                    size_bytes=len(body),
                    source_url=source_url,
                    source_item_id=source_item_id,
                    source_modified_at=source_modified_at,
                    object_uri=store.uri_for_key(key),
                    stored=False,
                    reason="immutable_exists",
                )
            uri = store.put_immutable(key, body, content_type=mime_type or "application/octet-stream")
            return CustodyResult(
                custody_mode=CUSTODY_SNAPSHOT,
                content_hash=digest,
                size_bytes=len(body),
                source_url=source_url,
                source_item_id=source_item_id,
                source_modified_at=source_modified_at,
                object_uri=uri,
                stored=True,
            )
        except Exception as exc:  # noqa: BLE001
            return _reference_result(
                source_item_id=source_item_id,
                source_url=source_url,
                source_modified_at=source_modified_at,
                content=body,
                reason=(f"snapshot_store_failed:{type(exc).__name__}:"f"{str(exc)}"),
            )

    return _reference_result(
        source_item_id=source_item_id,
        source_url=source_url,
        source_modified_at=source_modified_at,
        content=content,
    )


def _reference_result(
    *,
    source_item_id: str,
    source_url: str,
    source_modified_at: str,
    content: bytes | None = None,
    reason: str = "",
) -> CustodyResult:
    payload = content if content is not None else _reference_fingerprint(
        source_item_id=source_item_id,
        source_url=source_url,
        source_modified_at=source_modified_at,
    )
    digest = _sha256(payload)
    return CustodyResult(
        custody_mode=CUSTODY_REFERENCE_ONLY,
        content_hash=digest,
        size_bytes=len(payload),
        source_url=source_url,
        source_item_id=source_item_id,
        source_modified_at=source_modified_at,
        object_uri="",
        stored=False,
        reason=reason,
    )
