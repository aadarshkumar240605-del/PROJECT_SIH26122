"""
Seed the database with realistic schedule_items and task_history rows.

Run this AFTER init_db.py:
    python init_db.py
    python seed.py

Safe to re-run (idempotent):
  - schedule_items uses INSERT OR IGNORE on explicit IDs, so duplicates
    are skipped automatically.
  - task_history has no natural unique key, so this script DELETEs only
    the specific (task_type, planned_duration_days, actual_duration_days,
    delay_reason) tuples it owns before re-inserting them.  Rows created
    by real field activity (via routes.py) are never touched.
"""

from database import get_db

# ---------------------------------------------------------------------------
# 25 schedule_items across 3 disciplines and 4 zones.
# All start as 'pending' with a ~2-week planned window.
# ---------------------------------------------------------------------------
SCHEDULE_ITEMS = [
    # --- Civil (Zone A - Tank Farm) ---
    (1,  "Excavation for tank foundation",      "civil",      "Zone A - Tank Farm",       "2026-09-01", "2026-09-07", None, "pending"),
    (2,  "Concrete pouring for tank base",       "civil",      "Zone A - Tank Farm",       "2026-09-03", "2026-09-10", None, "pending"),
    (3,  "Backfilling around tank pad",          "civil",      "Zone A - Tank Farm",       "2026-09-05", "2026-09-12", None, "pending"),
    (4,  "Grading and leveling access road",     "civil",      "Zone A - Tank Farm",       "2026-09-08", "2026-09-14", None, "pending"),

    # --- Civil (Zone D - Control Room) ---
    (5,  "Foundation work for control room",     "civil",      "Zone D - Control Room",    "2026-09-02", "2026-09-09", None, "pending"),
    (6,  "Structural framing installation",      "civil",      "Zone D - Control Room",    "2026-09-06", "2026-09-14", None, "pending"),
    (7,  "Roof slab casting",                    "civil",      "Zone D - Control Room",    "2026-09-10", "2026-09-14", None, "pending"),

    # --- Piping (Zone A - Tank Farm) ---
    (8,  "Pipe spool fabrication",               "piping",     "Zone A - Tank Farm",       "2026-09-01", "2026-09-08", None, "pending"),
    (9,  "Pipe welding near tank 3",             "piping",     "Zone A - Tank Farm",       "2026-09-04", "2026-09-11", None, "pending"),
    (10, "Hydro testing of tank inlet line",     "piping",     "Zone A - Tank Farm",       "2026-09-07", "2026-09-14", None, "pending"),

    # --- Piping (Zone B - Pipeline Corridor) ---
    (11, "Trench excavation for pipeline",       "piping",     "Zone B - Pipeline Corridor", "2026-09-01", "2026-09-10", None, "pending"),
    (12, "16-inch pipeline laying",              "piping",     "Zone B - Pipeline Corridor", "2026-09-03", "2026-09-12", None, "pending"),
    (13, "Pipeline welding joints",              "piping",     "Zone B - Pipeline Corridor", "2026-09-05", "2026-09-14", None, "pending"),
    (14, "Pipeline pressure testing",            "piping",     "Zone B - Pipeline Corridor", "2026-09-08", "2026-09-14", None, "pending"),
    (15, "Pipe support installation",            "piping",     "Zone B - Pipeline Corridor", "2026-09-02", "2026-09-09", None, "pending"),

    # --- Electrical (Zone C - Substation) ---
    (16, "Cable tray installation",              "electrical", "Zone C - Substation",      "2026-09-01", "2026-09-07", None, "pending"),
    (17, "HT cable pulling",                     "electrical", "Zone C - Substation",      "2026-09-03", "2026-09-10", None, "pending"),
    (18, "Transformer foundation and mounting",  "electrical", "Zone C - Substation",      "2026-09-02", "2026-09-11", None, "pending"),
    (19, "Switchgear panel installation",        "electrical", "Zone C - Substation",      "2026-09-05", "2026-09-12", None, "pending"),
    (20, "Earthing and grounding work",          "electrical", "Zone C - Substation",      "2026-09-06", "2026-09-14", None, "pending"),

    # --- Electrical (Zone D - Control Room) ---
    (21, "LT cable laying in control room",      "electrical", "Zone D - Control Room",    "2026-09-04", "2026-09-11", None, "pending"),
    (22, "Panel wiring and termination",         "electrical", "Zone D - Control Room",    "2026-09-07", "2026-09-14", None, "pending"),
    (23, "Lighting installation",                "electrical", "Zone D - Control Room",    "2026-09-08", "2026-09-14", None, "pending"),

    # --- Mixed (Zone B - Pipeline Corridor) ---
    (24, "Cathodic protection installation",     "electrical", "Zone B - Pipeline Corridor", "2026-09-04", "2026-09-12", None, "pending"),
    (25, "Road crossing bore for pipeline",      "civil",      "Zone B - Pipeline Corridor", "2026-09-03", "2026-09-10", None, "pending"),
]

# ---------------------------------------------------------------------------
# 6 pre-completed task_history rows so the analytics chart has data.
# These represent tasks from a "previous phase" that are already done.
# ---------------------------------------------------------------------------
TASK_HISTORY = [
    # (task_type, planned_days, actual_days, delay_reason)
    ("civil",      7,  7,  None),                       # on-time
    ("civil",      10, 12, "Rain delay"),                # 2 days late
    ("piping",     8,  8,  None),                        # on-time
    ("piping",     14, 18, "Material delivery delayed"), # 4 days late
    ("electrical", 6,  6,  None),                        # on-time
    ("electrical", 9,  11, "Permit approval pending"),   # 2 days late
]


def seed():
    with get_db() as conn:
        # Seed schedule items
        conn.executemany(
            """INSERT OR IGNORE INTO schedule_items
               (id, task_name, discipline, location,
                planned_start, planned_end, actual_completion_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            SCHEDULE_ITEMS,
        )

        # Seed task history — idempotent.
        #
        # task_history has no natural unique key (only an auto-increment id),
        # so INSERT OR IGNORE cannot detect duplicates here.  Instead we
        # delete any existing rows that exactly match the tuples this script
        # owns, then re-insert them.  This leaves rows written by real field
        # activity (via /submit) completely untouched.
        conn.executemany(
            """DELETE FROM task_history
               WHERE task_type = ?
                 AND planned_duration_days = ?
                 AND actual_duration_days = ?
                 AND (delay_reason IS ? OR delay_reason = ?)""",
            # Pass each reason twice: once for the IS ? (NULL check) and
            # once for the = ? (non-NULL equality check).
            [(r[0], r[1], r[2], r[3], r[3]) for r in TASK_HISTORY],
        )
        conn.executemany(
            """INSERT INTO task_history
               (task_type, planned_duration_days, actual_duration_days, delay_reason)
               VALUES (?, ?, ?, ?)""",
            TASK_HISTORY,
        )

        conn.commit()
        print(f"Seeded {len(SCHEDULE_ITEMS)} schedule items and {len(TASK_HISTORY)} task history rows.")


if __name__ == "__main__":
    seed()
