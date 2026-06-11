"""Vector store abstraction for semantic evidence search."""

from ecs_platform.vectorstore.base import Chunk, SearchHit, VectorStore, VectorStoreError, chunk_text
from ecs_platform.vectorstore.factory import get_vector_store

__all__ = ["VectorStore", "VectorStoreError", "Chunk", "SearchHit", "chunk_text", "get_vector_store"]
