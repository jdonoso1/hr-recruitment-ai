-- HR Platform — Initial Schema
-- Compatible with SQLite (dev) and PostgreSQL (production)
-- Run once: sqlite3 hr_platform.db < migrations/001_initial.sql

-- ─────────────────────────────────────────────
-- CLIENTS (HR firms using the platform)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clients (
    client_id    TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    contact_name TEXT,
    email        TEXT,
    phone        TEXT,
    plan         TEXT NOT NULL DEFAULT 'starter',  -- starter | pro | enterprise
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- ─────────────────────────────────────────────
-- JOBS (open roles per client)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    job_id            TEXT PRIMARY KEY,
    client_id         TEXT NOT NULL REFERENCES clients(client_id),
    title             TEXT NOT NULL,
    company           TEXT NOT NULL,
    description       TEXT NOT NULL,
    required_skills   TEXT NOT NULL DEFAULT '[]',   -- JSON array
    nice_to_have      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    experience_min    INTEGER,
    experience_max    INTEGER,
    location          TEXT,
    remote_ok         INTEGER NOT NULL DEFAULT 0,
    salary_min        REAL,
    salary_max        REAL,
    status            TEXT NOT NULL DEFAULT 'open', -- open | screening | interviewing | closed
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- ─────────────────────────────────────────────
-- CANDIDATES (core intelligence asset)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id        TEXT PRIMARY KEY,
    client_id           TEXT NOT NULL REFERENCES clients(client_id),

    -- Identity
    name                TEXT NOT NULL,
    email               TEXT,
    phone               TEXT,
    linkedin_url        TEXT,
    location            TEXT,
    languages           TEXT NOT NULL DEFAULT '[]',  -- JSON array

    -- Professional profile
    current_role        TEXT,
    current_company     TEXT,
    years_experience    REAL,
    industries          TEXT NOT NULL DEFAULT '[]',  -- JSON array
    skills              TEXT NOT NULL DEFAULT '[]',  -- JSON array
    cv_raw_text         TEXT,                        -- full parsed CV text
    cv_file_path        TEXT,                        -- path to original PDF

    -- Preferences
    salary_expectation  REAL,
    salary_currency     TEXT DEFAULT 'USD',
    relocation_ok       INTEGER NOT NULL DEFAULT 0,
    availability        TEXT,                        -- immediate | 2 weeks | 1 month | etc.

    -- Intelligence / reusability
    reusable            INTEGER NOT NULL DEFAULT 1,
    recommended_roles   TEXT NOT NULL DEFAULT '[]',  -- JSON array
    recommended_industries TEXT NOT NULL DEFAULT '[]',
    priority_level      TEXT NOT NULL DEFAULT 'normal', -- low | normal | high
    notes               TEXT,

    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

-- ─────────────────────────────────────────────
-- CANDIDATE EVALUATIONS (per job application)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id       TEXT PRIMARY KEY,
    candidate_id        TEXT NOT NULL REFERENCES candidates(candidate_id),
    job_id              TEXT NOT NULL REFERENCES jobs(job_id),
    client_id           TEXT NOT NULL REFERENCES clients(client_id),

    -- Screening scores (breakdown)
    screening_score     REAL,                        -- 1–10 overall
    skills_score        REAL,                        -- 1–10
    experience_score    REAL,                        -- 1–10
    culture_score       REAL,                        -- 1–10
    screening_reasoning TEXT,
    strengths           TEXT NOT NULL DEFAULT '[]',  -- JSON array
    weaknesses          TEXT NOT NULL DEFAULT '[]',  -- JSON array
    red_flags           TEXT NOT NULL DEFAULT '[]',  -- JSON array

    -- Interview scores
    interview_score     REAL,
    interview_notes     TEXT,                        -- raw recruiter notes / transcript
    interview_reasoning TEXT,
    communication_score REAL,
    technical_score     REAL,
    motivation_score    REAL,

    -- Workflow state
    stage               TEXT NOT NULL DEFAULT 'uploaded',
    -- uploaded | screened | recruiter_review | approved | interview_scheduled
    -- | interviewed | evaluated | report_generated | hired | rejected

    recruiter_decision  TEXT,                        -- approved | rejected | hold
    recruiter_notes     TEXT,
    final_outcome       TEXT,                        -- hired | rejected | withdrew | on_hold

    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,

    UNIQUE(candidate_id, job_id)
);

-- ─────────────────────────────────────────────
-- INTERVIEWS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interviews (
    interview_id        TEXT PRIMARY KEY,
    evaluation_id       TEXT NOT NULL REFERENCES evaluations(evaluation_id),
    candidate_id        TEXT NOT NULL REFERENCES candidates(candidate_id),
    job_id              TEXT NOT NULL REFERENCES jobs(job_id),

    questions_generated TEXT NOT NULL DEFAULT '[]',  -- JSON array of questions
    transcript          TEXT,                        -- raw text input
    ai_analysis         TEXT,                        -- full JSON analysis from agent
    scheduled_at        TEXT,
    completed_at        TEXT,
    created_at          TEXT NOT NULL
);

-- ─────────────────────────────────────────────
-- KPI LOGS (per client, per period)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kpi_logs (
    kpi_id                  TEXT PRIMARY KEY,
    client_id               TEXT NOT NULL REFERENCES clients(client_id),
    job_id                  TEXT,
    period_start            TEXT NOT NULL,
    period_end              TEXT NOT NULL,

    candidates_processed    INTEGER NOT NULL DEFAULT 0,
    candidates_screened     INTEGER NOT NULL DEFAULT 0,
    candidates_interviewed  INTEGER NOT NULL DEFAULT 0,
    candidates_hired        INTEGER NOT NULL DEFAULT 0,
    candidates_reused       INTEGER NOT NULL DEFAULT 0,

    time_to_shortlist_days  REAL,
    time_to_hire_days       REAL,
    hours_saved_estimate    REAL,
    reuse_rate_pct          REAL,

    created_at              TEXT NOT NULL
);

-- ─────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_candidates_client    ON candidates(client_id);
CREATE INDEX IF NOT EXISTS idx_candidates_skills    ON candidates(skills);
CREATE INDEX IF NOT EXISTS idx_evaluations_job      ON evaluations(job_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_stage    ON evaluations(stage);
CREATE INDEX IF NOT EXISTS idx_jobs_client          ON jobs(client_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status          ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_kpi_client_period    ON kpi_logs(client_id, period_start);
