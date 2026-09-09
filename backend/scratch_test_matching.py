from rapidfuzz import process, fuzz

seeded_tasks = [
    "Erect Line 24-XX",
    "Trench excavation Zone B",
    "Valve installation Site C",
    "Cable laying Section D-2",
    "Foundation pour Bay 7",
]

extracted_task = "did the valve thing at site C"

matches = process.extract(
    extracted_task,
    seeded_tasks,
    scorer=fuzz.token_sort_ratio,
    limit=3
)

for match_text, score, _ in matches:
    print(f"{match_text!r} -> {score:.2f}")
