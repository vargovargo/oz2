"""
Fetch CDFI Fund certified institution list → update state_cdfi_count in
state_metadata.yaml.

Source
------
CDFI Fund — Certified CDFI Institution List
  Landing: https://www.cdfifund.gov/programs-training/certification/cdfi
  Download (Excel, periodically updated):
    https://www.cdfifund.gov/sites/cdfi/files/documents/cdfi-certified-institutions-list.xlsx

Note: CDFI Fund servers block requests from cloud/datacenter IP ranges.
Running from a standard developer workstation or CI runner on a
residential/business ISP will succeed. If this script fails in your
environment, download the Excel manually and place it at:
  data/raw/cdfi-certified-institutions-list.xlsx
then re-run.

What "state_cdfi_count" means
------------------------------
Count of CDFIs with a principal place of business (POBA_STATE column) in the
state AND certification status of "Certified" (STATUS column). This is the
number the CDFI Fund's own state-filtered search would return. It represents
capital intermediaries headquartered in-state, not all CDFIs that could
theoretically operate there.

Output
------
Patches state_metadata.yaml in-place: sets state_cdfi_count for all 51
entries. Also writes data/cdfi_counts.json as a standalone lookup file for
use by scripts or frontend.

Column mapping
--------------
The CDFI Fund Excel has changed column names across versions. This script
accepts all known variants:
  CDFI name:   "CDFI Name", "Institution Name", "Org Name"
  State:       "POBA State", "POBA_STATE", "State", "Inst State"
  Status:      "CDFI Certification Status", "Status", "Certification Status"
"""

import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CDFI_URLS = [
    "https://www.cdfifund.gov/sites/cdfi/files/documents/cdfi-certified-institutions-list.xlsx",
    "https://www.cdfifund.gov/sites/cdfi/files/2024-12/cdfi-certified-institutions-list.xlsx",
    "https://www.cdfifund.gov/sites/cdfi/files/2025-01/cdfi-certified-institutions-list.xlsx",
    "https://www.cdfifund.gov/sites/cdfi/files/documents/cdfi_certification_list.xlsx",
]

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
LOCAL_CACHE = RAW_DIR / "cdfi-certified-institutions-list.xlsx"
YAML_PATH = Path(__file__).parent.parent / "state_metadata.yaml"
OUT_JSON = DATA_DIR / "cdfi_counts.json"

TIMEOUT = 60

# Known column name variants (matched case-insensitively)
NAME_COLS   = ["CDFI Name", "Institution Name", "Org Name", "Organization Name"]
STATE_COLS  = ["POBA State", "POBA_STATE", "State", "Inst State", "Institution State"]
STATUS_COLS = ["CDFI Certification Status", "Status", "Certification Status"]

# State name → 2-letter abbreviation (for normalizing state column)
STATE_NAME_TO_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN",
    "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
ABBREV_TO_SLUG = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "DC": "district-of-columbia", "FL": "florida", "GA": "georgia",
    "HI": "hawaii", "ID": "idaho", "IL": "illinois", "IN": "indiana",
    "IA": "iowa", "KS": "kansas", "KY": "kentucky", "LA": "louisiana",
    "ME": "maine", "MD": "maryland", "MA": "massachusetts", "MI": "michigan",
    "MN": "minnesota", "MS": "mississippi", "MO": "missouri", "MT": "montana",
    "NE": "nebraska", "NV": "nevada", "NH": "new-hampshire", "NJ": "new-jersey",
    "NM": "new-mexico", "NY": "new-york", "NC": "north-carolina",
    "ND": "north-dakota", "OH": "ohio", "OK": "oklahoma", "OR": "oregon",
    "PA": "pennsylvania", "RI": "rhode-island", "SC": "south-carolina",
    "SD": "south-dakota", "TN": "tennessee", "TX": "texas", "UT": "utah",
    "VT": "vermont", "VA": "virginia", "WA": "washington",
    "WV": "west-virginia", "WI": "wisconsin", "WY": "wyoming",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch(url: str) -> bytes:
    print(f"  Fetching {url} …")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.cdfifund.gov/programs-training/certification/cdfi",
    }
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"    {len(r.content):,} bytes")
    return r.content


def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """First matching column name (case-insensitive)."""
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def fetch_cdfi_list() -> bytes:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_CACHE.exists():
        print(f"Using cached file: {LOCAL_CACHE}")
        return LOCAL_CACHE.read_bytes()

    last_exc: Exception | None = None
    for url in CDFI_URLS:
        try:
            raw = _fetch(url)
            LOCAL_CACHE.write_bytes(raw)
            print(f"  Cached → {LOCAL_CACHE}")
            return raw
        except Exception as exc:
            print(f"    Failed ({exc.__class__.__name__}: {exc})")
            last_exc = exc

    raise RuntimeError(
        f"Could not download CDFI certified list. Last error: {last_exc}\n\n"
        "Manual download:\n"
        "  1. Visit https://www.cdfifund.gov/programs-training/certification/cdfi\n"
        "  2. Download the certified institution list (Excel).\n"
        f"  3. Save to: {LOCAL_CACHE}\n"
        "  4. Re-run this script."
    )


def parse_cdfi_list(raw: bytes) -> pd.DataFrame:
    """Parse Excel; return DataFrame with columns: abbrev (2-letter), count (int)."""
    xl = pd.ExcelFile(io.BytesIO(raw))
    print(f"  Sheets: {xl.sheet_names}")

    df = None
    for sheet in xl.sheet_names:
        candidate = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, dtype=str)
        candidate.columns = [str(c).strip() for c in candidate.columns]
        state_col = _col(candidate, STATE_COLS)
        if state_col and len(candidate) >= 100:
            df = candidate
            print(f"  Using sheet '{sheet}' ({len(df):,} rows)")
            break

    if df is None:
        df = pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]

    state_col  = _col(df, STATE_COLS)
    status_col = _col(df, STATUS_COLS)

    if state_col is None:
        raise ValueError(f"No state column found. Columns: {df.columns.tolist()}")

    print(f"  State column:  '{state_col}'")
    print(f"  Status column: '{status_col}' (None = no filter applied)")

    # Filter to Certified only when status column exists
    if status_col:
        before = len(df)
        df = df[df[status_col].str.strip().str.lower() == "certified"].copy()
        print(f"  After certified filter: {len(df):,} of {before:,} rows")
    else:
        print(f"  No status column; counting all {len(df):,} rows")

    # Normalize state values to 2-letter abbreviations
    raw_states = df[state_col].str.strip().str.upper()

    # If values look like full state names, map them
    sample = df[state_col].dropna().head(10).tolist()
    if any(len(str(s)) > 3 for s in sample):
        # Likely full names — map via lookup (title-case the input)
        reverse = {v: k for k, v in STATE_NAME_TO_ABBREV.items()}
        normalized = []
        for s in df[state_col]:
            s = str(s).strip()
            abbrev = s.upper() if len(s) == 2 else STATE_NAME_TO_ABBREV.get(s.title(), s.upper())
            normalized.append(abbrev)
        raw_states = pd.Series(normalized)

    counts = (
        raw_states
        .value_counts()
        .rename_axis("abbrev")
        .reset_index(name="count")
    )
    # Keep only valid 2-letter state abbreviations in our target set
    counts = counts[counts["abbrev"].isin(ABBREV_TO_SLUG)].copy()
    print(f"  States with CDFIs: {len(counts)}")
    return counts


# ---------------------------------------------------------------------------
# YAML patch
# ---------------------------------------------------------------------------

def patch_yaml(counts_by_abbrev: dict[str, int]) -> None:
    """
    Update state_cdfi_count in state_metadata.yaml in-place.
    Replaces 'state_cdfi_count: null' or existing integer values.
    Does not reformat any other YAML content.
    """
    text = YAML_PATH.read_text()
    lines = text.splitlines(keepends=True)

    current_slug: str | None = None
    updated = 0

    # Build abbrev→slug reverse map using ABBREV_TO_SLUG
    slug_to_abbrev = {v: k for k, v in ABBREV_TO_SLUG.items()}

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Top-level state key
        if stripped.endswith(":") and not line.startswith(" "):
            key = stripped[:-1]
            current_slug = key if key in slug_to_abbrev else None

        if current_slug and re.match(r"^\s+state_cdfi_count:", line):
            abbrev = slug_to_abbrev[current_slug]
            count = counts_by_abbrev.get(abbrev, 0)
            indent = len(line) - len(line.lstrip())
            lines[i] = " " * indent + f"state_cdfi_count: {count}\n"
            updated += 1

    YAML_PATH.write_text("".join(lines))
    print(f"\nPatched {updated} state_cdfi_count fields in state_metadata.yaml")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching CDFI Fund certified institution list …")
    try:
        raw = fetch_cdfi_list()
    except RuntimeError as exc:
        sys.exit(f"\nFATAL: {exc}")

    print("\nParsing …")
    counts_df = parse_cdfi_list(raw)

    counts_by_abbrev = dict(zip(counts_df["abbrev"], counts_df["count"].astype(int)))

    # Summary
    print(f"\n--- CDFI Count Summary ---")
    total = sum(counts_by_abbrev.values())
    print(f"  Total certified CDFIs across 51 jurisdictions: {total:,}")
    top10 = sorted(counts_by_abbrev.items(), key=lambda x: -x[1])[:10]
    print("  Top 10 states by CDFI count:")
    for abbrev, n in top10:
        slug = ABBREV_TO_SLUG[abbrev]
        print(f"    {abbrev}  {n:>4}  ({slug})")

    # Write JSON
    out = {
        "fetched_at": date.today().isoformat(),
        "source": "CDFI Fund certified institution list",
        "counts": counts_by_abbrev,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"\nSaved → {OUT_JSON}")

    # Patch YAML
    patch_yaml(counts_by_abbrev)
    print("Done.")


if __name__ == "__main__":
    main()
