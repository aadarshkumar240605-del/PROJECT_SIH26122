"""
run_extraction_tests.py — Day 3 Hour 3-4.5 extraction test runner.

Reads test_reports.json, sends each report to POST /extract, validates
the response structure, and prints a summary.

Prerequisites:
    1. Server must be running:  uvicorn main:app --reload --port 8001
    2. venv must be active

Run:
    python run_extraction_tests.py
"""

import json
import sys
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ENDPOINT = "http://127.0.0.1:8001/extract"
TEST_FILE = Path(__file__).parent / "test_reports.json"
VALID_STATUSES = {"completed", "in_progress", "pending", "delayed", "unknown"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_response(body: dict) -> list[str]:
    """Return a list of structural violations. Empty list means valid."""
    violations = []

    if "activities" not in body:
        violations.append("Missing 'activities' key")
    elif not isinstance(body["activities"], list):
        violations.append("'activities' is not a list")
    else:
        for i, act in enumerate(body["activities"]):
            for field in ("activity", "location", "status", "progress_percent"):
                if field not in act:
                    violations.append(f"activities[{i}] missing field '{field}'")
            if act.get("status") not in VALID_STATUSES:
                violations.append(
                    f"activities[{i}] invalid status: '{act.get('status')}'"
                )
            pct = act.get("progress_percent")
            if pct is not None and not (0 <= pct <= 100):
                violations.append(
                    f"activities[{i}] progress_percent={pct} out of 0-100 range"
                )

    if "issues" not in body:
        violations.append("Missing 'issues' key")
    elif not isinstance(body["issues"], list):
        violations.append("'issues' is not a list")

    return violations


def print_activity(act: dict, indent: str = "    ") -> None:
    print(f"{indent}activity        : {act.get('activity')}")
    print(f"{indent}location        : {act.get('location')}")
    print(f"{indent}status          : {act.get('status')}")
    print(f"{indent}progress_percent: {act.get('progress_percent')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load test reports
    if not TEST_FILE.exists():
        print(f"ERROR: {TEST_FILE} not found.")
        sys.exit(1)

    with open(TEST_FILE) as f:
        reports = json.load(f)

    print(f"Loaded {len(reports)} test reports from {TEST_FILE.name}")
    print(f"Sending to: {ENDPOINT}")
    print("=" * 70)

    passed = 0
    failed = 0
    results = []

    for r in reports:
        report_id = r.get("id", "?")
        description = r.get("description", "")
        text = r.get("text", "")

        print(f"\nTest {report_id}: {description}")
        print(f"  Input: \"{text[:80]}{'...' if len(text) > 80 else ''}\"")

        # Make the request
        try:
            resp = requests.post(
                "http://127.0.0.1:8001/extract",
                json={"report_text": r["text"]}
            )
        except requests.exceptions.ConnectionError:
            print("  ERROR: Could not connect to server.")
            print("  Make sure uvicorn is running: uvicorn main:app --reload --port 8001")
            sys.exit(1)

        print(f"  HTTP status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"  FAIL — unexpected status {resp.status_code}")
            print(f"  Body: {resp.text[:200]}")
            failed += 1
            results.append({"id": report_id, "status": "FAIL",
                            "reason": f"HTTP {resp.status_code}"})
            continue

        body = resp.json()
        violations = validate_response(body)

        if violations:
            print(f"  FAIL — response structure violations:")
            for v in violations:
                print(f"    • {v}")
            failed += 1
            results.append({"id": report_id, "status": "FAIL",
                            "reason": "; ".join(violations)})
            continue

        # Print extracted activities
        activities = body.get("activities", [])
        issues = body.get("issues", [])
        print(f"  Extracted {len(activities)} activity/activities, "
              f"{len(issues)} issue(s)")

        for act in activities:
            print_activity(act)

        if issues:
            print(f"  Issues:")
            for issue in issues:
                print(f"    • {issue}")

        print("  PASS")
        passed += 1
        results.append({"id": report_id, "status": "PASS"})

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print()
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(reports)} reports")
    print("=" * 70)
    for res in results:
        icon = "✓" if res["status"] == "PASS" else "✗"
        line = f"  {icon} Test {res['id']}"
        if res["status"] == "FAIL":
            line += f" — {res.get('reason', '')}"
        print(line)
    print()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
