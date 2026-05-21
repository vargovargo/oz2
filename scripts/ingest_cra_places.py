"""
Build data/cra_lmi_places.json — per-state city and ZIP summaries for
tracts that are both OZ 2.0-eligible and CRA LMI-designated.

Sources
-------
  data/cra_lmi_overlap.parquet   — from ingest_cra_lmi.py
  data/eligible_tracts.parquet   — state/county info
  data/raw/ZIP_TRACT_122025.xlsx — HUD ZIP-to-tract crosswalk
      Columns: ZIP, TRACT (11-digit GEOID), USPS_ZIP_PREF_CITY, RES_RATIO, ...

Output: data/cra_lmi_places.json
------
{
  "<state_fips>": {
    "cities": [{"name": "Houston", "tracts": 375}, ...],  // all cities, desc
    "zips":   [{"zip": "77001", "city": "Houston", "tracts": 14}, ...]  // all ZIPs, desc
  },
  ...
}

All cities and all ZIPs are included (sorted by tract count descending).
The Astro template shows the top 5 and uses <details> for the full list.
"""

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

ZIP_TRACT_XLSX = RAW_DIR / "ZIP_TRACT_122025.xlsx"
CRA_PARQUET = DATA_DIR / "cra_lmi_overlap.parquet"
ELIG_PARQUET = DATA_DIR / "eligible_tracts.parquet"
OUT_JSON = DATA_DIR / "cra_lmi_places.json"


def main():
    print("=== ingest_cra_places.py ===")

    for p in (ZIP_TRACT_XLSX, CRA_PARQUET, ELIG_PARQUET):
        if not p.exists():
            raise FileNotFoundError(f"Required file missing: {p}")

    # ---- Load inputs ----
    print("Loading ZIP-tract crosswalk …")
    zt = pd.read_excel(ZIP_TRACT_XLSX, dtype=str)
    zt["RES_RATIO"] = pd.to_numeric(zt["RES_RATIO"], errors="coerce").fillna(0)
    zt = zt.rename(columns={"TRACT": "geoid", "USPS_ZIP_PREF_CITY": "city"})
    zt["city"] = zt["city"].str.strip().str.title()
    zt["ZIP"] = zt["ZIP"].str.strip().str.zfill(5)
    print(f"  {len(zt):,} ZIP-tract pairs")

    print("Loading CRA overlap parquet …")
    cra = pd.read_parquet(CRA_PARQUET)
    overlap_geoids = set(cra.loc[cra["is_cra_lmi"], "geoid"].astype(str))
    print(f"  {len(overlap_geoids):,} CRA+OZ overlap tracts")

    print("Loading eligible tracts parquet …")
    elig = pd.read_parquet(ELIG_PARQUET)[["geoid", "state_fips", "county_name"]]
    elig["geoid"] = elig["geoid"].astype(str)

    # ---- Filter ZIP-tract pairs to overlap tracts ----
    hits = zt[zt["geoid"].isin(overlap_geoids)].copy()
    hits = hits.merge(elig, on="geoid", how="left")
    print(f"  ZIP-tract pairs touching overlap tracts: {len(hits):,}")

    # ---- City fallback: use county name when city is blank ----
    hits["city"] = hits["city"].where(
        hits["city"].notna() & (hits["city"].str.strip() != ""),
        hits["county_name"].str.title() + " County"
    )

    # ---- Per-state aggregation ----
    result: dict = {}

    for state_fips, grp in hits.groupby("state_fips"):
        # Cities: count distinct tracts per city (a tract may touch multiple ZIPs
        # with the same city; deduplicate tract-city pairs before counting)
        city_tracts = (
            grp[["geoid", "city"]]
            .drop_duplicates()
            .groupby("city")["geoid"]
            .count()
            .sort_values(ascending=False)
        )
        cities = [
            {"name": name, "tracts": int(cnt)}
            for name, cnt in city_tracts.items()
        ]

        # ZIPs: for each ZIP, count distinct overlap tracts; label with the
        # USPS preferred city of that ZIP (use mode across rows for ZIP).
        zip_city = (
            grp.groupby("ZIP")["city"]
            .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
        )
        zip_tracts = (
            grp.groupby("ZIP")["geoid"]
            .nunique()
            .sort_values(ascending=False)
        )
        zips = [
            {"zip": z, "city": zip_city.get(z, ""), "tracts": int(cnt)}
            for z, cnt in zip_tracts.items()
        ]

        result[state_fips] = {"cities": cities, "zips": zips}

    # ---- Write output ----
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nSaved → {OUT_JSON}")

    # Summary
    total_cities = sum(len(v["cities"]) for v in result.values())
    total_zips = sum(len(v["zips"]) for v in result.values())
    print(f"  {len(result)} states")
    print(f"  {total_cities:,} city entries  ({total_cities // len(result):.0f} avg per state)")
    print(f"  {total_zips:,} ZIP entries    ({total_zips // len(result):.0f} avg per state)")

    # Spot-check
    tx = result.get("48", {})
    if tx:
        print(f"\n  Texas top 5 cities: {[c['name'] for c in tx['cities'][:5]]}")
        print(f"  Texas top 5 ZIPs:   {[(z['zip'], z['city']) for z in tx['zips'][:5]]}")


if __name__ == "__main__":
    main()
