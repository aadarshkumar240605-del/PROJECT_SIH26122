"""
All API endpoints for the SIH26122 backend.

Each endpoint has a docstring explaining WHAT it does and WHY it exists,
so any team member can read the code and understand the system flow.
"""

from datetime import datetime, date
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from contract import extract_response_to_match_payloads
from database import get_db
from extractor import extract_report
from match_engine import match_activity

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
    date: str | None = None  # ISO date string from the extraction step
    raw_text: str


class SubmitFieldReportRequest(BaseModel):
    """Plain-text field report payload accepted by the new /submit endpoint."""

    report_text: str = Field(
        ..., min_length=1, description="Raw field report text to extract and match"
    )


class ConfirmMatchPayload(BaseModel):
    """Used by the review UI to manually confirm a match."""

    report_id: int
    schedule_id: int


class ReportIdPayload(BaseModel):
    """Used to reject / mark a report as unplanned."""

    report_id: int


class ExtractRequest(BaseModel):
    """Input for the /extract endpoint — the raw field report text."""

    report_text: str = Field(
        ...,
        min_length=1,
        description="Raw field report text to extract activities from",
    )


class Activity(BaseModel):
    """A single construction activity extracted from a field report."""

    activity: str
    location: str | None = None
    date: str | None = None  # ISO date resolved by extractor post-processing
    status: Literal["completed", "in_progress", "pending", "delayed", "unknown"] = (
        "unknown"
    )
    progress_percent: int | None = Field(default=None, ge=0, le=100)


class ExtractResponse(BaseModel):
    """Structured output returned by the /extract endpoint."""

    activities: list[Activity]
    issues: list[str]


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
def submit_report(payload: SubmitFieldReportRequest):
    """Accept a plain-text field report, extract activities, map them to
    the locked /match contract, and return match results for every activity.

    Flow:
      1. Call extract_report(report_text)
      2. Convert each extracted activity via contract.extract_response_to_match_payloads
      3. For each contract payload, call match_activity(...)
      4. Persist one reports row per result (audit trail — keeps
         /review-queue, /audit-trail and /dashboard alive)
      5. Return the results array along with any extraction issues

    Persistence rules:
      - review_status maps from match_status: auto_linked -> auto_applied,
        review_queue -> needs_review, unplanned -> no_match.
      - matched_activity_code stores the Primavera activity_id string.
      - matched_schedule_id stays NULL for now: auto-applying (marking the
        schedule item done) requires the Primavera schedule to be imported
        into schedule_items, which is a pending task. Until then,
        /confirm-match remains the manual path once that import exists.
      - confidence_score is stored on the legacy 0.0–1.0 scale
        (engine confidence / 100) to stay consistent with the thresholds
        used elsewhere in this module.
    """
    extraction = extract_report(payload.report_text)
    contract_payloads, issues = extract_response_to_match_payloads(extraction)

    if not contract_payloads:
        return {
            "results": [],
            "issues": (
                issues
                if issues
                else ["No extractable activities were found in the report."]
            ),
        }

    results = []
    for item in contract_payloads:
        try:
            result = match_activity(
                extracted_description=item["activity_description"],
                discipline=item.get("discipline"),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Matching engine error: {str(exc)}"
            )

        results.append(
            {
                "matched_activity_id": result["matched_activity_id"],
                "matched_activity_name": result["matched_activity_name"],
                "confidence_score": result["confidence_score"],
                "match_status": result["match_status"],
                "rejection_reason": result.get("rejection_reason"),
            }
        )

    # ---- persistence: one audit row per matched activity ----
    STATUS_TO_REVIEW = {
        "auto_linked": "auto_applied",
        "review_queue": "needs_review",
        "unplanned": "no_match",
    }
    with get_db() as conn:
        for item, result in zip(contract_payloads, results):
            conn.execute(
                """INSERT INTO reports
                   (raw_text, extracted_task, extracted_location, extracted_date,
                    matched_activity_code, confidence_score, review_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload.report_text,
                    item["activity_description"],
                    item.get("location"),
                    item.get("actual_start"),
                    result["matched_activity_id"],
                    result["confidence_score"] / 100.0,
                    STATUS_TO_REVIEW[result["match_status"]],
                ),
            )
        conn.commit()

    return {
        "results": results,
        "issues": issues,
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
        rows = conn.execute("""SELECT r.*, s.task_name AS candidate_task,
                      s.discipline AS candidate_discipline,
                      s.location AS candidate_location,
                      s.planned_start, s.planned_end
               FROM reports r
               LEFT JOIN schedule_items s ON r.matched_schedule_id = s.id
               WHERE r.review_status = 'needs_review'
               ORDER BY r.created_at DESC""").fetchall()
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
        completion_date = report["extracted_date"] or datetime.now().strftime(
            "%Y-%m-%d"
        )

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
        rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
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


@router.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest):
    """Extract structured activity data from a plain-language field report.

    Why: Field workers submit voice or text reports in natural language.
    This endpoint sends that text to Ollama (llama3.2:3b) and returns
    structured data (activity name, location, date, status, progress %)
    ready for the scheduler to match against the Primavera baseline.

    Flow:
        1. Pydantic validates report_text (non-empty enforced by ExtractRequest)
        2. Known locations are loaded from schedule_items in the DB
        3. Ollama extraction function parses the text
        4. Deterministic post-processing validates locations, dates, progress
        5. Result is validated and returned as ExtractResponse
    """
    try:
        result = extract_report(payload.report_text)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction service error: {exc}",
        ) from exc

    return ExtractResponse(**result)
