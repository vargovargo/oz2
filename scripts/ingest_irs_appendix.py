"""
Fetch IRS Rev. Proc. 2026-14 Appendix → data/eligible_tracts.parquet
                                       → data/state_summaries.csv

Source
------
IRS Rev. Proc. 2026-14, released 2026-04-06.
Appendix Excel file: https://www.irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx

The appendix lists 25,332 census tracts that are low-income communities
eligible for nomination as Qualified Opportunity Zones under OZ 2.0 (OBBBA).
Of those, 8,334 are rural per Notice 2025-50, Section 4.01.

Columns in source (sheet "Appendix for Designation RP_cor")
------------------------------------------------------------
  State              — state name
  County             — county name (leading space stripped)
  Census Tract Number — 10- or 11-digit integer; zero-padded to 11 → GEOID
  Rural Status       — "Rural" | "Non-Rural"

Output schema (eligible_tracts.parquet)
---------------------------------------
  geoid         str   11-digit census tract GEOID
  state_fips    str   2-digit state FIPS
  county_fips   str   5-digit county FIPS
  state_name    str
  county_name   str
  is_rural      bool
  fetched_at    str   ISO date this script was run

Note: mfi, poverty_rate, and population are not in the IRS appendix.
Join data/dci.parquet (EIG Distressed Communities Index) on geoid for those.

State summaries (state_summaries.csv)
--------------------------------------
One row per state. Columns:
  state_fips, state_name, total_eligible, rural_eligible,
  pct_rural, max_designations (25% of total_eligible, ceil),
  top10_county_name, top10_county_fips, top10_county_eligible_count
  (last three are pipe-delimited strings of the top 10 counties)
"""

import io
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

APPENDIX_URL = "https://www.irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx"
DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PARQUET = DATA_DIR / "eligible_tracts.parquet"
OUT_CSV = DATA_DIR / "state_summaries.csv"

SHEET = "Appendix for Designation RP_cor"


def fetch_xlsx(url: str) -> bytes:
    print(f"Fetching {url} …")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    print(f"  {len(r.content):,} bytes received")
    return r.content


def parse_appendix(raw: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(raw), sheet_name=SHEET, dtype=str)

    # Normalise column names
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        "State": "state_name",
        "County": "county_name",
        "Census Tract Number": "tract_raw",
        "Rural Status": "rural_status",
    })

    df["state_name"] = df["state_name"].str.strip()
    df["county_name"] = df["county_name"].str.strip()
    df["tract_raw"] = df["tract_raw"].str.strip()

    # Zero-pad tract number to 11 digits → GEOID
    df["geoid"] = df["tract_raw"].str.zfill(11)

    df["state_fips"] = df["geoid"].str[:2]
    df["county_fips"] = df["geoid"].str[:5]
    df["is_rural"] = df["rural_status"].str.strip().str.lower() == "rural"
    df["fetched_at"] = date.today().isoformat()

    return df[["geoid", "state_fips", "county_fips", "state_name", "county_name",
               "is_rural", "fetched_at"]]


def compute_state_summaries(df: pd.DataFrame) -> pd.DataFrame:
    state_grp = df.groupby(["state_fips", "state_name"])
    agg = state_grp.agg(
        total_eligible=("geoid", "count"),
        rural_eligible=("is_rural", "sum"),
    ).reset_index()
    agg["pct_rural"] = (agg["rural_eligible"] / agg["total_eligible"] * 100).round(1)
    # 25% of eligible, rounded up — the statutory max designation quota
    agg["max_designations"] = agg["total_eligible"].apply(lambda n: math.ceil(n * 0.25))

    # Top-10 counties per state by eligible tract count
    county_counts = (
        df.groupby(["state_fips", "county_fips", "county_name"])
        .size()
        .reset_index(name="county_eligible_count")
    )

    def top10(grp):
        top = grp.nlargest(10, "county_eligible_count")
        return pd.Series({
            "top10_county_fips": "|".join(top["county_fips"]),
            "top10_county_name": "|".join(top["county_name"]),
            "top10_county_eligible_count": "|".join(top["county_eligible_count"].astype(str)),
        })

    top10_df = county_counts.groupby("state_fips").apply(top10, include_groups=False).reset_index()
    result = agg.merge(top10_df, on="state_fips", how="left")

    col_order = [
        "state_fips", "state_name",
        "total_eligible", "rural_eligible", "pct_rural", "max_designations",
        "top10_county_fips", "top10_county_name", "top10_county_eligible_count",
    ]
    return result[col_order].sort_values("state_fips").reset_index(drop=True)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw = fetch_xlsx(APPENDIX_URL)
    df = parse_appendix(raw)

    print(f"Parsed {len(df):,} eligible tracts across {df['state_fips'].nunique()} states/DC")
    print(f"  Rural: {df['is_rural'].sum():,} | Non-rural: {(~df['is_rural']).sum():,}")

    df.to_parquet(OUT_PARQUET, index=False)
    print(f"Saved → {OUT_PARQUET}")

    summaries = compute_state_summaries(df)
    summaries.to_csv(OUT_CSV, index=False)
    print(f"Saved → {OUT_CSV}")

    # Spot-check: print national totals
    print("\n--- National totals ---")
    print(f"  States/DC: {len(summaries)}")
    print(f"  Total eligible: {summaries['total_eligible'].sum():,}")
    print(f"  Rural eligible: {summaries['rural_eligible'].sum():,}")
    print(f"  Max total designations: {summaries['max_designations'].sum():,}")

    print("\n--- Top 10 states by total eligible ---")
    top_states = summaries.nlargest(10, "total_eligible")[
        ["state_name", "total_eligible", "rural_eligible", "pct_rural"]
    ]
    print(top_states.to_string(index=False))


if __name__ == "__main__":
    main()
