"""
Fetch USDA ERS County Typology Codes → data/persistent_poverty.parquet

Source
------
USDA Economic Research Service — 2015 County Typology Codes (Dataset 48652)
  Landing page:  https://www.ers.usda.gov/data-products/county-typology-codes/
  Direct download:
    https://www.ers.usda.gov/webdocs/DataFiles/48652/2015CountyTypologyCodes.xlsx

The 2015 County Typology Codes is the canonical ERS source for the classic
persistent-poverty definition used in federal policy. A 2025 edition also
exists at:
  https://www.ers.usda.gov/media/6174/ers-county-typology-codes-2025-edition.csv
but uses 2017-2021 ACS data (attribute: Persistent_Poverty_1721) rather than
the classic 1980-2010 decennial census definition required here.

Note: USDA ERS webdocs and media servers block requests from cloud/datacenter
IP ranges at the network layer (host_not_allowed). Running from a standard
developer workstation or CI runner on a residential/business ISP will succeed.
If this script fails in your environment, place the manually downloaded Excel
file at data/raw/2015CountyTypologyCodes.xlsx and re-run.

Persistent Poverty Definition
------------------------------
A county qualifies as "persistent poverty" if 20% or more of its population
was in poverty in EVERY decennial census from 1980 through 2010 — four
consecutive census counts. Source: USDA ERS County Typology Codes technical
documentation, based on U.S. Census Bureau decennial poverty estimates.

Column mapping (2015 file, wide format)
-----------------------------------------
  FIPStxt       — 5-char county FIPS code (leading zeros may be omitted; we
                  zero-pad to 5)
  County_name   — county name (also seen as "County_Name" or "county_name")
  State         — 2-char state abbreviation
  Persis_Poverty — 1 = persistent poverty county; 0 = not

Note on alternative column names: The ERS file has been republished in
multiple editions. This script accepts all known variants:
  persistent poverty flag: "Persis_Poverty", "Persistent_Poverty",
                           "PersistentPoverty", "Persistent_Poverty_1721"
  county FIPS:             "FIPStxt", "FIPS", "fips", "FIPScode"
  county name:             "County_name", "County_Name", "county_name",
                           "CountyName"

Fallback: local cache at data/raw/2015CountyTypologyCodes.xlsx.
If all network fetches fail (e.g., a sandboxed CI environment), download
manually and place at that path, then re-run.

Output schema (data/persistent_poverty.parquet)
-----------------------------------------------
One row per county that contains at least one eligible OZ tract.

  county_fips           str   5-digit county FIPS
  state_fips            str   2-digit state FIPS (first two chars of county_fips)
  county_name           str   county name from ERS file
  is_persistent_poverty bool  True if ERS Persis_Poverty == 1
  fetched_at            str   ISO date this script was run

Join: inner join on county_fips with the distinct county_fips values from
data/eligible_tracts.parquet, so only counties containing eligible OZ
nomination tracts are included in the output.
"""

import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ERS_URLS = [
    # 2015 County Typology Codes — wide-format Excel (classic 1980-2010 definition)
    "https://www.ers.usda.gov/webdocs/DataFiles/48652/2015CountyTypologyCodes.xlsx",
    # Some browsers use the versioned URL
    "https://www.ers.usda.gov/webdocs/DataFiles/48652/2015CountyTypologyCodes.xlsx?v=6551.3",
]

# The 2025 edition uses a different server path (media/) and long CSV format.
# It uses 2017-2021 ACS data for the poverty measure (attribute: Persistent_Poverty_1721)
# rather than the classic 1980-2010 decennial census definition.
# We keep it as a secondary reference; the 2015 file remains canonical for this project.
ERS_2025_CSV_URL = (
    "https://www.ers.usda.gov/media/6174/ers-county-typology-codes-2025-edition.csv"
    "?v=15553"
)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
LOCAL_CACHE = RAW_DIR / "2015CountyTypologyCodes.xlsx"
ELIGIBLE_PARQUET = DATA_DIR / "eligible_tracts.parquet"
OUT_PARQUET = DATA_DIR / "persistent_poverty.parquet"

TIMEOUT = 60

# Known column name variants in ERS files (case-insensitive matching done below)
FIPS_COLS = ["FIPStxt", "FIPS", "fips", "FIPScode", "GEOID"]
NAME_COLS = ["County_name", "County_Name", "county_name", "CountyName", "Name"]
STATE_COLS = ["State", "state", "Stabr"]
POVERTY_COLS = [
    "Persis_Poverty", "Persistent_Poverty", "PersistentPoverty",
    "Persistent_Poverty_1721",  # used in 2023/2025 edition
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch(url: str) -> bytes:
    """Download url; return raw bytes. Raises requests.HTTPError on failure."""
    print(f"  Fetching {url} …")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.ers.usda.gov/data-products/county-typology-codes/",
    }
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"    {len(r.content):,} bytes received")
    return r.content


def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first column name in df that matches a candidate (case-insensitive)."""
    df_cols_lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
        if candidate.lower() in df_cols_lower:
            return df_cols_lower[candidate.lower()]
    return None


def fetch_ers_typology() -> bytes:
    """
    Download ERS County Typology Codes Excel. Returns raw bytes.

    Tries live URLs first; falls back to local cache at data/raw/.
    If all sources fail, raises RuntimeError with manual download instructions.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Local cache takes precedence (allows offline re-runs)
    if LOCAL_CACHE.exists():
        print(f"Using cached file: {LOCAL_CACHE}")
        return LOCAL_CACHE.read_bytes()

    last_exc: Exception | None = None
    for url in ERS_URLS:
        try:
            raw = _fetch(url)
            LOCAL_CACHE.write_bytes(raw)
            print(f"  Cached → {LOCAL_CACHE}")
            return raw
        except Exception as exc:
            print(f"    Failed ({exc.__class__.__name__}: {exc})")
            last_exc = exc

    raise RuntimeError(
        f"Could not download ERS County Typology Codes. "
        f"Last error: {last_exc}\n\n"
        "Manual download instructions:\n"
        "  1. Visit https://www.ers.usda.gov/data-products/county-typology-codes/\n"
        "  2. Download the '2015 County Typology Codes' Excel file.\n"
        f"  3. Save it to: {LOCAL_CACHE}\n"
        "  4. Re-run this script.\n\n"
        "Note: USDA ERS webdocs servers block requests from certain data-center\n"
        "IP ranges. Running from a standard workstation or home IP should work."
    )


def parse_typology(raw: bytes) -> pd.DataFrame:
    """
    Parse the ERS County Typology Codes Excel file.

    Handles both:
    - Wide format (2015 edition): one row per county, Persis_Poverty column
    - Long format (potential future editions): Attribute/Value pivoted

    Returns DataFrame with columns:
        county_fips (str), county_name (str), is_persistent_poverty (bool)
    """
    xl = pd.ExcelFile(io.BytesIO(raw))
    print(f"  Sheets: {xl.sheet_names}")

    # Try each sheet; use the first one that has enough county rows
    df = None
    for sheet in xl.sheet_names:
        candidate = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, dtype=str)
        candidate.columns = [str(c).strip() for c in candidate.columns]
        # Need at least a FIPS column and 500+ rows to be the data sheet
        if _col(candidate, FIPS_COLS) is not None and len(candidate) >= 500:
            df = candidate
            print(f"  Using sheet: '{sheet}' ({len(df):,} rows × {len(df.columns)} cols)")
            break

    if df is None:
        # Last resort: use first sheet regardless
        df = pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        print(f"  Fallback to first sheet ({len(df):,} rows × {len(df.columns)} cols)")

    # --- Locate required columns ---
    fips_col = _col(df, FIPS_COLS)
    name_col = _col(df, NAME_COLS)
    pov_col  = _col(df, POVERTY_COLS)

    if fips_col is None:
        raise ValueError(
            f"Could not find a FIPS column. Columns present: {df.columns.tolist()}"
        )
    if pov_col is None:
        raise ValueError(
            f"Could not find a persistent poverty column. "
            f"Columns present: {df.columns.tolist()}\n"
            "Expected one of: " + ", ".join(POVERTY_COLS)
        )

    print(f"  FIPS column:    '{fips_col}'")
    print(f"  Name column:    '{name_col}'")
    print(f"  Poverty column: '{pov_col}'")

    # --- Build output ---
    result = pd.DataFrame()

    # county_fips: zero-pad to 5 digits
    result["county_fips"] = (
        df[fips_col]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)   # strip ".0" from float reads
        .str.zfill(5)
    )

    # county_name
    if name_col:
        result["county_name"] = df[name_col].astype(str).str.strip()
    else:
        result["county_name"] = ""

    # is_persistent_poverty: 1 → True, 0 → False
    result["is_persistent_poverty"] = (
        pd.to_numeric(df[pov_col], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(bool)
    )

    # Drop rows without a valid 5-digit county FIPS
    result = result[result["county_fips"].str.match(r"^\d{5}$", na=False)].copy()
    # Drop state-level rows (county part = "000")
    result = result[result["county_fips"].str[2:] != "000"].copy()
    result = result.reset_index(drop=True)

    print(f"  After filtering: {len(result):,} county rows")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1. Load eligible tracts ----
    if not ELIGIBLE_PARQUET.exists():
        sys.exit(
            f"ERROR: {ELIGIBLE_PARQUET} not found. "
            "Run scripts/ingest_irs_appendix.py first."
        )

    eligible = pd.read_parquet(ELIGIBLE_PARQUET)
    eligible_counties = (
        eligible[["county_fips", "state_fips", "county_name"]]
        .drop_duplicates(subset="county_fips")
        .copy()
    )
    print(f"Eligible tracts file: {len(eligible):,} tracts, "
          f"{len(eligible_counties):,} unique counties")

    # ---- 2. Fetch ERS typology data ----
    print("\nFetching USDA ERS County Typology Codes …")
    try:
        raw = fetch_ers_typology()
    except RuntimeError as exc:
        sys.exit(f"\nFATAL: {exc}")

    # ---- 3. Parse ----
    print("\nParsing …")
    try:
        typology = parse_typology(raw)
    except (ValueError, Exception) as exc:
        sys.exit(f"\nFATAL parsing typology file: {exc}")

    # ---- 4. Join: keep only counties with eligible tracts ----
    merged = eligible_counties.merge(
        typology[["county_fips", "is_persistent_poverty"]],
        on="county_fips",
        how="left",   # left = keep all eligible counties
    )

    # Counties not found in ERS file: mark as not persistent poverty (rare edge case)
    missing = merged["is_persistent_poverty"].isna().sum()
    if missing > 0:
        print(f"\nWarning: {missing} eligible counties not found in ERS file; "
              "defaulting is_persistent_poverty = False.")
    merged["is_persistent_poverty"] = merged["is_persistent_poverty"].fillna(False).astype(bool)

    merged["fetched_at"] = date.today().isoformat()

    out = merged[["county_fips", "state_fips", "county_name",
                  "is_persistent_poverty", "fetched_at"]].copy()
    out = out.sort_values("county_fips").reset_index(drop=True)

    # ---- 5. Summary ----
    n_pp  = int(out["is_persistent_poverty"].sum())
    n_not = int((~out["is_persistent_poverty"]).sum())
    total = len(out)

    print(f"\n--- Persistent Poverty Summary (eligible-tract counties only) ---")
    print(f"  Total counties with eligible tracts : {total:,}")
    print(f"  Persistent poverty counties         : {n_pp:,}  "
          f"({100 * n_pp / total:.1f}%)")
    print(f"  Not persistent poverty              : {n_not:,}  "
          f"({100 * n_not / total:.1f}%)")

    # State-level breakdown: how many eligible states have PP counties
    pp_states = out[out["is_persistent_poverty"]]["state_fips"].nunique()
    print(f"  States/territories with ≥1 PP county: {pp_states}")

    # Top states by PP county count
    pp_by_state = (
        out[out["is_persistent_poverty"]]
        .groupby("state_fips")["county_fips"]
        .count()
        .sort_values(ascending=False)
        .head(10)
    )
    if len(pp_by_state):
        print("\n  Top 10 states by persistent-poverty county count:")
        # Try to add state names from eligible tracts
        state_names = (
            eligible[["state_fips", "state_name"]]
            .drop_duplicates("state_fips")
            .set_index("state_fips")["state_name"]
        )
        for sfips, cnt in pp_by_state.items():
            sname = state_names.get(sfips, sfips)
            print(f"    {sname:<25} {cnt:>3} counties")

    # ---- 6. Save ----
    out.to_parquet(OUT_PARQUET, index=False)
    print(f"\nSaved → {OUT_PARQUET}")
    print(f"  {len(out):,} rows × {len(out.columns)} cols")


if __name__ == "__main__":
    main()
