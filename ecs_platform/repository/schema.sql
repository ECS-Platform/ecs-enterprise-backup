-- ECS Evidence Repository schema (PostgreSQL).
-- Idempotent: safe to run repeatedly on startup.

CREATE TABLE IF NOT EXISTS connectors (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    base_url        TEXT,
    last_health     TEXT,
    last_checked    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence (
    id                  BIGSERIAL PRIMARY KEY,
    evidence_uid        TEXT NOT NULL UNIQUE,
    source_system       TEXT NOT NULL,
    source_object_id    TEXT NOT NULL,
    object_type         TEXT NOT NULL,
    title               TEXT NOT NULL,
    content             TEXT,
    owner               TEXT,
    url                 TEXT,
    application         TEXT,
    collected_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash        TEXT NOT NULL,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_system, source_object_id, object_type)
);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence (source_system);
CREATE INDEX IF NOT EXISTS idx_evidence_app ON evidence (application);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence (object_type);

CREATE TABLE IF NOT EXISTS controls (
    id          BIGSERIAL PRIMARY KEY,
    control_id  TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    domain      TEXT
);

CREATE TABLE IF NOT EXISTS frameworks (
    id          BIGSERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL
);

-- Evidence <-> control mapping (many-to-many).
CREATE TABLE IF NOT EXISTS evidence_control_map (
    evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    control_id  TEXT NOT NULL,
    confidence  REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (evidence_id, control_id)
);

-- Evidence <-> framework mapping (many-to-many).
CREATE TABLE IF NOT EXISTS evidence_framework_map (
    evidence_id    BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    framework_code TEXT NOT NULL,
    PRIMARY KEY (evidence_id, framework_code)
);

-- Lineage: how a piece of evidence was produced/derived.
CREATE TABLE IF NOT EXISTS evidence_lineage (
    id           BIGSERIAL PRIMARY KEY,
    evidence_id  BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    parent_uid   TEXT,
    operation    TEXT NOT NULL,
    actor        TEXT,
    detail       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Correlation groups (same control satisfied by multiple sources).
CREATE TABLE IF NOT EXISTS correlation_groups (
    id          BIGSERIAL PRIMARY KEY,
    group_key   TEXT NOT NULL UNIQUE,
    control_id  TEXT,
    summary     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS correlation_members (
    group_id    BIGINT NOT NULL REFERENCES correlation_groups(id) ON DELETE CASCADE,
    evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id            BIGSERIAL PRIMARY KEY,
    connector     TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL,
    finished_at   TIMESTAMPTZ,
    ok            BOOLEAN,
    collected     INTEGER NOT NULL DEFAULT 0,
    error         TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    actor       TEXT NOT NULL,
    role        TEXT,
    action      TEXT NOT NULL,
    resource    TEXT,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor);
