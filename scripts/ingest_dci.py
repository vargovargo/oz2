"""
Fetch EIG Distressed Communities Index (2023) → data/dci.parquet

Sources
-------
EIG DCI (2023 edition):
  Landing page: https://eig.org/distressed-communities/
  Direct download (as of 2026-05):
    https://eig.org/wp-content/uploads/2023/11/2023-DCI-Full-Data.xlsx
  Fallback URL tried first:
    https://eig.org/wp-content/uploads/2023/11/DCI-2023-Full-Data.xlsx
  Note: EIG restricts direct hotlinking. If 403 is returned, download the file
  manually from https://eig.org/distressed-communities/ and place it at
  data/raw/2023-DCI-Full-Data.xlsx, then re-run this script.

HUD USPS ZIP-to-Tract crosswalk (Q4 2024):
  API endpoint:  https://www.huduser.gov/hudapi/public/usps?type=6&query=All
    Requires a free token from https://www.huduser.gov/hudapi/public/register/form
    Pass via env var HUD_API_TOKEN or --hud-token CLI argument.
  Flat file fallback (2024 Q4):
    https://www.huduser.gov/portal/datasets/usps/ZIP_TRACT_122024.xlsx
    (also try 092024 for Q3, 062024 for Q2)
  Census fallback: 2020 ZCTA-to-Tract relationship file (area-weighted, not
    residential-weighted):
    https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt
  Note: The HUD crosswalk uses residential address counts (res_ratio) as
    weights, which is preferable. The Census area-based crosswalk is used as
    a last resort; it weights by land-area overlap fraction instead.

Methodology — ZIP-to-Tract join
--------------------------------
The DCI is published at the 5-digit ZIP Code level; eligible tracts are
census tracts (11-digit GEOIDs). The crosswalk is many-to-many:

  • One ZIP may span multiple tracts (each row has a res_ratio ∈ (0,1])
  • One tract may overlap multiple ZIPs

Join steps:
  1. Load DCI ZIP scores (one row per ZIP, column: dci_score 0–100).
  2. Load ZIP-to-Tract crosswalk with res_ratio (fraction of residential
     addresses in that ZIP that fall within that tract).
  3. Inner-join DCI ↔ crosswalk on ZIP code.
  4. For each tract, compute a res_ratio-weighted average dci_score across
     all contributing ZIPs:
         score_tract = Σ(dci_score_z × res_ratio_z) / Σ(res_ratio_z)
  5. zip_primary = the ZIP with the highest res_ratio for that tract.
  6. dci_quintile: recompute as quintile of dci_score among eligible tracts
     (1 = most distressed quintile). EIG's ZIP-level quintiles are not
     transferred directly because the weighting shifts the distribution.
  7. Inner-join result with eligible_tracts.parquet on geoid.

Output schema (data/dci.parquet)
---------------------------------
  geoid       str   11-digit census tract GEOID (only eligible tracts)
  dci_score   float weighted-average DCI score (higher = more distressed
                    on EIG's 0–100 scale)
  dci_quintile int  1–5, recomputed among eligible tracts (1 = most distressed)
  zip_primary str   ZIP code with highest res_ratio contribution for this tract
  fetched_at  str   ISO date this script was run

Known limitations
-----------------
  • ~15–20% of eligible tracts may not match any ZIP in the crosswalk
    (rural areas with PO Box-only ZIPs, tribal lands, etc.). These tracts
    are excluded from the parquet; join on geoid returns NaN for dci_score.
  • The area-based Census fallback over-weights large-area but low-population
    portions of ZIPs; res_ratio-weighted HUD crosswalk is strongly preferred.
  • EIG DCI 2023 uses 2017–2021 ACS 5-year data.

Failure modes documented
------------------------
  As of 2026-05-08 this script was tested in a sandboxed environment where
  outbound HTTP is restricted to github.com / pypi.org. All EIG and HUD
  endpoints returned HTTP 403 ("host_not_allowed"). Census.gov also returned
  403. The script exits with a non-zero status and prints a clear error message
  listing manual download steps if any fetch fails.
"""

import io
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_PARQUET = DATA_DIR / "dci.parquet"
ELIGIBLE_PARQUET = DATA_DIR / "eligible_tracts.parquet"

# EIG DCI download URLs to try in order
EIG_URLS = [
    "https://eig.org/wp-content/uploads/2023/11/2023-DCI-Full-Data.xlsx",
    "https://eig.org/wp-content/uploads/2023/11/DCI-2023-Full-Data.xlsx",
    "https://eig.org/wp-content/uploads/2023/10/2023-DCI-Full-Dataset.xlsx",
    "https://eig.org/wp-content/uploads/2023/11/DCI-Full-Data-2023.xlsx",
]
# Local cache path (if user downloaded manually)
EIG_LOCAL = RAW_DIR / "2023-DCI-Full-Data.xlsx"

# HUD crosswalk API
HUD_API_URL = "https://www.huduser.gov/hudapi/public/usps?type=6&query=All"
HUD_TOKEN_ENV = "HUD_API_TOKEN"

# HUD flat file URLs to try (Q4/Q3/Q2 2024)
HUD_FLAT_URLS = [
    "https://www.huduser.gov/portal/datasets/usps/ZIP_TRACT_122024.xlsx",
    "https://www.huduser.gov/portal/datasets/usps/ZIP_TRACT_092024.xlsx",
    "https://www.huduser.gov/portal/datasets/usps/ZIP_TRACT_062024.xlsx",
    "https://www.huduser.gov/portal/datasets/usps/ZIP_TRACT_032024.xlsx",
]
# Local cache path
HUD_LOCAL = RAW_DIR / "ZIP_TRACT_crosswalk.xlsx"

# Census 2020 ZCTA-to-Tract relationship file (area-based fallback)
CENSUS_ZCTA_TRACT_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
    "tab20_zcta520_tract20_natl.txt"
)
CENSUS_LOCAL = RAW_DIR / "tab20_zcta520_tract20_natl.txt"

TODAY = date.today().isoformat()
TIMEOUT = 120  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, label: str, token: str | None = None) -> bytes:
    """Fetch URL; return raw bytes. Raises requests.HTTPError on failure."""
    print(f"  Fetching {label} …")
    print(f"    {url}")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"    {len(r.content):,} bytes received")
    return r.content


def fetch_eig_dci() -> pd.DataFrame:
    """
    Attempt to download EIG DCI Excel file. Returns a DataFrame with columns:
        zip_code (str, 5-char), dci_score (float)
    Tries URLs in EIG_URLS order, then falls back to EIG_LOCAL.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Try local cache first
    if EIG_LOCAL.exists():
        print(f"Using cached EIG DCI file: {EIG_LOCAL}")
        return _parse_eig_xlsx(EIG_LOCAL.read_bytes())

    # Try live URLs
    last_exc = None
    for url in EIG_URLS:
        try:
            raw = _fetch(url, "EIG DCI Excel")
            EIG_LOCAL.write_bytes(raw)
            return _parse_eig_xlsx(raw)
        except Exception as exc:
            print(f"    Failed ({exc.__class__.__name__}: {exc})")
            last_exc = exc

    # All URLs failed
    raise RuntimeError(
        f"Could not fetch EIG DCI data. All URLs returned errors (last: {last_exc}).\n"
        "Manual download instructions:\n"
        "  1. Visit https://eig.org/distressed-communities/\n"
        "  2. Click the 'Download the Data' button to get the Excel file.\n"
        f"  3. Save it to: {EIG_LOCAL}\n"
        "  4. Re-run this script."
    )


def _parse_eig_xlsx(raw: bytes) -> pd.DataFrame:
    """
    Parse EIG DCI Excel bytes → DataFrame(zip_code, dci_score).

    EIG DCI spreadsheet structure (2023 edition):
      The main data sheet contains columns including:
        - zipcode / zip_code / ZIP (5-digit)
        - score / dci_score / Score (0–100 percentile, higher = more distressed)
        - quintile / Quintile (1–5, 1 = most distressed)
        - city, state, pop columns, and 7 indicator columns
      Sheet name varies by year; try first sheet if named sheet not found.
    """
    xl = pd.ExcelFile(io.BytesIO(raw))
    print(f"    Sheets found: {xl.sheet_names}")

    # Prefer sheets with 'data' or 'dci' in the name, else use first sheet
    sheet = xl.sheet_names[0]
    for name in xl.sheet_names:
        if any(kw in name.lower() for kw in ("data", "dci", "index", "zip")):
            sheet = name
            break

    df = xl.parse(sheet, dtype=str)
    print(f"    Parsing sheet '{sheet}': {len(df):,} rows, columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Find ZIP column
    zip_col = None
    for candidate in ("zipcode", "zip_code", "zip", "zcta", "zcta5"):
        if candidate in df.columns:
            zip_col = candidate
            break
    if zip_col is None:
        raise ValueError(
            f"Cannot find ZIP column in EIG DCI sheet '{sheet}'. "
            f"Available columns: {list(df.columns)}"
        )

    # Find score column
    score_col = None
    for candidate in ("score", "dci_score", "composite_score", "percentile", "index_score"):
        if candidate in df.columns:
            score_col = candidate
            break
    if score_col is None:
        raise ValueError(
            f"Cannot find score column in EIG DCI sheet '{sheet}'. "
            f"Available columns: {list(df.columns)}"
        )

    df = df[[zip_col, score_col]].copy()
    df = df.rename(columns={zip_col: "zip_code", score_col: "dci_score"})

    # Clean
    df["zip_code"] = df["zip_code"].str.strip().str.zfill(5)
    df["dci_score"] = pd.to_numeric(df["dci_score"], errors="coerce")
    df = df.dropna(subset=["zip_code", "dci_score"])
    df = df[df["zip_code"].str.match(r"^\d{5}$")]

    print(f"    Parsed {len(df):,} ZIP-level DCI scores")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# HUD ZIP-to-Tract crosswalk
# ---------------------------------------------------------------------------

def fetch_hud_crosswalk() -> pd.DataFrame:
    """
    Return HUD ZIP-to-Tract crosswalk DataFrame with columns:
        zip (str, 5-char), tract (str, 11-char GEOID), res_ratio (float)
    Tries, in order:
      1. Local cache (HUD_LOCAL)
      2. HUD REST API (requires HUD_API_TOKEN env var)
      3. HUD flat-file Excel downloads
      4. Census 2020 ZCTA-to-tract area-based relationship file
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if HUD_LOCAL.exists():
        print(f"Using cached HUD crosswalk file: {HUD_LOCAL}")
        return _parse_hud_xlsx(HUD_LOCAL.read_bytes())

    # Try HUD API
    token = os.environ.get(HUD_TOKEN_ENV)
    if token:
        try:
            raw = _fetch(HUD_API_URL, "HUD crosswalk API", token=token)
            return _parse_hud_api_json(raw)
        except Exception as exc:
            print(f"    HUD API failed ({exc}); trying flat file …")
    else:
        print(f"    No {HUD_TOKEN_ENV} env var; skipping HUD API.")

    # Try flat-file URLs
    last_exc = None
    for url in HUD_FLAT_URLS:
        try:
            raw = _fetch(url, "HUD crosswalk XLSX")
            HUD_LOCAL.write_bytes(raw)
            return _parse_hud_xlsx(raw)
        except Exception as exc:
            print(f"    Failed ({exc.__class__.__name__}: {exc})")
            last_exc = exc

    # Census area-based fallback
    print("Falling back to Census 2020 ZCTA-to-Tract area crosswalk (area-weighted) …")
    return _fetch_census_zcta_crosswalk()


def _parse_hud_api_json(raw: bytes) -> pd.DataFrame:
    """Parse HUD API JSON response into crosswalk DataFrame."""
    import json
    data = json.loads(raw)
    # HUD API returns {"data": {"results": [{"query": ..., "data": [{zip, tract, res_ratio, ...}]}]}}
    # or a flat list depending on the endpoint version
    rows = []
    if isinstance(data, dict):
        results = data.get("data", {})
        if isinstance(results, dict):
            results = results.get("results", [])
        for block in (results if isinstance(results, list) else [results]):
            for row in block.get("data", []):
                rows.append(row)
    elif isinstance(data, list):
        rows = data

    df = pd.DataFrame(rows)
    print(f"    HUD API returned {len(df):,} crosswalk rows")
    return _normalise_hud_df(df)


def _parse_hud_xlsx(raw: bytes) -> pd.DataFrame:
    """Parse HUD ZIP-to-Tract XLSX into crosswalk DataFrame."""
    xl = pd.ExcelFile(io.BytesIO(raw))
    print(f"    HUD XLSX sheets: {xl.sheet_names}")
    df = xl.parse(xl.sheet_names[0], dtype=str)
    df.columns = [str(c).strip().upper() for c in df.columns]
    print(f"    {len(df):,} rows, columns: {list(df.columns)}")
    return _normalise_hud_df(df)


def _normalise_hud_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise HUD crosswalk columns.
    HUD files use: ZIP, TRACT, RES_RATIO (or USPS_ZIP_PREF_CITY, etc.)
    API JSON uses: zip, tract, res_ratio (lowercase)
    """
    # Lowercase for uniform handling
    df.columns = [c.lower() for c in df.columns]

    zip_col = _find_col(df.columns, ("zip", "zipcode", "zip_code"))
    tract_col = _find_col(df.columns, ("tract", "geoid", "census_tract", "tract_fips"))
    res_col = _find_col(df.columns, ("res_ratio", "residential_ratio", "res_share"))

    if zip_col is None or tract_col is None:
        raise ValueError(
            f"Cannot identify ZIP or TRACT columns in HUD data. "
            f"Available: {list(df.columns)}"
        )

    result = df[[zip_col, tract_col]].copy()
    result = result.rename(columns={zip_col: "zip", tract_col: "tract"})

    if res_col:
        result["res_ratio"] = pd.to_numeric(df[res_col], errors="coerce").fillna(0.0)
    else:
        print("    WARNING: no res_ratio column found; using equal weights.")
        result["res_ratio"] = 1.0

    result["zip"] = result["zip"].astype(str).str.strip().str.zfill(5)
    result["tract"] = result["tract"].astype(str).str.strip().str.zfill(11)

    result = result.dropna(subset=["zip", "tract"])
    result = result[result["zip"].str.match(r"^\d{5}$")]
    result = result[result["tract"].str.match(r"^\d{11}$")]
    result = result[result["res_ratio"] > 0]

    print(f"    Normalised crosswalk: {len(result):,} rows, "
          f"{result['zip'].nunique():,} ZIPs, {result['tract'].nunique():,} tracts")
    return result.reset_index(drop=True)


def _fetch_census_zcta_crosswalk() -> pd.DataFrame:
    """
    Fetch Census 2020 ZCTA-to-Tract relationship file and return a
    DataFrame(zip, tract, res_ratio) where res_ratio is area-weighted
    (AREALAND fraction of each tract within the ZCTA).

    Census file columns (tab-delimited):
      ZCTA5CE20, GEOID_TRACT_20, NAMELSAD_ZCTA5_20, NAMELSAD_TRACT_20,
      AREALAND_ZCTA5_20, AREAWATER_ZCTA5_20, AREALAND_TRACT_20,
      AREAWATER_TRACT_20, AREALAND_PART, AREAWATER_PART
    """
    if CENSUS_LOCAL.exists():
        print(f"Using cached Census crosswalk: {CENSUS_LOCAL}")
        raw = CENSUS_LOCAL.read_bytes()
    else:
        try:
            raw = _fetch(CENSUS_ZCTA_TRACT_URL, "Census ZCTA-Tract relationship file")
            CENSUS_LOCAL.write_bytes(raw)
        except Exception as exc:
            raise RuntimeError(
                f"All crosswalk sources failed. Last error: {exc}\n"
                "Manual download instructions:\n"
                "  Option A (preferred — residential-weighted):\n"
                "    1. Register free at https://www.huduser.gov/hudapi/public/register/form\n"
                "    2. Set env var: export HUD_API_TOKEN=<your_token>\n"
                "    3. Re-run this script.\n"
                "  Option B (area-weighted fallback):\n"
                "    1. Download from:\n"
                "       https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
                "tab20_zcta520_tract20_natl.txt\n"
                f"    2. Save to: {CENSUS_LOCAL}\n"
                "    3. Re-run this script."
            ) from exc

    df = pd.read_csv(
        io.BytesIO(raw),
        sep="|",
        dtype=str,
        usecols=["ZCTA5CE20", "GEOID_TRACT_20", "AREALAND_PART", "AREALAND_ZCTA5_20"],
    )
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={
        "zcta5ce20": "zip",
        "geoid_tract_20": "tract",
    })

    df["zip"] = df["zip"].astype(str).str.strip().str.zfill(5)
    df["tract"] = df["tract"].astype(str).str.strip().str.zfill(11)
    df["arealand_part"] = pd.to_numeric(df["arealand_part"], errors="coerce").fillna(0)
    df["arealand_zcta5_20"] = pd.to_numeric(df["arealand_zcta5_20"], errors="coerce")

    # Compute area-based res_ratio: part_area / zcta_total_area
    # (This approximates the fraction of the ZCTA's land area in each tract)
    df["res_ratio"] = df["arealand_part"] / df["arealand_zcta5_20"].replace(0, float("nan"))
    df = df.dropna(subset=["res_ratio"])
    df = df[df["res_ratio"] > 0]
    df = df[df["zip"].str.match(r"^\d{5}$")]
    df = df[df["tract"].str.match(r"^\d{11}$")]

    print(f"    Census crosswalk: {len(df):,} rows (area-weighted, not residential-weighted)")
    return df[["zip", "tract", "res_ratio"]].reset_index(drop=True)


def _find_col(columns, candidates):
    """Return the first column name that matches any candidate (case-insensitive)."""
    col_lower = [c.lower() for c in columns]
    for cand in candidates:
        if cand.lower() in col_lower:
            return list(columns)[col_lower.index(cand.lower())]
    return None


# ---------------------------------------------------------------------------
# Join and compute
# ---------------------------------------------------------------------------

def build_tract_dci(
    dci_df: pd.DataFrame,
    crosswalk_df: pd.DataFrame,
    eligible_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join DCI ZIP scores to census tracts via crosswalk, filter to eligible
    tracts, and compute weighted average dci_score per tract.

    Parameters
    ----------
    dci_df       : DataFrame(zip_code, dci_score)
    crosswalk_df : DataFrame(zip, tract, res_ratio)
    eligible_df  : DataFrame with column 'geoid'

    Returns
    -------
    DataFrame(geoid, dci_score, dci_quintile, zip_primary, fetched_at)
    """
    # Join DCI → crosswalk on ZIP
    merged = crosswalk_df.merge(
        dci_df,
        left_on="zip",
        right_on="zip_code",
        how="inner",
    )
    print(f"DCI × crosswalk join: {len(merged):,} rows "
          f"({merged['tract'].nunique():,} unique tracts)")

    # Weighted average per tract
    merged["weighted_score"] = merged["dci_score"] * merged["res_ratio"]

    tract_agg = (
        merged.groupby("tract")
        .agg(
            sum_weighted=("weighted_score", "sum"),
            sum_weight=("res_ratio", "sum"),
        )
        .reset_index()
    )
    tract_agg["dci_score"] = tract_agg["sum_weighted"] / tract_agg["sum_weight"]

    # zip_primary: ZIP with the highest res_ratio for each tract
    zip_primary = (
        merged.sort_values("res_ratio", ascending=False)
        .drop_duplicates(subset=["tract"])
        [["tract", "zip"]]
        .rename(columns={"zip": "zip_primary"})
    )
    tract_agg = tract_agg.merge(zip_primary, on="tract", how="left")
    tract_agg = tract_agg[["tract", "dci_score", "zip_primary"]].rename(
        columns={"tract": "geoid"}
    )

    # Inner join with eligible tracts
    eligible_geoids = eligible_df[["geoid"]].drop_duplicates()
    result = eligible_geoids.merge(tract_agg, on="geoid", how="inner")

    print(f"Eligible tracts: {len(eligible_geoids):,} | "
          f"Matched to DCI: {len(result):,} "
          f"({100 * len(result) / len(eligible_geoids):.1f}%)")
    print(f"  Unmatched (no DCI coverage): "
          f"{len(eligible_geoids) - len(result):,} tracts")

    # Recompute quintile within the matched eligible-tract distribution
    # quintile 1 = most distressed (highest score on EIG's scale)
    result["dci_quintile"] = pd.qcut(
        result["dci_score"],
        q=5,
        labels=[5, 4, 3, 2, 1],  # reversed: highest score → quintile 1
    ).astype(int)

    result["fetched_at"] = TODAY

    return result[["geoid", "dci_score", "dci_quintile", "zip_primary", "fetched_at"]]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=== ingest_dci.py ===")
    print(f"Date: {TODAY}")

    # Load eligible tracts
    print(f"\nLoading eligible tracts from {ELIGIBLE_PARQUET} …")
    if not ELIGIBLE_PARQUET.exists():
        sys.exit(f"ERROR: {ELIGIBLE_PARQUET} not found. Run scripts/ingest_irs_appendix.py first.")
    eligible_df = pd.read_parquet(ELIGIBLE_PARQUET, columns=["geoid"])
    print(f"  {len(eligible_df):,} eligible tracts loaded")

    # Fetch EIG DCI
    print("\n--- Step 1: EIG Distressed Communities Index ---")
    try:
        dci_df = fetch_eig_dci()
    except RuntimeError as exc:
        print(f"\nFATAL: {exc}")
        sys.exit(1)

    # Fetch crosswalk
    print("\n--- Step 2: HUD ZIP-to-Tract crosswalk ---")
    try:
        crosswalk_df = fetch_hud_crosswalk()
    except RuntimeError as exc:
        print(f"\nFATAL: {exc}")
        sys.exit(1)

    # Build tract-level DCI
    print("\n--- Step 3: Join and compute tract-level DCI ---")
    result = build_tract_dci(dci_df, crosswalk_df, eligible_df)

    # Save
    result.to_parquet(OUT_PARQUET, index=False)
    print(f"\nSaved → {OUT_PARQUET}")

    # Summary stats
    print("\n--- Summary stats ---")
    print(f"  Rows in dci.parquet: {len(result):,}")
    print(f"  Eligible tracts with DCI coverage: {len(result):,} / {len(eligible_df):,} "
          f"({100 * len(result) / len(eligible_df):.1f}%)")
    print(f"  DCI score range: {result['dci_score'].min():.2f} – {result['dci_score'].max():.2f}")
    print(f"  DCI score mean:  {result['dci_score'].mean():.2f}")
    print(f"  Quintile distribution (1=most distressed):")
    print(result["dci_quintile"].value_counts().sort_index().to_string())

    print(f"\n  Unique primary ZIPs: {result['zip_primary'].nunique():,}")
    print(f"  fetched_at: {TODAY}")
    print("\nDone.")


if __name__ == "__main__":
    main()
