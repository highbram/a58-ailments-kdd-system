-- Ailments Knowledge Discovery System - UHS Jaja (Group A58)
-- Database schema

CREATE TABLE IF NOT EXISTS user (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('Admin', 'Analyst'))
);

CREATE TABLE IF NOT EXISTS ailment (
    ailment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ailment_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS patient (
    patient_code   TEXT PRIMARY KEY,
    age_group      TEXT NOT NULL,
    sex            TEXT NOT NULL,
    patient_type   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visit (
    visit_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_code   TEXT NOT NULL REFERENCES patient(patient_code),
    visit_date     TEXT NOT NULL,
    complaint      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnosis (
    diagnosis_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id        INTEGER NOT NULL REFERENCES visit(visit_id),
    ailment_id      INTEGER NOT NULL REFERENCES ailment(ailment_id),
    treatment_given TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES user(user_id),
    action      TEXT NOT NULL,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mining_run (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES user(user_id),
    technique   TEXT NOT NULL,
    parameters  TEXT,
    run_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pattern (
    pattern_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL REFERENCES mining_run(run_id),
    description  TEXT NOT NULL,
    support      REAL,
    confidence   REAL,
    lift         REAL
);

-- Seed the fixed list of ailments the frontend/seed data expects
INSERT OR IGNORE INTO ailment (ailment_name) VALUES
    ('Malaria'),
    ('Typhoid fever'),
    ('Upper respiratory infection'),
    ('Hypertension'),
    ('Peptic ulcer'),
    ('Skin infection'),
    ('Migraine'),
    ('Urinary tract infection'),
    ('Allergy'),
    ('Injury/Sprain');
