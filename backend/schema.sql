-- schedule_items: the official project schedule imported from the planner.
-- Each row is one task that a supervisor might report progress on.
CREATE TABLE IF NOT EXISTS schedule_items (
    id                      INTEGER PRIMARY KEY,
    task_name               TEXT NOT NULL,
    discipline              TEXT,            -- e.g. civil, piping, electrical
    location                TEXT,            -- zone or site name
    planned_start           TEXT,            -- ISO date (YYYY-MM-DD)
    planned_end             TEXT,            -- ISO date (YYYY-MM-DD)
    actual_completion_date  TEXT,            -- filled when status becomes 'done'
    status                  TEXT DEFAULT 'pending'  -- pending / in_progress / done / flagged
);

-- reports: every supervisor submission, whether it matched or not.
-- This is the audit log for "what came in and what happened to it."
CREATE TABLE IF NOT EXISTS reports (
    id                   INTEGER PRIMARY KEY,
    raw_text             TEXT NOT NULL,       -- the original plain-language report
    extracted_task       TEXT,                -- AI-extracted task name
    extracted_quantity   TEXT,                -- AI-extracted quantity (e.g. "50 meters")
    extracted_location   TEXT,                -- AI-extracted location
    extracted_date       TEXT,                -- AI-extracted date
    matched_schedule_id  INTEGER,            -- FK → schedule_items.id (NULL if no match)
    confidence_score     REAL,               -- how confident the matcher was (0.0–1.0)
    review_status        TEXT,               -- auto_applied / needs_review / rejected / no_match
    created_at           TEXT DEFAULT (datetime('now'))  -- when this report was received
);

-- task_history: historical record of completed tasks for analytics.
-- Populated automatically when any task moves to 'done'.
CREATE TABLE IF NOT EXISTS task_history (
    id                      INTEGER PRIMARY KEY,
    task_type               TEXT NOT NULL,    -- discipline of the task (civil/piping/electrical)
    planned_duration_days   INTEGER,          -- planned_end - planned_start
    actual_duration_days    INTEGER,          -- actual_completion_date - planned_start
    delay_reason            TEXT              -- NULL by default; filled by human or future logic
);
