"""
test_edge_cases.py — Deterministic unit tests for Day 4 Step 3.

Tests the post-processing logic in extractor._postprocess and the
Pydantic validation in routes.Activity WITHOUT calling Ollama/the LLM.

Each test uses the actual production function signatures and data structures
confirmed in the Step 2 inspection:

    _postprocess(raw_result: dict, report_text: str, known_locations: list[str]) -> dict
    Activity(activity, location, date, status, progress_percent)

Run with:
    pytest test_edge_cases.py -v
"""

from datetime import date

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Imports — use the real production modules, no mocking
# ---------------------------------------------------------------------------
# extractor._postprocess is module-private but importable for unit testing.
from extractor import _postprocess

# Activity and ExtractResponse live in routes.py (confirmed in Step 2 inspection).
from routes import Activity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_raw(
    activity: str = "Pipe welding",
    location: str | None = None,
    date_val: str | None = None,
    status: str = "in_progress",
    progress_percent: int | None = None,
) -> dict:
    """
    Build the minimal dict shape that the LLM would return and that
    _postprocess expects under the 'activities' key.
    """
    return {
        "activities": [
            {
                "activity":         activity,
                "location":         location,
                "date":             date_val,
                "status":           status,
                "progress_percent": progress_percent,
            }
        ],
        "issues": [],
    }


# ---------------------------------------------------------------------------
# Test 1 — Missing date is defaulted to today by _postprocess
# ---------------------------------------------------------------------------

def test_missing_date_defaults_to_today():
    """
    When the LLM returns date=null and the report text contains no date
    reference, _postprocess must fill in today's ISO date.
    """
    raw = _minimal_raw(date_val=None)
    result = _postprocess(raw, "Pipe welding ongoing.", known_locations=[])

    assert result["activities"], "Expected at least one activity in the result"
    resolved_date = result["activities"][0]["date"]

    assert resolved_date is not None, (
        "_postprocess must not leave date as null — it should default to today"
    )
    assert resolved_date == date.today().isoformat(), (
        f"Expected today's date {date.today().isoformat()!r}, got {resolved_date!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — An already-present ISO date is preserved unchanged
# ---------------------------------------------------------------------------

def test_existing_date_is_preserved():
    """
    When the LLM returns a valid ISO date string, _postprocess must not
    overwrite it with today's date or any other value.
    """
    fixed_date = "2025-06-15"
    raw = _minimal_raw(date_val=fixed_date)
    result = _postprocess(raw, "Pipe welding ongoing.", known_locations=[])

    assert result["activities"], "Expected at least one activity in the result"
    resolved_date = result["activities"][0]["date"]

    assert resolved_date == fixed_date, (
        f"_postprocess must preserve existing date {fixed_date!r}; got {resolved_date!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Activity model accepts all-null optional fields
# ---------------------------------------------------------------------------

def test_activity_model_accepts_all_null_optionals():
    """
    The Activity Pydantic model must accept:
      - activity as a non-empty string
      - location=None
      - date=None
      - status="unknown"  (the declared default)
      - progress_percent=None
    This verifies that every optional field is genuinely optional with null.
    """
    act = Activity(
        activity="Trench excavation",
        location=None,
        date=None,
        status="unknown",
        progress_percent=None,
    )

    assert act.activity == "Trench excavation"
    assert act.location is None
    assert act.date is None
    assert act.status == "unknown"
    assert act.progress_percent is None


# ---------------------------------------------------------------------------
# Test 4 — Activity model rejects out-of-range progress_percent
# ---------------------------------------------------------------------------

def test_activity_model_rejects_invalid_progress_percent():
    """
    Activity.progress_percent is validated as ge=0, le=100 (confirmed in routes.py).
    Values outside that range must raise pydantic.ValidationError.
    """
    # Below 0
    with pytest.raises(ValidationError):
        Activity(
            activity="Cable laying",
            status="in_progress",
            progress_percent=-1,
        )

    # Above 100
    with pytest.raises(ValidationError):
        Activity(
            activity="Cable laying",
            status="in_progress",
            progress_percent=101,
        )
