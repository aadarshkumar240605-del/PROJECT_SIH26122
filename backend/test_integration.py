"""
test_integration.py — Slow integration tests for the /extract endpoint.

These tests call the LIVE server on port 8001.
They are marked @pytest.mark.slow and are SKIPPED during normal pytest runs.

To run them explicitly:
    uvicorn main:app --reload --port 8001   # in a separate terminal
    pytest --runslow -v test_integration.py

They are NOT a replacement for test_extraction.py (which runs 23 full
LLM regression cases).  These tests verify only the basic response structure
using two simple, fixed inputs — fast enough for a smoke-check but still
exercising the live Ollama model.
"""

import pytest
import requests

ENDPOINT = "http://127.0.0.1:8001/extract"
TIMEOUT_S = 30


@pytest.mark.slow
class TestExtractLive:
    """Integration tests that hit the live /extract endpoint."""

    def test_simple_activity_response_structure(self):
        """
        A clear, specific field report must return a valid ExtractResponse
        structure: an 'activities' list and an 'issues' list.

        Input: straightforward single-activity report with a known location.
        We do NOT assert on exact activity names or locations — those are
        covered by the 23 LLM regression tests in test_extraction.py.
        We only verify the outer shape of the response matches the contract.
        """
        resp = requests.post(
            ENDPOINT,
            json={"report_text": "Trench excavation in Zone B is complete."},
            timeout=TIMEOUT_S,
        )
        assert resp.status_code == 200, (
            f"Expected 200 OK, got {resp.status_code}: {resp.text[:200]}"
        )

        body = resp.json()

        # Top-level keys must be present
        assert "activities" in body, "Response missing 'activities' key"
        assert "issues" in body, "Response missing 'issues' key"

        # activities must be a list
        assert isinstance(body["activities"], list), (
            f"'activities' must be a list, got {type(body['activities'])}"
        )

        # issues must be a list
        assert isinstance(body["issues"], list), (
            f"'issues' must be a list, got {type(body['issues'])}"
        )

        # Each activity must have the required fields from the Activity schema
        for act in body["activities"]:
            assert "activity" in act, f"Activity entry missing 'activity' field: {act}"
            assert "status" in act,   f"Activity entry missing 'status' field: {act}"
            assert isinstance(act["activity"], str), (
                f"'activity' must be a string, got {type(act['activity'])}"
            )
            valid_statuses = {"completed", "in_progress", "pending", "delayed", "unknown"}
            assert act["status"] in valid_statuses, (
                f"'status' must be one of {valid_statuses}, got {act['status']!r}"
            )

    def test_vague_report_response_structure(self):
        """
        Even a vague report must return the correct outer structure —
        even if it results in an empty activities list.

        This verifies that the endpoint handles gracefully inputs that
        yield no extracted activities, without returning a 5xx error or
        a malformed response body.
        """
        resp = requests.post(
            ENDPOINT,
            json={"report_text": "Work done today."},
            timeout=TIMEOUT_S,
        )
        assert resp.status_code == 200, (
            f"Expected 200 OK, got {resp.status_code}: {resp.text[:200]}"
        )

        body = resp.json()

        assert "activities" in body, "Response missing 'activities' key"
        assert "issues" in body, "Response missing 'issues' key"
        assert isinstance(body["activities"], list)
        assert isinstance(body["issues"], list)
