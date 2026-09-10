"""
demo_extract_to_match.py
------------------------
Proves the full extraction -> matching chain WITHOUT Ollama or servers:

    hardcoded /extract JSON  ->  contract adapter  ->  match_activity()

The hardcoded JSON mirrors exactly what the live /extract endpoint returns
(shape of routes.py's ExtractResponse).  When Ollama and both servers are
running, the same chain works over HTTP:

    POST /extract (main2:app, port 8001)
        -> contract.extract_response_to_match_payloads()
    POST /match   (main:app,  port 8000)

Run:
    python demo_extract_to_match.py
"""

from match_engine import load_activity_index, match_activity
from contract import extract_response_to_match_payloads

# ---------------------------------------------------------------------------
# Simulated Member 5 extraction output — the real /extract response shape
# for a typical multi-activity field report (hardcoded; no LLM called).
# ---------------------------------------------------------------------------

EXTRACT_RESPONSE = {
    "activities": [
        {
            "activity": "Trench excavation",
            "location": "Zone B - Pipeline Corridor",
            "date": "2026-09-01",
            "status": "completed",
            "progress_percent": 100,
        },
        {
            "activity": "Cable pulling in substation",
            "location": "Zone C - Substation",
            "date": "2026-09-01",
            "status": "in_progress",
            "progress_percent": 40,
        },
        {
            "activity": "Toolbox talk for all workers",
            "location": None,
            "date": "2026-09-02",
            "status": "completed",
            "progress_percent": None,
        },
    ],
    "issues": ["Concrete mixer breakdown delayed the pour"],
}

# Disciplines are not produced by the extractor yet. In production these
# would come from the extraction prompt or a UI dropdown; here we infer
# them from the activity text to exercise the discipline filter.
DISCIPLINE_HINTS = [
    ("trench", "Piping"),
    ("cable", "Electrical"),
    ("toolbox", None),  # no discipline -> full-index search
]


def infer_discipline(description: str) -> str | None:
    text = description.lower()
    for keyword, discipline in DISCIPLINE_HINTS:
        if keyword in text:
            return discipline
    return None


def main() -> None:
    print("=" * 78)
    print("END-TO-END DEMO: extraction output -> contract adapter -> matching engine")
    print("=" * 78)

    load_activity_index("primavera_schedule.xlsx")

    payloads, issues = extract_response_to_match_payloads(
        EXTRACT_RESPONSE, source_format="free_text"
    )

    print(f"\nAdapter produced {len(payloads)} match payloads "
          f"and passed through {len(issues)} issue(s): {issues}")

    for i, payload in enumerate(payloads, 1):
        # Attach the (future) discipline, then match.
        payload["discipline"] = infer_discipline(payload["activity_description"])

        print(f"\n--- Report item {i} ---")
        print("PAYLOAD (in /match contract):")
        for key, value in payload.items():
            print(f"  {key:22s}: {value!r}")

        result = match_activity(
            payload["activity_description"],
            discipline=payload["discipline"],
        )
        print("MATCH:")
        print(f"  activity_id   : {result['matched_activity_id']}")
        print(f"  activity_name : {result['matched_activity_name']}")
        print(f"  confidence    : {result['confidence_score']}%")
        print(f"  routing       : {result['match_status']}")
        if result["rejection_reason"]:
            print(f"  reason        : {result['rejection_reason']}")


if __name__ == "__main__":
    main()
