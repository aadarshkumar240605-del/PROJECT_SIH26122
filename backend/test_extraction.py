"""
test_extraction.py — Day 3 Hour 3-4.5, Step 3.

Sends every report in test_reports.json to POST /extract and saves
all results to extraction_test_results.json for manual review.

Prerequisites:
    Server must be running on port 8001:
        uvicorn main:app --reload --port 8001

Run:
    python test_extraction.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ENDPOINT     = "http://127.0.0.1:8001/extract"
INPUT_FILE   = Path(__file__).parent / "test_reports.json"
OUTPUT_FILE  = Path(__file__).parent / "extraction_test_results.json"
REQUEST_TIMEOUT_S = 30  # seconds per request

# ---------------------------------------------------------------------------
# Load test reports
# ---------------------------------------------------------------------------
if not INPUT_FILE.exists():
    print(f"ERROR: {INPUT_FILE} not found. Run Step 2 first.")
    sys.exit(1)

with open(INPUT_FILE) as f:
    reports = json.load(f)

print(f"Loaded {len(reports)} reports from {INPUT_FILE.name}")
print(f"Endpoint : {ENDPOINT}")
print(f"Results  : {OUTPUT_FILE.name}")
print("=" * 70)

# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------
results = []
passed  = 0
failed  = 0

for index, report in enumerate(reports, start=1):
    category   = report.get("category", "unknown")
    input_text = report.get("text", "")

    print(f"\n[{index:02d}/{len(reports)}] category={category}")
    print(f"  Input : \"{input_text[:80]}{'...' if len(input_text) > 80 else ''}\"")

    record = {
        "index":    index,
        "category": category,
        "input":    input_text,
        "status_code": None,
        "output":   None,
        "error":    None,
    }

    # Send request
    try:
        resp = requests.post(
            "http://127.0.0.1:8001/extract",
            json={"report_text": report["text"]},
            timeout=REQUEST_TIMEOUT_S,
        )
        record["status_code"] = resp.status_code

        if resp.status_code == 200:
            body = resp.json()
            record["output"] = body

            activities = body.get("activities", [])
            issues     = body.get("issues", [])

            print(f"  Status : {resp.status_code} OK")
            print(f"  Extracted {len(activities)} activity/activities, "
                  f"{len(issues)} issue(s)")

            for act in activities:
                print(f"    • [{act.get('status','?'):12}] "
                      f"{act.get('activity','?')} "
                      f"@ {act.get('location') or 'no location'} "
                      f"({act.get('progress_percent')}%)")

            for issue in issues:
                print(f"    ⚠ {issue}")

            # ------------------------------------------------------------------
            # Semantic assertions — only run when the test report defines them.
            # Existing reports without an "assertions" key are unaffected.
            # ------------------------------------------------------------------
            assertion_spec = report.get("assertions")
            if assertion_spec:
                assertion_failures = []

                # Per-activity checks
                for check in assertion_spec.get("activity_checks", []):
                    needle      = check["activity_contains"].lower()
                    # Find the first activity whose name contains the needle
                    matched_act = next(
                        (a for a in activities
                         if needle in a.get("activity", "").lower()),
                        None,
                    )

                    if matched_act is None:
                        msg = (f"Activity containing {check['activity_contains']!r} "
                               f"not found in response")
                        assertion_failures.append(msg)
                        continue

                    # Location check
                    if "expected_location" in check:
                        actual_loc   = matched_act.get("location")
                        expected_loc = check["expected_location"]
                        if actual_loc != expected_loc:
                            critical = check.get("critical", "")
                            msg = (
                                f"Activity {check['activity_contains']!r}: "
                                f"location={actual_loc!r}, "
                                f"expected={expected_loc!r}"
                                + (f" | CRITICAL: {critical}" if critical else "")
                            )
                            assertion_failures.append(msg)

                    # Status check
                    if "expected_status" in check:
                        actual_st   = matched_act.get("status")
                        expected_st = check["expected_status"]
                        if actual_st != expected_st:
                            msg = (
                                f"Activity {check['activity_contains']!r}: "
                                f"status={actual_st!r}, expected={expected_st!r}"
                            )
                            assertion_failures.append(msg)

                # Per-issue checks
                for check in assertion_spec.get("issue_checks", []):
                    needle = check["issue_contains"].lower()
                    if not any(needle in i.lower() for i in issues):
                        critical = check.get("critical", "")
                        msg = (
                            f"Issue containing {check['issue_contains']!r} "
                            f"not found in response"
                            + (f" | CRITICAL: {critical}" if critical else "")
                        )
                        assertion_failures.append(msg)

                if assertion_failures:
                    print(f"  ASSERTION FAILURES ({len(assertion_failures)}):")
                    for af in assertion_failures:
                        print(f"    ✗ {af}")
                    # Override the pass recorded above
                    passed  -= 1
                    failed  += 1
                    record["assertion_failures"] = assertion_failures
                else:
                    print(f"  Assertions : {len(assertion_spec.get('activity_checks', []))} "
                          f"activity check(s) + "
                          f"{len(assertion_spec.get('issue_checks', []))} "
                          f"issue check(s) — all passed ✓")

            passed += 1

        else:
            record["error"] = resp.text
            print(f"  Status : {resp.status_code} — {resp.text[:120]}")
            failed += 1

    except requests.exceptions.ConnectionError:
        msg = (f"Connection refused at {ENDPOINT}. "
               f"Is uvicorn running on port 8001?")
        record["error"] = msg
        print(f"  ERROR  : {msg}")
        failed += 1
        # Do not abort — keep trying remaining reports

    except requests.exceptions.Timeout:
        msg = f"Request timed out after {REQUEST_TIMEOUT_S}s."
        record["error"] = msg
        print(f"  ERROR  : {msg}")
        failed += 1

    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        record["error"] = msg
        print(f"  ERROR  : {msg}")
        failed += 1

    results.append(record)

    # Small delay to avoid hammering the Gemini API quota
    if index < len(reports):
        time.sleep(0.5)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print(f"SUMMARY: {passed} passed, {failed} failed out of {len(reports)} reports")
print("=" * 70)
for res in results:
    icon = "✓" if res["error"] is None and res["status_code"] == 200 and not res.get("assertion_failures") else "✗"
    print(f"  {icon} [{res['index']:02d}] [{res['category']:<30}] ", end="")
    if res["error"]:
        print(f"ERROR — {str(res['error'])[:60]}")
    elif res.get("assertion_failures"):
        print(f"ASSERTION FAILED ({len(res['assertion_failures'])} violation(s))")
        for af in res["assertion_failures"]:
            print(f"       ✗ {af}")
    else:
        act_count   = len(res["output"].get("activities", []))
        issue_count = len(res["output"].get("issues", []))
        print(f"{act_count} activities, {issue_count} issues")

# ---------------------------------------------------------------------------
# Save results to JSON
# ---------------------------------------------------------------------------
output = {
    "run_timestamp": datetime.now(timezone.utc).isoformat(),
    "endpoint":      ENDPOINT,
    "total":         len(reports),
    "passed":        passed,
    "failed":        failed,
    "results":       results,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print()
print(f"Results saved to: {OUTPUT_FILE}")

if failed > 0:
    sys.exit(1)
