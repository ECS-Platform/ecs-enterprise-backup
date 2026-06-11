"""PostgreSQL-backed evidence repository.

psycopg2 is imported lazily inside connect() so importing this module never breaks
the host application when the driver/DB is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Iterable

from ecs_platform.config import load_repository_config, resolve_secret

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class RepositoryError(RuntimeError):
    pass


def _content_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class EvidenceRepository:
    """Thin, dependency-light DAL over the evidence schema."""

    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or load_repository_config()
        self._pg = (cfg.get("repository", {}) or {}).get("postgres", {})
        self._conn = None

    # ---- connection ----
    def _dsn(self) -> dict[str, Any]:
        return {
            "host": self._pg.get("host", "postgres"),
            "port": int(self._pg.get("port", 5432)),
            "dbname": self._pg.get("database", "ecs_repository"),
            "user": self._pg.get("user", "ecs_user"),
            "password": resolve_secret(self._pg.get("password_env", "ECS_REPO_PG_PASSWORD")),
        }

    def connect(self):
        if self._conn is not None:
            return self._conn
        try:
            import psycopg2
        except ImportError as exc:  # pragma: no cover
            raise RepositoryError("psycopg2 is required for the evidence repository") from exc
        try:
            self._conn = psycopg2.connect(**self._dsn())
            self._conn.autocommit = True
        except Exception as exc:  # noqa: BLE001
            raise RepositoryError(f"Cannot connect to evidence repository: {exc}") from exc
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "EvidenceRepository":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---- schema ----
    def init_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self.connect().cursor() as cur:
            cur.execute(sql)

    # ---- writes ----
    def upsert_evidence(self, item: dict[str, Any]) -> int:
        """Insert/update one evidence row (idempotent on source identity). Returns id."""
        chash = _content_hash(item.get("source_system", ""), item.get("source_object_id", ""),
                              item.get("title", ""), item.get("content", ""))
        uid = item.get("evidence_uid") or str(uuid.uuid4())
        with self.connect().cursor() as cur:
            cur.execute(
                """
                INSERT INTO evidence (evidence_uid, source_system, source_object_id, object_type,
                    title, content, owner, url, application, content_hash, metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (source_system, source_object_id, object_type) DO UPDATE SET
                    title = EXCLUDED.title, content = EXCLUDED.content, owner = EXCLUDED.owner,
                    url = EXCLUDED.url, application = EXCLUDED.application,
                    content_hash = EXCLUDED.content_hash, metadata = EXCLUDED.metadata,
                    collected_timestamp = now()
                RETURNING id
                """,
                (uid, item.get("source_system"), item.get("source_object_id"), item.get("object_type"),
                 item.get("title"), item.get("content"), item.get("owner"), item.get("url"),
                 item.get("application"), chash, json.dumps(item.get("metadata", {}))),
            )
            ev_id = cur.fetchone()[0]
            for ctrl in item.get("control_mapping", []) or []:
                cur.execute(
                    "INSERT INTO evidence_control_map (evidence_id, control_id) VALUES (%s,%s) "
                    "ON CONFLICT DO NOTHING", (ev_id, ctrl))
            for fw in item.get("framework_mapping", []) or []:
                cur.execute(
                    "INSERT INTO evidence_framework_map (evidence_id, framework_code) VALUES (%s,%s) "
                    "ON CONFLICT DO NOTHING", (ev_id, fw))
            cur.execute(
                "INSERT INTO evidence_lineage (evidence_id, operation, actor, detail) VALUES (%s,%s,%s,%s)",
                (ev_id, "collect", item.get("source_system"), json.dumps({"uid": uid})))
        return ev_id

    def bulk_upsert(self, items: Iterable[dict[str, Any]]) -> int:
        count = 0
        for item in items:
            self.upsert_evidence(item)
            count += 1
        return count

    def record_sync(self, connector: str, summary: dict[str, Any]) -> None:
        with self.connect().cursor() as cur:
            cur.execute(
                "INSERT INTO sync_runs (connector, started_at, finished_at, ok, collected, error) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (connector, summary.get("started"), summary.get("finished"), summary.get("ok"),
                 summary.get("collected", 0), summary.get("error")))

    def record_audit(self, actor: str, action: str, *, role: str = "", resource: str = "",
                     detail: dict[str, Any] | None = None) -> None:
        with self.connect().cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (actor, role, action, resource, detail) VALUES (%s,%s,%s,%s,%s)",
                (actor, role, action, resource, json.dumps(detail or {})))

    # ---- reads ----
    def search_evidence(self, *, application: str | None = None, source_system: str | None = None,
                        object_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        clauses, params = [], []
        if application:
            clauses.append("application = %s"); params.append(application)
        if source_system:
            clauses.append("source_system = %s"); params.append(source_system)
        if object_type:
            clauses.append("object_type = %s"); params.append(object_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self.connect().cursor() as cur:
            cur.execute(
                f"SELECT id, evidence_uid, source_system, object_type, title, content, application, url, "
                f"collected_timestamp FROM evidence {where} ORDER BY collected_timestamp DESC LIMIT %s", params)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def evidence_for_control(self, control_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect().cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.evidence_uid, e.source_system, e.object_type, e.title, e.application, e.url
                FROM evidence e JOIN evidence_control_map m ON m.evidence_id = e.id
                WHERE m.control_id = %s ORDER BY e.collected_timestamp DESC LIMIT %s
                """, (control_id, limit))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def counts(self) -> dict[str, Any]:
        with self.connect().cursor() as cur:
            cur.execute("SELECT count(*) FROM evidence")
            total = cur.fetchone()[0]
            cur.execute("SELECT source_system, count(*) FROM evidence GROUP BY source_system")
            by_source = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute("SELECT object_type, count(*) FROM evidence GROUP BY object_type")
            by_type = {r[0]: r[1] for r in cur.fetchall()}
        return {"total": total, "by_source": by_source, "by_type": by_type}

    def evidence_by_uid(self, uid: str) -> dict[str, Any] | None:
        with self.connect().cursor() as cur:
            cur.execute(
                "SELECT id, evidence_uid, source_system, source_object_id, object_type, title, "
                "content, owner, url, application, collected_timestamp, metadata "
                "FROM evidence WHERE evidence_uid = %s", (uid,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def distinct_values(self) -> dict[str, list[str]]:
        """Filter options for the Evidence Explorer."""
        with self.connect().cursor() as cur:
            cur.execute("SELECT DISTINCT source_system FROM evidence ORDER BY 1")
            sources = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT DISTINCT object_type FROM evidence ORDER BY 1")
            types = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT DISTINCT application FROM evidence WHERE application <> '' ORDER BY 1")
            apps = [r[0] for r in cur.fetchall()]
        return {"sources": sources, "object_types": types, "applications": apps}

    # ---- relationships (Commit -> Build -> Sonar Scan) ----
    def link_evidence(self, parent_uid: str, child_uid: str, operation: str,
                      actor: str = "", detail: dict[str, Any] | None = None) -> None:
        """Record a derivation edge (child produced from parent). Idempotent."""
        with self.connect().cursor() as cur:
            cur.execute("SELECT id FROM evidence WHERE evidence_uid = %s", (child_uid,))
            row = cur.fetchone()
            if not row:
                return
            cur.execute(
                """
                INSERT INTO evidence_lineage (evidence_id, parent_uid, operation, actor, detail)
                SELECT %s,%s,%s,%s,%s
                WHERE NOT EXISTS (
                    SELECT 1 FROM evidence_lineage
                    WHERE evidence_id = %s AND parent_uid = %s AND operation = %s
                )
                """,
                (row[0], parent_uid, operation, actor, json.dumps(detail or {}),
                 row[0], parent_uid, operation))

    def create_correlation(self, group_key: str, control_id: str, summary: str,
                           evidence_uids: list[str]) -> int:
        with self.connect().cursor() as cur:
            cur.execute(
                "INSERT INTO correlation_groups (group_key, control_id, summary) VALUES (%s,%s,%s) "
                "ON CONFLICT (group_key) DO UPDATE SET summary = EXCLUDED.summary, "
                "control_id = EXCLUDED.control_id RETURNING id", (group_key, control_id, summary))
            gid = cur.fetchone()[0]
            for uid in evidence_uids:
                cur.execute("SELECT id FROM evidence WHERE evidence_uid = %s", (uid,))
                r = cur.fetchone()
                if r:
                    cur.execute(
                        "INSERT INTO correlation_members (group_id, evidence_id) VALUES (%s,%s) "
                        "ON CONFLICT DO NOTHING", (gid, r[0]))
        return gid

    def list_correlations(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect().cursor() as cur:
            cur.execute(
                """
                SELECT g.group_key, g.control_id, g.summary,
                       json_agg(json_build_object('uid', e.evidence_uid, 'source', e.source_system,
                                'type', e.object_type, 'title', e.title) ORDER BY e.id) AS members
                FROM correlation_groups g
                JOIN correlation_members m ON m.group_id = g.id
                JOIN evidence e ON e.id = m.evidence_id
                GROUP BY g.id ORDER BY g.created_at DESC LIMIT %s
                """, (limit,))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ---- dashboard reads ----
    def list_sync_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        with self.connect().cursor() as cur:
            cur.execute(
                "SELECT connector, started_at, finished_at, ok, collected, error "
                "FROM sync_runs ORDER BY started_at DESC LIMIT %s", (limit,))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect().cursor() as cur:
            cur.execute(
                "SELECT actor, role, action, resource, detail, created_at "
                "FROM audit_log ORDER BY created_at DESC LIMIT %s", (limit,))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
