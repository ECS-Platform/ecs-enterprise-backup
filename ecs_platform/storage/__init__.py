"""ECS object storage for evidence custody (MinIO/S3-compatible + local fallback)."""

from ecs_platform.storage.object_store import (
    EvidenceObjectStore,
    LocalObjectStore,
    get_object_store,
    object_key_for_evidence,
    reset_object_store,
    set_object_store,
)

__all__ = [
    "EvidenceObjectStore",
    "LocalObjectStore",
    "get_object_store",
    "object_key_for_evidence",
    "reset_object_store",
    "set_object_store",
]
