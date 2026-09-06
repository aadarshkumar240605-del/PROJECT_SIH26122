import sqlite3
import os
from contextlib import contextmanager

# Path to the database file, stored inside the backend folder
DB_PATH = os.path.join(os.path.dirname(__file__), "project.db")


def get_db_connection():
    """Open a raw connection. Caller is responsible for closing it."""
    conn = sqlite3.connect(DB_PATH)
    # Row factory lets us access columns by name (row["task_name"])
    # instead of by index (row[1]), which is much more readable.
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager that auto-closes the connection.

    Usage:
        with get_db() as conn:
            rows = conn.execute("SELECT ...").fetchall()
    This way we never forget to call conn.close().
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
