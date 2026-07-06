-- =============================================================================
-- ECS Audit Intelligence — Durable Persistence Schema
-- =============================================================================
-- Canonical schema for the audit-intelligence persistence foundation.
--
-- Two dialects are supported by the same application code:
--   * SQLite  (default; used by tests and local runs — no external DB required)
--   * Postgres (production target; JSONB documents + indexed scalar columns)
--
-- This file is the Postgres-oriented reference DDL. The SQLite equivalent is
-- emitted at runtime by
--   modules/audit_intelligence/services/sql_persistence.py
-- (TEXT documents instead of JSONB; otherwise identical shape).
--
-- Design:
--   * Each durable entity is one row with a JSON(B) `document` column holding the
--     full serialized model (stable while models evolve).
--   * Indexed scalar columns (ids, run_id, created_at, version, severity, status)
--     support the read/query methods without a migration per new field.
--   * NOTHING here stores credentials or secrets. Evidence rows carry hashes and
--     non-secret metadata only; raw evidence bodies are never persisted.
--
-- Apply (Postgres):   psql "$ECS_AUDIT_DB_URL" -f docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql
-- Idempotent: safe to run repeatedly (IF NOT EXISTS throughout).
-- =============================================================================

-- Optional: keep audit-intelligence objects in their own schema.
-- CREATE SCHEMA IF NOT EXISTS audit_intelligence;
-- SET search_path TO audit_intelligence, public;

-- -----------------------------------------------------------------------------
-- 1) Evidence runs  (+ 2) evidence results are embedded in the run document)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_runs (
    run_id       TEXT PRIMARY KEY,
    created_at   TEXT,
    status       TEXT,
    scope_kind   TEXT,
    scope_value  TEXT,
    document     JSONB NOT NULL          -- full EvidenceRun incl. records + audit_trail
);
CREATE INDEX IF NOT EXISTS ix_runs_created ON audit_runs (created_at);
CREATE INDEX IF NOT EXISTS ix_runs_status  ON audit_runs (status);

-- -----------------------------------------------------------------------------
-- 3) Validation results (per run, ordered by seq)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_validation_results (
    run_id       TEXT NOT NULL,
    seq          INTEGER NOT NULL,
    control_id   TEXT,
    verdict      TEXT,
    document     JSONB NOT NULL,         -- full ValidationResult
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX IF NOT EXISTS ix_val_run ON audit_validation_results (run_id);

-- -----------------------------------------------------------------------------
-- 4) Observations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_observations (
    observation_id TEXT PRIMARY KEY,
    created_at     TEXT,
    severity       TEXT,
    status         TEXT,
    control_id     TEXT,
    document       JSONB NOT NULL         -- full Observation incl. history
);
CREATE INDEX IF NOT EXISTS ix_obs_created  ON audit_observations (created_at);
CREATE INDEX IF NOT EXISTS ix_obs_status   ON audit_observations (status);
CREATE INDEX IF NOT EXISTS ix_obs_severity ON audit_observations (severity);

-- -----------------------------------------------------------------------------
-- 5) Evidence versions (versioned per evidence_key)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_evidence_versions (
    evidence_key TEXT NOT NULL,
    version      INTEGER NOT NULL,
    control_id   TEXT,
    asset_id     TEXT,
    collected_at TEXT,
    document     JSONB NOT NULL,         -- full EvidenceArtifact (hash + metadata only)
    PRIMARY KEY (evidence_key, version)
);
CREATE INDEX IF NOT EXISTS ix_ev_key    ON audit_evidence_versions (evidence_key);
CREATE INDEX IF NOT EXISTS ix_ev_asset  ON audit_evidence_versions (asset_id);

-- -----------------------------------------------------------------------------
-- 6) Evidence packs (manifests)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_packs (
    pack_id      TEXT PRIMARY KEY,
    generated_at TEXT,
    document     JSONB NOT NULL          -- full pack manifest (pure metadata)
);
CREATE INDEX IF NOT EXISTS ix_packs_generated ON audit_packs (generated_at);

-- -----------------------------------------------------------------------------
-- 7) Scheduler history (append-only event log)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_scheduler_history (
    seq          BIGSERIAL PRIMARY KEY,  -- SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT
    at           TEXT,
    document     JSONB NOT NULL          -- scheduler event (schedule_id, scope, action, ...)
);
CREATE INDEX IF NOT EXISTS ix_sched_at ON audit_scheduler_history (at);

-- =============================================================================
-- Retention (operator policy — see PRODUCTION_READINESS_GAP_REGISTER.md)
-- =============================================================================
-- Example bounded-retention statements (run by a scheduled job; tune to policy):
--   DELETE FROM audit_scheduler_history WHERE at < (now() - interval '90 days')::text;
--   -- Keep only the most recent N versions per evidence_key, etc.
-- Retention is intentionally NOT enforced by DDL; it is an operational decision.
