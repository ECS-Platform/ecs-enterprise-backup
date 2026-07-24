"""Vector store contract and shared chunking utility."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class VectorStoreError(RuntimeError):
    pass


@dataclass
class Chunk:
    chunk_id: str
    evidence_uid: str
    text: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    chunk_id: str
    evidence_uid: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split text into overlapping windows on word boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    words = text.split()
    chunks, current, length = [], [], 0
    for word in words:
        current.append(word)
        length += len(word) + 1
        if length >= chunk_size:
            chunks.append(" ".join(current))
            # carry overlap words forward
            carry, carry_len = [], 0
            for w in reversed(current):
                if carry_len >= overlap:
                    break
                carry.insert(0, w)
                carry_len += len(w) + 1
            current, length = carry, carry_len
    if current:
        chunks.append(" ".join(current))
    return chunks


class VectorStore(ABC):
    @abstractmethod
    def init_store(self) -> None: ...

    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> int: ...

    @abstractmethod
    def search(self, embedding: list[float], *, top_k: int = 8,
               filters: dict[str, Any] | None = None) -> list[SearchHit]: ...

    @abstractmethod
    def delete_for_evidence(self, evidence_uid: str) -> None: ...

    @abstractmethod
    def delete_stale_managed_chunks(
        self,
        candidate_chunk_ids: set[str],
        *,
        managed_doc_kinds: tuple[str, ...] = ("evidence", "governance"),
    ) -> int:
        """Remove managed corpus rows whose chunk_id is no longer a reindex candidate."""
        ...
