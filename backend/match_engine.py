"""
match_engine.py
---------------
Task 1: Standalone Semantic Matching Engine

Purpose:
    Loads a Primavera schedule Excel file, encodes all activity names
    into vector embeddings ONCE at startup, and provides a matching
    function that finds the closest activity for any natural-language
    description using cosine similarity (semantic matching only —
    no keyword or string-based fuzzy matching).

Author: SIH 2026 — Fuzzy Matching & System Integration Team
"""

import os
import sys
import numpy as np
from sentence_transformers import SentenceTransformer, util

from parse_primavera import parse_schedule, get_activity_names

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# The exact model required by the project spec.
# all-MiniLM-L6-v2 is fast, lightweight (~80MB), and free.
MODEL_NAME = "all-MiniLM-L6-v2"

# Confidence thresholds — defined once here so they are easy to find and explain.
THRESHOLD_AUTO_LINKED = 75.0   # >= 75  → auto_linked
THRESHOLD_REVIEW_QUEUE = 40.0  # >= 40  → review_queue (else → unplanned)

# The exact Excel column names as agreed with the team.
REQUIRED_COLUMNS = [
    "activity_id",
    "activity_name",
    "discipline",
    "planned_start",
    "planned_end",
    "wbs_level",
]

# ---------------------------------------------------------------------------
# MODULE-LEVEL STATE (in-memory store, populated once at startup)
# ---------------------------------------------------------------------------

# The sentence-transformer model, loaded once when the module is imported.
model: SentenceTransformer = None

# The full activity index as a list of dicts.
# Each dict: {activity_id, activity_name, discipline, planned_start, ...}
activity_index: list[dict] = []

# Numpy array of shape (N, embedding_dim) holding one vector per activity.
# Row i corresponds to activity_index[i].
activity_embeddings: np.ndarray = None


# ---------------------------------------------------------------------------
# INITIALISATION
# ---------------------------------------------------------------------------

def _load_model() -> None:
    """
    Load the sentence-transformer model into memory.
    Called once when the module is first imported.
    The model is kept in the global `model` variable so it is never
    re-loaded on subsequent requests.
    """
    global model
    print(f"[match_engine] Loading sentence-transformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"[match_engine] Model loaded successfully.")


# Load the model immediately when this module is imported.
_load_model()


# ---------------------------------------------------------------------------
# INDEX LOADING
# ---------------------------------------------------------------------------

def load_activity_index(filepath: str) -> None:
    """
    Reads the Primavera schedule Excel file, encodes all activity_name
    values into embeddings, and stores everything in module-level memory.

    Task 5: the Excel reading itself is now delegated to
    parse_primavera.parse_schedule(), which owns header detection, date
    normalisation, whitespace stripping, and skip logging.  This function
    keeps the engine-side responsibilities: raising the errors the FastAPI
    wrapper expects, encoding the names, and populating module state.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the Primavera Excel file.

    Raises
    ------
    FileNotFoundError
        If the Excel file does not exist at the given path.
    ValueError
        If the file parses to zero activities (missing columns, unreadable,
        or empty).  parse_schedule() reports the specific reason on stdout
        and returns [] — we convert that into the ValueError that main.py's
        error handling (422/503 responses) is built around.

    Notes
    -----
    - This function REPLACES the in-memory index every time it is called,
      which is intentional — it supports the /reload-index endpoint in Task 2.
    """
    global activity_index, activity_embeddings

    print(f"[match_engine] Loading activity index from: {filepath}")

    # parse_schedule() returns [] on a missing file (with a printed error),
    # but callers of THIS function (main.py lifespan, /reload-index) expect
    # a FileNotFoundError — keep the exception contract intact.
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[match_engine] Excel file not found: {filepath}")

    # Parse via the shared parser (Task 4). Handles header detection,
    # date conversion to ISO strings, whitespace stripping, blank rows.
    activities = parse_schedule(filepath)

    if len(activities) == 0:
        raise ValueError(
            "[match_engine] Activity index is empty after parsing. "
            "Check the Excel file — see parse_primavera output above."
        )

    # Store the full activity dicts (same keys the parser contract defines:
    # activity_id, activity_name, discipline, planned_start, planned_end,
    # wbs_level).  match_activity() reads activity_id / activity_name /
    # discipline from these dicts.
    activity_index = activities

    # Parallel (names, ids) lists from the parser — order is preserved, so
    # embedding row i corresponds to activity_index[i].
    activity_names, activity_ids = get_activity_names(activities)

    print(f"[match_engine] Encoding {len(activity_names)} activities — this happens only once...")

    # Encode all activity names into dense vector embeddings in one batch.
    # convert_to_numpy=True returns a numpy array instead of a PyTorch tensor,
    # which is easier to slice and index when discipline filtering is applied.
    activity_embeddings = model.encode(
        activity_names,
        convert_to_numpy=True,
        show_progress_bar=True,   # Shows a progress bar in terminal during startup
        batch_size=64,            # 64 sentences per forward pass — good for CPU
    )

    print(f"[match_engine] Index ready. {len(activity_index)} activities encoded.")
    print(f"[match_engine] Embedding matrix shape: {activity_embeddings.shape}")

    # Print a breakdown by discipline so it is easy to verify correctness.
    discipline_counts = {}
    for row in activity_index:
        d = str(row.get("discipline", "Unknown")).strip()
        discipline_counts[d] = discipline_counts.get(d, 0) + 1
    for disc, count in sorted(discipline_counts.items()):
        print(f"  {disc}: {count} activities")


# ---------------------------------------------------------------------------
# MATCHING LOGIC
# ---------------------------------------------------------------------------

def match_activity(
    extracted_description: str,
    discipline: str = None,
) -> dict:
    """
    Finds the best-matching Primavera schedule activity for a given
    natural-language activity description using semantic similarity.

    Parameters
    ----------
    extracted_description : str
        The activity description extracted from the worker's log.
        Example: "column footing concrete pouring Unit 7"

    discipline : str, optional
        If provided and non-null, matching is restricted to activities
        belonging to this discipline only.
        Valid values: "Civil", "Piping", "Electrical", "Instrumentation", "HSE"
        If None or empty string, matching runs against the full index.

    Returns
    -------
    dict with keys:
        matched_activity_id   : str   — e.g. "L5-CIVIL-2847"
        matched_activity_name : str   — e.g. "Concrete placement column foundations Unit 7"
        confidence_score      : float — cosine similarity × 100, rounded to 2 decimal places
        match_status          : str   — "auto_linked" | "review_queue" | "unplanned"

    Raises
    ------
    RuntimeError
        If the activity index has not been loaded yet (empty index or
        missing embeddings).
    ValueError
        If the extracted_description is empty or None.
    """
    # Guard: ensure the index has been loaded before attempting to match.
    if not activity_index or activity_embeddings is None:
        raise RuntimeError(
            "[match_engine] Activity index is not loaded. "
            "Call load_activity_index() first."
        )

    # Guard: reject empty descriptions — they cannot produce meaningful matches.
    if not extracted_description or not extracted_description.strip():
        raise ValueError("[match_engine] extracted_description cannot be empty.")

    # -----------------------------------------------------------------------
    # Step 1: Determine the candidate pool (full index vs discipline subset)
    # -----------------------------------------------------------------------

    use_discipline_filter = (
        discipline is not None
        and isinstance(discipline, str)
        and discipline.strip() != ""
    )

    if use_discipline_filter:
        # Build a list of (original_index, activity_row) pairs for this discipline.
        # We keep the original index so we can retrieve the correct embedding row.
        discipline_clean = discipline.strip()
        candidates = [
            (i, row)
            for i, row in enumerate(activity_index)
            if str(row.get("discipline", "")).strip() == discipline_clean
        ]

        if len(candidates) == 0:
            # The discipline value from the extraction engine doesn't match any
            # activity in the index. Fall back to full-index search.
            print(
                f"[match_engine] WARNING: No activities found for discipline "
                f"'{discipline_clean}'. Falling back to full-index search."
            )
            use_discipline_filter = False

    if not use_discipline_filter:
        # Use the full index — enumerate all rows.
        candidates = list(enumerate(activity_index))

    # Extract the embedding rows for just the candidate pool.
    # np.array([...]) stacks the individual embedding vectors into a 2D matrix.
    candidate_indices = [idx for idx, _ in candidates]
    candidate_embeddings = activity_embeddings[candidate_indices]  # shape: (M, dim)

    # -----------------------------------------------------------------------
    # Step 2: Encode the query description into the same embedding space
    # -----------------------------------------------------------------------

    # FUTURE ENHANCEMENT — Multilingual / Hindi input support:
    # The current model (all-MiniLM-L6-v2) is English-primary. Hindi inputs in
    # Devanagari or romanised Hinglish (e.g. "column ka concrete daala") will
    # produce lower confidence scores because the model cannot interpret Hindi
    # grammar words, only shared technical terms like "column", "concrete", "Unit 7".
    #
    # Production fix: before encoding, detect non-ASCII or Hinglish input and
    # pass it through a lightweight translation step, e.g.:
    #   from deep_translator import GoogleTranslator
    #   translated = GoogleTranslator(source='auto', target='en').translate(text)
    # Then encode the translated string instead of the raw input.
    #
    # This is deliberately not implemented in the prototype. Hindi inputs
    # currently route to review_queue (human verification), which is a safe
    # and acceptable fallback for the demo. Translation is a post-hackathon task.

    # Encode returns shape (1, dim) when given a single string in a list.
    query_embedding = model.encode(
        [extracted_description.strip()],
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    # -----------------------------------------------------------------------
    # Step 3: Compute cosine similarity between query and all candidates
    # -----------------------------------------------------------------------

    # util.cos_sim returns a tensor of shape (1, M).
    # We convert to numpy and flatten to a 1D array of M similarity scores.
    similarity_scores = util.cos_sim(query_embedding, candidate_embeddings)
    similarity_scores = similarity_scores.numpy().flatten()  # shape: (M,)

    # -----------------------------------------------------------------------
    # Step 4: Find the best match
    # -----------------------------------------------------------------------

    # np.argmax returns the index of the highest similarity score in the
    # candidate array (not the original full-index position).
    best_candidate_pos = int(np.argmax(similarity_scores))
    best_raw_score = float(similarity_scores[best_candidate_pos])

    # Convert cosine similarity (0–1) to a confidence percentage (0–100).
    confidence_score = round(best_raw_score * 100, 2)

    # Retrieve the winning activity using the original full-index position.
    best_original_idx = candidate_indices[best_candidate_pos]
    best_activity = activity_index[best_original_idx]

    # -----------------------------------------------------------------------
    # Step 5: Determine match_status and rejection_reason
    # -----------------------------------------------------------------------

    if confidence_score >= THRESHOLD_AUTO_LINKED:
        match_status = "auto_linked"
        # No rejection — match is confident. rejection_reason is null.
        rejection_reason = None

    elif confidence_score >= THRESHOLD_REVIEW_QUEUE:
        match_status = "review_queue"
        # Match exists but confidence is low — flag for human review.
        # Provide a reason so the dashboard can display it to the manager.
        rejection_reason = (
            f"Confidence {confidence_score}% is below the auto-link threshold "
            f"of {THRESHOLD_AUTO_LINKED}%. Human review required before linking."
        )

    else:
        match_status = "unplanned"
        # Confidence is too low to associate this log with any scheduled activity.
        # This means the input is either too vague, or the activity genuinely
        # does not exist in the current Primavera schedule (truly unplanned work).
        rejection_reason = (
            f"Confidence {confidence_score}% is below the minimum threshold "
            f"of {THRESHOLD_REVIEW_QUEUE}%. Description too vague, or activity "
            f"not present in the Primavera schedule."
        )

    # -----------------------------------------------------------------------
    # Step 6: Return the result in the agreed output format
    # -----------------------------------------------------------------------

    return {
        "matched_activity_id":   str(best_activity["activity_id"]),
        "matched_activity_name": str(best_activity["activity_name"]),
        "confidence_score":      confidence_score,
        "match_status":          match_status,
        # rejection_reason is null for auto_linked, descriptive string otherwise.
        # This field is extra context for the manager dashboard — not in the
        # core database contract, but included as an informational field.
        "rejection_reason":      rejection_reason,
    }


# ---------------------------------------------------------------------------
# TEST HARNESS (runs when the script is executed directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Quick test harness for Task 1.
    Run with:  python match_engine.py
    Requires primavera_schedule.xlsx in the same directory.
    """

    EXCEL_PATH = "primavera_schedule.xlsx"

    # Load and encode the full index.
    try:
        load_activity_index(EXCEL_PATH)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[ERROR] Could not load index: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("TASK 1 — SEMANTIC MATCHING TEST (6 CASES)")
    print("=" * 70)

    # 6 test descriptions covering different disciplines, confidence levels,
    # and languages. Each tuple: (description, discipline, expected_hint)
    test_cases = [
        (
            # Case 1: Clear Civil match — should auto_link
            "column footing concrete pouring Unit 7",
            "Civil",
            "Expect: auto_linked (clear civil match)",
        ),
        (
            # Case 2: Piping-related description — should auto_link
            "hydrostatic pressure testing on 6 inch pipeline section",
            "Piping",
            "Expect: auto_linked (piping test match)",
        ),
        (
            # Case 3: Vague description, correct discipline — too vague to match
            "some electrical work done in the morning",
            "Electrical",
            "Expect: unplanned (too vague for semantic match)",
        ),
        (
            # Case 4: No discipline provided — full index search
            "safety briefing and toolbox talk for all workers",
            None,
            "Expect: auto_linked or review_queue (HSE, full index search)",
        ),
        (
            # Case 5: Completely unrelated description — should be unplanned
            "ordered lunch for the team and fixed the site office wifi",
            None,
            "Expect: unplanned (no meaningful match in schedule)",
        ),
        (
            # Case 6: Hindi input — tests cross-lingual semantic matching.
            # Translation: 'In Unit 7, poured concrete for the column,
            # started from 6 AM in the morning'
            # Should match the same Civil activity as Case 1.
            "Unit 7 mein column ka concrete daala subah 6 baje se shuru kiya",
            "Civil",
            "Expect: auto_linked (Hindi input — same meaning as Case 1)",
        ),
    ]

    for i, (description, discipline, hint) in enumerate(test_cases, start=1):
        print(f"\n--- Test Case {i} ---")
        print(f"  Input description : {description}")
        print(f"  Discipline filter : {discipline}")
        print(f"  {hint}")

        try:
            result = match_activity(description, discipline=discipline)
            print(f"  matched_activity_id   : {result['matched_activity_id']}")
            print(f"  matched_activity_name : {result['matched_activity_name']}")
            print(f"  confidence_score      : {result['confidence_score']}%")
            print(f"  match_status          : {result['match_status']}")
            # Only print rejection_reason when it has a value (not null)
            if result["rejection_reason"] is not None:
                print(f"  rejection_reason      : {result['rejection_reason']}")
        except (RuntimeError, ValueError) as e:
            print(f"  [ERROR] {e}")

    print("\n" + "=" * 70)
    print("Test complete. Confirm results before moving to Task 2.")
    print("=" * 70)
