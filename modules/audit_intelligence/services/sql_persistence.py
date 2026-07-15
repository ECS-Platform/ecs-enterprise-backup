"""SQL persistence skeleton for ECS Audit Intelligence (SQLite default; Postgres-ready).

A concrete :class:`~modules.audit_intelligence.services.persistence.AuditPersistence`
backed by a DB-API 2.0 connection. It is intentionally a *skeleton*:

  * The default backend is **SQLite** (stdlib ``sqlite3``) — in-memory or file —
    so tests and local runs need **no external database**.
  * It is **Postgres-ready**: pass a ``connection_factory`` returning a live
    ``psycopg``/``psycopg2`` connection and set ``paramstyle="pyformat"``; the DDL
    is written to be compatible (``TEXT``/``JSONB``-friendly, upserts via
    ``INSERT ... ON CONFLICT``).
  * Every durable entity is stored as a row with a **JSON document** column, so the
    schema is stable while models evolve. Indexed scalar columns (ids, run_id,
    created_at, version) support the query methods without a migration per field.

No credentials/secrets are stored (the models only carry hashes + non-secret
metadata). See ``docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`` for the canonical schema
and ``docs/audit-intelligence/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md`` for wiring notes.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Callable, Optional

from modules.audit_intelligence.models import (
    EvidenceArtifact,
    EvidenceRecord,
    EvidenceRun,
    Observation,
    ValidationResult,
)
from modules.audit_intelligence.services.persistence import (
    AuditPersistence,
    artifact_from_dict,
    artifact_to_dict,
    observation_from_dict,
    observation_to_dict,
    record_from_dict,
    run_from_dict,
    run_to_dict,
    validation_from_dict,
    validation_to_dict,
)

#: A connection factory returns a fresh DB-API connection (SQLite by default).
ConnectionFactory = Callable[[], Any]


def _sqlite_memory_factory() -> Callable[[], sqlite3.Connection]:
    """Factory for a single shared in-memory SQLite DB (per backend instance)."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return lambda: conn


def sqlite_file_factory(path: str) -> Callable[[], sqlite3.Connection]:
    """Factory for a file-backed SQLite DB (durable across process restarts)."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return lambda: conn


# --------------------------------------------------------------------------- #
# DDL (SQLite-compatible; also valid on Postgres with TEXT/JSONB)
# --------------------------------------------------------------------------- #
_DDL = [
    """CREATE TABLE IF NOT EXISTS audit_runs (
        run_id       TEXT PRIMARY KEY,
        created_at   TEXT,
        status       TEXT,
        scope_kind   TEXT,
        scope_value  TEXT,
        document     TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_validation_results (
        run_id       TEXT NOT NULL,
        seq          INTEGER NOT NULL,
        control_id   TEXT,
        verdict      TEXT,
        document     TEXT NOT NULL,
        PRIMARY KEY (run_id, seq)
    )""",
    """CREATE TABLE IF NOT EXISTS audit_observations (
        observation_id TEXT PRIMARY KEY,
        created_at     TEXT,
        severity       TEXT,
        status         TEXT,
        control_id     TEXT,
        document       TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_evidence_versions (
        evidence_key TEXT NOT NULL,
        version      INTEGER NOT NULL,
        control_id   TEXT,
        asset_id     TEXT,
        collected_at TEXT,
        source_item_id TEXT,
        content_hash TEXT,
        document     TEXT NOT NULL,
        PRIMARY KEY (evidence_key, version)
    )""",
    """CREATE TABLE IF NOT EXISTS audit_packs (
        pack_id      TEXT PRIMARY KEY,
        generated_at TEXT,
        document     TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_scheduler_history (
        seq          INTEGER PRIMARY KEY AUTOINCREMENT,
        at           TEXT,
        document     TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_runs_created ON audit_runs (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_obs_created ON audit_observations (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_ev_key ON audit_evidence_versions (evidence_key)",
    "CREATE INDEX IF NOT EXISTS ix_ev_source_hash ON audit_evidence_versions (source_item_id, content_hash)",
]

_EVIDENCE_MIGRATIONS = [
    "ALTER TABLE audit_evidence_versions ADD COLUMN source_item_id TEXT",
    "ALTER TABLE audit_evidence_versions ADD COLUMN content_hash TEXT",
]


class SqlAuditPersistence(AuditPersistence):
    """DB-API-backed persistence (SQLite default). Postgres wiring is a config swap.

    Parameters
    ----------
    connection_factory:
        Returns a DB-API connection. Defaults to a shared in-memory SQLite DB.
    paramstyle:
        ``"qmark"`` for SQLite (``?``) or ``"pyformat"`` for Postgres (``%s``).
    """

    def __init__(
        self,
        connection_factory: Optional[ConnectionFactory] = None,
        *,
        paramstyle: str = "qmark",
    ) -> None:
        self._lock = threading.RLock()
        self._factory = connection_factory or _sqlite_memory_factory()
        self._ph = "?" if paramstyle == "qmark" else "%s"
        self._initialized = False

    # ---- helpers ---------------------------------------------------------- #
    def _conn(self):
        return self._factory()

    def _sql(self, statement: str) -> str:
        """Translate ``?`` placeholders to the configured paramstyle."""
        if self._ph == "?":
            return statement
        return statement.replace("?", self._ph)

    def _execute(self, statement: str, params: tuple = ()) -> None:
        conn = self._conn()
        conn.execute(self._sql(statement), params)
        conn.commit()

    def _query(self, statement: str, params: tuple = ()) -> list[Any]:
        conn = self._conn()
        cur = conn.execute(self._sql(statement), params)
        return list(cur.fetchall())

    @staticmethod
    def _doc(row: Any, column: str = "document") -> dict[str, Any]:
        # Works for sqlite3.Row (mapping-like) and plain tuples (fallback).
        try:
            raw = row[column]
        except (KeyError, IndexError, TypeError):
            raw = row[-1]
        return json.loads(raw)

    # ---- lifecycle -------------------------------------------------------- #
    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            conn = self._conn()
            for ddl in _DDL:
                conn.execute(ddl)
            for migration in _EVIDENCE_MIGRATIONS:
                try:
                    conn.execute(migration)
                except Exception:  # noqa: BLE001 - column may already exist
                    pass
            conn.commit()
            self._initialized = True

    def clear(self) -> None:
        self.initialize()
        with self._lock:
            for table in (
                "audit_runs", "audit_validation_results", "audit_observations",
                "audit_evidence_versions", "audit_packs", "audit_scheduler_history",
            ):
                self._execute(f"DELETE FROM {table}")

    # ---- runs + results --------------------------------------------------- #
    def save_run(self, run: EvidenceRun) -> EvidenceRun:
        self.initialize()
        doc = json.dumps(run_to_dict(run), default=str)
        with self._lock:
            self._execute(
                """INSERT INTO audit_runs (run_id, created_at, status, scope_kind, scope_value, document)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(run_id) DO UPDATE SET
                     created_at=excluded.created_at, status=excluded.status,
                     scope_kind=excluded.scope_kind, scope_value=excluded.scope_value,
                     document=excluded.document""",
                (run.run_id, run.created_at, run.status, run.scope_kind, run.scope_value, doc),
            )
        return run

    def get_run(self, run_id: str) -> Optional[EvidenceRun]:
        rows = self._query("SELECT document FROM audit_runs WHERE run_id = ?", (run_id,))
        return run_from_dict(self._doc(rows[0])) if rows else None

    def list_runs(self) -> list[EvidenceRun]:
        rows = self._query("SELECT document FROM audit_runs ORDER BY created_at DESC")
        return [run_from_dict(self._doc(r)) for r in rows]

    def get_run_results(self, run_id: str) -> list[EvidenceRecord]:
        run = self.get_run(run_id)
        return list(run.records) if run else []

    # ---- validation ------------------------------------------------------- #
    def save_validation_results(self, run_id: str, results: list[ValidationResult]) -> None:
        self.initialize()
        with self._lock:
            self._execute("DELETE FROM audit_validation_results WHERE run_id = ?", (run_id,))
            for seq, result in enumerate(results):
                self._execute(
                    """INSERT INTO audit_validation_results (run_id, seq, control_id, verdict, document)
                       VALUES (?, ?, ?, ?, ?)""",
                    (run_id, seq, result.control_id, result.verdict,
                     json.dumps(validation_to_dict(result), default=str)),
                )

    def get_validation_results(self, run_id: str) -> list[ValidationResult]:
        rows = self._query(
            "SELECT document FROM audit_validation_results WHERE run_id = ? ORDER BY seq",
            (run_id,),
        )
        return [validation_from_dict(self._doc(r)) for r in rows]

    # ---- observations ----------------------------------------------------- #
    def save_observation(self, observation: Observation) -> Observation:
        self.initialize()
        doc = json.dumps(observation_to_dict(observation), default=str)
        with self._lock:
            self._execute(
                """INSERT INTO audit_observations
                     (observation_id, created_at, severity, status, control_id, document)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(observation_id) DO UPDATE SET
                     created_at=excluded.created_at, severity=excluded.severity,
                     status=excluded.status, control_id=excluded.control_id,
                     document=excluded.document""",
                (observation.observation_id, observation.created_at, observation.severity,
                 observation.status, observation.control_id, doc),
            )
        return observation

    def get_observation(self, observation_id: str) -> Optional[Observation]:
        rows = self._query(
            "SELECT document FROM audit_observations WHERE observation_id = ?",
            (observation_id,),
        )
        return observation_from_dict(self._doc(rows[0])) if rows else None

    def list_observations(self) -> list[Observation]:
        rows = self._query("SELECT document FROM audit_observations ORDER BY created_at DESC")
        return [observation_from_dict(self._doc(r)) for r in rows]

    # ---- evidence versions ------------------------------------------------ #
    def append_evidence_version(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        self.initialize()
        if artifact.source_item_id and artifact.content_hash:
            existing = self.find_evidence_by_source_hash(
                artifact.source_item_id, artifact.content_hash,
            )
            if existing is not None:
                return existing
        doc = json.dumps(artifact_to_dict(artifact), default=str)
        with self._lock:
            self._execute(
                """INSERT INTO audit_evidence_versions
                     (evidence_key, version, control_id, asset_id, collected_at,
                      source_item_id, content_hash, document)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(evidence_key, version) DO UPDATE SET
                     control_id=excluded.control_id, asset_id=excluded.asset_id,
                     collected_at=excluded.collected_at,
                     source_item_id=excluded.source_item_id,
                     content_hash=excluded.content_hash,
                     document=excluded.document""",
                (artifact.evidence_key, artifact.version, artifact.control_id,
                 artifact.asset_id, artifact.collected_at, artifact.source_item_id,
                 artifact.content_hash, doc),
            )
        return artifact

    def find_evidence_by_source_hash(
        self, source_item_id: str, content_hash: str,
    ) -> Optional[EvidenceArtifact]:
        if not source_item_id or not content_hash:
            return None
        self.initialize()
        rows = self._query(
            "SELECT document FROM audit_evidence_versions "
            "WHERE source_item_id = ? AND content_hash = ? LIMIT 1",
            (source_item_id, content_hash),
        )
        return artifact_from_dict(self._doc(rows[0])) if rows else None

    def get_evidence_versions(self, evidence_key: str) -> list[EvidenceArtifact]:
        rows = self._query(
            "SELECT document FROM audit_evidence_versions WHERE evidence_key = ? ORDER BY version",
            (evidence_key,),
        )
        return [artifact_from_dict(self._doc(r)) for r in rows]

    def list_evidence_latest(self) -> list[EvidenceArtifact]:
        # Group in Python for portability (avoids window-function dialect differences).
        rows = self._query(
            "SELECT evidence_key, version, document FROM audit_evidence_versions "
            "ORDER BY evidence_key, version"
        )
        latest: dict[str, EvidenceArtifact] = {}
        for r in rows:
            art = artifact_from_dict(self._doc(r))
            latest[art.evidence_key] = art  # last one wins (highest version)
        return list(latest.values())

    def list_all_evidence_versions(self) -> list[EvidenceArtifact]:
        rows = self._query(
            "SELECT document FROM audit_evidence_versions "
            "ORDER BY evidence_key, version"
        )
        return [artifact_from_dict(self._doc(r)) for r in rows]

    # ---- packs ------------------------------------------------------------ #
    def save_pack(self, pack_id: str, manifest: dict[str, Any]) -> None:
        self.initialize()
        with self._lock:
            self._execute(
                """INSERT INTO audit_packs (pack_id, generated_at, document)
                   VALUES (?, ?, ?)
                   ON CONFLICT(pack_id) DO UPDATE SET
                     generated_at=excluded.generated_at, document=excluded.document""",
                (pack_id, manifest.get("generated_at", ""), json.dumps(manifest, default=str)),
            )

    def get_pack(self, pack_id: str) -> Optional[dict[str, Any]]:
        rows = self._query("SELECT document FROM audit_packs WHERE pack_id = ?", (pack_id,))
        return self._doc(rows[0]) if rows else None

    def list_packs(self) -> list[dict[str, Any]]:
        rows = self._query("SELECT document FROM audit_packs ORDER BY generated_at DESC")
        return [self._doc(r) for r in rows]

    # ---- scheduler -------------------------------------------------------- #
    def record_scheduler_event(self, event: dict[str, Any]) -> None:
        self.initialize()
        with self._lock:
            self._execute(
                "INSERT INTO audit_scheduler_history (at, document) VALUES (?, ?)",
                (event.get("at", ""), json.dumps(event, default=str)),
            )

    def get_scheduler_history(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT document FROM audit_scheduler_history ORDER BY seq DESC LIMIT ?",
            (max(0, limit),),
        )
        return [self._doc(r) for r in rows]
