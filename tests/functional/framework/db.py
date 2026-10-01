"""Database validation helper for the ECS PostgreSQL system of record.

Tables are limited to those that really exist in ``ecs_platform/repository/schema.sql`` and
``governance_schema.sql`` (``KNOWN_TABLES``); anything else is refused so the suite can never query an invented
table. The password is read from the env var named in config (``ECS_REPO_PG_PASSWORD``) - never stored.
Read-only by default (autocommit session set to READ ONLY).
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

from .config import FunctionalConfig
from .errors import CapabilityBlocked

# Authoritative list: CREATE TABLE statements in ecs_platform/repository/{schema,governance_schema}.sql
KNOWN_TABLES: dict[str, tuple[str, ...]] = {
    "connectors": ("id", "name", "type", "enabled", "base_url", "last_health", "last_checked", "created_at"),
    "evidence": ("id", "evidence_uid", "source_system", "source_object_id", "object_type", "title", "content", "owner",
                 "url", "application", "collected_timestamp", "content_hash", "metadata", "created_at"),
    "controls": ("id", "control_id", "name", "description", "domain"),
    "frameworks": ("id", "code", "name"),
    "evidence_control_map": ("evidence_id", "control_id", "confidence"),
    "evidence_framework_map": ("evidence_id", "framework_code"),
    "evidence_lineage": ("id", "evidence_id", "parent_uid", "operation", "actor", "detail", "created_at"),
    "correlation_groups": ("id", "group_key", "control_id", "summary", "created_at"),
    "correlation_members": ("group_id", "evidence_id"),
    "sync_runs": ("id", "connector", "started_at", "finished_at", "ok", "collected", "error"),
    "audit_log": ("id", "actor", "role", "action", "resource", "detail", "created_at", "before_state", "after_state",
                  "request_id", "auth_source", "prev_hash"),
    "observations": ("id", "observation_id", "application_id", "title", "description", "status", "owner", "created_by",
                     "created_at", "updated_at", "framework", "control_id", "severity", "updated_by", "closed_by",
                     "closed_at", "due_date", "remediation_plan", "comments"),
    "applications": ("id", "slug", "name", "description", "owner", "owner_email", "business_unit", "criticality",
                     "environment", "lifecycle_status", "tech_stack", "hosting", "onboarded_at", "updated_at"),
    "application_frameworks": ("app_slug", "framework_code"),
    "control_catalog": ("control_id", "name", "domain", "framework_code", "description"),
    "control_framework_crosswalk": ("control_id", "framework_code", "requirement_ref"),
    "evidence_reviews": ("evidence_uid", "status", "reviewer", "note", "reviewed_at", "valid_until", "updated_at"),
    "collection_schedules": ("id", "name", "connector", "app_slug", "frequency", "owner", "enabled", "last_run",
                             "last_status", "next_run", "created_at"),
}
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


class EcsDatabase:
    def __init__(self, cfg: FunctionalConfig) -> None:
        self.cfg = cfg
        self._conn: Any = None

    # ---- connection ----------------------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("database.enabled"))

    def connect(self):
        if not self.enabled:
            raise CapabilityBlocked("Database validation is disabled (set ECS_FT_DB_ENABLED=true and ECS_REPO_PG_* env vars).",
                                    requires="PostgreSQL access")
        if self._conn is not None and not getattr(self._conn, "closed", 1):
            return self._conn
        try:
            import psycopg2
        except ImportError as exc:  # pragma: no cover
            raise CapabilityBlocked("psycopg2 is not installed.", requires="psycopg2-binary") from exc
        db = self.cfg.get("database", {})
        password = self.cfg.secret(db.get("password_env", "ECS_REPO_PG_PASSWORD"))
        self._conn = psycopg2.connect(host=db.get("host"), port=db.get("port"), dbname=db.get("database"),
                                      user=db.get("user"), password=password, connect_timeout=int(self.cfg.timeout),
                                      options=f"-c search_path={db.get('schema', 'public')} -c default_transaction_read_only=on")
        self._conn.autocommit = True
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---- generic ---------------------------------------------------------------------------------------
    def query(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        """Parameterised query -> list of dict rows. ALWAYS pass values via ``params`` (never f-string them)."""
        from psycopg2.extras import RealDictCursor

        with self.connect().cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()] if cur.description else []

    def scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        rows = self.query(sql, params)
        return next(iter(rows[0].values())) if rows else None

    @staticmethod
    def _table(name: str) -> str:
        if name not in KNOWN_TABLES:
            raise ValueError(f"'{name}' is not an ECS table. Known tables: {sorted(KNOWN_TABLES)}")
        return name

    def _where(self, table: str, filters: Mapping[str, Any]) -> tuple[str, list[Any]]:
        cols = KNOWN_TABLES[table]
        clauses, params = [], []
        for col, val in filters.items():
            base = col.split("__")[0]
            if base not in cols or not _IDENT.match(base):
                raise ValueError(f"'{base}' is not a column of {table}: {cols}")
            op = col.split("__")[1] if "__" in col else "eq"
            if op == "eq":
                clauses.append(f"{base} = %s")
            elif op == "ilike":
                clauses.append(f"{base}::text ILIKE %s")
                val = f"%{val}%"
            elif op == "gte":
                clauses.append(f"{base} >= %s")
            elif op == "lte":
                clauses.append(f"{base} <= %s")
            elif op == "in":
                clauses.append(f"{base} = ANY(%s)")
                val = list(val)
            else:
                raise ValueError(f"unsupported filter op '{op}'")
            params.append(val)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    # ---- record lookups -----------------------------------------------------------------------------------
    def find(self, table: str, order_by: str | None = None, limit: int = 100, **filters: Any) -> list[dict[str, Any]]:
        t = self._table(table)
        where, params = self._where(t, filters)
        order = f" ORDER BY {order_by}" if order_by and _IDENT.match(order_by.split()[0]) else ""
        return self.query(f"SELECT * FROM {t}{where}{order} LIMIT %s", [*params, int(limit)])

    def one(self, table: str, **filters: Any) -> dict[str, Any] | None:
        rows = self.find(table, limit=1, **filters)
        return rows[0] if rows else None

    def count(self, table: str, **filters: Any) -> int:
        t = self._table(table)
        where, params = self._where(t, filters)
        return int(self.scalar(f"SELECT count(*) FROM {t}{where}", params) or 0)

    def exists(self, table: str, **filters: Any) -> bool:
        return self.count(table, **filters) > 0

    # ---- ECS-specific verifications -----------------------------------------------------------------------
    def evidence(self, **filters: Any) -> list[dict[str, Any]]:
        return self.find("evidence", order_by="created_at DESC", **filters)

    def verify_status(self, table: str, key_col: str, key: Any, status_col: str, expected: str) -> dict[str, Any]:
        row = self.one(table, **{key_col: key})
        assert row is not None, f"{table}.{key_col}={key!r} not found"
        assert str(row.get(status_col)).lower() == expected.lower(), f"{table}.{status_col}={row.get(status_col)!r}, expected {expected!r}"
        return row

    def verify_timestamp(self, row: Mapping[str, Any], column: str, *, not_before: Any = None, not_after: Any = None) -> Any:
        ts = row.get(column)
        assert ts is not None, f"timestamp column '{column}' is empty"
        if not_before is not None:
            assert ts >= not_before, f"{column}={ts} earlier than {not_before}"
        if not_after is not None:
            assert ts <= not_after, f"{column}={ts} later than {not_after}"
        return ts

    def verify_metadata(self, evidence_uid: str, expected: Mapping[str, Any]) -> dict[str, Any]:
        from .assertions import assert_metadata

        row = self.one("evidence", evidence_uid=evidence_uid)
        assert row is not None, f"evidence_uid={evidence_uid!r} not found"
        assert_metadata(row, expected)
        return row

    def audit_records(self, *, request_id: str | None = None, action: str | None = None, resource: str | None = None,
                      actor: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        f: dict[str, Any] = {}
        if request_id:
            f["request_id"] = request_id
        if action:
            f["action__ilike"] = action
        if resource:
            f["resource__ilike"] = resource
        if actor:
            f["actor__ilike"] = actor
        return self.find("audit_log", order_by="created_at DESC", limit=limit, **f)

    def relationships(self, evidence_uid: str) -> dict[str, list[dict[str, Any]]]:
        """Controls, frameworks and lineage linked to one evidence row (many-to-many maps in schema.sql)."""
        ev = self.one("evidence", evidence_uid=evidence_uid)
        if not ev:
            return {"controls": [], "frameworks": [], "lineage": []}
        eid = ev["id"]
        return {"controls": self.find("evidence_control_map", evidence_id=eid),
                "frameworks": self.find("evidence_framework_map", evidence_id=eid),
                "lineage": self.find("evidence_lineage", order_by="created_at", evidence_id=eid)}

    def duplicate_groups(self, table: str, columns: Iterable[str]) -> list[dict[str, Any]]:
        t = self._table(table)
        cols = list(columns)
        for c in cols:
            if c not in KNOWN_TABLES[t]:
                raise ValueError(f"{c} not in {t}")
        return self.query(f"SELECT {', '.join(cols)}, count(*) AS n FROM {t} GROUP BY {', '.join(cols)} HAVING count(*) > 1")
