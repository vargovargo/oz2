"""
Ingest Urban Institute investability dataset → data/urban_investability.parquet

Source
------
Urban Institute, "Data to Inform 2026 Opportunity Zone Selections"
https://datacatalog.urban.org/dataset/data-inform-2026-opportunity-zone-selections

File location
-------------
Place the downloaded file at ONE of:
  data/raw/investability_urban.csv      ← CSV (preferred if that's what you have)
  data/raw/urban_investability.xlsx     ← Excel fallback

Input data note
---------------
The Urban Institute dataset uses a 3-tier categorical classification column
('oztoolclassification') rather than a numeric score. This script maps it to
a 1–3 ordinal tier used as both ui_invest_score and ui_invest_quintile:
  Tier 1: "More likely to attract OZ investment, with larger impact"  (sweet spot)
  Tier 2: "Likely to attract capital even without OZ designation"     (overheated)
  Tier 3: "Less likely to attract OZ investment"                      (low probability)

Output schema (data/urban_investability.parquet)
------------------------------------------------
  geoid               str   11-digit census tract GEOID (OZ 2.0 eligible tracts only)
  ui_invest_score     float 1.0 / 2.0 / 3.0 ordinal from classification (1 = best)
  ui_invest_quintile  int   same ordinal as int (1–3); null for unscored tracts
  ui_invest_label     str   full category label from Urban Institute
  fetched_at          str   ISO date of ingestion

Coverage note
-------------
All 25,259 rows in the Urban Institute CSV have a classification. After filtering
to OZ 2.0 eligible tracts, expect ~25,000 rows covered.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_FILE  = DATA_DIR / "urban_investability.parquet"
ELIG_FILE = DATA_DIR / "eligible_tracts.parquet"

# Candidate raw file locations, checked in order
RAW_CANDIDATES = [
    DATA_DIR / "raw" / "investability_urban.csv",
    DATA_DIR / "raw" / "urban_investability.csv",
    DATA_DIR / "raw" / "urban_investability.xlsx",
    DATA_DIR / "raw" / "investability_urban.xlsx",
]

GEOID_CANDIDATES = [
    "geoid", "GEOID", "tract_geoid", "TRACTFIPS", "tractfips",
    "census_tract", "Census Tract", "CensusTract", "tract_id",
]

# 3-tier classification mapping (Tier 1 = most desirable for OZ purposes)
CLASSIFICATION_COLUMN = "oztoolclassification"
CLASSIFICATION_MAP = {
    "More likely to attract OZ investment, with larger impact": 1,
    "Likely to attract capital even without OZ designation": 2,
    "Less likely to attract OZ investment": 3,
}


def find_column(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    cols_lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    print(f"\nCould not auto-detect {label} column.")
    print(f"Available columns: {list(df.columns)}")
    print(f"Tried: {candidates}")
    sys.exit(1)


def load_raw() -> pd.DataFrame:
    for path in RAW_CANDIDATES:
        if path.exists():
            print(f"Reading {path.name} …")
            if path.suffix == ".csv":
                df = pd.read_csv(path, dtype=str, low_memory=False)
            else:
                xl = pd.ExcelFile(path)
                print(f"  Sheets: {xl.sheet_names}")
                df = xl.parse(xl.sheet_names[0])
            print(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
            print(f"  Columns: {list(df.columns)}")
            return df

    print(f"""
ERROR: Urban Institute data file not found. Checked:
{"".join(f"  {p}" + chr(10) for p in RAW_CANDIDATES)}
Place the file at one of the paths above and re-run.
""")
    sys.exit(1)


def main():
    if not ELIG_FILE.exists():
        sys.exit(f"Missing eligible_tracts.parquet at {ELIG_FILE}. Run ingest_irs_appendix.py first.")

    df = load_raw()

    # --- Detect and normalize GEOID ---
    geoid_col = find_column(df, GEOID_CANDIDATES, "GEOID")
    print(f"  Using '{geoid_col}' as GEOID column")
    df["geoid"] = df[geoid_col].astype(str).str.strip().str.zfill(11)

    # --- Map classification column to 1–3 ordinal ---
    if CLASSIFICATION_COLUMN not in df.columns:
        print(f"\nERROR: Expected classification column '{CLASSIFICATION_COLUMN}' not found.")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    print(f"\n  Classification column: '{CLASSIFICATION_COLUMN}'")
    print("  Category breakdown:")
    for label, count in df[CLASSIFICATION_COLUMN].value_counts().items():
        tier = CLASSIFICATION_MAP.get(str(label), "UNMAPPED")
        print(f"    Tier {tier}: {count:,}  —  {label}")

    unmapped = df[~df[CLASSIFICATION_COLUMN].isin(CLASSIFICATION_MAP)][CLASSIFICATION_COLUMN].unique()
    if len(unmapped):
        print(f"\n  WARNING: {len(unmapped)} unmapped category value(s): {unmapped}")
        print("  These tracts will have null tier values.")

    df["ui_invest_quintile"] = df[CLASSIFICATION_COLUMN].map(CLASSIFICATION_MAP).astype("Int64")
    df["ui_invest_score"]    = df["ui_invest_quintile"].astype(float)
    df["ui_invest_label"]    = df[CLASSIFICATION_COLUMN].astype(str)

    # --- Filter to OZ 2.0 eligible tracts only ---
    elig = pd.read_parquet(ELIG_FILE, columns=["geoid"])
    elig_set = set(elig["geoid"])
    before = len(df)
    df = df[df["geoid"].isin(elig_set)].copy()
    after = len(df)
    print(f"\n  Filtered to OZ 2.0 eligible tracts: {before:,} → {after:,} "
          f"({after / len(elig_set):.1%} coverage)")

    # --- Output ---
    out = df[["geoid", "ui_invest_score", "ui_invest_quintile", "ui_invest_label"]].copy()
    out["fetched_at"] = str(date.today())
    out = out.drop_duplicates(subset="geoid")

    n_tier1 = (out["ui_invest_quintile"] == 1).sum()
    n_tier2 = (out["ui_invest_quintile"] == 2).sum()
    n_tier3 = (out["ui_invest_quintile"] == 3).sum()
    print(f"\n  Tier 1 (sweet spot):  {n_tier1:,}")
    print(f"  Tier 2 (overheated):  {n_tier2:,}")
    print(f"  Tier 3 (low prob):    {n_tier3:,}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_FILE, index=False)
    print(f"\n  Wrote {OUT_FILE}  ({OUT_FILE.stat().st_size // 1024} KB)")
    print("\nNext steps:")
    print("  1. python scripts/build_state_geo.py --state 39  (Ohio test)")
    print("  2. python scripts/build_state_geo.py             (full run)")
    print("  3. python scripts/patch_overlay_stats.py         (updates state_metadata.yaml)")
    print("  4. npm run dev → verify map at http://localhost:4321/states/ohio")


if __name__ == "__main__":
    main()
