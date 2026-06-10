"""
Fetch FFIEC Census Flat File → data/cra_lmi_overlap.parquet

Source
------
FFIEC (Federal Financial Institutions Examination Council) Census Flat File.
Published annually; used by bank examiners to determine CRA tract income
designations for examination years. The 2023 exam year file is based on
2017–2021 ACS 5-year estimates.

  Landing page:  https://www.ffiec.gov/censusapp.htm
  Flat files:    https://www.ffiec.gov/cra/craflatfiles.htm

CRA eligibility — two tracks
-----------------------------
Track 1 — LMI: A census tract is CRA Low-to-Moderate Income (LMI) if its
estimated median family income (MFI) is less than 80% of the area MFI,
where "area" is the MSA/Metropolitan Division for metropolitan tracts, or
the statewide non-metropolitan area for rural tracts. Tract income level:
  L — Low Income      (tract MFI < 50% of area MFI)
  M — Moderate Income (tract MFI 50–80% of area MFI)
  U — Upper Income    (tract MFI 80–120% of area MFI)
  I — Income > 120%   (in some file versions)
  NA or blank — tract income not available / no classification

Track 2 — Distressed/Underserved: Non-metropolitan census tracts that are
middle-income (not LMI) but are designated "Distressed or Underserved" by
FFIEC based on: unemployment ≥ 1.5× national average, poverty rate ≥ 20%,
or population loss ≥ 10% / net migration loss ≥ 5%. These qualify for CRA
Community Development credit even without LMI status.

CRA-eligible = LMI (L or M) OR distressed/underserved designation.

FFIEC Census Flat File format
------------------------------
Fixed-width text file (pipe-delimited in newer editions). Key columns:
  State Code                    (2-digit)
  County Code                   (3-digit)
  Census Tract                  (6-digit, with implied decimal before last 2)
  Tract Income Ind              (1 char: L, M, U; or blank/NA)
  Distressed or Underserved     (Yes/No or 0/1 flag)

The exact column layout varies by year. This script handles:
  - 2023/2024 pipe-delimited format (newer FFIEC releases)
  - FFIEC Census Tract List XLSX (2024+, preferred)
  - Fixed-width format (legacy)
  - ACS Census API fallback (income level only — no distressed/underserved)

NOTE: The ACS fallback does NOT include distressed/underserved designation.
Running it will undercount CRA-eligible tracts. To get the full picture,
provide the FFIEC Census Tract List XLSX in data/raw/ and re-run.

Output schema (data/cra_lmi_overlap.parquet)
--------------------------------------------
One row per OZ-eligible tract that could be matched to the FFIEC data.

  geoid                    str   11-digit census tract GEOID
  state_fips               str   2-digit state FIPS
  county_fips              str   5-digit county FIPS
  income_level             str   FFIEC income level code (L, M, U, or NA)
  is_distressed_underserved bool  True if FFIEC distressed/underserved flag set
                                  (always False when ACS fallback is used)
  is_cra_lmi               bool  True if income_level in ('L','M') OR
                                  is_distressed_underserved
  fetched_at               str   ISO date this script was run
"""

import io
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
ELIGIBLE_PARQUET = DATA_DIR / "eligible_tracts.parquet"
OUT_PARQUET = DATA_DIR / "cra_lmi_overlap.parquet"

TIMEOUT = 90

# FFIEC Census Flat File download candidates (ordered by preference)
# The FFIEC publishes these at https://www.ffiec.gov/cra/craflatfiles.htm
# File format: pipe-delimited ZIP containing a .txt flat file
FFIEC_URLS = [
    # 2024 exam year (based on 2018-2022 ACS 5-year estimates)
    "https://www.ffiec.gov/cra/pdf/CensusFlatFile2024.zip",
    # 2023 exam year (based on 2017-2021 ACS 5-year estimates)
    "https://www.ffiec.gov/cra/pdf/CensusFlatFile2023.zip",
]

# Known column name variants across FFIEC flat file editions
INCOME_LEVEL_COLS = [
    "Tract Income Level",
    "Tract income level",
    "TractIncomeIndicator",
    "TRACT_INCOME_LEVEL",
    "tract_income_level",
    "Income Level",
    "IncomeLevel",
    "MSAorMD_INCOME_IND",
]

# Distressed or Underserved — CRA Track 2 designation
DISTRESSED_COLS = [
    "Distressed or Underserved Tract",
    "Distressed or Underserved",
    "distressed_or_underserved",
    "DistressedOrUnderserved",
    "Distressed",
    "DistressedInd",
    "DISTRESSED",
    "D_U_IND",
    "Underserved",
]

STATE_COLS = ["State Code", "STATE_CODE", "state_code", "State", "MSAorMD_STATE"]
COUNTY_COLS = ["County Code", "COUNTY_CODE", "county_code", "County"]
TRACT_COLS = ["Census Tract", "CENSUS_TRACT", "census_tract", "Tract", "CensusTract"]


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
        "Referer": "https://www.ffiec.gov/cra/craflatfiles.htm",
    }
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"    {len(r.content):,} bytes received")
    return r.content


def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return first matching column name (case-insensitive)."""
    df_cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in df_cols_lower:
            return df_cols_lower[c.lower()]
    return None


def _parse_ffiec_zip(raw: bytes) -> pd.DataFrame:
    """
    Extract and parse a FFIEC Census Flat File ZIP.

    Returns DataFrame with columns: geoid (11-digit), income_level (str).
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        print(f"  ZIP contents: {names}")
        # Pick the first .txt or .csv file
        txt_files = [n for n in names if n.lower().endswith(('.txt', '.csv', '.dat'))]
        if not txt_files:
            raise ValueError(f"No text file found in ZIP: {names}")
        fname = txt_files[0]
        print(f"  Parsing: {fname}")
        content = zf.read(fname)

    # Try pipe-delimited first (newer FFIEC format)
    for sep in ('|', '\t', ','):
        try:
            df = pd.read_csv(io.BytesIO(content), sep=sep, dtype=str,
                             encoding='latin-1', low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            if len(df.columns) >= 5:
                print(f"  Parsed as sep='{sep}': {len(df):,} rows × {len(df.columns)} cols")
                result = _extract_geoid_income(df)
                if result is not None:
                    return result
        except Exception:
            pass

    # Fallback: try fixed-width (legacy FFIEC format)
    # Classic layout: positions 0-1 state, 2-4 county, 5-10 tract, 11 income level
    print("  Trying fixed-width parse …")
    lines = content.decode('latin-1').splitlines()
    records = []
    for line in lines:
        if len(line) < 12:
            continue
        state = line[0:2].strip()
        county = line[2:5].strip()
        tract = line[5:11].strip()
        income = line[11:12].strip().upper() if len(line) > 11 else ""
        if state.isdigit() and county.isdigit():
            geoid = f"{state.zfill(2)}{county.zfill(3)}{tract.zfill(6)}"
            records.append({"geoid": geoid, "income_level": income})

    if records:
        df = pd.DataFrame(records)
        print(f"  Fixed-width parse: {len(df):,} rows")
        return df

    raise ValueError("Could not parse FFIEC flat file in any known format")


def _extract_geoid_income(df: pd.DataFrame) -> pd.DataFrame | None:
    """Extract geoid + income_level + is_distressed_underserved from a parsed FFIEC DataFrame."""
    state_col = _col(df, STATE_COLS)
    county_col = _col(df, COUNTY_COLS)
    tract_col = _col(df, TRACT_COLS)
    income_col = _col(df, INCOME_LEVEL_COLS)
    distressed_col = _col(df, DISTRESSED_COLS)

    if not income_col:
        print(f"  Could not find income level column. Available: {df.columns.tolist()[:20]}")
        return None

    print(f"  State: '{state_col}', County: '{county_col}', Tract: '{tract_col}', "
          f"Income: '{income_col}', Distressed: '{distressed_col}'")

    result = pd.DataFrame()

    if state_col and county_col and tract_col:
        state_s = df[state_col].astype(str).str.strip().str.zfill(2)
        county_s = df[county_col].astype(str).str.strip().str.zfill(3)
        # Tract may be 6-char with implied decimal (e.g., "012345" = tract 123.45)
        # Remove decimal points, pad to 6
        tract_s = (
            df[tract_col].astype(str).str.strip()
            .str.replace('.', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.zfill(6)
        )
        result["geoid"] = state_s + county_s + tract_s
    else:
        # Try to find a combined FIPS/GEOID column
        geoid_col = _col(df, ["GEOID", "geoid", "GeoID", "FIPS", "TractFIPS"])
        if geoid_col:
            result["geoid"] = df[geoid_col].astype(str).str.strip().str.zfill(11)
        else:
            print(f"  Could not construct GEOID. Columns: {df.columns.tolist()[:20]}")
            return None

    result["income_level"] = df[income_col].astype(str).str.strip().str.upper()
    # Normalize: blank/nan/"NA"/"N/A" → "NA"
    result["income_level"] = result["income_level"].replace(
        {"NAN": "NA", "N/A": "NA", "": "NA", "NONE": "NA"}
    )

    # CRA Track 2: distressed or underserved non-metropolitan middle-income tracts
    if distressed_col:
        raw_d = df[distressed_col].astype(str).str.strip().str.upper()
        result["is_distressed_underserved"] = raw_d.isin(["YES", "Y", "1", "TRUE"])
        n_du = int(result["is_distressed_underserved"].sum())
        print(f"  Distressed/Underserved tracts found: {n_du:,}")
    else:
        result["is_distressed_underserved"] = False
        print("  No distressed/underserved column found — Track 2 will be missing")

    # Keep only rows with valid 11-digit GEOIDs
    result = result[result["geoid"].str.match(r"^\d{11}$", na=False)].copy()
    result = result.reset_index(drop=True)
    print(f"  Valid GEOIDs: {len(result):,}")
    return result


# ---------------------------------------------------------------------------
# ACS fallback: compute LMI from ACS tract MFI vs. area MFI
# ---------------------------------------------------------------------------

def _acs_fallback(elig: pd.DataFrame) -> pd.DataFrame:
    """
    Fallback: fetch 2021 ACS 5-year tract median family income via Census API
    and compare to county/MSA median to flag LMI tracts.

    This is a simplified approximation — uses county MFI as the area benchmark
    (rather than MSA/MD, which is the official FFIEC standard). Results will
    slightly overcount LMI in high-income metros and undercount in low-income
    rural areas, but are directionally accurate for a summary statistic.
    """
    print("\nUsing Census ACS fallback for CRA LMI estimation …")
    api_key_hint = (
        "For better rate limits, set env var CENSUS_API_KEY. "
        "Free key: https://api.census.gov/data/key_signup.html"
    )
    print(f"  Note: {api_key_hint}")

    import os
    api_key = os.environ.get("CENSUS_API_KEY", "")
    key_param = f"&key={api_key}" if api_key else ""

    # Variables: B19113_001E = Median family income in past 12 months (tract)
    # We'll fetch by state to stay within API limits
    records = []
    states = elig["state_fips"].unique()
    print(f"  Fetching ACS tract MFI for {len(states)} states …")

    for sfips in sorted(states):
        url = (
            f"https://api.census.gov/data/2021/acs/acs5"
            f"?get=B19113_001E,GEO_ID"
            f"&for=tract:*&in=state:{sfips}"
            f"{key_param}"
        )
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            for row in data[1:]:  # skip header
                mfi_raw, geo_id, _, county_code, tract_code = row[0], row[1], row[2], row[3], row[4]
                geoid = f"{sfips.zfill(2)}{county_code.zfill(3)}{tract_code.zfill(6)}"
                mfi = int(mfi_raw) if mfi_raw and mfi_raw != "-666666666" else None
                records.append({"geoid": geoid, "state_fips": sfips,
                                "county_fips": sfips.zfill(2) + county_code.zfill(3),
                                "tract_mfi": mfi})
        except Exception as exc:
            print(f"    Warning: ACS fetch failed for state {sfips}: {exc}")

    if not records:
        raise RuntimeError("ACS fallback: no tract data retrieved")

    tracts_df = pd.DataFrame(records)

    # Compute county median MFI as area benchmark
    county_mfi = (
        tracts_df.dropna(subset=["tract_mfi"])
        .groupby("county_fips")["tract_mfi"]
        .median()
        .rename("county_mfi")
    )
    tracts_df = tracts_df.merge(county_mfi, on="county_fips", how="left")

    def _income_level(row):
        if pd.isna(row["tract_mfi"]) or pd.isna(row["county_mfi"]) or row["county_mfi"] == 0:
            return "NA"
        ratio = row["tract_mfi"] / row["county_mfi"]
        if ratio < 0.50:
            return "L"
        if ratio < 0.80:
            return "M"
        return "U"

    tracts_df["income_level"] = tracts_df.apply(_income_level, axis=1)
    # ACS fallback cannot determine distressed/underserved (Track 2) — always False here
    tracts_df["is_distressed_underserved"] = False

    print(f"  ACS fallback: {len(tracts_df):,} tracts, "
          f"{(tracts_df['income_level'].isin(['L','M'])).sum():,} LMI")
    print("  WARNING: ACS fallback has no distressed/underserved data — CRA count is LMI-only")
    return tracts_df[["geoid", "income_level", "is_distressed_underserved"]].copy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Known XLSX filenames that FFIEC publishes (check raw/ for these first)
FFIEC_XLSX_NAMES = [
    "FFIEC_CensusTractList2026.xlsx",
    "FFIEC_CensusTractList2025.xlsx",
    "FFIEC_CensusTractList2024.xlsx",
]

# Known flat CSV/TXT filenames (pipe-delimited or comma-delimited)
FFIEC_CSV_NAMES = [
    "CensusFlatFile2025.csv",
    "CensusFlatFile2024.csv",
    "CensusFlatFile2026.csv",
    "CensusFlatFile2025.txt",
    "CensusFlatFile2024.txt",
]

# Map FFIEC word-form income levels → standard single-letter codes
FFIEC_WORD_TO_CODE = {
    "LOW": "L",
    "MODERATE": "M",
    "MIDDLE": "U",
    "UPPER": "U",
    "UNKNOWN": "NA",
}


def _parse_local_xlsx() -> pd.DataFrame | None:
    """
    Parse a locally downloaded FFIEC Census Tract List XLSX from data/raw/.

    The XLSX format (2024–2026 and later) has a 'Notes' sheet and one or more
    data sheets named like '2024-2026 tracts'. Relevant columns:
      FIPS code            — 11-digit census tract GEOID
      Tract income level   — word form: Low, Moderate, Middle, Upper, Unknown
    """
    for name in FFIEC_XLSX_NAMES:
        path = RAW_DIR / name
        if not path.exists():
            continue
        print(f"\nFound local FFIEC XLSX: {path}")
        try:
            xf = pd.ExcelFile(path)
            # Find the first data sheet (skip Notes)
            data_sheets = [s for s in xf.sheet_names if s.lower() != "notes"]
            if not data_sheets:
                print("  No data sheets found; skipping")
                continue
            sheet = data_sheets[0]
            print(f"  Reading sheet: '{sheet}' …")
            df = pd.read_excel(path, sheet_name=sheet, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]

            fips_col = _col(df, ["FIPS code", "FIPS Code", "fips_code", "GEOID"])
            income_col = _col(df, ["Tract income level", "Tract Income Level",
                                   "tract_income_level"] + INCOME_LEVEL_COLS)
            distressed_col = _col(df, DISTRESSED_COLS)
            if not fips_col or not income_col:
                print(f"  Could not find required columns. Available: {df.columns.tolist()}")
                continue

            print(f"  FIPS: '{fips_col}', Income: '{income_col}', Distressed: '{distressed_col}'")

            result = pd.DataFrame()
            result["geoid"] = df[fips_col].astype(str).str.strip().str.zfill(11)
            raw_level = df[income_col].astype(str).str.strip().str.upper()
            result["income_level"] = raw_level.map(
                lambda v: FFIEC_WORD_TO_CODE.get(v, v if v in ("L", "M", "U") else "NA")
            )

            # CRA Track 2: distressed or underserved designation
            if distressed_col:
                raw_d = df[distressed_col].astype(str).str.strip().str.upper()
                result["is_distressed_underserved"] = raw_d.isin(["YES", "Y", "1", "TRUE"])
                n_du = int(result["is_distressed_underserved"].sum())
                print(f"  Distressed/Underserved tracts: {n_du:,}")
            else:
                result["is_distressed_underserved"] = False
                print("  No distressed/underserved column found — Track 2 will be missing")

            result = result[result["geoid"].str.match(r"^\d{11}$", na=False)].copy()
            result = result.reset_index(drop=True)
            print(f"  Parsed: {len(result):,} tracts  "
                  f"LMI: {result['income_level'].isin(['L','M']).sum():,}  "
                  f"D/U: {result['is_distressed_underserved'].sum():,}")
            return result
        except Exception as exc:
            print(f"  Failed to parse {name}: {exc}")
    return None


def _parse_local_csv() -> "pd.DataFrame | None":
    """
    Parse the FFIEC Census Flat File CSV from data/raw/ using its positional layout.

    This is the full FFIEC census file (one row per census tract, no header row,
    comma-delimited, ~87k rows). Key columns per the FFIEC data dictionary:

      Col  0  Activity year
      Col  2  FIPS state code (2-digit)
      Col  3  FIPS county code (3-digit)
      Col  4  Census tract (6-digit, implied decimal)
      Col  8  Demographic data flag (D=data present, X=zero pop/MFI, I=island)
      Col 14  Income indicator: 1=Low, 2=Moderate, 3=Middle, 4=Upper, 0=N/A
      Col 17  CRA distressed criteria ('X' = yes, blank = no)
      Col 18  CRA remote rural (underserved) criteria ('X' = yes, blank = no)
      Col 21  Meets current OR previous year's D/U criteria ('X' = yes, blank = no)

    CRA Track 2 eligibility uses col 21 (includes the FFIEC's standard one-year
    lag period for tracts that were distressed/underserved the prior exam year).
    """
    INCOME_MAP = {"1": "L", "2": "M", "3": "Middle", "4": "U", "0": "NA"}

    for name in FFIEC_CSV_NAMES:
        path = RAW_DIR / name
        if not path.exists():
            continue
        print(f"\nFound local FFIEC Census Flat File CSV: {path}")
        try:
            df = pd.read_csv(path, header=None, dtype=str, encoding='latin-1',
                             low_memory=False)
            print(f"  {len(df):,} rows × {len(df.columns)} cols")
            if len(df.columns) < 22:
                print(f"  Too few columns ({len(df.columns)}) — not the positional flat file format; skipping")
                continue

            # Build 11-digit GEOID from state + county + tract
            state_s = df[2].astype(str).str.strip().str.zfill(2)
            county_s = df[3].astype(str).str.strip().str.zfill(3)
            tract_s = (df[4].astype(str).str.strip()
                       .str.replace('.', '', regex=False)
                       .str.zfill(6))
            geoid = state_s + county_s + tract_s

            # Income level from col 14 (numeric indicator)
            income_level = df[14].astype(str).str.strip().map(
                lambda v: INCOME_MAP.get(v, "NA")
            )

            # CRA Track 2: col 21 = current OR previous year distressed/underserved
            # ('X' = yes, blank/NaN = no). This includes the FFIEC one-year lag period.
            du_flag = df[21].astype(str).str.strip().str.upper() == "X"
            n_du = int(du_flag.sum())
            print(f"  Income indicator col 14 — unique values: {sorted(df[14].dropna().unique()[:10])}")
            print(f"  D/U col 21 — 'X' count: {n_du:,}")

            result = pd.DataFrame({
                "geoid": geoid,
                "income_level": income_level,
                "is_distressed_underserved": du_flag,
            })

            # Drop rows where geoid is not a valid 11-digit number (e.g., island areas
            # with I demographic flag or rows with zero-population tracts)
            result = result[result["geoid"].str.match(r"^\d{11}$", na=False)].copy()
            result = result.reset_index(drop=True)
            print(f"  Valid GEOIDs: {len(result):,}  "
                  f"LMI (L+M): {result['income_level'].isin(['L','M']).sum():,}  "
                  f"D/U: {result['is_distressed_underserved'].sum():,}")
            return result

        except Exception as exc:
            print(f"  Failed to parse {name}: {exc}")
    return None


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not ELIGIBLE_PARQUET.exists():
        sys.exit(
            f"ERROR: {ELIGIBLE_PARQUET} not found. "
            "Run scripts/ingest_irs_appendix.py first."
        )

    print("=== ingest_cra_lmi.py ===")

    elig = pd.read_parquet(ELIGIBLE_PARQUET)
    print(f"Eligible tracts: {len(elig):,}")

    # ---- 1. Try local CSV flat file first — it has D/U designation (Track 2) ----
    ffiec_df: pd.DataFrame | None = _parse_local_csv()

    # ---- 1b. Fall back to XLSX (income levels only, no D/U) ----
    if ffiec_df is None:
        ffiec_df = _parse_local_xlsx()

    # ---- 2. Fall back to FFIEC ZIP download ----
    last_exc: Exception | None = None
    if ffiec_df is None:
        for url in FFIEC_URLS:
            cache_name = url.split("/")[-1]
            cache_path = RAW_DIR / cache_name
            try:
                if cache_path.exists():
                    print(f"\nUsing cached file: {cache_path}")
                    raw = cache_path.read_bytes()
                else:
                    print(f"\nDownloading FFIEC flat file …")
                    raw = _fetch(url)
                    cache_path.write_bytes(raw)
                    print(f"  Cached → {cache_path}")

                print("Parsing FFIEC flat file …")
                ffiec_df = _parse_ffiec_zip(raw)
                if ffiec_df is not None and len(ffiec_df) > 10000:
                    print(f"  Parsed: {len(ffiec_df):,} tracts")
                    break
                else:
                    print("  Parse returned too few rows; trying next URL")
                    ffiec_df = None

            except Exception as exc:
                print(f"  Failed ({exc.__class__.__name__}: {exc})")
                last_exc = exc
                ffiec_df = None
                continue

    # ---- 3. ACS fallback if both local file and download failed ----
    if ffiec_df is None:
        print(
            f"\nFFIEC flat file unavailable ({last_exc}). "
            "Falling back to ACS tract MFI computation …"
        )
        print(
            "NOTE: Manual alternative — download the FFIEC Census Flat File from:\n"
            "  https://www.ffiec.gov/cra/craflatfiles.htm\n"
            f"  Save the ZIP to: {RAW_DIR}/CensusFlatFile2023.zip\n"
            "  Then re-run this script."
        )
        try:
            ffiec_df = _acs_fallback(elig)
        except Exception as exc:
            sys.exit(f"\nFATAL: Both FFIEC and ACS fallback failed.\n{exc}")

    # ---- Join FFIEC income levels to eligible tracts ----
    print("\nJoining to eligible tracts …")
    elig_with_income = elig[["geoid", "state_fips", "county_fips"]].copy()
    elig_with_income["geoid"] = elig_with_income["geoid"].astype(str)

    ffiec_df["geoid"] = ffiec_df["geoid"].astype(str)

    # Ensure is_distressed_underserved column exists (older code paths may omit it)
    if "is_distressed_underserved" not in ffiec_df.columns:
        ffiec_df["is_distressed_underserved"] = False

    merged = elig_with_income.merge(
        ffiec_df[["geoid", "income_level", "is_distressed_underserved"]],
        on="geoid",
        how="left",
    )

    missing = merged["income_level"].isna().sum()
    if missing > 0:
        print(f"  Warning: {missing:,} eligible tracts not in FFIEC file → marked NA")
    merged["income_level"] = merged["income_level"].fillna("NA")
    merged["is_distressed_underserved"] = merged["is_distressed_underserved"].fillna(False)

    # CRA-eligible = LMI (Track 1) OR distressed/underserved (Track 2)
    merged["is_cra_lmi"] = merged["income_level"].isin(["L", "M"]) | merged["is_distressed_underserved"]
    merged["fetched_at"] = date.today().isoformat()

    # ---- Summary ----
    total = len(merged)
    n_cra = int(merged["is_cra_lmi"].sum())
    n_low = int((merged["income_level"] == "L").sum())
    n_mod = int((merged["income_level"] == "M").sum())
    n_upper = int((merged["income_level"] == "U").sum())
    n_na = int((merged["income_level"] == "NA").sum())
    n_du = int(merged["is_distressed_underserved"].sum())
    n_du_only = int((merged["is_distressed_underserved"] & ~merged["income_level"].isin(["L","M"])).sum())

    print(f"\n--- CRA Eligibility Summary (eligible OZ tracts) ---")
    print(f"  Total eligible tracts    : {total:,}")
    print(f"  CRA-eligible (any track) : {n_cra:,}  ({100*n_cra/total:.1f}%)")
    print(f"  Track 1 — LMI (L+M)     : {(merged['income_level'].isin(['L','M'])).sum():,}")
    print(f"    Low Income (L)         : {n_low:,}")
    print(f"    Moderate Income (M)    : {n_mod:,}")
    print(f"  Track 2 — Distressed/U  : {n_du:,}  ({n_du_only:,} non-LMI, Track 2 only)")
    print(f"  Upper Income (U)         : {n_upper:,}")
    print(f"  Not classified (NA)      : {n_na:,}")
    if n_du == 0:
        print("\n  NOTE: Distressed/underserved count is 0 — likely running on ACS fallback.")
        print("  To include Track 2, place FFIEC Census Tract List XLSX in data/raw/ and re-run.")

    # Top states by CRA-eligible tract count
    cra_by_state = (
        merged[merged["is_cra_lmi"]]
        .groupby("state_fips")["geoid"]
        .count()
        .sort_values(ascending=False)
        .head(10)
    )
    if len(cra_by_state):
        state_names = (
            elig[["state_fips", "state_name"]]
            .drop_duplicates("state_fips")
            .set_index("state_fips")["state_name"]
        )
        print("\n  Top 10 states by CRA-eligible tract count:")
        for sfips, cnt in cra_by_state.items():
            sname = state_names.get(sfips, sfips)
            print(f"    {sname:<30} {cnt:>4} tracts")

    # ---- Save ----
    out = merged[["geoid", "state_fips", "county_fips", "income_level",
                  "is_distressed_underserved", "is_cra_lmi", "fetched_at"]].copy()
    out = out.sort_values("geoid").reset_index(drop=True)
    out.to_parquet(OUT_PARQUET, index=False)
    print(f"\nSaved → {OUT_PARQUET}")
    print(f"  {len(out):,} rows × {len(out.columns)} cols")


if __name__ == "__main__":
    main()
