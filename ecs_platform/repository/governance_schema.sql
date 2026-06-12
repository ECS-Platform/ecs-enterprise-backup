-- ECS governance / management layer schema (PostgreSQL).
-- Idempotent: safe to run repeatedly on startup. Builds on the evidence schema.

-- Application inventory (onboarded business applications).
CREATE TABLE IF NOT EXISTS applications (
    id              BIGSERIAL PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,          -- matches evidence.application
    name            TEXT NOT NULL,
    description     TEXT,
    owner           TEXT,
    owner_email     TEXT,
    business_unit   TEXT,
    criticality     TEXT NOT NULL DEFAULT 'Medium', -- Critical|High|Medium|Low
    environment     TEXT NOT NULL DEFAULT 'Production',
    lifecycle_status TEXT NOT NULL DEFAULT 'Active', -- Onboarding|Active|Decommissioned
    tech_stack      TEXT,
    hosting         TEXT,
    onboarded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Frameworks in scope per application (many-to-many).
CREATE TABLE IF NOT EXISTS application_frameworks (
    app_slug        TEXT NOT NULL,
    framework_code  TEXT NOT NULL,
    PRIMARY KEY (app_slug, framework_code)
);

-- Control catalog: the controls ECS expects evidence for (the "denominator").
CREATE TABLE IF NOT EXISTS control_catalog (
    control_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    domain          TEXT,
    framework_code  TEXT,                          -- primary framework this control rolls up to
    description     TEXT
);

-- Control <-> framework crosswalk (many-to-many). This is what makes evidence
-- REUSE measurable: a single control (and therefore a single evidence item
-- mapped to it) satisfies a requirement in many frameworks simultaneously.
CREATE TABLE IF NOT EXISTS control_framework_crosswalk (
    control_id      TEXT NOT NULL,
    framework_code  TEXT NOT NULL,
    requirement_ref TEXT,                          -- e.g. "CC8.1", "A.14.2.1", "6.3"
    PRIMARY KEY (control_id, framework_code)
);
CREATE INDEX IF NOT EXISTS idx_crosswalk_fw ON control_framework_crosswalk (framework_code);

-- Evidence lifecycle / review state (one row per evidence_uid).
CREATE TABLE IF NOT EXISTS evidence_reviews (
    evidence_uid    TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'Collected', -- Collected|UnderReview|Approved|Rejected|Expired
    reviewer        TEXT,
    note            TEXT,
    reviewed_at     TIMESTAMPTZ,
    valid_until     TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Recurring evidence collection schedules.
CREATE TABLE IF NOT EXISTS collection_schedules (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    connector       TEXT,
    app_slug        TEXT,
    frequency       TEXT NOT NULL DEFAULT 'Daily',  -- Hourly|Daily|Weekly|Monthly
    owner           TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    last_run        TIMESTAMPTZ,
    last_status     TEXT,
    next_run        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_fw_slug ON application_frameworks (app_slug);
CREATE INDEX IF NOT EXISTS idx_sched_app ON collection_schedules (app_slug);
