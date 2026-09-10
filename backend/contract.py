"""
contract.py
-----------
Adapter between Member 5's extraction engine output and the matching
engine's input contract.

WHY THIS EXISTS
---------------
The extraction engine (/extract) returns:

    {
      "activities": [
        {"activity": "Trench excavation", "location": "Zone B - Pipeline Corridor",
         "date": "2026-09-01", "status": "in_progress", "progress_percent": 70},
        ...
      ],
      "issues": ["Crane breakdown halted work"]
    }

The matching engine (/match) expects one flat payload PER activity:

    {
      "activity_description": "...",
      "discipline": "Civil" | null,
      "actual_start": "2026-09-01T06:00" | null,
      "actual_end":  null,
      "location":    "..." | null,
      "reported_by": null,
      "source_format": null
    }

This module converts the first shape into the second.  It is PURE —
no HTTP calls, no LLM, no model loading — so it can be unit-tested in
milliseconds and used anywhere in the pipeline.

FIELD MAPPING (extractor -> /match contract)
--------------------------------------------
    activity   -> activity_description     (required; empty/missing skips the row)
    date       -> actual_start             (passed through if it looks like a
                                                date; else None)
    location   -> location                 (non-empty strings only)
    (nothing)  -> discipline               (extractor does not produce it;
                                            null = full-index matching fallback)
    (nothing)  -> actual_end               (null)
    (nothing)  -> reported_by              (null, or defaults override)
    (nothing)  -> source_format            (null, or defaults override)

    issues     -> passed through untouched (returned alongside the payloads)

Author: SIH 2026 — Fuzzy Matching & System Integration Team
"""

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def activity_to_match_payload(
    activity: dict,
    discipline: Optional[str] = None,
    reported_by: Optional[str] = None,
    source_format: Optional[str] = None,
) -> dict:
    """
    Convert ONE extractor activity dict into ONE /match contract payload.

    Input:
        activity — a single dict from the extractor's "activities" list.
        Optional keyword overrides for the fields the extractor cannot
        supply (discipline, reported_by, source_format).  In a future
        phase, reported_by/source_format will come from the input form
        or voice client; for now callers may pass them or leave None.

    Returns:
        A dict matching the /match data contract EXACTLY — the same
        7 keys the ActivityLogInput model in main.py validates.

    Never raises on bad field values inside the dict — bad values
    become None.  (Structural problems, like a non-dict activity,
    are the caller's responsibility — see extract_response_to_match_payloads.)
    """
    if not isinstance(activity, dict):
        activity = {}

    return {
        "activity_description": _clean_text(activity.get("activity")),
        "discipline":           _clean_text(discipline),
        "actual_start":         _normalise_date(activity.get("date")),
        "actual_end":           None,
        "location":             _clean_text(activity.get("location")),
        "reported_by":          _clean_text(reported_by),
        "source_format":        _clean_text(source_format),
    }


def extract_response_to_match_payloads(
    extract_response: dict,
    reported_by: Optional[str] = None,
    source_format: Optional[str] = None,
) -> tuple[list[dict], list[str]]:
    """
    Convert a FULL /extract response into /match payloads.

    Input:
        extract_response — the JSON returned by POST /extract, i.e. a dict
            with "activities" (list of activity dicts) and "issues" (list
            of strings).
        reported_by, source_format — optional pass-through overrides
            applied to every generated payload.

    Returns:
        (payloads, issues) where:
            payloads — one /match contract dict per extractable activity,
                       in the same order as the extractor returned them.
            issues   — the extractor's issues list, passed through
                       unchanged (these surface in the review queue).

    Raises:
        ValueError — if extract_response is not a dict or has no usable
                     "activities" list.  (A valid response with an EMPTY
                     activity list is NOT an error — it returns ([], issues).)
    """
    if not isinstance(extract_response, dict):
        raise ValueError(
            f"contract: extract_response must be a dict, got "
            f"{type(extract_response).__name__}"
        )

    raw_activities = extract_response.get("activities")
    if raw_activities is None:
        raise ValueError(
            "contract: extract_response is missing the 'activities' key — "
            "is this really a /extract response?"
        )
    if not isinstance(raw_activities, list):
        raise ValueError(
            f"contract: 'activities' must be a list, got "
            f"{type(raw_activities).__name__}"
        )

    issues = extract_response.get("issues")
    issues = [i for i in issues if isinstance(i, str) and i.strip()] if isinstance(issues, list) else []

    payloads = []
    for activity in raw_activities:
        # Skip only structurally-broken or description-less entries;
        # the matching engine cannot process those.
        description = _clean_text(activity.get("activity")) if isinstance(activity, dict) else None
        if not description:
            continue
        payloads.append(
            activity_to_match_payload(
                activity,
                reported_by=reported_by,
                source_format=source_format,
            )
        )

    return payloads, issues


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_text(value: Any) -> Optional[str]:
    """Strip a value to a clean string; empty/whitespace/non-string -> None."""
    if not isinstance(value, str):
        # Tolerate numbers by stringifying; everything else -> None
        if isinstance(value, (int, float)):
            value = str(value)
        else:
            return None
    value = value.strip()
    return value if value else None


def _normalise_date(value: Any) -> Optional[str]:
    """
    Pass through a date string if it is ISO-shaped (YYYY-MM-DD, optionally
    followed by a time part); anything else -> None.

    Why strict: the /match contract documents actual_start as an ISO
    datetime string.  The extractor already resolves relative dates
    ("yesterday") to ISO in post-processing, so a value failing this
    check is a bug upstream — better to null it than forward garbage.
    """
    text = _clean_text(value)
    if not text:
        return None
    date_part = text.split("T")[0]
    if len(date_part) != 10 or date_part[4] != "-" or date_part[7] != "-":
        return None
    y, m, d = date_part.split("-")
    if not (y.isdigit() and m.isdigit() and d.isdigit()):
        return None
    if not (1 <= int(m) <= 12 and 1 <= int(d) <= 31):
        return None
    return text
