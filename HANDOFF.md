# SiteSync (SIH26122) — Developer Handoff

**Project:** Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management
**Problem owner:** Oil India Limited (Smart India Hackathon 2026)
**One-liner:** Site supervisors report work in plain language → the system extracts structured
data, matches it to the official Primavera schedule, auto-updates what it is confident about,
and routes the rest to a human review queue.

This document is the full working context for anyone continuing the backend/matching work.
Last updated: 2026-09-11 (Expo mobile manager workspace).

## 0. Mobile frontend handoff

The frontend is an Expo SDK 57 React Native app using NativeWind. The app starts
with a role picker in `frontend/App.tsx`:

- `ManagerHome` is the implemented manager dashboard.
- `WorkerPlaceholder` is intentionally temporary and is the worker-side starting point.
- Keep the `Role` type and role picker intact when replacing the worker placeholder.

The shared API client is `frontend/src/api.ts`. Reuse it instead of adding fetch
logic inside worker screens. It reads `EXPO_PUBLIC_API_URL`; use
`http://127.0.0.1:8001` for the same computer, `http://10.0.2.2:8001` for an
Android emulator, or the laptop LAN address such as `http://192.168.1.14:8001`
for a physical phone.

Manager endpoints currently used:

- `GET /ping`
- `GET /dashboard`
- `GET /schedule`
- `GET /review-queue`
- `POST /submit` with `{ "report_text": "..." }`

Worker-side work should preserve the existing teal/green NativeWind visual
language and use the current `global.css`, `tailwind.config.js`, and
`nativewind-env.d.ts` setup. A natural next worker flow is: capture a daily
report, show activity/status/quantity fields, submit through the shared API,
and show the returned match result or extraction issues.

### Mobile run commands

Backend terminal:

```bash
cd backend
python -m uvicorn main2:app --host 0.0.0.0 --port 8001 --reload
```

Frontend terminal:

```bash
cd frontend
set EXPO_PUBLIC_API_URL=http://YOUR_LAPTOP_IP:8001
npm.cmd run start -- --lan
```

Both devices must be on the same Wi-Fi. Keep both terminals running while
testing with Expo Go.

---

## 1. System architecture

```
Field report (text / voice transcript)
        │
        ▼
[Extraction]  extractor.py — qwen2.5:7b via local Ollama   (Member 5)
        │     POST /extract on the legacy app (port 8001)
        │     Returns: {activities: [...], issues: [...]}
        ▼
[Contract adapter]  contract.py                            (Member 6)
        │     Converts each activity → a /match payload
        ▼
[Matching engine]  match_engine.py — all-MiniLM-L6-v2      (Member 6)
        │     loads primavera_schedule.xlsx via parse_primavera.py
        │     POST /match on the wrapper (port 8000)
        │     Returns: matched_activity_id + confidence 0–100 + status
        ▼
[Confidence router]
        │   ≥ 75%  → auto_linked    (mark done in DB, write task_history)
        │   40–75% → review_queue   (manager confirms/rejects in dashboard)
        │   < 40%  → unplanned      (logged, not linked)
        ▼
[SQLite]  project.db: schedule_items / reports / task_history
        ▼
[React dashboard]  frontend/ — NOT STARTED (empty Vite scaffold)
```

## 2. Two backend services — ports matter

| Service | File | Run command | Endpoints |
|---|---|---|---|
| **Matching wrapper** | `backend/main.py` | `uvicorn main:app --port 8000` | `POST /match`, `POST /reload-index`, `GET /health` (+ `/docs`) |
| **Legacy app** | `backend/main2.py` | `uvicorn main2:app --port 8001` | `POST /submit` (NEW: text in → matches out), `/extract`, `/schedule`, `/review-queue`, `/confirm-match`, `/unplanned`, `/audit-trail`, `/dashboard`, `/activities`, `/ping` |

⚠️ **History:** `main.py` used to be the legacy app. It was replaced by the matching wrapper
(Task 2), and the legacy app now lives in `main2.py`. Anyone running `uvicorn main:app` out
of habit gets the matching service, not the old API.

⚠️ **/submit is a one-call pipeline now:** it takes `{"report_text": "..."}` and returns
`{"results": [...], "issues": [...]}` where each result is a full /match response. The old
`{task, quantity, location, date, raw_text}` payload no longer works. BUT it has two open
bugs — see §6 items 7 and 8.

## 3. File map (backend/)

| File | Purpose | Status |
|---|---|---|
| `match_engine.py` | Task 1 — semantic matching (embeddings + cosine similarity) | ✅ refactored in Task 5 to load via the parser |
| `main.py` | Task 2 — FastAPI wrapper for the engine | ✅ verified 29/29 HTTP checks |
| `parse_primavera.py` | Task 4 — Excel parser (`parse_schedule`, `print_summary`, `get_activity_names`) | ✅ verified incl. edge cases |
| `contract.py` | Adapter: `/extract` output → `/match` payloads | ✅ 24/24 unit tests |
| `test_match_integration.py` | Task 3 — engine-level test, 5 hardcoded contract inputs | ✅ 5/5 |
| `test_match_api.py` | Task 2 — HTTP-level wrapper test (needs server on 8000) | ✅ 29/29 |
| `test_contract.py` | Adapter unit tests (no server needed) | ✅ 24/24 |
| `demo_extract_to_match.py` | End-to-end demo: hardcoded extract JSON → adapter → engine | ✅ runs |
| `test_pipeline.py` | Teammate's Task 3 script (HTTP, targets port 8000) | ✅ works unmodified |
| `primavera_schedule.xlsx` | The real index: 110 activities, 5 disciplines, L5/L6 | source of truth for matching |
| `extractor.py`, `routes.py`, `database.py`, `schema.sql`, `init_db.py`, `seed.py`, `matcher.py` | Member 5 / legacy stack | unchanged |
| `matcher.py` | OLD stub matcher still wired into `main2`'s `/submit` | to be replaced by match_engine |
| `TEAM_NOTES.txt` | Quick flags doc (day 1) | read me first if new |

## 4. Data contracts (exact shapes)

**`POST /extract` returns (Member 5's engine):**
```json
{
  "activities": [
    {"activity": "Trench excavation", "location": "Zone B - Pipeline Corridor",
     "date": "2026-09-01", "status": "completed", "progress_percent": 100}
  ],
  "issues": ["Crane breakdown halted work"]
}
```

**`contract.py` converts each activity into a `/match` payload:**
```json
{
  "activity_description": "Trench excavation",
  "discipline": null,
  "actual_start": "2026-09-01",
  "actual_end": null,
  "location": "Zone B - Pipeline Corridor",
  "reported_by": null,
  "source_format": "free_text"
}
```
Fields the extractor cannot supply (`discipline`, `actual_end`, `reported_by`,
`source_format`) are `null`; the engine treats `discipline: null` as "search the full index".
`issues` pass through untouched for the review queue.

**`POST /match` returns:**
```json
{
  "matched_activity_id": "L6-PIPING-1193",
  "matched_activity_name": "Erect spool 24-PL-0047 north rack elevation 7.5m",
  "confidence_score": 89.86,
  "match_status": "auto_linked",
  "rejection_reason": null
}
```

⚠️ **Confidence scale warning:** the matching engine uses **0–100** (thresholds 75 / 40).
The legacy `/submit` in `main2.py` uses **0.0–1.0** (thresholds 0.80 / 0.50). These two
scales MUST be unified when the engine is wired into `/submit` — divide by 100 or move
the thresholds.

## 5. How to run the tests

```bash
cd backend

# Engine-level (no server, no Ollama; loads model ~10 s first time)
python test_match_integration.py      # expect: 5/5

# Adapter unit tests (milliseconds, nothing else needed)
python test_contract.py               # expect: 24/24

# HTTP wrapper tests (start server first in another terminal)
python -m uvicorn main:app --port 8000
python test_match_api.py              # expect: 29/29

# End-to-end demo (no Ollama — hardcoded extraction output)
python demo_extract_to_match.py

# Excel parser self-test + summary
python parse_primavera.py             # expect: 110 activities, none skipped
```

First-ever run downloads all-MiniLM-L6-v2 (~80 MB) from Hugging Face into the user cache.
Ollama + `qwen2.5:7b` are only needed for the real `/extract` endpoint (legacy app, 8001).

## 6. Known issues & open flags

1. **No CORS on `main.py`** — the React dashboard (different port) cannot call `/match`
   from a browser until the standard CORSMiddleware block is added (see TEAM_NOTES.txt
   for the exact snippet). Python/scripts are unaffected.
2. **Grid mismatch (backlog):** a report saying grid "C-7/F-12" matched activity
   "C-7/F-01 to F-06" because matching uses `activity_description` only — the payload's
   `location` field is ignored. Fix = score fusion (description + location + date).
3. **Short extractor names score low:** 2–4-word activities from the extractor land in
   `review_queue` (40–50 %), while rich descriptions hit 82–90 % auto-link. Expected
   behaviour, but auto-link rate depends on extraction quality.
4. **Two overlapping datasets:** SQLite `schedule_items` (25 seeded Zone A–D tasks) and
   the Primavera Excel (110 Unit 5–7 activities) are different data. Before the dashboard
   shows "matched & updated", the Excel must be imported into `schedule_items`
   (import script = next backend task).
5. **`matcher.py` stub** is still what `main2`'s `/submit` uses. Replace with
   `match_engine` + scale fix (see §4) during DB wiring.
6. `requirements.txt` is missing the matching stack: add `sentence-transformers`,
   `numpy`, `pandas`, `openpyxl`. `pytest` is not installed in this environment — all
   test scripts are standalone `python file.py` runners on purpose.
7. ~~BUG: `/submit` on main2 always returns 503~~ **FIXED 2026-09-10.** `main2.py`
   now has a lifespan startup that loads the activity index (same policy as the
   matching wrapper: missing file → server still boots, /submit 503s). Verified
   with a mocked-extraction TestClient run: /submit returns 200 without any
   manual index loading.
8. ~~BUG: the new `/submit` never writes to the database~~ **FIXED 2026-09-10.**
   `/submit` now inserts one `reports` row per matched activity:
   `matched_activity_code` (new column, stores the Primavera activity_id string),
   `confidence_score` on the legacy 0.0–1.0 scale (engine /100), and
   `review_status` mapped from match_status (auto_linked→auto_applied,
   review_queue→needs_review, unplanned→no_match). Verified: /review-queue,
   /audit-trail and /dashboard serve real data after submissions.
   **Still open (by design):** auto-APPLYING to `schedule_items` (marking a task
   done) is not wired — it needs the Primavera Excel → `schedule_items` import
   script first (§7 item 3). Until then `matched_schedule_id` stays NULL and
   `/confirm-match` (which needs a real schedule id) only works for imported
   activities.

## 7. Next steps (priority order)

1. Add CORS to `main.py` (10 min, unblocks frontend). CORS already exists on main2.
2. **Import script:** Primavera Excel → `schedule_items` (one source of truth).
   This also unlocks auto-apply: /submit already stores the Primavera
   `matched_activity_code` on every report, so the import + a code→id lookup is
   all that's missing to mark tasks done automatically.
3. Frontend dashboard (biggest remaining chunk — see §8).
4. Score fusion with location/date (fixes flag 2).
5. Ask Member 5 to confirm the extractor's final output shape + whether the
   Google-API switch (mentioned in test_pipeline.py) is real.

## 8. Frontend developer guide

**Before anything else:** ask for the CORS fix (§7.1) — without it every browser call to
port 8000 fails with a CORS policy error. Test scripts work because they aren't browsers.

**Which port serves what:**
- `http://127.0.0.1:8000` — matching service. Interactive docs at `/docs`.
  Call `GET /health` on app start; if `index_loaded` is false, show "matching unavailable".
- `http://127.0.0.1:8001` — legacy app: review queue, schedule, dashboard counts, audit
  trail, and the real `/extract` (needs Ollama running).

**Submission flow (what to build):**
1. User types/speaks a report → `POST /submit` (8001) with `{"report_text": "..."}`.
   Response: `{"results": [list of /match results], "issues": [...]}` — the UI must
   handle multiple results and surface `issues` (e.g. as warnings). NOTE: until bugs
   7–8 in §6 are fixed, /submit 503s on a freshly started server, and nothing it
   returns is persisted (review queue stays empty).
2. Alternative two-step flow: `POST /extract` (8001) then map + `POST /match` (8000)
   per activity (see contract.py for the exact mapping).
3. Render each result per the badge rules below.

**Rendering `match_status` (suggested):**
- `auto_linked` → green badge, confidence % prominent ("Linked to L6-PIPING-1193 — 89.9%")
- `review_queue` → amber badge + the `rejection_reason` string (it is written for humans)
- `unplanned` → gray/red badge + `rejection_reason`

**Numbers & edge cases:**
- `confidence_score` is 0–100 (float, 2 dp) — NOT 0–1.
- `rejection_reason` is `null` exactly when status is `auto_linked`.
- First `/match` call after startup can take a few seconds (model warm-up) — skeleton the
  result card; the server itself takes ~5–30 s to boot while encoding 110 activities.
- Handle non-200s: 422 = malformed payload (show validation errors), 503 = index not
  loaded (show "schedule not loaded" state), 500 = engine error.

**Dashboard views to build (per the build plan):**
- Live schedule table from `/schedule` (8001) with status colours; highlight rows that
  just changed after a match is applied.
- Review queue from `/review-queue` (8001) with confirm (`/confirm-match`) and reject
  (`/unplanned`) buttons — both take `{report_id, schedule_id?}` JSON bodies.
- Delay analytics from `/dashboard` + `task_history` (Recharts bar chart, planned vs actual).
