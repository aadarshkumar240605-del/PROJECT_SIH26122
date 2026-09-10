"""
parse_primavera.py
------------------
Task 4: Primavera Excel Parser Utility

Reads the synthetic Primavera schedule Excel file and converts it into
clean Python structures for the rest of the system:

    parse_schedule(filepath)   -> list[dict]   (one dict per activity)
    print_summary(activities)  -> None         (prints counts + skipped rows)
    get_activity_names(activities) -> (names, ids)  (parallel lists for
                                     the matching engine's embedding index)

Output contract (DO NOT CHANGE — match_engine.py depends on it):
    [
        {
            "activity_id":   "L5-CIVIL-2847",
            "activity_name": "Concrete placement column foundations Unit 7",
            "discipline":    "Civil",
            "planned_start": "2026-09-01",
            "planned_end":   "2026-09-03",
            "wbs_level":     "L5"
        },
        ...
    ]

Notes on the Excel layout:
    Rows 1-2 are title/legend.  The header row position can vary between
    exports (the current file has headers in spreadsheet row 3; the Task 4
    spec mentions row 4).  Rather than hardcoding either, this parser
    AUTO-DETECTS the header row by scanning the first few rows for the
    six required column names, so both layouts parse identically.

Author: SIH 2026 — Fuzzy Matching & System Integration Team
"""

import sys
from datetime import datetime, date

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# The exact column names as agreed with the team. Order matters only for
# the output dicts; the Excel may list them in any order.
REQUIRED_COLUMNS = [
    "activity_id",
    "activity_name",
    "discipline",
    "planned_start",
    "planned_end",
    "wbs_level",
]

# How many top rows to scan when auto-detecting the header row.
HEADER_SCAN_ROWS = 10

# Default file used by the __main__ block. The real schedule currently
# lives next to this script in backend/ (not ./data/).
DEFAULT_SCHEDULE_PATH = "primavera_schedule.xlsx"

# Module-level log of skipped rows from the most recent parse_schedule
# call.  parse_schedule's return value is a locked contract (list of
# dicts only), so skip details are surfaced here and by print_summary().
PARSE_LOG: list[str] = []


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _to_iso_date(value) -> str | None:
    """
    Convert an Excel date cell to a 'YYYY-MM-DD' string.

    Excel exports are inconsistent: the same column may contain real
    datetime/date objects, pandas Timestamps, or plain strings like
    '2026-09-01' or '01-09-2026'.  This handles all of them:

        datetime/date/Timestamp  -> .strftime('%Y-%m-%d')
        'YYYY-MM-DD' string      -> returned as-is (after strip)
        other parseable strings  -> parsed via pd.to_datetime, reformatted
        anything else            -> None (caller decides whether to skip)

    Returns None for empty/NaN values and for values that cannot be
    parsed as a date.
    """
    # Empty cell / NaN -> no date
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass  # non-numeric, non-NA-able value — keep processing below

    # Real date/datetime objects (includes pandas Timestamp)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime("%Y-%m-%d")

    # Strings — trim, fast-path ISO format, otherwise try parsing
    text = str(value).strip()
    if not text:
        return None
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _clean_str(value) -> str:
    """
    Coerce a cell to a stripped string ('' for empty/NaN).
    Used for the non-date text columns.
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _find_header_row(filepath: str) -> int | None:
    """
    Scan the first HEADER_SCAN_ROWS rows of the Excel file and return the
    0-indexed row that contains all six required column names, or None
    if not found.

    Why: different Primavera exports place the header row at different
    positions (row 3 in the current file).  Auto-detection means this
    parser never silently eats a data row or mis-labels columns.
    """
    probe = pd.read_excel(filepath, header=None, nrows=HEADER_SCAN_ROWS, engine="openpyxl")
    required = set(REQUIRED_COLUMNS)
    for idx, row in probe.iterrows():
        cells = {str(c).strip().lower() for c in row if c is not None}
        if required.issubset(cells):
            return idx
    return None


# ---------------------------------------------------------------------------
# FUNCTION 1 — parse_schedule
# ---------------------------------------------------------------------------

def parse_schedule(filepath: str) -> list[dict]:
    """
    Read a Primavera schedule Excel file and return clean activity dicts.

    Input:
        filepath — path to the .xlsx file (absolute or relative).

    Returns:
        List of dicts with EXACTLY these keys (contract — do not change):
            activity_id, activity_name, discipline,
            planned_start, planned_end, wbs_level
        All string values are stripped of whitespace.  Dates are
        'YYYY-MM-DD' strings regardless of how Excel stored them.

    Behaviour:
        - Skips rows where activity_id or activity_name is empty,
          recording the reason in PARSE_LOG.
        - Skips rows with unparseable dates (date fields become None),
          recording the reason in PARSE_LOG — but keeps the row, because
          the matching engine only needs the activity name.
        - Never raises on bad cell values; bad cells are cleaned or the
          row is skipped with a logged reason.

    Error handling:
        - File not found  -> prints a clear error, returns [].
        - Missing columns -> prints WHICH column is missing, returns [].
        - Unreadable file -> prints the error, returns [].
    """
    global PARSE_LOG
    PARSE_LOG = []  # reset the skip log for this parse run

    # ---- file existence -------------------------------------------------
    try:
        open(filepath).close()
    except FileNotFoundError:
        print(f"[parse_primavera] ERROR: File not found: '{filepath}'")
        print("                   Check the path and try again.")
        return []
    except PermissionError:
        print(f"[parse_primavera] ERROR: No permission to read '{filepath}'.")
        return []
    except OSError as exc:
        print(f"[parse_primavera] ERROR: Cannot open '{filepath}': {exc}")
        return []

    # ---- locate the header row (auto-detect, see module docstring) ------
    header_row = _find_header_row(filepath)
    if header_row is None:
        print(
            "[parse_primavera] ERROR: Could not find a header row containing "
            f"all required columns {REQUIRED_COLUMNS} in the first "
            f"{HEADER_SCAN_ROWS} rows of '{filepath}'."
        )
        return []

    # ---- read with the detected header ----------------------------------
    try:
        df = pd.read_excel(filepath, header=header_row, engine="openpyxl")
    except ValueError as exc:
        print(f"[parse_primavera] ERROR: Could not parse '{filepath}': {exc}")
        return []

    df.columns = [str(c).strip() for c in df.columns]

    # ---- validate required columns ---------------------------------------
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        print("[parse_primavera] ERROR: Missing required column(s) in Excel: "
              f"{missing}")
        print(f"                   Found columns: {list(df.columns)}")
        return []

    # ---- row-by-row conversion -------------------------------------------
    activities: list[dict] = []

    for pos, row in df.iterrows():
        excel_row = pos + header_row + 2  # 1-indexed sheet row (for messages)

        activity_id   = _clean_str(row["activity_id"])
        activity_name = _clean_str(row["activity_name"])

        # Skip rows with no identity — they are blank separators or corrupt
        if not activity_id or not activity_name:
            PARSE_LOG.append(
                f"Skipped sheet row {excel_row}: missing "
                f"{'activity_id' if not activity_id else 'activity_name'}."
            )
            continue

        planned_start = _to_iso_date(row["planned_start"])
        planned_end   = _to_iso_date(row["planned_end"])
        if (row["planned_start"] is not None and planned_start is None) or \
           (row["planned_end"] is not None and planned_end is None):
            PARSE_LOG.append(
                f"Skipped sheet row {excel_row}: unparseable date "
                f"(planned_start={row['planned_start']!r}, "
                f"planned_end={row['planned_end']!r}) — dates set to None."
            )

        activities.append({
            "activity_id":   activity_id,
            "activity_name": activity_name,
            "discipline":    _clean_str(row["discipline"]),
            "planned_start": planned_start,
            "planned_end":   planned_end,
            "wbs_level":     _clean_str(row["wbs_level"]),
        })

    return activities


# ---------------------------------------------------------------------------
# FUNCTION 2 — print_summary
# ---------------------------------------------------------------------------

def print_summary(activities: list[dict]) -> None:
    """
    Print a human-readable summary of a parse_schedule() result.

    Input:
        activities — the list returned by parse_schedule().

    Output (printed to stdout, returns None):
        - total activities loaded
        - count per discipline
        - count of L5 vs L6 (wbs_level) activities
        - any rows skipped during parsing and why (from PARSE_LOG)
    """
    print("=" * 70)
    print("PRIMAVERA SCHEDULE PARSE SUMMARY")
    print("=" * 70)

    if not activities:
        print("No activities loaded.")
        _print_skip_log()
        return

    # Total
    print(f"\nTotal activities loaded : {len(activities)}")

    # Per discipline
    print("\nBy discipline:")
    discipline_counts: dict[str, int] = {}
    for act in activities:
        d = act["discipline"] or "(unknown)"
        discipline_counts[d] = discipline_counts.get(d, 0) + 1
    for disc, count in sorted(discipline_counts.items()):
        print(f"  {disc:<18} {count}")

    # Per WBS level
    print("\nBy WBS level:")
    level_counts: dict[str, int] = {}
    for act in activities:
        lvl = act["wbs_level"] or "(unknown)"
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
    for lvl, count in sorted(level_counts.items()):
        print(f"  {lvl:<18} {count}")

    _print_skip_log()


def _print_skip_log() -> None:
    """Print the skipped-row log from the most recent parse, if any."""
    if PARSE_LOG:
        print(f"\nRows skipped during parse ({len(PARSE_LOG)}):")
        for entry in PARSE_LOG:
            print(f"  - {entry}")
    else:
        print("\nRows skipped during parse: none.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# FUNCTION 3 — get_activity_names
# ---------------------------------------------------------------------------

def get_activity_names(activities: list[dict]) -> tuple[list[str], list[str]]:
    """
    Extract parallel (names, ids) lists for the matching engine.

    Input:
        activities — the list returned by parse_schedule().

    Returns:
        (activity_names, activity_ids) — two lists of EQUAL LENGTH where
        activity_names[i] corresponds to activity_ids[i].  Order follows
        the input list exactly, so these feed straight into
        match_engine's model.encode(activity_names) with no
        transformation.

    Example:
        names, ids = get_activity_names(parse_schedule("schedule.xlsx"))
        # names[0] -> "Topographic survey and setting out Unit 5"
        # ids[0]   -> "L5-CIVIL-2801"
    """
    activity_ids:   list[str] = []
    activity_names: list[str] = []

    for act in activities:
        activity_names.append(act["activity_name"])
        activity_ids.append(act["activity_id"])

    return activity_names, activity_ids


# ---------------------------------------------------------------------------
# MAIN BLOCK — quick self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[parse_primavera] Parsing: {DEFAULT_SCHEDULE_PATH}\n")

    activities = parse_schedule(DEFAULT_SCHEDULE_PATH)

    if activities:
        print_summary(activities)

        names, ids = get_activity_names(activities)
        print("\nFirst 5 activities (name <-> id pairing check):")
        for name, act_id in list(zip(names, ids))[:5]:
            print(f"  {act_id:<18} {name}")

        # Contract sanity check: parallel lists must be equal length
        assert len(names) == len(ids), "name/id lists out of sync!"
        print(f"\nOK — {len(names)} names and {len(ids)} ids, order preserved.")
    else:
        print("[parse_primavera] No activities parsed — see errors above.")
        sys.exit(1)
