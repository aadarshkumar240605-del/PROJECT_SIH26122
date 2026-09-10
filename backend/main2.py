"""
FastAPI application entry point.

This file is deliberately small — it just wires things together:
1. Creates the FastAPI app
2. Adds CORS middleware (so the frontend can call us)
3. Mounts the router from routes.py

Run with:  uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router

app = FastAPI(
    title="SIH26122 — Schedule Linking API",
    description="Backend for Intelligent Data Capture & Schedule-Linking Layer",
    version="0.1.0",
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
