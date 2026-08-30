CREATE TABLE IF NOT EXISTS schedule_items (
    id                      INTEGER PRIMARY KEY,
    task_name               TEXT NOT NULL,
    location                TEXT,
    planned_start           DATE,
    planned_end             DATE,
    status                  TEXT DEFAULT 'pending',
    actual_completion_date  DATE,
    linked_report_id        INTEGER
);

CREATE TABLE IF NOT EXISTS reports (
    id                   INTEGER PRIMARY KEY,
    raw_text             TEXT NOT NULL,
    extracted_task       TEXT,
    extracted_quantity   TEXT,
    extracted_location   TEXT,
    extracted_date       DATE,
    matched_schedule_id  INTEGER,
    confidence_score     REAL,
    review_status        TEXT,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_history (
    id                      INTEGER PRIMARY KEY,
    task_type               TEXT NOT NULL,
    planned_duration_days   INTEGER,
    actual_duration_days    INTEGER,
    delay_reason            TEXT
);
