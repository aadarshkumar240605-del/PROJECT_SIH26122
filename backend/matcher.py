"""
Stub matcher — replace this with the real matching engine later.

This file exists so the routes can call match_report() without caring
whether the matcher is real or fake.  When the matching team delivers
their engine, just change the logic inside this function.
"""

from database import get_db


def match_report(extracted_data: dict) -> dict:
    """Compare extracted report fields against the schedule and return
    a match candidate with a confidence score.

    Args:
        extracted_data: dict with keys {task, quantity, location, date, raw_text}

    Returns:
        {"schedule_id": int | None, "confidence": float}

    Stub logic (so we can test all three confidence branches):
      - If task name matches a schedule item's task_name → 0.85 (auto-apply)
      - If only location matches                        → 0.60 (needs review)
      - Otherwise                                       → 0.30 (no match)
    """
    task = (extracted_data.get("task") or "").lower()
    location = (extracted_data.get("location") or "").lower()

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, task_name, location FROM schedule_items WHERE status != 'done'"
        ).fetchall()

    # Try to find a match by task name first (strongest signal)
    for row in rows:
        if task and task in row["task_name"].lower():
            return {"schedule_id": row["id"], "confidence": 0.85}

    # Fall back to location-only match (weaker signal)
    for row in rows:
        if location and location in (row["location"] or "").lower():
            return {"schedule_id": row["id"], "confidence": 0.60}

    # Nothing matched at all
    return {"schedule_id": None, "confidence": 0.30}
