"""
extractor.py — Ollama-powered field report extraction with deterministic
post-processing.

Responsibility:
  1. Call the local Ollama model to extract structured data from a raw
     field report.
  2. Apply deterministic post-processing rules that the LLM cannot
     reliably handle:
       - Resolve relative dates ("today", "yesterday", "this morning")
         to ISO date strings.  Default missing dates to today.
       - Validate locations against the real schedule_items locations
         fetched from the database; set to null if not a known location.
       - Prevent quantities (metres, tonnes) from being misread as
         progress percentages; only accept an integer % when an actual
         percentage was stated or clearly implied.
       - Strip verb prefixes and embedded location tokens from activity
         names so they match schedule item task_names more reliably.

This module has NO knowledge of FastAPI routing or matching logic.
It only handles the LLM call, post-processing, and returns a clean dict
matching the ExtractResponse schema defined in routes.py.

Ollama must be running locally:
    ollama serve
    ollama run qwen2.5:7b

Usage:
    from extractor import extract_report
    result = extract_report("Laid 40m of conduit on Level 3", known_locations=[...])
"""

import json
import logging
import re
from datetime import date, timedelta

import ollama
from ollama import ResponseError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------
_MODEL = "qwen2.5:7b"
_OLLAMA_HOST = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Relative-date tokens → day offsets from today
# ---------------------------------------------------------------------------
_RELATIVE_DATE_OFFSETS: dict[str, int] = {
    "today": 0,
    "this morning": 0,
    "this afternoon": 0,
    "this evening": 0,
    "tonight": 0,
    "yesterday": -1,
    "last night": -1,
    "day before yesterday": -2,
    "tomorrow": 1,
}

# Regex that matches any of the relative tokens (case-insensitive)
_RELATIVE_DATE_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _RELATIVE_DATE_OFFSETS) + r")\b",
    re.IGNORECASE,
)

# Verb prefixes the LLM tends to prepend to activity names
_VERB_PREFIX_RE = re.compile(
    r"^(completed?|finished?|done|carried\s+out|performed?|conducted?|"
    r"started?|initiated?|commenced?)\s+",
    re.IGNORECASE,
)

# Unit patterns that look like numbers but are NOT percentages
# e.g. "60 metres", "20 tonnes", "5 valves", "3 lengths"
_QUANTITY_UNIT_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(metre|meter|m\b|km|tonne|ton|kg|pipe|valve|"
    r"spool|length|section|unit|piece|bolt|joint|bay|panel|duct|"
    r"cable|conduit|drum|coil|reel|bag|pack|load|truck|shift|hour|hr)\b",
    re.IGNORECASE,
)

# Explicit percentage patterns — only these justify a numeric progress_percent
_PCT_EXPLICIT_RE = re.compile(
    r"\b(\d{1,3})\s*%|\b(\d{1,3})\s*percent\b",
    re.IGNORECASE,
)

# Clear completion language that implies 100%
_COMPLETE_LANGUAGE_RE = re.compile(
    r"\b(fully\s+complete[d]?|100\s*%|all\s+done|entirely\s+done|"
    r"finish(?:ed)?|wrap(?:ped)?\s+up)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Explicit alias map — field-report location strings → canonical DB location
#
# Keys are lowercase strings that may appear verbatim in a field report.
# Values are the exact strings stored in schedule_items.location.
#
# RULES for adding entries:
#   - The canonical location MUST exist in schedule_items.location.
#   - The alias MUST have direct, documented evidence as a known synonym
#     for that canonical location — not inferred from a shared letter or word.
#   - Do NOT add aliases based on partial similarity (e.g. "Section D-2"
#     shares "D" with "Zone D" but is NOT the same location).
#   - When in doubt, leave the alias out — null is safer than a wrong mapping.
#   - When the project schedule changes, update this map to match.
#
# Current canonical locations (from schedule_items):
#   'Zone A - Tank Farm'
#   'Zone B - Pipeline Corridor'
#   'Zone C - Substation'
#   'Zone D - Control Room'
# ---------------------------------------------------------------------------
_LOCATION_ALIASES: dict[str, str] = {
    # Zone A — Tank Farm
    "zone a": "Zone A - Tank Farm",
    "zone a - tank farm": "Zone A - Tank Farm",
    "tank farm": "Zone A - Tank Farm",
    # Zone B — Pipeline Corridor
    "zone b": "Zone B - Pipeline Corridor",
    "zone b - pipeline corridor": "Zone B - Pipeline Corridor",
    "pipeline corridor": "Zone B - Pipeline Corridor",
    # Zone C — Substation
    # "substation" is a distinctive enough term and all Zone C tasks
    # are substation tasks, so this alias is safe.
    "zone c": "Zone C - Substation",
    "zone c - substation": "Zone C - Substation",
    "substation": "Zone C - Substation",
    # Zone D — Control Room
    "zone d": "Zone D - Control Room",
    "zone d - control room": "Zone D - Control Room",
    "control room": "Zone D - Control Room",
    # NOTE: "Section D-2", "Section D2", "Site C", "Bay 7", "Line 24-*"
    # are NOT in the canonical location list and have no verified mapping.
    # They must return null until the project schedule explicitly defines them.
}

# ---------------------------------------------------------------------------
# Deterministic report scanner — runs BEFORE trusting the LLM
# ---------------------------------------------------------------------------


def _scan_report_for_location(
    report_text: str,
    known_locations: list[str],
) -> str | None:
    """
    Scan the raw report text for an explicit location reference and return
    the canonical DB location string, or None if nothing is found.

    Precedence (stops at first match):
      1. Exact or alias match from _LOCATION_ALIASES — longest alias wins
         (prevents "zone b" matching before "zone b - pipeline corridor").
      2. Canonical location string directly present in the report text.

    This function deliberately does NOT do fuzzy or word-overlap matching.
    If the report contains "Zone B" we return "Zone B - Pipeline Corridor".
    If the report contains only "pipe" or "cable" we return None.

    The result of this scan OVERRIDES the LLM's location field in _postprocess
    when a match is found, preventing the LLM from hallucinating locations while
    ensuring explicit field-report aliases are always recognised.
    """
    report_lower = report_text.lower()

    # Pass 1: check _LOCATION_ALIASES — test longer keys first so that
    # "zone b - pipeline corridor" matches before the shorter "zone b"
    for alias in sorted(_LOCATION_ALIASES, key=len, reverse=True):
        if alias in report_lower:
            canonical = _LOCATION_ALIASES[alias]
            # Verify the mapped canonical location is still in the live DB list
            if not known_locations or canonical in known_locations:
                logger.debug("Direct alias match: %r → %r", alias, canonical)
                return canonical

    # Pass 2: check canonical location strings verbatim
    for known in known_locations:
        if known.lower() in report_lower:
            logger.debug("Canonical location found verbatim in report: %r", known)
            return known

    return None


# ---------------------------------------------------------------------------
# Prompt builder — accepts known locations so the model never needs to guess
# ---------------------------------------------------------------------------


def _build_system_prompt(known_locations: list[str]) -> str:
    locations_block = (
        "\n".join(f'  - "{loc}"' for loc in known_locations)
        if known_locations
        else "  (none available — use null for location)"
    )

    today_iso = date.today().isoformat()

    return f"""\
You are an information extraction engine for construction and infrastructure project sites.

You will receive a plain-language field report written by a site supervisor or worker.
Your job is to extract structured data from it and return ONLY valid JSON — no prose,
no markdown, no explanation.

=== KNOWN PROJECT LOCATIONS ===
Only use one of these exact strings for the "location" field:
{locations_block}

If the report mentions a location that clearly maps to one of the above, use that exact
string.  If the location is ambiguous, partially mentioned, or not in the list, use null.
Do NOT invent or guess a location.

=== TODAY'S DATE ===
Today is {today_iso}.  Use this to resolve relative date references:
- "today" / "this morning" / "this afternoon" → {today_iso}
- "yesterday" / "last night" → {(date.today() - timedelta(days=1)).isoformat()}
If no date is mentioned in the report, use null for the date field.

=== EXTRACTION RULES ===

For every construction activity or task mentioned, extract:

- "activity": the construction task name only — nothing else.
  RULES for activity:
    * Preserve the full technical description from the report when it includes
      specific technical details such as rack elevation, spool numbers, grid
      references, floor levels, zone names, unit numbers, corridor names, or
      other precise identifiers.
    * Do NOT collapse the activity to a generic summary such as "Spool erection"
      when the report gives the detailed description. Keep the specific task
      wording, such as "Spool erection on north rack elevation 7.5m" or
      "Concrete pour for column footing on Unit 7".
    * The activity field must be descriptive enough that someone unfamiliar with
      the report could identify exactly which work item it refers to.
    * Do NOT include the location, zone, site, section, bay, or area name as part
      of the activity text when that information is already captured separately in
      the "location" field. However, when the report has technical detail that is
      part of the work description, keep it in the activity text.
    * Do NOT start with a completion or status verb.
      Remove prefixes such as "Completed", "Finished", "Carried out",
      "Performed", "Conducted".
    * Keep it short but specific: aim for a precise task description that still
      clearly identifies the work item without unnecessary narration.
    * One sentence = one activity unless it clearly describes two separate tasks.

  EXAMPLES (input phrase → correct activity value):
    "Completed spool erection on north rack elevation 7.5 metres, Zone A piping corridor"
      → activity: "Spool erection on north rack elevation 7.5m"  location: "Zone A - Tank Farm"

    "Cable laying in Section D-2 is 70% complete"
      → activity: "Cable laying"               location: null

    "Valve installation at Site C pump station"
      → activity: "Valve installation"         location: null

    "Structural erection work was carried out today in Zone D"
      → activity: "Structural erection"        location: "Zone D - Control Room"

    "HT cable pulling in the substation area"
      → activity: "HT cable pulling"           location: "Zone C - Substation"

    "Foundation pour for the control room in Zone D is done"
      → activity: "Foundation pour"            location: "Zone D - Control Room"

    "Pipe welding near tank 3 ongoing"
      → activity: "Pipe welding"               location: null

- "location": one of the KNOWN PROJECT LOCATIONS listed above, or null.
  IMPORTANT:
    * Never return null for location when the report contains any location detail,
      including zone names, rack references, corridor names, unit numbers,
      floor levels, bay names, or other clear physical references.
    * If the location is a zone, rack, corridor, or unit that maps to the project
      locations list, use the exact known location string from the list above.
    * If the report gives any location clue at all, do not default to null unless
      it is clearly not a project location and no valid known location can be
      matched.

- "date": ISO date string (YYYY-MM-DD) if a date or relative time reference
  (today, yesterday, this morning) appears in the report; otherwise null.

- "status": exactly one of:
    "completed"   — work is finished
    "in_progress" — work is currently happening
    "pending"     — work is planned but NOT yet started
    "delayed"     — work was supposed to happen but is blocked or behind schedule
    "unknown"     — not enough information to determine status

  IMPORTANT:
    * Use "in_progress" for work that is partially done or has started.
    * Use "pending" ONLY for work that has not started at all.
    * Past-tense language ("work happened", "team was there") → "in_progress" or
      "completed", NOT "pending".

- "progress_percent": integer 0–100 ONLY when:
    * An explicit percentage is stated (e.g. "70% complete", "80 percent done"), OR
    * Clear completion language is used ("fully complete", "all done") → 100.
  DO NOT convert quantities (metres, tonnes, valves, pipes) into percentages.
  If progress is described vaguely ("some", "a bit", "most of it"), use null.
  
  ACTIVITY SPECIFICITY RULE:

Only extract an activity when a specific construction task or work operation
is explicitly identified.

Do NOT create an activity from vague status statements that do not identify
what physical work was performed.

Examples that must return NO activity:
- "Work done today"
- "Team was on site"
- "Some progress was made"
- "Work is ongoing"
- "Details to follow"

A valid activity must describe a specific task such as excavation, welding,
cable laying, concrete pouring, installation, fabrication, erection, etc.

PENDING ACTIVITY VS ISSUE:

A specific construction task that is pending, not started, awaiting execution,
or scheduled for later is still an ACTIVITY.

Extract the task with:
- status: "pending"

Do NOT treat "pending", "not started", "not started yet", or "awaiting execution"
as an issue by themselves.

A pending task becomes associated with an issue ONLY when the report explicitly
states a separate negative cause, blocker, delay, approval problem, access problem,
resource problem, failure, or other condition preventing the work.

Examples:

"Road crossing bore is still pending"
→ Activity: "Road crossing bore", status: "pending"
→ Issues: []

"Earthing and grounding work has not started yet"
→ Activity: "Earthing and grounding work", status: "pending"
→ Issues: []

"Road crossing bore is pending because contractor approval is awaited"
→ Activity: "Road crossing bore", status: "pending"
→ Issue: "Contractor approval awaited"

IMPORTANT:
The construction task itself must NEVER appear in the issues list merely because
it is pending or has not started.

ISSUES — STRICT RULE:
Only extract an issue when the report explicitly describes a real problem, blocker,
delay, failure, safety concern, damage, missing resource, weather disruption,
equipment malfunction, approval problem, or other condition that negatively affects
the work.

Do NOT treat normal narration, incomplete progress, uncertainty, future updates,
staffing notes, or descriptive status statements as issues.

The following are NOT issues:
  "Some sections are done but not all"
  "Team working through the afternoon"
  "Workers were on site most of the day"
  "Foreman will update tomorrow"
  "Progress is reasonable"
  "Details to follow"
  "No delays reported"

Examples of actual issues:
  "Work stopped early due to high wind"
  "Cable laying was halted because of heavy rain"
  "Equipment breakdown stopped progress"
  "Supplier delivered the wrong cable specification"
  "Permit approval is still pending"
  "Access was blocked due to a safety incident"

If no explicit problem or blocker is stated, return "issues": []


EXAMPLE 1:
Report: "Pipe welding near tank 3 ongoing. Some sections done but not all.
Team working through the afternoon."
Correct output:
  activities: [{{ "activity": "Pipe welding", "location": null, "date": null,
                 "status": "in_progress", "progress_percent": null }}]
  issues: []
Reason: incomplete progress and normal work narration are not issues.

EXAMPLE 2:
Report: "Pipe welding was halted due to equipment failure."
Correct output:
  activities: [{{ "activity": "Pipe welding", "location": null, "date": null,
                 "status": "delayed", "progress_percent": null }}]
  issues: ["Equipment failure halted work"]

Return ONLY this JSON structure, nothing else:

{{
  "activities": [
    {{
      "activity": "string",
      "location": "exact known location string or null",
      "date": "YYYY-MM-DD or null",
      "status": "completed | in_progress | pending | delayed | unknown",
      "progress_percent": integer or null
    }}
  ],
  "issues": ["string", ...]
}}
"""


# ---------------------------------------------------------------------------
# Deterministic post-processing
# ---------------------------------------------------------------------------


def _resolve_date(report_text: str, model_date: str | None) -> str:
    """
    Resolve the date for an activity.

    Priority:
      1. If model returned a valid ISO date string → use it.
      2. If model returned null but report contains a relative date token
         → resolve that token to an absolute date.
      3. Default → today's ISO date.
    """
    today = date.today()

    # Trust a non-null model date if it looks like a valid ISO date
    if model_date:
        try:
            date.fromisoformat(model_date)
            return model_date
        except ValueError:
            pass  # fall through to relative-date scan

    # Scan the report text for relative date tokens
    match = _RELATIVE_DATE_RE.search(report_text)
    if match:
        token = match.group(1).lower()
        offset = _RELATIVE_DATE_OFFSETS.get(token, 0)
        return (today + timedelta(days=offset)).isoformat()

    # Nothing found — default to today
    return today.isoformat()


def _validate_location(
    raw_location: str | None,
    known_locations: list[str],
    report_text: str = "",
) -> str | None:
    """
    Accept the model's location only when TWO independent conditions are met:

      1. SCHEMA CHECK — the raw location fuzzy-matches a known schedule location
         (exact, prefix-substring, or distinctive-word overlap).

      2. EVIDENCE CHECK — the report text itself contains at least one
         distinctive token from the matched known location.
         This prevents the model from hallucinating a valid-looking location
         that has no support in the input text.

    Both conditions must pass.  If either fails → return null.

    Matching strategy for condition 1 (stops at first match):
      a. Exact match (case-insensitive).
      b. Model value is a prefix substring of the known location
         (ends at a word boundary — avoids "Zone B" matching "Zone A - ...").
      c. Known location is a substring of the model value.
      d. Word-level overlap using only words longer than 4 chars
         (excludes generic tokens: "zone", "area", "site", "room").

    Evidence tokens for condition 2 are the distinctive words extracted from
    the MATCHED known location — words longer than 4 chars.  Generic words
    that appear across many locations ("zone", "area") are excluded.
    Additionally, short zone identifiers like "Zone A", "Zone B", "Zone C",
    "Zone D" are tested as literal substrings of the report text so that
    "Zone B" in the input is always sufficient evidence for condition 2.
    """
    if not raw_location or not known_locations:
        return None

    normalised = raw_location.strip().lower()
    report_lower = report_text.strip().lower()

    for known in known_locations:
        k = known.lower()
        matched = False

        # --- Condition 1: schema match ---

        # a. Exact
        if normalised == k:
            matched = True

        # b. Model value is a prefix/suffix substring of the known location
        #    at a word boundary
        if not matched and normalised in k:
            idx = k.find(normalised)
            end = idx + len(normalised)
            if end == len(k) or not k[end].isalnum():
                matched = True

        # c. Known location contained inside the model value
        if not matched and k in normalised:
            matched = True

        # d. Word-level overlap (words > 4 chars only)
        if not matched:
            raw_words = {w for w in re.split(r"[\s\-–/]+", normalised) if len(w) > 4}
            known_words = {w for w in re.split(r"[\s\-–/]+", k) if len(w) > 4}
            if raw_words and known_words and (raw_words & known_words):
                matched = True

        if not matched:
            continue

        # --- Condition 2: evidence check ---
        # The report text must contain at least one token that supports
        # this specific known location.  We test two token types:
        #
        #   i.  Short zone identifiers: "zone a", "zone b", "zone c", "zone d"
        #       These are literal substrings of the known location key and are
        #       distinctive enough at 6 chars.
        #
        #  ii.  Distinctive words from the known location string (len > 4).
        #       e.g. for "Zone B - Pipeline Corridor":
        #         distinctive = {"pipeline", "corridor"}
        #
        # If EITHER token type is found verbatim in the report → evidence found.

        # Type i: short zone identifiers embedded in the known location
        zone_id_re = re.compile(r"\bzone\s+[a-z]\b", re.IGNORECASE)
        zone_match = zone_id_re.search(k)
        if zone_match:
            zone_token = zone_match.group(0).lower()  # e.g. "zone b"
            if zone_token in report_lower:
                return known  # both conditions met

        # Type ii: distinctive long words from the known location
        distinctive = {w for w in re.split(r"[\s\-–/]+", k) if len(w) > 4}
        for token in distinctive:
            if token in report_lower:
                return known  # both conditions met

        # Condition 2 failed — report has no textual evidence for this location
        # even though it matched the schema.  Reject it.
        logger.debug(
            "Location %r matched schema (%r) but no evidence found in report text.",
            raw_location,
            known,
        )
        return None

    return None


def _clean_activity_name(name: str) -> str:
    """
    Strip verb prefixes from activity names, restore sentence case, and
    apply narrow canonical normalisation for known construction task variants.

    Verb-prefix stripping:
        "Completed pipe welding"        -> "Pipe welding"
        "Carried out trench excavation" -> "Trench excavation"

    Canonical normalisation (applied after stripping):
        "Trench digging"                       -> "Trench excavation"
        "Digging the trench"                   -> "Trench excavation"
        "Digging work for the pipeline trench" -> "Trench excavation"
        "Pipeline trench excavation"           -> "Trench excavation"
    """
    cleaned = _VERB_PREFIX_RE.sub("", name).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    # Narrow canonical lookup — (compiled_pattern, canonical_name) pairs.
    # Applied to the cleaned name. First match wins.
    _CANONICAL_NAMES = [
        # Trench excavation variants
        (
            re.compile(
                r"^(pipeline\s+)?trench\s+digging$"
                r"|^digging\s+(the\s+)?trench$"
                r"|^digging\s+work\s+(for\s+(the\s+)?)?([\w]+\s+)?trench$"
                r"|^([\w]+\s+)?trench\s+(digging|dug|dig)$"
                r"|^pipeline\s+trench\s+excavation$",
                re.IGNORECASE,
            ),
            "Trench excavation",
        ),
    ]
    for pattern, canonical in _CANONICAL_NAMES:
        if pattern.match(cleaned.strip()):
            return canonical

    return cleaned


def _validate_progress(
    raw_pct: int | None,
    report_text: str,
    activity_text: str,
) -> int | None:
    """
    Accept a progress_percent value only when evidence of an actual percentage
    exists in the report text.

    Rejects:
      - Numeric values that appear next to unit words (metres, tonnes, etc.)
        without an accompanying % sign.
      - Values from reports that contain no % sign and no completion language.

    Accepts:
      - Explicit "N%" or "N percent" in the report.
      - Clear completion language ("fully complete", "all done") → 100.
    """
    if raw_pct is None:
        return None

    combined = f"{report_text} {activity_text}".lower()

    # Case 1: explicit percentage present in the report
    if _PCT_EXPLICIT_RE.search(combined):
        return max(0, min(100, int(raw_pct)))

    # Case 2: clear completion language implies 100%
    if _COMPLETE_LANGUAGE_RE.search(combined):
        return 100

    # Case 3: the number appears beside a unit word — it's a quantity, not a %
    if _QUANTITY_UNIT_RE.search(combined):
        return None

    # Case 4: no % evidence at all — discard
    return None


def _validate_status(status: str, report_text: str) -> str:
    """
    Hard-rule override: if the model returned "pending" but the report
    contains past-tense work language, upgrade to "in_progress".

    This catches the Test 8 class of error where "work happened" was
    classified as pending.
    """
    if status != "pending":
        return status

    past_tense_re = re.compile(
        r"\b(happened|occurred|took\s+place|was\s+done|was\s+carried|"
        r"was\s+completed|was\s+performed|finished|wrapped\s+up|"
        r"was\s+on\s+site|were\s+on\s+site|worked|started|began)\b",
        re.IGNORECASE,
    )
    if past_tense_re.search(report_text):
        return "in_progress"

    return status


def _is_noise_activity(name: str, report_text: str) -> bool:
    """
    Return True if the activity name is too vague to be useful.

    An activity is considered noise if:
      - The name is nearly identical to the entire report (model just
        echoed the input — Test 9 class).
      - The name contains no domain-relevant words (fewer than 2 words
        from a minimum meaningful vocabulary).
    """
    name_norm = name.strip().lower()
    report_norm = report_text.strip().lower()

    # Activity is the whole report ± a few chars → noise
    if len(name_norm) > 0 and (
        name_norm in report_norm and len(name_norm) / len(report_norm) > 0.75
    ):
        return True

    # Fewer than 2 meaningful words (> 3 chars)
    words = [w for w in name_norm.split() if len(w) > 3]
    if len(words) < 2:
        return True

    return False


def _rescue_pending_tasks(
    activities: list[dict],
    issues: list[str],
    report_text: str,
    known_locations: list[str],
) -> tuple[list[dict], list[str]]:
    """
    Rescue pending construction tasks that the LLM incorrectly placed in
    the issues list instead of extracting them as activities.

    An issue string is eligible for rescue when it contains BOTH:
      a) a specific construction task/work-operation keyword, AND
      b) a pending-state expression ("not started", "pending", "not yet begun", etc.)

    AND does NOT contain a blocker-only pattern (permit, approval, permission)
    that would make it a legitimate issue even though it contains "pending".

    Example of correct rescue:
      issue "Earthing and grounding work has not started yet"
      → removed from issues
      → added as activity {"activity": "Earthing and grounding work",
                           "status": "pending", ...}

    Example of correct non-rescue:
      issue "Permit approval still pending"
      → kept in issues (contains "approval" blocker keyword)

    Duplicate guard: if an activity with the same normalised name already
    exists in the activities list, the issue is simply removed without
    adding a duplicate activity.
    """
    # --- Detection regexes ---

    # Construction task / work-operation keywords
    _TASK_KW = re.compile(
        r"\b(excavat|weld|install|lay|laying|pour|erect|fabricat|mount|pull|"
        r"trench|bore|ground|earth|cable|conduit|pipe|slab|foundation|"
        r"concrete|structural|panel|switchgear|transformer|valve|scaffold|"
        r"commission|terminat|wire|reinstat)\w*\b",
        re.IGNORECASE,
    )

    # Pending-state expressions — ordered longest-first so compound phrases
    # like "is still pending" match before the bare "\bpending\b" does
    _PENDING_STATE = re.compile(
        r"\b(?:is\s+still\s+pending|still\s+pending|is\s+pending|"
        r"not\s+started(?:\s+yet)?|not\s+yet\s+started|hasn['']?t\s+started|"
        r"has\s+not\s+started|have\s+not\s+started|yet\s+to\s+start|"
        r"awaiting\s+execution|scheduled\s+for\s+later|"
        r"yet\s+to\s+begin|not\s+commenced|not\s+begun|not\s+yet\s+begun|"
        r"yet\s+to\s+be\s+started|has\s+yet\s+to|"
        r"\bpending\b)\b",
        re.IGNORECASE,
    )

    # Blocker-only patterns — keep these as issues even if they contain "pending"
    _BLOCKER_ONLY = re.compile(
        r"\b(permit|approval|permission|sign[\s\-]?off|authoris|authoriz|"
        r"inspection\s+approval|regulatory|license|licence)\b",
        re.IGNORECASE,
    )

    def _is_rescuable(issue_str: str) -> bool:
        # If the string contains a separator (— , ; :), check only the FIRST
        # segment for task + pending keywords. The second segment may describe
        # a blocker (e.g. "waiting for contractor approval") and should stay
        # as an issue — but the task part should still be rescued as an activity.
        # We therefore check task+pending on the whole string, and apply the
        # blocker-only guard only when the ENTIRE string is a blocker with no
        # task content.
        has_task = bool(_TASK_KW.search(issue_str))
        has_pending = bool(_PENDING_STATE.search(issue_str))
        # Only suppress rescue if blocker keywords appear WITHOUT any task keyword
        # (i.e. it's purely an administrative/approval issue, not a task + blocker)
        pure_blocker = bool(_BLOCKER_ONLY.search(issue_str)) and not has_task
        return has_task and has_pending and not pure_blocker

    def _existing_names(acts: list[dict]) -> set[str]:
        return {a["activity"].strip().lower() for a in acts}

    # Resolve location and date once for the whole report (same logic as
    # _postprocess uses for each activity).
    report_location = _scan_report_for_location(report_text, known_locations)
    resolved_date = _resolve_date(report_text, None)

    surviving_issues: list[str] = []

    for issue in issues:
        if not _is_rescuable(issue):
            surviving_issues.append(issue)
            continue

        # Strip the pending-state phrase to get a cleaner activity name.
        # Also handle compound strings like:
        #   "Road crossing bore is still pending — waiting for contractor approval"
        # Split on separator (— , ;) to isolate the task clause from any
        # blocker clause that follows. The blocker clause is re-added as a
        # separate issue so it is not lost.
        _SEPARATOR_RE = re.compile(r"\s*[—–]\s*|\s*;\s*")
        parts = _SEPARATOR_RE.split(issue, maxsplit=1)
        task_part = parts[0].strip()
        blocker_part = parts[1].strip() if len(parts) > 1 else ""

        # Remove pending-state phrase from the task part only.
        # _PENDING_STATE now matches compound forms like "is still pending",
        # "still pending", "is pending" in a single substitution, so one
        # cleanup pass is sufficient.
        raw_name = _PENDING_STATE.sub("", task_part).strip(" .,;:-—")
        _TRAILING_FILLER = re.compile(
            r"\s+(still|yet|now|is|was|are|has|have|also)\s*$", re.IGNORECASE
        )
        _LEADING_FILLER = re.compile(
            r"^\s*(still|yet|now|also|and|but|is|was|are)\s+", re.IGNORECASE
        )
        raw_name = _TRAILING_FILLER.sub("", raw_name).strip(" .,;:-—")
        raw_name = _LEADING_FILLER.sub("", raw_name).strip(" .,;:-—")
        name = _clean_activity_name(raw_name) if raw_name else issue

        # Duplicate guard
        if name.strip().lower() in _existing_names(activities):
            logger.debug(
                "Pending-task rescue: duplicate activity %r already exists, "
                "issue dropped.",
                name,
            )
            # Drop the issue; if there is a blocker clause, keep it as an issue
            if blocker_part:
                surviving_issues.append(blocker_part)
            continue

        # Resolve location: start from the full-report scan, then apply the
        # sentence-level gate to prevent cross-sentence location inheritance.
        # A rescued activity whose own sentence contains no location evidence
        # must receive null — even when the location appears elsewhere in the
        # report.
        candidate_location = (
            report_location
            if report_location is not None
            else _validate_location(None, known_locations, report_text)
        )
        if candidate_location is not None and not _location_in_activity_context(
            name, candidate_location, report_text, known_locations
        ):
            logger.debug(
                "Pending-task rescue: location %r not in activity sentence for %r "
                "— set to null.",
                candidate_location,
                name,
            )
            candidate_location = None
        final_location = candidate_location

        activities.append(
            {
                "activity": name,
                "location": final_location,
                "date": resolved_date,
                "status": "pending",
                "progress_percent": None,
            }
        )
        logger.debug(
            "Pending-task rescue: moved issue %r → activity %r (status=pending).",
            issue,
            name,
        )
        # Task clause consumed. If there is a blocker clause after the separator
        # (e.g. "waiting for contractor approval"), keep it as a separate issue.
        if blocker_part:
            surviving_issues.append(blocker_part)
        # Issue fully handled — do NOT add the original string to surviving_issues

    return activities, surviving_issues


def _location_in_activity_context(
    activity_name: str,
    resolved_location: str,
    report_text: str,
    known_locations: list[str],
) -> bool:
    """
    Final sentence-level gate: returns True only when the resolved location
    is explicitly present in the sentence that describes this specific activity.

    Why this is needed:
      The LLM can inherit a location from a neighbouring sentence (proximity
      inheritance).  The full-report evidence check confirms the location
      exists *somewhere* in the report, but cannot verify it belongs to *this*
      activity.  This function splits the report into sentences, finds the one
      most likely describing the activity by keyword overlap, then checks
      whether a known location is present in THAT sentence.

    Matching strategy:
      1. Split report_text on sentence boundaries (.  !  ?).
      2. For each sentence, count how many meaningful words (>3 chars) from
         the activity name appear in it.
      3. The sentence with the highest overlap score is the activity's sentence.
      4. Run _scan_report_for_location on that sentence alone.
      5. Return True only if the result equals resolved_location.

    If no sentence achieves a score ≥ 1, the function returns False (safe
    default — better to null the location than inherit a wrong one).
    """
    sentences = re.split(r"(?<=[.!?])\s+", report_text.strip())
    if not sentences:
        return False

    name_words = [w for w in activity_name.lower().split() if len(w) > 3]
    if not name_words:
        return False

    # Find the sentence with the most keyword overlap
    best_sent = None
    best_score = 0
    for sent in sentences:
        score = sum(1 for w in name_words if w in sent.lower())
        if score > best_score:
            best_score = score
            best_sent = sent

    # No sentence matched at all → conservative null
    if best_score < 1 or best_sent is None:
        return False

    # Check whether the resolved location is present in the activity's sentence
    loc_in_sentence = _scan_report_for_location(best_sent, known_locations)
    return loc_in_sentence == resolved_location


def _merge_duplicate_activities(activities: list[dict]) -> list[dict]:
    """
    Collapse duplicate activities that share the same normalised name AND
    the same resolved location into a single merged entry.

    Duplicates arise when a multi-sentence report mentions the same task
    twice — once with partial progress and once at completion.

    Merge rules (applied when two entries share the same key):
      - status:           "completed" > "delayed" > "in_progress" > "pending" > "unknown"
      - progress_percent: highest explicit value wins; 100 beats any lower number
      - location:         non-null beats null; both non-null must match (same key)
      - date:             non-null beats null; if both non-null, keep the later one
      - activity name:    keep as-is (already normalised by _clean_activity_name)

    Only merges when the key (name, location) is identical — no fuzzy matching.
    Activities with different names or different locations are always kept separate.
    """
    if len(activities) <= 1:
        return activities

    STATUS_RANK = {
        "completed": 5,
        "delayed": 4,
        "in_progress": 3,
        "pending": 2,
        "unknown": 1,
    }

    # Preserve insertion order; use (name_lower, location) as the merge key.
    seen: dict[tuple, dict] = {}
    order: list[tuple] = []

    for act in activities:
        name_key = act["activity"].strip().lower()
        loc_key = act["location"]  # already canonical or None
        key = (name_key, loc_key)

        if key not in seen:
            seen[key] = dict(act)  # first occurrence — copy
            order.append(key)
            continue

        # Merge into the existing entry
        existing = seen[key]

        # Status: keep the higher-ranked one
        if STATUS_RANK.get(act["status"], 0) > STATUS_RANK.get(existing["status"], 0):
            existing["status"] = act["status"]

        # progress_percent: keep the highest explicit value.
        # Additionally, if the merged status is "completed", force 100 —
        # a completed task is by definition 100% done regardless of any
        # partial progress value recorded earlier.
        ep = existing.get("progress_percent")
        ap = act.get("progress_percent")
        if ap is not None and (ep is None or ap > ep):
            existing["progress_percent"] = ap
        if existing["status"] == "completed":
            existing["progress_percent"] = 100

        # date: prefer non-null; if both non-null prefer the later date string
        ed = existing.get("date")
        ad = act.get("date")
        if ad and (not ed or ad > ed):
            existing["date"] = ad

        logger.debug(
            "Merged duplicate activity %r (location=%r): status=%r progress=%r",
            existing["activity"],
            existing["location"],
            existing["status"],
            existing["progress_percent"],
        )

    return [seen[k] for k in order]


# ---------------------------------------------------------------------------
# Vague-report rescue — fires only when the LLM returns zero activities
# ---------------------------------------------------------------------------

# Narrow keyword → canonical-activity map.
# Only entries where the keyword UNIQUELY and unambiguously identifies one
# specific construction task are included.  Broad terms like "pipeline",
# "cable", "pipe" are intentionally omitted to avoid false positives on
# tests 9/10/11 ("Work done today", "Some progress made on the pipeline").
_VAGUE_RESCUE_MAP: list[tuple[re.Pattern, str]] = [
    # "trench" / "trenches" → Trench excavation
    (re.compile(r"\btrenches?\b", re.IGNORECASE), "Trench excavation"),
]

# Progress expressions that imply in_progress (not completion)
_VAGUE_IN_PROGRESS_RE = re.compile(
    r"\b(some\s+progress|made\s+progress|making\s+progress|ongoing|"
    r"in\s+progress|underway|continuing|progressing)\b",
    re.IGNORECASE,
)

# Explicit completion expressions that imply completed
_VAGUE_COMPLETED_RE = re.compile(
    r"\b(completed?|finished?|all\s+done|fully\s+done|wrapped?\s+up)\b",
    re.IGNORECASE,
)


def _rescue_from_vague_report(
    activities: list[dict],
    report_text: str,
    known_locations: list[str],
    resolved_date: str,
) -> list[dict]:
    """
    Last-resort rescue: when the LLM returns zero activities but the report
    contains a keyword that unambiguously identifies a canonical construction
    task, inject that activity deterministically.

    Rules:
      - Only fires when activities == [].
      - Uses a deliberately narrow keyword map (_VAGUE_RESCUE_MAP) to avoid
        false positives on legitimately vague reports (tests 9, 10, 11).
      - location is always null — no evidence in a vague report.
      - progress_percent is always null — no explicit percentage stated.
      - status is inferred from the report text; defaults to "in_progress".
    """
    if activities:
        return activities

    for pattern, canonical_name in _VAGUE_RESCUE_MAP:
        if pattern.search(report_text):
            if _VAGUE_COMPLETED_RE.search(report_text):
                status = "completed"
            else:
                # "made some progress", "ongoing", or any other phrasing
                # implies work has started → in_progress
                status = "in_progress"

            logger.debug(
                "Vague-report rescue: keyword matched → activity=%r status=%r",
                canonical_name,
                status,
            )
            return [
                {
                    "activity": canonical_name,
                    "location": None,
                    "date": resolved_date,
                    "status": status,
                    "progress_percent": None,
                }
            ]

    return activities


def _postprocess(
    raw_result: dict,
    report_text: str,
    known_locations: list[str],
) -> dict:
    """
    Apply all deterministic post-processing rules to the raw LLM output.

    Location resolution precedence (per activity):
      1. Deterministic scan of raw report text via _scan_report_for_location
         (aliases + verbatim canonical strings).  If a match is found here,
         it is used unconditionally — the LLM's guess is discarded.
      2. If the scan returns None, fall back to _validate_location which
         checks the LLM's returned location against the known list AND
         requires textual evidence in the report.
      3. If both return None → location = null.

    Other rules applied per activity:
      - Strip verb prefix from activity name.
      - Discard noise/echo activities.
      - Validate status (past-tense override for pending).
      - Validate progress_percent (reject misread quantities).
      - Resolve date (relative → absolute → today default).

    Internal corrections (location nulled, activity discarded, etc.) are
    logged at DEBUG level.  They are NEVER added to the user-facing issues
    list — that list contains only construction/project issues from the report.
    """
    activities = []
    issues = list(raw_result.get("issues", []))

    VALID_STATUSES = {"completed", "in_progress", "pending", "delayed", "unknown"}

    for item in raw_result.get("activities", []):
        if not isinstance(item, dict):
            continue

        # ---- activity name ----
        raw_name = (item.get("activity") or "").strip()
        if not raw_name:
            logger.debug("Skipped activity with empty name.")
            continue

        name = _clean_activity_name(raw_name)

        # Discard noise
        if _is_noise_activity(name, report_text):
            logger.debug("Discarded low-information activity: %r", raw_name)
            continue

        # ---- location — per-activity resolution (three-tier) ----
        #
        # IMPORTANT: location is resolved per-activity, NOT globally.
        # Using a single scan of the full report text and stamping it on every
        # activity causes location leakage in multi-activity reports where each
        # sentence mentions a different zone.
        #
        # Tier 1: canonicalise the LLM's own location guess via the alias map.
        #   The LLM already extracted the correct per-activity location string
        #   (e.g. "Zone A", "Zone C substation"). Run _scan_report_for_location
        #   on THAT string (not the full report) to map it to a canonical DB value.
        #   This preserves per-activity accuracy while still normalising aliases.
        #
        # Tier 2: if Tier 1 returns None, use the full evidence-gated validator
        #   which checks the LLM's string against known locations AND requires
        #   textual evidence in the report.
        #
        # Tier 3: null — no guessing.

        model_loc = (item.get("location") or "").strip() or None
        final_location = None

        if model_loc:
            # Tier 1: treat the model's location string as a mini-report and
            # run the alias scan against it — this maps "Zone A" → canonical,
            # "Zone C substation" → canonical, etc., without touching other
            # activities' locations.
            # Evidence gate: also require the matched token to appear in the
            # actual report text, so a hallucinated canonical string like
            # "Zone B - Pipeline Corridor" on a vague report is rejected.
            candidate = _scan_report_for_location(model_loc, known_locations)
            if candidate is not None:
                # Verify the alias/token that produced this match is also in
                # the report text (reuse _validate_location's evidence logic).
                final_location = _validate_location(
                    model_loc, known_locations, report_text
                )
                if final_location is None:
                    # Alias matched but no evidence in report text → null
                    logger.debug(
                        "Location %r alias-matched to %r but no evidence in report — set to null.",
                        model_loc,
                        candidate,
                    )

            if final_location is None:
                # Tier 2: evidence-gated validation against the full report text
                final_location = _validate_location(
                    model_loc, known_locations, report_text
                )
                if final_location is None:
                    logger.debug(
                        "Location %r from model not supported by report text — set to null.",
                        model_loc,
                    )

        # ---- sentence-level location gate ----
        # If a location was resolved above, verify it actually appears in the
        # sentence that describes THIS activity (not just somewhere in the report).
        # This prevents cross-sentence location inheritance in multi-activity reports.
        if final_location is not None:
            if not _location_in_activity_context(
                name, final_location, report_text, known_locations
            ):
                logger.debug(
                    "Location %r not in activity sentence for %r — set to null.",
                    final_location,
                    name,
                )
                final_location = None

        # ---- status ----
        raw_status = item.get("status", "unknown")
        if raw_status not in VALID_STATUSES:
            raw_status = "unknown"
        status = _validate_status(raw_status, report_text)

        # Pending-status override: if the activity's own sentence contains
        # an explicit "not started" phrase, force status to "pending"
        # regardless of what the LLM returned.
        # This catches cases where the LLM returns "in_progress" for phrases
        # like "has not started yet" — the LLM misreads the sentence as
        # describing ongoing work rather than work that hasn't begun.
        # Only applies when the current status is NOT already a definitive
        # completed/delayed — those take precedence.
        _NOT_STARTED_RE = re.compile(
            r"\b(not\s+started(?:\s+yet)?|not\s+yet\s+started|"
            r"hasn['']?t\s+started|has\s+not\s+started|"
            r"yet\s+to\s+start|yet\s+to\s+begin|not\s+commenced|"
            r"not\s+begun)\b",
            re.IGNORECASE,
        )
        if status not in ("completed", "delayed") and _NOT_STARTED_RE.search(
            report_text
        ):
            # Narrow check: only override if the phrase appears in the
            # activity's own sentence, not a neighbouring sentence
            if _location_in_activity_context.__module__:  # guard: helper available
                sentences = re.split(r"(?<=[.!?])\s+", report_text.strip())
                name_words = [w for w in name.lower().split() if len(w) > 3]
                best_sent, best_score = None, 0
                for sent in sentences:
                    score = sum(1 for w in name_words if w in sent.lower())
                    if score > best_score:
                        best_score, best_sent = score, sent
                if best_score >= 1 and best_sent and _NOT_STARTED_RE.search(best_sent):
                    logger.debug(
                        "Forcing status=pending for %r — 'not started' in activity sentence.",
                        name,
                    )
                    status = "pending"

        # ---- progress_percent ----
        progress_percent = _validate_progress(
            item.get("progress_percent"),
            report_text,
            name,
        )

        # ---- date ----
        resolved_date = _resolve_date(report_text, item.get("date"))

        activities.append(
            {
                "activity": name,
                "location": final_location,
                "date": resolved_date,
                "status": status,
                "progress_percent": progress_percent,
            }
        )

    # Clean issues — remove empty strings and model meta-commentary only.
    # Internal post-processing warnings are logged, not added here.
    META_COMMENTARY_RE = re.compile(
        r"not enough information|cannot determine|unable to determine|"
        r"details to follow|no (further )?details",
        re.IGNORECASE,
    )
    cleaned_issues = [i for i in issues if i and not META_COMMENTARY_RE.search(i)]

    # Rescue any pending construction tasks the LLM accidentally placed in
    # the issues list instead of extracting them as activities.
    activities, cleaned_issues = _rescue_pending_tasks(
        activities, cleaned_issues, report_text, known_locations
    )

    # Merge duplicate activities that share the same normalised name and
    # resolved location (can arise from multi-sentence reports where the
    # same task is mentioned twice with different progress states).
    activities = _merge_duplicate_activities(activities)

    # Last-resort: when the LLM returned nothing but the report contains an
    # unambiguous domain keyword, rescue the canonical activity name.
    # This handles vague reports like "made some progress on the trenches"
    # where the LLM's specificity rule suppressed extraction.
    activities = _rescue_from_vague_report(
        activities,
        report_text,
        known_locations,
        _resolve_date(report_text, None),
    )

    return {"activities": activities, "issues": cleaned_issues}


# ---------------------------------------------------------------------------
# Location loader — fetches distinct locations from schedule_items
# ---------------------------------------------------------------------------


def load_known_locations() -> list[str]:
    """
    Load the distinct location values from schedule_items in project.db.

    Called once per /extract request so the model always works against
    the real current schedule, not a hardcoded list.

    Returns an empty list on any DB error (safe — post-processor will then
    null-out all locations rather than guess).
    """
    try:
        from database import get_db

        with get_db() as conn:
            rows = conn.execute(
                "SELECT DISTINCT location FROM schedule_items "
                "WHERE location IS NOT NULL ORDER BY location"
            ).fetchall()
        return [row["location"] for row in rows]
    except Exception as exc:
        logger.warning("Could not load known locations from DB: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def extract_report(report_text: str, known_locations: list[str] | None = None) -> dict:
    """Send a field report to Ollama (llama3.2:3b) and return structured data.

    Args:
        report_text:      Raw plain-language text from a field supervisor.
        known_locations:  Optional list of valid location strings fetched from
                          schedule_items.  If None, loaded automatically from DB.

    Returns:
        A dict matching the ExtractResponse schema:
        {
            "activities": [
                {
                    "activity":         str,
                    "location":         str | None,
                    "date":             str,          # ISO date, always present
                    "status":           str,
                    "progress_percent": int | None,
                }
            ],
            "issues": [str, ...]
        }

    Raises:
        Nothing — all exceptions are caught and surfaced as issues.
    """
    if not report_text or not report_text.strip():
        return {"activities": [], "issues": ["Report text was empty."]}

    # Load known locations if not provided (normal production path)
    if known_locations is None:
        known_locations = load_known_locations()

    system_prompt = _build_system_prompt(known_locations)

    try:
        response = ollama.chat(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": report_text},
            ],
            options={"temperature": 0},
        )

        raw_text = response.message.content.strip()

        # Strip markdown code fences if the model wraps the JSON in them
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            raw_text = "\n".join(lines[1:-1]).strip()

        parsed = json.loads(raw_text)

    except ResponseError as exc:
        logger.error("Ollama model error: %s", exc)
        return {
            "activities": [],
            "issues": [
                f"Extraction failed: Ollama model error — {exc}. "
                f"Make sure '{_MODEL}' is available (run: ollama pull {_MODEL})."
            ],
        }

    except ConnectionError as exc:
        logger.error("Could not connect to Ollama: %s", exc)
        return {
            "activities": [],
            "issues": [
                f"Extraction failed: cannot connect to Ollama at {_OLLAMA_HOST}. "
                "Make sure Ollama is running (run: ollama serve)."
            ],
        }

    except json.JSONDecodeError as exc:
        logger.warning("Ollama returned non-JSON response: %s", exc)
        return {
            "activities": [],
            "issues": [
                f"Extraction failed: model returned an unreadable response ({exc})."
            ],
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during extraction: %s", exc)
        return {
            "activities": [],
            "issues": [f"Extraction failed: {type(exc).__name__}: {exc}"],
        }

    # Apply deterministic post-processing
    return _postprocess(parsed, report_text, known_locations)
