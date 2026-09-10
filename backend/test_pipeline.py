"""
test_pipeline.py
----------------
Task 3: Integration Test Script

Purpose:
    Simulates Member 5's AI extraction engine sending structured JSON
    payloads to our FastAPI matching engine. 
    (Note: Acknowledged that the extraction engine now uses Google API 
    instead of Ollama. The data contract remains the same.)

Requirements:
    - FastAPI server must be running (uvicorn main:app --reload)
    - Server URL: http://127.0.0.1:8000

Author: SIH 2026 — Fuzzy Matching & System Integration Team
"""

import json
import urllib.request
import urllib.error
import sys

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000/match"

# ---------------------------------------------------------------------------
# TEST CASES
# ---------------------------------------------------------------------------
# Simulating the exact JSON output that the Google API extraction engine will produce.
# We include cases that will hit all 3 match_status conditions.

TEST_CASES = [
    {
        "name": "Case 1: Clear match (Expected: auto_linked)",
        "payload": {
            "activity_description": "column footing concrete pouring Unit 7",
            "discipline": "Civil",
            "actual_start": "2026-09-01T06:00",
            "actual_end": "2026-09-01T14:00",
            "location": "Unit 7, Grid C-7/F-12",
            "reported_by": "Rajan",
            "source_format": "free_text"
        }
    },
    {
        "name": "Case 2: Piping match (Expected: auto_linked)",
        "payload": {
            "activity_description": "hydrostatic pressure testing on 6 inch pipeline section",
            "discipline": "Piping",
            "actual_start": "2026-09-01T10:00",
            "actual_end": "2026-09-01T16:00",
            "location": "Unit 5",
            "reported_by": "Amit",
            "source_format": "voice"
        }
    },
    {
        "name": "Case 3: HSE generic (Expected: review_queue)",
        "payload": {
            "activity_description": "safety briefing and toolbox talk for all workers",
            "discipline": None,  # Testing missing discipline (fallback to full index)
            "actual_start": "2026-09-01T08:00",
            "actual_end": "2026-09-01T08:30",
            "location": "Site Office",
            "reported_by": "Safety Officer",
            "source_format": "free_text"
        }
    },
    {
        "name": "Case 4: Unrelated/Vague (Expected: unplanned)",
        "payload": {
            "activity_description": "some electrical work done in the morning",
            "discipline": "Electrical",
            "actual_start": "2026-09-01T09:00",
            "actual_end": None,
            "location": "MCC Room",
            "reported_by": "Vikram",
            "source_format": "free_text"
        }
    },
    {
        "name": "Case 5: Completely unrelated (Expected: unplanned)",
        "payload": {
            "activity_description": "ordered lunch for the team and fixed the site office wifi",
            "discipline": None,
            "actual_start": "2026-09-01T12:00",
            "actual_end": "2026-09-01T13:00",
            "location": "Site Office",
            "reported_by": "Manager",
            "source_format": "voice"
        }
    }
]

# ---------------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------------
def run_tests():
    print("=" * 80)
    print("TASK 3 — INTEGRATION TEST SUITE")
    print(f"Target API: {API_URL}")
    print("=" * 80)

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n--- {test['name']} ---")
        
        payload_data = test["payload"]
        print("INPUT PAYLOAD (from Extraction Engine):")
        print(json.dumps(payload_data, indent=2))
        
        # Prepare the HTTP POST request
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            # Send the request
            with urllib.request.urlopen(req) as response:
                status_code = response.getcode()
                response_data = json.loads(response.read().decode("utf-8"))
                
                print("\nOUTPUT RESPONSE (from Matching Engine):")
                print(f"HTTP Status: {status_code}")
                print(json.dumps(response_data, indent=2))
                
        except urllib.error.HTTPError as e:
            # Handle HTTP errors (e.g., 422 Validation Error)
            print("\n[HTTP ERROR]")
            print(f"HTTP Status: {e.code}")
            try:
                error_body = json.loads(e.read().decode("utf-8"))
                print(json.dumps(error_body, indent=2))
            except:
                print(e.read().decode("utf-8"))
                
        except urllib.error.URLError as e:
            # Handle connection errors (server not running)
            print("\n[CONNECTION ERROR]")
            print(f"Could not connect to the API. Is the server running at {API_URL}?")
            print(f"Details: {e.reason}")
            sys.exit(1)

    print("\n" + "=" * 80)
    print("Integration tests complete.")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
