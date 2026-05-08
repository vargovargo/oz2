"""
Process CDFI NMTC project data → data/cdfi_nmtc.parquet + state_cdfi_count in YAML.

Primary source (local file)
----------------------------
CDFI Fund — NMTC Public Data Release (2024)
  File: data/raw/cdfi_nmtc2024.xlsx
  Sheet: "Projects 2 - Data Set PUBLISH.P"
  Columns used:
    2020 Census Tract  — 10-digit GEOID (zero-pad to 11 for join)
    State              — full state name (e.g., "Alaska")
    Community Development Entity (CDE) Name — the financing CDFI
    QLICI Amount       — total Qualified Low-Income Community Investment ($)
    Origination Year   — year of investment

Fallback source (original certified-institution list)
-------------------------------------------------------
CDFI Fund — Certified CDFI Institution List
  URL: https://www.cdfifund.gov/sites/cdfi/files/documents/cdfi-certified-institutions-list.xlsx
  Local: data/raw/cdfi-certified-institutions-list.xlsx
  In this mode: state_cdfi_count = # certified CDFIs with POBA in-state.
  No cdfi_nmtc.parquet is produced.

What state_cdfi_count means (NMTC mode)
-----------------------------------------
Number of distinct CDEs (Community Development Entities) that have made
at least one NMTC investment in a census tract that is eligible under IRS
Rev. Proc. 2026-14. This indicates how many CDFIs have prior capital-
deployment track record in OZ-eligible tracts in the state.

Output files
------------
  data/cdfi_nmtc.parquet  — one row per NMTC project in an eligible OZ tract:
      geoid, state_fips, cde_name, qlici_amount, origination_year, fetched_at

  data/cdfi_counts.json   — {state_abbrev: cde_count} lookup

  state_metadata.yaml     — state_cdfi_count patched in-place for all 51 states
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

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

# NMTC project data — tract-level join for overlay parquet
LOCAL_NMTC = RAW_DIR / "cdfi_nmtc2024.xlsx"

# Certified institution list — any matching filename in data/raw/
# Detects manually downloaded files like CDFI_Cert_List_Manual_*.xlsx
_CERT_GLOBS = ["CDFI_Cert_List*.xlsx", "cdfi-certified-institutions-list.xlsx",
               "cdfi_certification_list.xlsx"]
LOCAL_CERT = next(
    (p for g in _CERT_GLOBS for p in sorted(RAW_DIR.glob(g)) if p.exists()),
    RAW_DIR / "cdfi-certified-institutions-list.xlsx",  # fallback path (may not exist)
)
CDFI_URLS = [
    "https://www.cdfifund.gov/sites/cdfi/files/documents/cdfi-certified-institutions-list.xlsx",
    "https://www.cdfifund.gov/sites/cdfi/files/2024-12/cdfi-certified-institutions-list.xlsx",
    "https://www.cdfifund.gov/sites/cdfi/files/2025-01/cdfi-certified-institutions-list.xlsx",
]

ELIGIBLE_PARQUET = DATA_DIR / "eligible_tracts.parquet"
OUT_PARQUET = DATA_DIR / "cdfi_nmtc.parquet"
OUT_JSON = DATA_DIR / "cdfi_counts.json"
YAML_PATH = Path(__file__).parent.parent / "state_metadata.yaml"

TIMEOUT = 60

# Column name variants for the certified-list fallback
CERT_STATE_COLS  = ["POBA State", "POBA_STATE", "State", "Inst State", "Institution State"]
CERT_STATUS_COLS = ["CDFI Certification Status", "Status", "Certification Status"]

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

def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None


# ---------------------------------------------------------------------------
# NMTC path (primary)
# ---------------------------------------------------------------------------

def parse_nmtc(path: Path, eligible_geoids: set[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Parse NMTC project Excel. Join to eligible tracts. Return:
      - tract_df: one row per project in an eligible OZ tract
      - counts_by_abbrev: {state_abbrev: unique_cde_count}
    """
    xl = pd.ExcelFile(path)
    print(f"  Sheets: {xl.sheet_names}")

    # Find the projects sheet
    sheet = xl.sheet_names[0]
    for name in xl.sheet_names:
        if "project" in name.lower():
            sheet = name
            break

    df = xl.parse(sheet, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  Using sheet '{sheet}': {len(df):,} rows, {len(df.columns)} cols")

    # Locate columns
    tract_col = _col(df, ["2020 Census Tract", "Census Tract", "Tract GEOID", "GEOID"])
    state_col = _col(df, ["State", "state"])
    cde_col   = _col(df, ["Community Development Entity (CDE) Name", "CDE Name", "CDE"])
    amt_col   = _col(df, ["Project QLICI Amount", "QLICI Amount", "Amount", "Investment Amount"])
    year_col  = _col(df, ["Origination Year", "Year", "Fiscal Year"])

    if tract_col is None or state_col is None:
        raise ValueError(
            f"Cannot find required columns. Available: {df.columns.tolist()}"
        )

    print(f"  tract='{tract_col}'  state='{state_col}'  cde='{cde_col}'  "
          f"amount='{amt_col}'  year='{year_col}'")

    # Normalize GEOID to 11 digits
    df["geoid"] = (
        df[tract_col]
        .astype(str).str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(11)
    )

    # Normalize state to 2-letter abbreviation
    df["abbrev"] = df[state_col].astype(str).str.strip().apply(
        lambda s: STATE_NAME_TO_ABBREV.get(s.title(), s.upper()[:2])
    )

    # Inner join to eligible OZ tracts
    before = len(df)
    df = df[df["geoid"].isin(eligible_geoids)].copy()
    print(f"  Projects in eligible OZ tracts: {len(df):,} of {before:,} total")

    # Build output parquet columns
    out = pd.DataFrame()
    out["geoid"] = df["geoid"].values

    # state_fips from geoid (first 2 chars)
    out["state_fips"] = df["geoid"].str[:2].values

    out["cde_name"] = df[cde_col].astype(str).str.strip().values if cde_col else ""

    if amt_col:
        out["qlici_amount"] = pd.to_numeric(df[amt_col], errors="coerce")
    else:
        out["qlici_amount"] = float("nan")

    if year_col:
        out["origination_year"] = df[year_col].astype(str).str.strip().values
    else:
        out["origination_year"] = ""

    out["fetched_at"] = date.today().isoformat()

    # Counts: unique CDEs per state (among eligible-tract projects only)
    cde_col_out = "cde_name"
    counts_by_abbrev: dict[str, int] = {}
    if cde_col:
        for abbrev, grp in df.groupby("abbrev"):
            if abbrev in ABBREV_TO_SLUG:
                counts_by_abbrev[abbrev] = int(grp[cde_col].nunique())
    else:
        # Fall back to project count if CDE name unavailable
        for abbrev, grp in df.groupby("abbrev"):
            if abbrev in ABBREV_TO_SLUG:
                counts_by_abbrev[abbrev] = len(grp)

    print(f"  States with NMTC activity in eligible tracts: {len(counts_by_abbrev)}")
    return out.reset_index(drop=True), counts_by_abbrev


# ---------------------------------------------------------------------------
# Certified-list path (fallback)
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


def fetch_and_parse_cert_list() -> dict[str, int]:
    """Parse certified CDFI list; return {state_abbrev: count}."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_CERT.exists():
        print(f"Using certified list: {LOCAL_CERT}")
        raw = LOCAL_CERT.read_bytes()
    else:
        last_exc = None
        raw = None
        for url in CDFI_URLS:
            try:
                raw = _fetch(url)
                LOCAL_CERT.write_bytes(raw)
                break
            except Exception as exc:
                print(f"    Failed ({exc.__class__.__name__}: {exc})")
                last_exc = exc
        if raw is None:
            raise RuntimeError(
                f"Could not download CDFI certified list. Last error: {last_exc}\n\n"
                "Manual download:\n"
                "  1. Visit https://www.cdfifund.gov/programs-training/certification/cdfi\n"
                "  2. Download the certified institution list (Excel).\n"
                f"  3. Save to data/raw/ and re-run this script."
            )

    xl = pd.ExcelFile(io.BytesIO(raw))
    print(f"  Sheets: {xl.sheet_names}")

    # Fast path: look for a pre-aggregated by-state summary sheet
    for sheet in xl.sheet_names:
        if "state" in sheet.lower():
            candidate = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, dtype=str)
            candidate.columns = [str(c).strip() for c in candidate.columns]
            state_col = _col(candidate, ["States and Territories with Certified CDFI Headquarters",
                                         "State", "Abbrev", "Abbreviation"] + CERT_STATE_COLS)
            count_col = _col(candidate, ["Number of Certified CDFIs", "Count", "Total"])
            if state_col and count_col and len(candidate) >= 40:
                print(f"  Using pre-aggregated sheet '{sheet}' ({len(candidate)} rows)")
                result = {}
                for _, row in candidate.iterrows():
                    abbrev = str(row[state_col]).strip().upper()
                    if abbrev in ABBREV_TO_SLUG:
                        try:
                            result[abbrev] = int(float(str(row[count_col]).strip()))
                        except (ValueError, TypeError):
                            pass
                print(f"  Parsed {len(result)} state counts from summary sheet")
                return result

    # Slow path: count rows in the full institution list
    df = None
    for sheet in xl.sheet_names:
        candidate = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, dtype=str)
        candidate.columns = [str(c).strip() for c in candidate.columns]
        if _col(candidate, CERT_STATE_COLS) and len(candidate) >= 100:
            df = candidate
            print(f"  Using institution sheet '{sheet}' ({len(df):,} rows)")
            break
    if df is None:
        df = pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]

    state_col  = _col(df, CERT_STATE_COLS)
    status_col = _col(df, CERT_STATUS_COLS)

    if status_col:
        df = df[df[status_col].str.strip().str.lower() == "certified"].copy()

    sample = df[state_col].dropna().head(10).tolist()
    if any(len(str(s)) > 3 for s in sample):
        normalized = [
            STATE_NAME_TO_ABBREV.get(str(s).strip().title(), str(s).strip().upper()[:2])
            for s in df[state_col]
        ]
        states = pd.Series(normalized)
    else:
        states = df[state_col].str.strip().str.upper()

    counts = states.value_counts().to_dict()
    return {k: int(v) for k, v in counts.items() if k in ABBREV_TO_SLUG}


# ---------------------------------------------------------------------------
# YAML patch
# ---------------------------------------------------------------------------

def patch_yaml(counts_by_abbrev: dict[str, int]) -> None:
    text = YAML_PATH.read_text()
    lines = text.splitlines(keepends=True)

    slug_to_abbrev = {v: k for k, v in ABBREV_TO_SLUG.items()}
    current_slug: str | None = None
    updated = 0

    for i, line in enumerate(lines):
        stripped = line.rstrip()
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
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not ELIGIBLE_PARQUET.exists():
        sys.exit(f"ERROR: {ELIGIBLE_PARQUET} not found. Run ingest_irs_appendix.py first.")

    eligible = pd.read_parquet(ELIGIBLE_PARQUET, columns=["geoid"])
    eligible_geoids = set(eligible["geoid"].tolist())
    print(f"Eligible tracts loaded: {len(eligible_geoids):,}")

    # --- Step 1: Certified CDFI counts (state_cdfi_count in YAML) ---
    print("\n--- Certified CDFI list ---")
    try:
        cert_counts = fetch_and_parse_cert_list()
    except RuntimeError as exc:
        sys.exit(f"\nFATAL: {exc}")

    total_cert = sum(cert_counts.values())
    print(f"  Total certified CDFIs: {total_cert:,} across {len(cert_counts)} jurisdictions")
    top10 = sorted(cert_counts.items(), key=lambda x: -x[1])[:10]
    print("  Top 10 by certified CDFI count:")
    for abbrev, n in top10:
        print(f"    {abbrev}  {n:>4}")

    # --- Step 2: NMTC tract parquet (if available) ---
    tract_df = None
    if LOCAL_NMTC.exists():
        print(f"\n--- NMTC project data ---")
        tract_df, _ = parse_nmtc(LOCAL_NMTC, eligible_geoids)
        amt = tract_df["qlici_amount"].sum()
        print(f"  Projects in eligible OZ tracts: {len(tract_df):,}")
        print(f"  Unique tracts with NMTC investment: {tract_df['geoid'].nunique():,}")
        print(f"  Total QLICI in eligible tracts: ${amt:,.0f}")
        tract_df.to_parquet(OUT_PARQUET, index=False)
        print(f"  Saved → {OUT_PARQUET}")
    else:
        print(f"\nNMTC file not found at {LOCAL_NMTC}; skipping tract parquet.")

    # --- Step 3: Save JSON and patch YAML with certified counts ---
    out_json = {
        "fetched_at": date.today().isoformat(),
        "source": str(LOCAL_CERT),
        "counts": cert_counts,
    }
    OUT_JSON.write_text(json.dumps(out_json, indent=2, sort_keys=True))
    print(f"\nSaved → {OUT_JSON}")

    patch_yaml(cert_counts)
    print("Done.")


if __name__ == "__main__":
    main()
