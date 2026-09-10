"""
test_match_integration.py
-------------------------
Task 3: Integration Test — Matching Engine vs Member 5's Data Contract

Purpose:
    Simulates Member 5's extraction engine output using HARDCODED JSON
    inputs that match the agreed data contract, and verifies that the
    semantic matching engine (match_engine.py) routes each one to the
    correct bucket:

        auto_linked   (confidence >= 75)  → auto-update the schedule
        review_queue  (confidence >= 40)  → human must confirm
        unplanned     (confidence < 40)   → not in the schedule

    NO external LLM or extraction engine is called.  All inputs are
    frozen examples agreed with the extraction team.  The only runtime
    dependency is the local sentence-transformer model (all-MiniLM-L6-v2)
    and the real Primavera schedule (primavera_schedule.xlsx).

Run:
    python test_match_integration.py

Exit codes:
    0 — all cases passed
    1 — one or more cases failed (or the index could not be loaded)

Author: SIH 2026 — Fuzzy Matching & System Integration Team
"""

import sys

from match_engine import (
    load_activity_index,
    match_activity,
    THRESHOLD_AUTO_LINKED,
    THRESHOLD_REVIEW_QUEUE,
    MODEL_NAME,
)

SCHEDULE_PATH = "primavera_schedule.xlsx"

# ---------------------------------------------------------------------------
# TEST CASES — frozen extraction-engine outputs (agreed data contract).
# Each case: (case_name, payload, expected_match_status)
# ---------------------------------------------------------------------------

TEST_CASES = [
    (
        "Case 1: Clear civil match",
        {
            "activity_description": "concrete pouring column footing Unit 7",
            "discipline": "Civil",
            "actual_start": "2026-09-01T06:00",
            "actual_end": None,
            "location": "Unit 7 grid C-7/F-12",
            "reported_by": "Rajan",
            "source_format": "free_text",
        },
        "auto_linked",
    ),
    (
        "Case 2: Clear piping match",
        {
            "activity_description": "spool erection north rack elevation 7.5 metres",
            "discipline": "Piping",
            "actual_start": "2026-09-01T14:00",
            "actual_end": "2026-09-02T09:00",
            "location": "North rack elevation 7.5m",
            "reported_by": "Priya",
            "source_format": "voice_transcript",
        },
        "auto_linked",
    ),
    (
        "Case 3: Vague electrical work",
        {
            "activity_description": "cable work done room B morning shift",
            "discipline": "Electrical",
            "actual_start": "2026-09-01T08:00",
            "actual_end": "2026-09-01T13:00",
            "location": "MCC Room B",
            "reported_by": "Suresh",
            "source_format": "free_text",
        },
        "review_queue",
    ),
    (
        "Case 4: Partial HSE match",
        {
            "activity_description": "safety toolbox talk conducted all workers morning",
            "discipline": None,
            "actual_start": "2026-09-02T07:00",
            "actual_end": "2026-09-02T07:30",
            "location": "Site assembly point",
            "reported_by": "HSE Officer Mehta",
            "source_format": "free_text",
        },
        "review_queue",
    ),
    (
        "Case 5: Not in schedule",
        {
            "activity_description": "generator fuel refilling site office",
            "discipline": None,
            "actual_start": "2026-09-01T11:00",
            "actual_end": "2026-09-01T11:30",
            "location": "Site office",
            "reported_by": "Ramesh",
            "source_format": "free_text",
        },
        "unplanned",
    ),
]

# ---------------------------------------------------------------------------
# Contract validation — every engine response must carry the agreed fields.
# ---------------------------------------------------------------------------

REQUIRED_RESPONSE_FIELDS = [
    "matched_activity_id",
    "matched_activity_name",
    "confidence_score",
    "match_status",
    "rejection_reason",
]

VALID_MATCH_STATUSES = {"auto_linked", "review_queue", "unplanned"}


def validate_response_contract(result: dict) -> list[str]:
    """Return a list of contract violations for an engine response (empty = OK)."""
    errors = []

    for field in REQUIRED_RESPONSE_FIELDS:
        if field not in result:
            errors.append(f"missing required response field {field!r}")

    if result.get("match_status") not in VALID_MATCH_STATUSES:
        errors.append(f"invalid match_status {result.get('match_status')!r}")

    score = result.get("confidence_score")
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        errors.append(f"confidence_score {score!r} is not a number in [0, 100]")

    # Status must be consistent with the published thresholds.
    status = result.get("match_status")
    if isinstance(score, (int, float)) and status in VALID_MATCH_STATUSES:
        if status == "auto_linked" and score < THRESHOLD_AUTO_LINKED:
            errors.append(f"auto_linked but score {score} < {THRESHOLD_AUTO_LINKED}")
        if status == "review_queue" and not (
            THRESHOLD_REVIEW_QUEUE <= score < THRESHOLD_AUTO_LINKED
        ):
            errors.append(
                f"review_queue but score {score} outside "
                f"[{THRESHOLD_REVIEW_QUEUE}, {THRESHOLD_AUTO_LINKED})"
            )
        if status == "unplanned" and score >= THRESHOLD_REVIEW_QUEUE:
            errors.append(f"unplanned but score {score} >= {THRESHOLD_REVIEW_QUEUE}")

    # auto_linked responses must never carry a rejection reason.
    if status == "auto_linked" and result.get("rejection_reason") is not None:
        errors.append("auto_linked must have rejection_reason = null")

    # Everything below auto-link threshold MUST carry a rejection reason.
    if status in ("review_queue", "unplanned") and not result.get("rejection_reason"):
        errors.append(f"{status} must include a rejection_reason string")

    return errors


# ---------------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------------

def run_tests() -> int:
    print("=" * 80)
    print("TASK 3 — MATCHING ENGINE INTEGRATION TEST (hardcoded contract inputs)")
    print(f"Schedule index : {SCHEDULE_PATH}")
    print(f"Model          : {MODEL_NAME}")
    print(f"Thresholds     : auto_linked >= {THRESHOLD_AUTO_LINKED}  |  "
          f"review_queue >= {THRESHOLD_REVIEW_QUEUE}  |  else unplanned")
    print("=" * 80)

    # Load the real schedule index ONCE (this also warms the model).
    try:
        load_activity_index(SCHEDULE_PATH)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[FATAL] Could not load activity index: {e}")
        return 1

    failures = 0

    for case_name, payload, expected_status in TEST_CASES:
        print(f"\n--- {case_name} ---")
        print("INPUT (simulated extraction engine output):")
        for key, value in payload.items():
            print(f"  {key:22s}: {value!r}")
        print(f"  EXPECTED match_status : {expected_status}")

        description = payload["activity_description"]
        discipline  = payload["discipline"]

        try:
            result = match_activity(description, discipline=discipline)
        except (RuntimeError, ValueError) as e:
            print(f"  [FAIL] Engine raised: {e}")
            failures += 1
            continue

        print("OUTPUT (matching engine):")
        print(f"  matched_activity_id   : {result['matched_activity_id']}")
        print(f"  matched_activity_name : {result['matched_activity_name']}")
        print(f"  confidence_score      : {result['confidence_score']}%")
        print(f"  match_status          : {result['match_status']}")
        if result["rejection_reason"] is not None:
            print(f"  rejection_reason      : {result['rejection_reason']}")

        case_errors = validate_response_contract(result)

        if result["match_status"] != expected_status:
            case_errors.append(
                f"expected match_status {expected_status!r}, "
                f"got {result['match_status']!r}"
            )

        if case_errors:
            failures += 1
            for err in case_errors:
                print(f"  [FAIL] {err}")
        else:
            print("  [PASS] status and response contract OK")

    print("\n" + "=" * 80)
    total = len(TEST_CASES)
    passed = total - failures
    print(f"RESULT: {passed}/{total} cases passed")
    if failures:
        print("TASK 3 INTEGRATION TEST: FAILED")
    else:
        print("TASK 3 INTEGRATION TEST: ALL PASSED")
    print("=" * 80)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_tests())
