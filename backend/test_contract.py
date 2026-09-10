"""
test_contract.py
----------------
Unit tests for contract.py — the extractor-output -> /match-payload adapter.

Pure tests: no server, no Ollama, no model loading.  Runs in milliseconds.

Run:
    python test_contract.py
"""

import sys

import contract
from contract import activity_to_match_payload, extract_response_to_match_payloads

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


CONTRACT_KEYS = {
    "activity_description", "discipline", "actual_start", "actual_end",
    "location", "reported_by", "source_format",
}

# A realistic /extract response — exactly the shape routes.py returns.
SAMPLE_EXTRACT_RESPONSE = {
    "activities": [
        {
            "activity": "Trench excavation",
            "location": "Zone B - Pipeline Corridor",
            "date": "2026-09-01",
            "status": "completed",
            "progress_percent": 100,
        },
        {
            "activity": "Pipe welding near tank 3",
            "location": None,
            "date": "2026-09-01",
            "status": "in_progress",
            "progress_percent": None,
        },
    ],
    "issues": ["Crane breakdown halted work", "  ", None, ""],
}


def main() -> int:
    print("=" * 70)
    print("CONTRACT ADAPTER UNIT TESTS (contract.py)")
    print("=" * 70)

    # ---- 1. Full response mapping -------------------------------------------
    print("\n--- extract_response_to_match_payloads ---")
    payloads, issues = extract_response_to_match_payloads(SAMPLE_EXTRACT_RESPONSE)

    check("two payloads from two activities", len(payloads) == 2, str(len(payloads)))
    check("all 7 contract keys present, no extras",
          all(set(p.keys()) == CONTRACT_KEYS for p in payloads))

    p1 = payloads[0]
    check("activity -> activity_description",
          p1["activity_description"] == "Trench excavation", str(p1))
    check("location passes through",
          p1["location"] == "Zone B - Pipeline Corridor", str(p1))
    check("date -> actual_start",
          p1["actual_start"] == "2026-09-01", str(p1))
    check("actual_end is None (extractor has no end times)", p1["actual_end"] is None)
    check("discipline is None (extractor has no discipline)", p1["discipline"] is None)
    check("reported_by is None by default", p1["reported_by"] is None)
    check("source_format is None by default", p1["source_format"] is None)

    check("null location stays null", payloads[1]["location"] is None)

    # Issues: pass through, but only clean strings
    check("issues passed through, whitespace/None dropped",
          issues == ["Crane breakdown halted work"], str(issues))

    # ---- 2. Overrides --------------------------------------------------------
    payloads, _ = extract_response_to_match_payloads(
        SAMPLE_EXTRACT_RESPONSE, reported_by="Rajan", source_format="free_text"
    )
    check("reported_by override applied",
          payloads[0]["reported_by"] == "Rajan", str(payloads[0]))
    check("source_format override applied",
          payloads[0]["source_format"] == "free_text")

    # ---- 3. Dirty field values ------------------------------------------------
    print("\n--- dirty field handling ---")
    dirty = activity_to_match_payload({
        "activity": "   Cable pulling   ",
        "location": "   ",
        "date": "not-a-date",
    })
    check("whitespace stripped from description",
          dirty["activity_description"] == "Cable pulling", str(dirty))
    check("whitespace-only location -> None", dirty["location"] is None)
    check("garbage date -> None", dirty["actual_start"] is None)

    datetime_cell = activity_to_match_payload({
        "activity": "Concrete pour",
        "date": "2026-09-01T06:00",
    })
    check("datetime-shaped date passes through",
          datetime_cell["actual_start"] == "2026-09-01T06:00")

    bad_md = activity_to_match_payload({"activity": "X", "date": "2026-13-40"})
    check("impossible month/day -> None", bad_md["actual_start"] is None)

    # ---- 4. Structural edge cases ---------------------------------------------
    print("\n--- structural edge cases ---")
    payloads, issues = extract_response_to_match_payloads(
        {"activities": [], "issues": ["nothing happened"]}
    )
    check("empty activities -> no payloads, issues kept",
          payloads == [] and issues == ["nothing happened"])

    payloads, _ = extract_response_to_match_payloads(
        {"activities": [{"activity": ""}, "not-a-dict", None,
                        {"activity": "Valid task"}], "issues": []}
    )
    check("broken activity entries skipped, valid one kept",
          len(payloads) == 1 and
          payloads[0]["activity_description"] == "Valid task", str(payloads))

    for bad_input, label in [
        (None, "None input"),
        ("string", "string input"),
        ({"issues": []}, "missing activities key"),
        ({"activities": "not-a-list"}, "activities not a list"),
    ]:
        try:
            extract_response_to_match_payloads(bad_input)
            check(f"ValueError for {label}", False, "no exception raised")
        except ValueError:
            check(f"ValueError for {label}", True)

    # ---- Summary ----------------------------------------------------------------
    print("\n" + "=" * 70)
    total = passed + failed
    print(f"RESULT: {passed}/{total} checks passed")
    print("CONTRACT ADAPTER TEST: " + ("ALL PASSED" if failed == 0 else "FAILED"))
    print("=" * 70)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
