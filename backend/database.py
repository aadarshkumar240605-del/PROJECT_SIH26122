import sqlite3
import os

# Path to the database file, stored inside the backend folder
DB_PATH = os.path.join(os.path.dirname(__file__), "project.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
