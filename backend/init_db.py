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

print("Database initialized successfully!")
