"""Select a vector store implementation from vectorstore.yaml."""

from __future__ import annotations

from typing import Any

from ecs_platform.config import load_vectorstore_config
from ecs_platform.vectorstore.base import VectorStore, VectorStoreError


def get_vector_store(config: dict[str, Any] | None = None) -> VectorStore:
    cfg = (config or load_vectorstore_config()).get("vectorstore", {})
    provider = cfg.get("provider", "pgvector")
    if provider == "pgvector":
        from ecs_platform.vectorstore.pgvector_store import PgVectorStore
        return PgVectorStore(cfg)
    raise VectorStoreError(
        f"Vector provider '{provider}' is configured but not yet implemented. "
        "pgvector is the supported development backend."
    )
