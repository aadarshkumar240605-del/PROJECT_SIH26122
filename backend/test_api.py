"""
Tests for the SIH26122 backend API.

Each test uses a fresh in-memory SQLite database so tests are isolated
and don't touch the real project.db.

Run with:  python -m pytest test_api.py -v
"""

import sqlite3
import os
from unittest.mock import patch
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Test database setup — use in-memory SQLite for speed and isolation
# ---------------------------------------------------------------------------

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# We store the in-memory connection at module level so all calls within
# a single test share the same database (in-memory DBs are per-connection).
_test_conn = None


def _get_test_connection():
    """Return the shared in-memory test connection."""
    global _test_conn
    if _test_conn is None:
        # check_same_thread=False because FastAPI's TestClient runs
        # endpoint code in a different thread than the test itself.
        _test_conn = sqlite3.connect(":memory:", check_same_thread=False)
        _test_conn.row_factory = sqlite3.Row
        with open(SCHEMA_PATH) as f:
            _test_conn.executescript(f.read())
    return _test_conn


@contextmanager
def _get_test_db():
    """Context manager matching database.get_db() but using the test DB.
    NOTE: We do NOT close the connection here because it's in-memory
    and shared across calls within a single test.
    """
    yield _get_test_connection()


def _get_test_db_connection():
    """Matches database.get_db_connection() for the test DB."""
    return _get_test_connection()


@pytest.fixture(autouse=True)
def fresh_db():
    """Reset the in-memory DB before each test so tests don't interfere."""
    global _test_conn
    _test_conn = None  # Force a new connection for each test

    # Patch both database functions so all app code uses our test DB
    with patch("database.get_db", _get_test_db), \
         patch("database.get_db_connection", _get_test_db_connection), \
         patch("matcher.get_db", _get_test_db):
        # Import app AFTER patching so routes pick up the patched DB
        from main import app
        yield TestClient(app)


def _seed_one_task(conn):
    """Insert a single schedule item for testing."""
    conn.execute(
        """INSERT INTO schedule_items
           (id, task_name, discipline, location,
            planned_start, planned_end, status)
           VALUES (1, 'Pipe welding near tank 3', 'piping',
                   'Zone A - Tank Farm', '2026-09-04', '2026-09-11', 'pending')"""
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPing:
    def test_ping_returns_ok(self, fresh_db):
        """GET /ping should always return status ok."""
        client = fresh_db
        resp = client.get("/ping")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestSchedule:
    def test_schedule_returns_list(self, fresh_db):
        """GET /schedule should return a JSON list (empty if no data)."""
        client = fresh_db
        resp = client.get("/schedule")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_schedule_returns_seeded_data(self, fresh_db):
        """GET /schedule should include items we inserted."""
        client = fresh_db
        conn = _get_test_connection()
        _seed_one_task(conn)

        resp = client.get("/schedule")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["task_name"] == "Pipe welding near tank 3"


class TestSubmit:
    def test_high_confidence_auto_applies(self, fresh_db):
        """POST /submit with a task that matches by name should auto-apply.

        Expected: confidence >= 0.80, review_status = 'auto_applied',
        schedule item marked 'done', task_history row created.
        """
        client = fresh_db
        conn = _get_test_connection()
        _seed_one_task(conn)

        resp = client.post("/submit", json={
            "task": "Pipe welding",
            "quantity": "50 meters",
            "location": "Zone A",
            "date": "2026-09-10",
            "raw_text": "finished welding pipe near tank 3",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "auto_applied"
        assert data["confidence"] >= 0.80

        # Verify the schedule item was updated
        item = conn.execute(
            "SELECT * FROM schedule_items WHERE id = 1"
        ).fetchone()
        assert item["status"] == "done"
        assert item["actual_completion_date"] == "2026-09-10"

        # Verify task_history was populated
        history = conn.execute("SELECT * FROM task_history").fetchall()
        assert len(history) == 1
        assert history[0]["task_type"] == "piping"

    def test_medium_confidence_needs_review(self, fresh_db):
        """POST /submit with only a location match should flag for review.

        Expected: 0.50 <= confidence < 0.80, review_status = 'needs_review',
        schedule item NOT touched.
        """
        client = fresh_db
        conn = _get_test_connection()
        _seed_one_task(conn)

        resp = client.post("/submit", json={
            "task": "something unrelated",
            "quantity": None,
            "location": "Zone A",
            "date": "2026-09-10",
            "raw_text": "did some work in zone A today",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "needs_review"
        assert 0.50 <= data["confidence"] < 0.80

        # Schedule item should still be pending
        item = conn.execute(
            "SELECT * FROM schedule_items WHERE id = 1"
        ).fetchone()
        assert item["status"] == "pending"

    def test_low_confidence_no_match(self, fresh_db):
        """POST /submit with no matching info should return no_match."""
        client = fresh_db

        resp = client.post("/submit", json={
            "task": "xyz",
            "quantity": None,
            "location": "nowhere",
            "date": "2026-09-10",
            "raw_text": "random text with no matches",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "no_match"
        assert data["confidence"] < 0.50
