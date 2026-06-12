"""pgvector-backed vector store. psycopg2 imported lazily."""

from __future__ import annotations

from typing import Any

from ecs_platform.config import resolve_secret
from ecs_platform.vectorstore.base import Chunk, SearchHit, VectorStore, VectorStoreError


class PgVectorStore(VectorStore):
    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg
        self._pg = (cfg.get("providers", {}) or {}).get("pgvector", {})
        self._dim = int(cfg.get("embedding_dim", 768))
        self._table = self._pg.get("table", "evidence_embeddings")
        self._conn = None

    def _connect(self):
        if self._conn is not None:
            return self._conn
        try:
            import psycopg2
        except ImportError as exc:  # pragma: no cover
            raise VectorStoreError("psycopg2 is required for pgvector") from exc
        try:
            self._conn = psycopg2.connect(
                host=self._pg.get("host", "pgvector"), port=int(self._pg.get("port", 5432)),
                dbname=self._pg.get("database", "ecs_vectors"), user=self._pg.get("user", "ecs_user"),
                password=resolve_secret(self._pg.get("password_env", "ECS_VECTOR_PG_PASSWORD")))
            self._conn.autocommit = True
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Cannot connect to pgvector: {exc}") from exc
        return self._conn

    @staticmethod
    def _vec(embedding: list[float]) -> str:
        return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

    def init_store(self) -> None:
        with self._connect().cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    chunk_id      TEXT PRIMARY KEY,
                    evidence_uid  TEXT NOT NULL,
                    text          TEXT NOT NULL,
                    metadata      JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding     vector({self._dim})
                )
                """)
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table}_uid ON {self._table} (evidence_uid)")
            # If the embedding model changed dimension (e.g. provider switch), the
            # existing column type won't match. Detect and rebuild empty/mismatched.
            cur.execute(
                "SELECT a.atttypmod FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "WHERE c.relname = %s AND a.attname = 'embedding'", (self._table,))
            row = cur.fetchone()
            current_dim = int(row[0]) if row and row[0] and row[0] > 0 else self._dim
            if current_dim != self._dim:
                cur.execute(f"SELECT count(*) FROM {self._table}")
                if int(cur.fetchone()[0]) == 0:
                    cur.execute(f"ALTER TABLE {self._table} ALTER COLUMN embedding TYPE vector({self._dim})")

    def upsert(self, chunks: list[Chunk]) -> int:
        import json
        with self._connect().cursor() as cur:
            for c in chunks:
                cur.execute(
                    f"""
                    INSERT INTO {self._table} (chunk_id, evidence_uid, text, metadata, embedding)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (chunk_id) DO UPDATE SET text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata, embedding = EXCLUDED.embedding
                    """,
                    (c.chunk_id, c.evidence_uid, c.text, json.dumps(c.metadata), self._vec(c.embedding)))
        return len(chunks)

    def search(self, embedding: list[float], *, top_k: int = 8,
               filters: dict[str, Any] | None = None) -> list[SearchHit]:
        vec = self._vec(embedding)
        # Params in statement order: SELECT score vec, optional filters, ORDER BY vec, LIMIT.
        select_params: list[Any] = [vec]
        filter_clause = ""
        filter_params: list[Any] = []
        if filters:
            conds = []
            for key, val in filters.items():
                conds.append("metadata->>%s = %s")
                filter_params.extend([key, str(val)])
            if conds:
                filter_clause = "WHERE " + " AND ".join(conds)
        params = [*select_params, *filter_params, vec, top_k]
        sql = (
            f"SELECT chunk_id, evidence_uid, text, metadata, "
            f"1 - (embedding <=> %s::vector) AS score "
            f"FROM {self._table} {filter_clause} "
            f"ORDER BY embedding <=> %s::vector LIMIT %s"
        )
        with self._connect().cursor() as cur:
            cur.execute(sql, params)
            return [
                SearchHit(chunk_id=row[0], evidence_uid=row[1], text=row[2],
                          metadata=row[3] or {}, score=float(row[4]))
                for row in cur.fetchall()
            ]

    def delete_for_evidence(self, evidence_uid: str) -> None:
        with self._connect().cursor() as cur:
            cur.execute(f"DELETE FROM {self._table} WHERE evidence_uid = %s", (evidence_uid,))
