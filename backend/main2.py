"""
FastAPI application entry point.

This file is deliberately small — it just wires things together:
1. Creates the FastAPI app
2. Adds CORS middleware (so the frontend can call us)
3. Loads the matching engine's activity index at startup
4. Mounts the router from routes.py

Run with:  uvicorn main2:app --reload --port 8001
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import match_engine
from routes import router

DEFAULT_INDEX_PATH = os.path.join(os.path.dirname(__file__), "primavera_schedule.xlsx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the Primavera activity index before the server accepts requests.

    Why: routes.py's /submit calls match_engine.match_activity(), which
    raises RuntimeError (surfaced as HTTP 503) when the index is empty.
    Without this startup hook every /submit on the legacy app would 503.
    """
    print("[main2] Server starting — loading activity index...")
    try:
        match_engine.load_activity_index(DEFAULT_INDEX_PATH)
        print(f"[main2] Startup complete. "
              f"{len(match_engine.activity_index)} activities in memory.")
    except (FileNotFoundError, ValueError) as exc:
        # Non-fatal: server starts, but /submit returns 503 until the
        # index is available. Same policy as the matching wrapper.
        print(f"[main2] WARNING: could not load activity index: {exc}")
    yield
    print("[main2] Server shutting down.")


app = FastAPI(
    title="SIH26122 — Schedule Linking API",
    description="Backend for Intelligent Data Capture & Schedule-Linking Layer",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the frontend (running on a different port) to call our API.
# In production you'd restrict origins, but for a hackathon "*" is fine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all the endpoints defined in routes.py
app.include_router(router)


# Keep the original /ping health check
@app.get("/ping")
def ping():
    """Simple health check — returns ok if the server is running."""
    return {"status": "ok", "message": "Server is running"}
