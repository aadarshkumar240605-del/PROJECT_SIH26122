"""
All API endpoints for the SIH26122 backend.

Each endpoint has a docstring explaining WHAT it does and WHY it exists,
so any team member can read the code and understand the system flow.
"""

from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import get_db
from matcher import match_report

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models — these define what the API accepts/returns.
# Using models gives us automatic validation and clear documentation.
# ---------------------------------------------------------------------------

class ReportPayload(BaseModel):
    """The contract defined by the extraction team. Do NOT rename these fields."""
    task: str
    quantity: str | None = None
    location: str | None = None
    date: str | None = None       # ISO date string from the extraction step
    raw_text: str


class ConfirmMatchPayload(BaseModel):
    """Used by the review UI to manually confirm a match."""
    report_id: int
    schedule_id: int


class ReportIdPayload(BaseModel):
    """Used to reject / mark a report as unplanned."""
    report_id: int


# ---------------------------------------------------------------------------
# Helper: apply a match (used by both auto-match and manual confirm)
# ---------------------------------------------------------------------------

def _apply_match(conn, schedule_id: int, completion_date: str):
    """Mark a schedule item as 'done' and record it in task_history.

    This is factored out because both the auto-match path (/submit with
    high confidence) and the manual-confirm path (/confirm-match) need
    to do the exact same thing.
    """
    # Fetch the schedule item so we can compute durations
    item = conn.execute(
        "SELECT * FROM schedule_items WHERE id = ?", (schedule_id,)
    ).fetchone()

    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")

    # Update the schedule item to 'done'
    conn.execute(
        """UPDATE schedule_items
           SET status = 'done', actual_completion_date = ?
           WHERE id = ?""",
        (completion_date, schedule_id),
    )

    # Compute durations for task_history.
    # We parse ISO dates and subtract to get day counts.
    planned_start = date.fromisoformat(item["planned_start"])
    planned_end = date.fromisoformat(item["planned_end"])
    actual_end = date.fromisoformat(completion_date)

    planned_days = (planned_end - planned_start).days
    actual_days = (actual_end - planned_start).days

    # Insert into task_history so the analytics layer has data
    conn.execute(
        """INSERT INTO task_history (task_type, planned_duration_days,
                                     actual_duration_days, delay_reason)
           VALUES (?, ?, ?, NULL)""",
        (item["discipline"], planned_days, actual_days),
    )


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@router.get("/schedule")
def get_schedule():
    """Return all rows from schedule_items.

    Why: The frontend schedule view needs the full list of planned tasks
    to render the Gantt chart / table.
    """
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM schedule_items").fetchall()
    # sqlite3.Row objects aren't JSON-serializable, so convert to dicts
    return [dict(row) for row in rows]


@router.post("/submit")
def submit_report(payload: ReportPayload):
    """Accept a field report from the extraction pipeline and process it.

    Why: This is the main entry point for new data. The extraction team
    sends us structured JSON; we match it against the schedule and
    decide whether to auto-apply, flag for review, or mark as no-match.

    Flow:
      1. Call the matcher to get a candidate schedule_id + confidence
      2. Branch on confidence:
         >= 0.80 → auto-apply (update schedule, insert task_history)
         0.50–0.79 → needs_review (human must confirm)
         < 0.50  → no_match
      3. Always insert a row into reports for the audit trail
    """
    extracted = {
        "task": payload.task,
        "quantity": payload.quantity,
        "location": payload.location,
        "date": payload.date,
        "raw_text": payload.raw_text,
    }

    # Step 1: Ask the matcher for a candidate
    result = match_report(extracted)
    schedule_id = result["schedule_id"]
    confidence = result["confidence"]

    # Step 2: Decide what to do based on confidence
    if confidence >= 0.80:
        review_status = "auto_applied"
    elif confidence >= 0.50:
        review_status = "needs_review"
    else:
        review_status = "no_match"

    with get_db() as conn:
        # Step 3a: If auto-applying, update the schedule and log history
        if review_status == "auto_applied" and schedule_id is not None:
            completion_date = payload.date or datetime.now().strftime("%Y-%m-%d")
            _apply_match(conn, schedule_id, completion_date)

        # Step 3b: Always insert the report (this IS the audit trail)
        conn.execute(
            """INSERT INTO reports
               (raw_text, extracted_task, extracted_quantity,
                extracted_location, extracted_date,
                matched_schedule_id, confidence_score, review_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload.raw_text,
                payload.task,
                payload.quantity,
                payload.location,
                payload.date,
                schedule_id,
                confidence,
                review_status,
            ),
        )
        conn.commit()

    return {
        "review_status": review_status,
        "matched_schedule_id": schedule_id,
        "confidence": confidence,
    }


@router.get("/review-queue")
def review_queue():
    """Return all reports that need human review, with their matched candidate info.

    Why: When confidence is between 0.50 and 0.80, a supervisor needs to
    look at the match and confirm or reject it.  This endpoint powers
    that review UI.
    """
    with get_db() as conn:
        # LEFT JOIN so we get the candidate schedule item's details
        # alongside the report.  If matched_schedule_id is NULL, the
        # schedule columns will just be NULL.
        rows = conn.execute(
            """SELECT r.*, s.task_name AS candidate_task,
                      s.discipline AS candidate_discipline,
                      s.location AS candidate_location,
                      s.planned_start, s.planned_end
               FROM reports r
               LEFT JOIN schedule_items s ON r.matched_schedule_id = s.id
               WHERE r.review_status = 'needs_review'
               ORDER BY r.created_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("/confirm-match")
def confirm_match(payload: ConfirmMatchPayload):
    """Manually confirm a match between a report and a schedule item.

    Why: When auto-matching wasn't confident enough, a human reviews it.
    If they agree, we apply the same logic as an auto-match: mark the
    schedule item 'done' and record task_history.
    """
    with get_db() as conn:
        # Verify the report exists and is actually pending review
        report = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (payload.report_id,)
        ).fetchone()

        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        if report["review_status"] != "needs_review":
            raise HTTPException(
                status_code=400,
                detail=f"Report is '{report['review_status']}', not 'needs_review'",
            )

        # Use the extracted date from the report, or today as fallback
        completion_date = report["extracted_date"] or datetime.now().strftime("%Y-%m-%d")

        # Apply the match (same logic as auto-match)
        _apply_match(conn, payload.schedule_id, completion_date)

        # Update the report to reflect the confirmation
        conn.execute(
            """UPDATE reports
               SET review_status = 'auto_applied', matched_schedule_id = ?
               WHERE id = ?""",
            (payload.schedule_id, payload.report_id),
        )
        conn.commit()

    return {"status": "confirmed", "report_id": payload.report_id}


@router.post("/unplanned")
def mark_unplanned(payload: ReportIdPayload):
    """Mark a report as rejected (unplanned / doesn't match anything real).

    Why: Sometimes a supervisor reports something that isn't in the
    schedule at all (ad-hoc work, wrong site, duplicate, etc.).
    This endpoint lets the reviewer dismiss it without touching
    the schedule.
    """
    with get_db() as conn:
        report = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (payload.report_id,)
        ).fetchone()

        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")

        conn.execute(
            "UPDATE reports SET review_status = 'rejected' WHERE id = ?",
            (payload.report_id,),
        )
        conn.commit()

    return {"status": "rejected", "report_id": payload.report_id}


@router.get("/audit-trail")
def audit_trail():
    """Return all reports in chronological order.

    Why: This is the full log view — every report that ever came in,
    what it matched, and what happened to it.  Useful for compliance,
    debugging, and demo day.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/dashboard")
def dashboard():
    """Return summary counts for the dashboard widgets.

    Why: The frontend dashboard needs quick aggregate numbers —
    how many tasks are pending vs done, how many reports need review, etc.
    Doing this in SQL is faster than fetching all rows and counting in Python.
    """
    with get_db() as conn:
        # Count schedule items by status
        task_counts = {}
        for status in ("pending", "in_progress", "done", "flagged"):
            count = conn.execute(
                "SELECT COUNT(*) FROM schedule_items WHERE status = ?",
                (status,),
            ).fetchone()[0]
            task_counts[status] = count

        # Count reports by review_status
        report_counts = {}
        for status in ("auto_applied", "needs_review", "rejected", "no_match"):
            count = conn.execute(
                "SELECT COUNT(*) FROM reports WHERE review_status = ?",
                (status,),
            ).fetchone()[0]
            report_counts[status] = count

    return {
        "tasks": task_counts,
        "reports": report_counts,
    }


@router.get("/activities")
def activities(discipline: str | None = Query(default=None)):
    """Return schedule items, optionally filtered by discipline.

    Why: The activities view is like /schedule but lets the frontend
    filter by trade (civil, piping, electrical) via a dropdown.
    """
    with get_db() as conn:
        if discipline:
            rows = conn.execute(
                "SELECT * FROM schedule_items WHERE discipline = ?",
                (discipline,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM schedule_items").fetchall()
    return [dict(row) for row in rows]
