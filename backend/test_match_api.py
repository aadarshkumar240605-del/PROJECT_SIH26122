"""
test_match_api.py
-----------------
Task 2 test: HTTP-level verification of the FastAPI wrapper (main.py).

Different from test_match_integration.py (Task 3), which calls the
matching engine function directly.  This script verifies the WRAPPER:

    - GET  /health        → correct status payload (index_loaded, count)
    - POST /match         → the 5 agreed contract inputs route correctly
    - POST /match         → malformed payloads rejected with 422
    - POST /reload-index  → default reload works, missing file gives 404

Requirements:
    - The wrapper must be running:
        uvicorn main:app --reload --port 8000
    - Then:
        python test_match_api.py

Author: SIH 2026 — Fuzzy Matching & System Integration Team
"""

import sys

import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_S = 60  # /match can be slow on the very first call (model warm-up)

# ---------------------------------------------------------------------------
# The same 5 frozen contract inputs used in Task 3 — expected statuses must
# match, proving the HTTP layer does not alter engine decisions.
# ---------------------------------------------------------------------------

MATCH_CASES = [
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

REQUIRED_FIELDS = [
    "matched_activity_id",
    "matched_activity_name",
    "confidence_score",
    "match_status",
    "rejection_reason",
]

VALID_STATUSES = {"auto_linked", "review_queue", "unplanned"}

# ---------------------------------------------------------------------------
# Minimal check framework
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def validate_match_response(result: dict) -> list[str]:
    """Contract violations in a /match response body (empty list = OK)."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in result:
            errors.append(f"missing field {field!r}")
    status = result.get("match_status")
    if status not in VALID_STATUSES:
        errors.append(f"invalid match_status {status!r}")
    score = result.get("confidence_score")
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        errors.append(f"confidence_score {score!r} not in [0, 100]")
    if status == "auto_linked" and result.get("rejection_reason") is not None:
        errors.append("auto_linked must have rejection_reason = null")
    if status in ("review_queue", "unplanned") and not result.get("rejection_reason"):
        errors.append(f"{status} must include a rejection_reason")
    return errors


# ---------------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 80)
    print("TASK 2 — HTTP WRAPPER TEST (main.py)")
    print(f"Target: {BASE_URL}")
    print("=" * 80)

    # ---- 1. Server reachable + health contract --------------------------------
    print("\n--- GET /health ---")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
    except requests.ConnectionError:
        print("[FATAL] Cannot connect. Start the server first:")
        print("    uvicorn main:app --reload --port 8000")
        return 1

    check("HTTP 200", resp.status_code == 200, f"got {resp.status_code}")
    body = resp.json()
    check("status is 'ok'", body.get("status") == "ok", str(body))
    check("index_loaded is true", body.get("index_loaded") is True, str(body))
    check("activity_count == 110", body.get("activity_count") == 110, str(body))
    check("model_name present", bool(body.get("model_name")), str(body))

    # ---- 2. The 5 contract inputs ---------------------------------------------
    for case_name, payload, expected in MATCH_CASES:
        print(f"\n--- POST /match — {case_name} (expect {expected}) ---")
        resp = requests.post(f"{BASE_URL}/match", json=payload, timeout=TIMEOUT_S)
        check("HTTP 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text[:150]}")
        result = resp.json()
        check(f"match_status == {expected}", result.get("match_status") == expected,
              f"got {result.get('match_status')!r} "
              f"(id={result.get('matched_activity_id')}, "
              f"score={result.get('confidence_score')})")
        errors = validate_match_response(result)
        check("response contract fields", not errors, "; ".join(errors))

    # ---- 3. Input validation → 422 ---------------------------------------------
    print("\n--- POST /match — validation errors (expect 422) ---")

    bad_payloads = [
        ("missing activity_description",
         {k: v for k, v in MATCH_CASES[0][1].items() if k != "activity_description"}),
        ("empty activity_description", {"activity_description": ""}),
        ("whitespace-only activity_description", {"activity_description": "   "}),
        ("wrong type: activity_description is a number",
         {**MATCH_CASES[0][1], "activity_description": 123}),
        ("empty JSON body", {}),
    ]
    for name, payload in bad_payloads:
        resp = requests.post(f"{BASE_URL}/match", json=payload, timeout=TIMEOUT_S)
        check(f"422 for {name}", resp.status_code == 422,
              f"got {resp.status_code}: {resp.text[:120]}")

    # ---- 4. Unknown discipline falls back to full index (200, no crash) --------
    print("\n--- POST /match — unknown discipline falls back to full index ---")
    resp = requests.post(
        f"{BASE_URL}/match",
        json={**MATCH_CASES[0][1], "discipline": "NoSuchDiscipline"},
        timeout=TIMEOUT_S,
    )
    check("HTTP 200 (graceful fallback)", resp.status_code == 200,
          f"got {resp.status_code}: {resp.text[:120]}")

    # ---- 5. reload-index --------------------------------------------------------
    print("\n--- POST /reload-index ---")
    resp = requests.post(f"{BASE_URL}/reload-index", json={}, timeout=120)
    check("default reload → HTTP 200", resp.status_code == 200,
          f"got {resp.status_code}: {resp.text[:120]}")
    check("activity_count == 110 after reload",
          resp.json().get("activity_count") == 110, resp.text[:200])

    resp = requests.post(f"{BASE_URL}/reload-index",
                         json={"filepath": "no_such_file.xlsx"}, timeout=30)
    check("missing file → HTTP 404", resp.status_code == 404,
          f"got {resp.status_code}: {resp.text[:120]}")

    # ---- Summary ----------------------------------------------------------------
    print("\n" + "=" * 80)
    total = passed + failed
    print(f"RESULT: {passed}/{total} checks passed")
    print("TASK 2 WRAPPER TEST: " + ("ALL PASSED" if failed == 0 else "FAILED"))
    print("=" * 80)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
