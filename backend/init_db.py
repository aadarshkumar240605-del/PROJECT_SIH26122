import os
from database import get_db_connection

# Path to schema.sql in the same backend directory
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

conn = get_db_connection()

with open(SCHEMA_PATH, "r") as f:
    schema = f.read()

conn.executescript(schema)
conn.commit()
conn.close()

# ---------------------------------------------------------------------------
# Lightweight migration for databases created before matched_activity_code
# was added to reports. CREATE TABLE IF NOT EXISTS cannot add columns to an
# existing table, so ALTER here; duplicate ALTERs are ignored.
# ---------------------------------------------------------------------------
conn = get_db_connection()
try:
    conn.execute("ALTER TABLE reports ADD COLUMN matched_activity_code TEXT")
    print("Migration applied: reports.matched_activity_code added.")
except Exception as exc:
    if "duplicate column" in str(exc).lower():
        print("Migration check: matched_activity_code already present.")
    else:
        raise
conn.commit()
conn.close()

print("Database initialized successfully!")
