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
            "connect_timeout": int(self._pg.get("connect_timeout", 3)),
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
                     detail: dict[str, Any] | None = None,
                     before_state: dict[str, Any] | None = None,
                     after_state: dict[str, Any] | None = None,
                     request_id: str = "", auth_source: str = "",
                     prev_hash: str = "") -> None:
        """Insert one audit row.

        Phase 4 Step 1: before_state/after_state/request_id/auth_source/prev_hash
        are OPTIONAL and default to empty, so existing callers (which pass none of
        them) behave exactly as before. The extra columns are written as NULL when
        not supplied."""
        with self.connect().cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log "
                "(actor, role, action, resource, detail, "
                " before_state, after_state, request_id, auth_source, prev_hash) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (actor, role, action, resource, json.dumps(detail or {}),
                 json.dumps(before_state) if before_state is not None else None,
                 json.dumps(after_state) if after_state is not None else None,
                 request_id or None, auth_source or None, prev_hash or None))

    def insert_observation(self, observation_id: str, *, title: str, application_id: str = "",
                           description: str = "", status: str = "Open", owner: str = "",
                           created_by: str = "") -> None:
        """Insert (or no-op upsert) a durable observation row.

        Phase 4 Step 1: durable storage only — NOT wired into the observation
        workflow yet (which still uses in-memory state). Idempotent on
        observation_id so re-runs are safe."""
        with self.connect().cursor() as cur:
            cur.execute(
                "INSERT INTO observations "
                "(observation_id, application_id, title, description, status, owner, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (observation_id) DO NOTHING",
                (observation_id, application_id or None, title, description or None,
                 status, owner or None, created_by or None))

    # ---- observations: durable persistence (Phase 4 Step 3) ----
    _OBS_COLS = (
        "observation_id, application_id, framework, control_id, title, description, "
        "severity, status, owner, due_date, remediation_plan, comments, "
        "created_by, created_at, updated_by, updated_at, closed_by, closed_at"
    )

    def upsert_observation(self, observation_id: str, *, title: str = "",
                           application_id: str = "", framework: str = "",
                           control_id: str = "", description: str = "",
                           severity: str = "", status: str = "Open", owner: str = "",
                           due_date: str = "", remediation_plan: str = "",
                           comments: list[Any] | None = None,
                           created_by: str = "", updated_by: str = "") -> None:
        """Create the observation if missing, else update its mutable fields.

        Idempotent and safe to re-run (the basis for migration). created_by /
        created_at are preserved on update; updated_at is always bumped. Pass
        title only on create — on update an empty title keeps the existing one."""
        with self.connect().cursor() as cur:
            cur.execute(
                """
                INSERT INTO observations
                  (observation_id, application_id, framework, control_id, title,
                   description, severity, status, owner, due_date, remediation_plan,
                   comments, created_by, updated_by, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                ON CONFLICT (observation_id) DO UPDATE SET
                  application_id   = COALESCE(NULLIF(EXCLUDED.application_id, ''), observations.application_id),
                  framework        = COALESCE(NULLIF(EXCLUDED.framework, ''), observations.framework),
                  control_id       = COALESCE(NULLIF(EXCLUDED.control_id, ''), observations.control_id),
                  title            = COALESCE(NULLIF(EXCLUDED.title, ''), observations.title),
                  description      = COALESCE(NULLIF(EXCLUDED.description, ''), observations.description),
                  severity         = COALESCE(NULLIF(EXCLUDED.severity, ''), observations.severity),
                  status           = EXCLUDED.status,
                  owner            = COALESCE(NULLIF(EXCLUDED.owner, ''), observations.owner),
                  due_date         = COALESCE(NULLIF(EXCLUDED.due_date, ''), observations.due_date),
                  remediation_plan = COALESCE(NULLIF(EXCLUDED.remediation_plan, ''), observations.remediation_plan),
                  comments         = EXCLUDED.comments,
                  updated_by       = COALESCE(NULLIF(EXCLUDED.updated_by, ''), observations.updated_by),
                  updated_at       = now()
                """,
                (observation_id, application_id or None, framework or None,
                 control_id or None, title or observation_id, description or None,
                 severity or None, status, owner or None, due_date or None,
                 remediation_plan or None, json.dumps(comments or []),
                 created_by or None, updated_by or created_by or None))

    def update_observation(self, observation_id: str, **fields: Any) -> None:
        """Patch mutable observation fields. Only supplied keys are updated."""
        allowed = {"application_id", "framework", "control_id", "title", "description",
                   "severity", "status", "owner", "due_date", "remediation_plan",
                   "comments", "updated_by", "closed_by", "closed_at"}
        sets, params = [], []
        for key, val in fields.items():
            if key not in allowed:
                continue
            if key == "comments":
                sets.append("comments = %s"); params.append(json.dumps(val or []))
            else:
                sets.append(f"{key} = %s"); params.append(val)
        if not sets:
            return
        sets.append("updated_at = now()")
        params.append(observation_id)
        with self.connect().cursor() as cur:
            cur.execute(
                f"UPDATE observations SET {', '.join(sets)} WHERE observation_id = %s", params)

    def close_observation(self, observation_id: str, *, closed_by: str = "",
                          status: str = "Closed") -> None:
        """Mark an observation closed (sets closed_by/closed_at)."""
        with self.connect().cursor() as cur:
            cur.execute(
                "UPDATE observations SET status = %s, closed_by = %s, closed_at = now(), "
                "updated_by = %s, updated_at = now() WHERE observation_id = %s",
                (status, closed_by or None, closed_by or None, observation_id))

    def reopen_observation(self, observation_id: str, *, reopened_by: str = "",
                           status: str = "Open") -> None:
        """Reopen a previously-closed observation (clears closure fields)."""
        with self.connect().cursor() as cur:
            cur.execute(
                "UPDATE observations SET status = %s, closed_by = NULL, closed_at = NULL, "
                "updated_by = %s, updated_at = now() WHERE observation_id = %s",
                (status, reopened_by or None, observation_id))

    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        with self.connect().cursor() as cur:
            cur.execute(
                f"SELECT {self._OBS_COLS} FROM observations WHERE observation_id = %s",
                (observation_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip([c[0] for c in cur.description], row))

    def list_observations(self, *, status: str | None = None,
                          application_id: str | None = None,
                          framework: str | None = None,
                          limit: int = 1000) -> list[dict[str, Any]]:
        clauses, params = [], []
        if status:
            clauses.append("status = %s"); params.append(status)
        if application_id:
            clauses.append("application_id = %s"); params.append(application_id)
        if framework:
            clauses.append("framework = %s"); params.append(framework)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self.connect().cursor() as cur:
            cur.execute(
                f"SELECT {self._OBS_COLS} FROM observations {where} "
                f"ORDER BY created_at DESC LIMIT %s", params)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def search_observations(self, term: str, *, limit: int = 200) -> list[dict[str, Any]]:
        like = f"%{term}%"
        with self.connect().cursor() as cur:
            cur.execute(
                f"SELECT {self._OBS_COLS} FROM observations "
                "WHERE observation_id ILIKE %s OR title ILIKE %s OR description ILIKE %s "
                "OR control_id ILIKE %s OR application_id ILIKE %s "
                "ORDER BY created_at DESC LIMIT %s",
                (like, like, like, like, like, limit))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def observation_counts(self) -> dict[str, int]:
        with self.connect().cursor() as cur:
            cur.execute("SELECT status, count(*) FROM observations GROUP BY status")
            by_status = {r[0]: r[1] for r in cur.fetchall()}
        total = sum(by_status.values())
        return {"total": total, "by_status": by_status}

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
                f"SELECT id, evidence_uid, source_system, source_object_id, object_type, title, content, "
                f"url, application, content_hash, metadata, collected_timestamp "
                f"FROM evidence {where} ORDER BY collected_timestamp DESC LIMIT %s", params)
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
