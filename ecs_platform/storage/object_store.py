"""Minimal evidence object store (MinIO/S3-compatible with local fallback).

Reuses ``repository.yaml`` / ``load_repository_config()`` object_store settings.
No large bodies are written to PostgreSQL — immutable evidence bytes live here only.
"""

from __future__ import annotations

import os
import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional

_STORE: Optional["EvidenceObjectStore"] = None
_STORE_LOCK = threading.RLock()


def _sanitize(segment: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (segment or "unknown").strip())
    return cleaned[:120] or "unknown"


def object_key_for_evidence(
    *,
    source_connector: str,
    evidence_key: str,
    version: int,
    content_hash: str,
    filename: str,
) -> str:
    """Immutable object path: evidence/{connector}/{key}/v{N}/{hash}_{file}."""
    key_part = _sanitize(evidence_key.replace("::", "--"))
    hash_prefix = (content_hash or "nohash")[:16]
    fname = _sanitize(filename or "artifact.bin")
    return (
        f"evidence/{_sanitize(source_connector)}/{key_part}/"
        f"v{max(1, int(version))}/{hash_prefix}_{fname}"
    )


class EvidenceObjectStore(ABC):
    """Store immutable evidence object bytes outside PostgreSQL."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def put_immutable(self, key: str, body: bytes, *, content_type: str = "") -> str:
        """Write once; raise ``FileExistsError`` when the key already exists."""

    @abstractmethod
    def uri_for_key(self, key: str) -> str:
        ...

    @abstractmethod
    def get_bytes(self, key: str) -> bytes | None:
        """Return object bytes when present; ``None`` when missing or unreadable."""
        ...


class LocalObjectStore(EvidenceObjectStore):
    """Filesystem-backed store for tests and offline/demo fallback."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._root / key

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def put_immutable(self, key: str, body: bytes, *, content_type: str = "") -> str:
        path = self._path(key)
        if path.exists():
            raise FileExistsError(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return self.uri_for_key(key)

    def uri_for_key(self, key: str) -> str:
        return f"file://{self._path(key).resolve()}"

    def get_bytes(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            return path.read_bytes()
        except Exception:  # noqa: BLE001
            return None


class S3ObjectStore(EvidenceObjectStore):
    """S3/MinIO-compatible store using boto3 when available."""

    def __init__(self, *, endpoint: str, bucket: str, access_key: str,
                 secret_key: str, secure: bool = False) -> None:
        self._bucket = bucket
        self._endpoint = endpoint
        self._secure = secure
        self._access_key = access_key
        self._secret_key = secret_key
        self._client = None

    def _client_or_create(self):
        if self._client is not None:
            return self._client
        import boto3  # type: ignore
        from botocore.client import Config  # type: ignore

        endpoint_url = f"http{'s' if self._secure else ''}://{self._endpoint}"
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        return self._client

    def exists(self, key: str) -> bool:
        try:
            self._client_or_create().head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False

    def put_immutable(self, key: str, body: bytes, *, content_type: str = "") -> str:
        if self.exists(key):
            raise FileExistsError(key)
        kwargs: dict[str, Any] = {"Bucket": self._bucket, "Key": key, "Body": body}
        if content_type:
            kwargs["ContentType"] = content_type
        self._client_or_create().put_object(**kwargs)
        return self.uri_for_key(key)

    def uri_for_key(self, key: str) -> str:
        scheme = "https" if self._secure else "http"
        return f"{scheme}://{self._endpoint}/{self._bucket}/{key}"

    def get_bytes(self, key: str) -> bytes | None:
        try:
            response = self._client_or_create().get_object(Bucket=self._bucket, Key=key)
            body = response.get("Body")
            return body.read() if body is not None else None
        except Exception:  # noqa: BLE001
            return None


def _default_local_root() -> Path:
    return Path(os.environ.get("ECS_EVIDENCE_OBJECT_STORE_FALLBACK", "./data/evidence-objects"))


def _build_default_store() -> EvidenceObjectStore:
    from ecs_platform.config import load_repository_config, resolve_secret

    cfg = (load_repository_config().get("repository", {}) or {}).get("object_store", {})
    if not bool(cfg.get("enabled", True)):
        return LocalObjectStore(_default_local_root())
    access_key = resolve_secret(str(cfg.get("access_key_env", "MINIO_ACCESS_KEY")))
    secret_key = resolve_secret(str(cfg.get("secret_key_env", "MINIO_SECRET_KEY")))
    if access_key and secret_key:
        try:
            return S3ObjectStore(
                endpoint=str(cfg.get("endpoint", "minio:9000")),
                bucket=str(cfg.get("bucket", "ecs-evidence")),
                access_key=access_key,
                secret_key=secret_key,
                secure=bool(cfg.get("secure", False)),
            )
        except Exception:  # noqa: BLE001 - fall back to local store
            pass
    return LocalObjectStore(_default_local_root())


def get_object_store() -> EvidenceObjectStore:
    """Return the process-wide evidence object store (lazy default)."""
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = _build_default_store()
        return _STORE


def set_object_store(store: Optional[EvidenceObjectStore]) -> None:
    """Install a store backend (tests / explicit wiring). ``None`` resets."""
    global _STORE
    with _STORE_LOCK:
        _STORE = store


def reset_object_store() -> None:
    set_object_store(None)
