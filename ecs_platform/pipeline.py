"""Evidence collection pipeline: connector -> repository -> vector index.

Ties the platform layers together. Each stage degrades gracefully: a failure in
embedding/indexing does not lose the persisted evidence, and a sync summary is
always returned for the health dashboard.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from ecs_platform.config import load_vectorstore_config
from ecs_platform.connectors import ConnectorFactory
from ecs_platform.repository import EvidenceRepository


@dataclass
class PipelineResult:
    connector: str
    ok: bool
    collected: int = 0
    persisted: int = 0
    indexed: int = 0
    error: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class EvidencePipeline:
    def __init__(self, repository: EvidenceRepository | None = None,
                 factory: ConnectorFactory | None = None):
        self._repo = repository or EvidenceRepository()
        self._factory = factory or ConnectorFactory()
        chunk_cfg = (load_vectorstore_config().get("vectorstore", {}) or {}).get("chunking", {})
        self._chunk_size = int(chunk_cfg.get("chunk_size", 1000))
        self._overlap = int(chunk_cfg.get("chunk_overlap", 150))

    def collect(self, connector_name: str, *, index: bool = True) -> PipelineResult:
        result = PipelineResult(connector=connector_name, ok=False)
        try:
            connector = self._factory.create(connector_name)
        except KeyError as exc:
            result.error = str(exc)
            return result

        summary = connector.sync()
        result.collected = summary.get("collected", 0)
        if not summary.get("ok"):
            result.error = summary.get("error", "sync failed")
            self._safe_record_sync(connector_name, summary)
            return result

        items = summary.get("items", [])
        dict_items = [it.to_dict() if hasattr(it, "to_dict") else it for it in items]

        # Persist to the system of record.
        try:
            for item in dict_items:
                item.setdefault("evidence_uid", str(uuid.uuid4()))
                self._repo.upsert_evidence(item)
                result.persisted += 1
        except Exception as exc:  # noqa: BLE001
            result.error = f"repository error: {exc}"
            self._safe_record_sync(connector_name, summary)
            return result

        # Index into the vector store (best-effort).
        if index:
            try:
                result.indexed = self._index(dict_items)
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"vector indexing skipped: {exc}")

        self._safe_record_sync(connector_name, summary)
        result.ok = True
        return result

    def collect_all_enabled(self, *, index: bool = True) -> list[PipelineResult]:
        return [self.collect(name, index=index) for name in self._factory.create_enabled()]

    def _index(self, items: list[dict[str, Any]]) -> int:
        from ecs_platform.llm_engine.provider import get_provider
        from ecs_platform.vectorstore import Chunk, chunk_text, get_vector_store

        provider = get_provider()
        store = get_vector_store()
        store.init_store()

        chunks: list[Chunk] = []
        for item in items:
            uid = item["evidence_uid"]
            text = f"{item.get('title', '')}\n{item.get('content', '')}".strip()
            pieces = chunk_text(text, chunk_size=self._chunk_size, overlap=self._overlap)
            if not pieces:
                continue
            embeddings = provider.embed(pieces)
            meta = {
                "source_system": item.get("source_system"),
                "object_type": item.get("object_type"),
                "application": item.get("application"),
            }
            for idx, (piece, emb) in enumerate(zip(pieces, embeddings)):
                chunks.append(Chunk(chunk_id=f"{uid}:{idx}", evidence_uid=uid,
                                    text=piece, embedding=emb, metadata=meta))
        return store.upsert(chunks) if chunks else 0

    def _safe_record_sync(self, connector: str, summary: dict[str, Any]) -> None:
        try:
            self._repo.record_sync(connector, summary)
        except Exception:  # noqa: BLE001 - never fail the pipeline on audit write
            pass


def correlate_by_control(repository: EvidenceRepository, control_id: str) -> dict[str, Any]:
    """Group all evidence satisfying a control across source systems."""
    rows = repository.evidence_for_control(control_id)
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_source.setdefault(row.get("source_system", "?"), []).append(row)
    return {
        "control_id": control_id,
        "total_evidence": len(rows),
        "source_systems": list(by_source.keys()),
        "by_source": by_source,
    }
