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

Output schema (data/urban_investability.parquet)
------------------------------------------------
  geoid               str   11-digit census tract GEOID (OZ 2.0 eligible tracts only)
  ui_invest_score     float Investability score from Urban Institute model
  ui_invest_quintile  int   1–5 quintile among covered tracts (1 = most investable)
  fetched_at          str   ISO date of ingestion

Coverage note
-------------
Only covers tracts where sufficient OZ 1.0 investment data existed to model from.
Tracts with no Urban Institute record receive null ui_invest_* in GeoJSON and map.
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
SCORE_CANDIDATES = [
    "investability_score", "invest_score", "score", "predicted_investment",
    "investment_score", "investability", "predicted_investability",
    "goldilocks_score", "readiness_score",
]
QUINTILE_CANDIDATES = [
    "ui_invest_quintile", "invest_quintile", "investability_quintile",
    "score_quintile", "quintile",
]


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

    # --- Detect score column ---
    score_col = find_column(df, SCORE_CANDIDATES, "investability score")
    print(f"  Using '{score_col}' as investability score column")
    df["ui_invest_score"] = pd.to_numeric(df[score_col], errors="coerce")

    # --- Detect or compute quintile ---
    quintile_col = None
    cols_lower = {c.lower(): c for c in df.columns}
    for candidate in QUINTILE_CANDIDATES:
        if candidate in df.columns or candidate.lower() in cols_lower:
            quintile_col = df.columns[list(cols_lower.keys()).index(candidate.lower())] \
                if candidate.lower() in cols_lower else candidate
            break

    if quintile_col:
        print(f"  Using '{quintile_col}' as quintile column (provided by Urban Institute)")
        df["ui_invest_quintile"] = pd.to_numeric(df[quintile_col], errors="coerce").astype("Int64")
    else:
        print("  Quintile column not found — computing from score distribution")
        valid = df["ui_invest_score"].dropna()
        print(f"  {len(valid):,} tracts with valid scores (range {valid.min():.2f}–{valid.max():.2f})")
        # Q1 = most investable (highest scores)
        df["ui_invest_quintile"] = pd.qcut(
            df["ui_invest_score"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop"
        ).astype("Int64")
        print("  NOTE: Verify quintile direction against Urban Institute documentation.")
        print("        Q1 is assigned to the HIGHEST scores here (most investable).")
        print("        If Urban Institute uses Q1 for lowest scores, swap labels to [1,2,3,4,5].")

    # --- Filter to OZ 2.0 eligible tracts only ---
    elig = pd.read_parquet(ELIG_FILE, columns=["geoid"])
    elig_set = set(elig["geoid"])
    before = len(df)
    df = df[df["geoid"].isin(elig_set)].copy()
    after = len(df)
    print(f"\n  Filtered to OZ 2.0 eligible tracts: {before:,} → {after:,} "
          f"({after / len(elig_set):.1%} coverage)")

    # --- Output ---
    out = df[["geoid", "ui_invest_score", "ui_invest_quintile"]].copy()
    out["fetched_at"] = str(date.today())
    out = out.drop_duplicates(subset="geoid")

    n_scored = out["ui_invest_score"].notna().sum()
    n_quintiled = out["ui_invest_quintile"].notna().sum()
    print(f"\n  Tracts with score:    {n_scored:,}")
    print(f"  Tracts with quintile: {n_quintiled:,}")
    print(f"\n  Quintile distribution:")
    print(out["ui_invest_quintile"].value_counts().sort_index().to_string())

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_FILE, index=False)
    print(f"\n  Wrote {OUT_FILE}  ({OUT_FILE.stat().st_size // 1024} KB)")
    print("\nNext steps:")
    print("  1. Review quintile direction note above if quintiles were auto-computed")
    print("  2. python scripts/build_state_geo.py   (rebuilds all 56 state GeoJSON files — ~15–40 min first run)")
    print("  3. python scripts/patch_overlay_stats.py   (updates state_metadata.yaml with Q1 counts)")
    print("  4. git add -A && git commit -m 'Add Urban Institute investability data'")
    print("  5. git push")


if __name__ == "__main__":
    main()
