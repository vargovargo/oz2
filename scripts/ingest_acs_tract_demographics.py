#!/usr/bin/env python3
"""
ACS 2020–2024 5-year tract demographics for OZ 2.0 eligible tracts.

    → data/acs_tract_demographics.parquet

Same ACS vintage Treasury used to determine eligibility (2020–2024 5-year), so the
demographics line up with the income and poverty figures in data/oz2_tracts.parquet.

Source
------
Census Bureau ACS Summary File, table-based format (no API key required):
  https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/
  acsdt5y2024-<table>.dat — pipe-delimited, GEO_ID column, one file per table, all
  geographies. Tract rows have GEO_ID prefix "1400000US".
Census Gazetteer 2024 tracts (land area for population density):
  https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_tracts_national.zip

The Island Areas (AS, GU, MP, VI) are not in the ACS; their rows are null.

Output columns
--------------
  geoid, pop, median_age, pct_white_nh, pct_black_nh, pct_hispanic, pct_asian_nh,
  pct_aian_nh, pct_nonwhite, unemp_rate, lfpr, pct_ba_plus, pct_no_hs,
  pct_renter, vacancy_rate, median_home_value, median_gross_rent, median_hh_income,
  pct_rent_burdened, housing_units, land_sqmi, pop_density
"""

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw" / "acs2024"
ACS = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-{t}.dat"
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_tracts_national.zip"
TABLES = ["b01003", "b01002", "b03002", "b23025", "b15003", "b25003", "b25002",
          "b25077", "b25064", "b19013", "b25070"]


def fetch(url: str, name: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / name
    if not dest.exists():
        print(f"  downloading {name}")
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return dest


def load_table(t: str, geoids: set[str]) -> pd.DataFrame:
    path = fetch(ACS.format(t=t), f"{t}.dat")
    chunks = []
    for ch in pd.read_csv(path, sep="|", dtype=str, chunksize=200_000):
        ch = ch[ch.GEO_ID.str.startswith("1400000US")]
        ch["geoid"] = ch.GEO_ID.str[9:]
        ch = ch[ch.geoid.isin(geoids)]
        est = [c for c in ch.columns if "_E" in c]
        chunks.append(ch[["geoid"] + est])
    df = pd.concat(chunks).set_index("geoid")
    df = df.apply(pd.to_numeric, errors="coerce")
    return df.where(df >= 0)  # negative values are ACS suppression sentinels


def share(num, den):
    return (num / den.where(den > 0)).round(4)


def main() -> None:
    tracts = pd.read_parquet(DATA / "oz2_tracts.parquet", columns=["geoid"])
    ids = set(tracts.geoid)
    T = {t: load_table(t, ids) for t in TABLES}
    out = pd.DataFrame(index=sorted(ids))
    out.index.name = "geoid"

    out["pop"] = T["b01003"]["B01003_E001"]
    out["median_age"] = T["b01002"]["B01002_E001"]
    r = T["b03002"]
    out["pct_white_nh"] = share(r.B03002_E003, r.B03002_E001)
    out["pct_black_nh"] = share(r.B03002_E004, r.B03002_E001)
    out["pct_aian_nh"] = share(r.B03002_E005, r.B03002_E001)
    out["pct_asian_nh"] = share(r.B03002_E006, r.B03002_E001)
    out["pct_hispanic"] = share(r.B03002_E012, r.B03002_E001)
    out["pct_nonwhite"] = share(r.B03002_E001 - r.B03002_E003, r.B03002_E001)
    e = T["b23025"]
    out["unemp_rate"] = share(e.B23025_E005, e.B23025_E003)
    out["lfpr"] = share(e.B23025_E002, e.B23025_E001)
    ed = T["b15003"]
    out["pct_ba_plus"] = share(ed[[f"B15003_E0{i}" for i in range(22, 26)]].sum(axis=1), ed.B15003_E001)
    out["pct_no_hs"] = share(ed[[f"B15003_E{i:03d}" for i in range(2, 17)]].sum(axis=1), ed.B15003_E001)
    ten = T["b25003"]
    out["pct_renter"] = share(ten.B25003_E003, ten.B25003_E001)
    occ = T["b25002"]
    out["housing_units"] = occ.B25002_E001
    out["vacancy_rate"] = share(occ.B25002_E003, occ.B25002_E001)
    out["median_home_value"] = T["b25077"]["B25077_E001"]
    out["median_gross_rent"] = T["b25064"]["B25064_E001"]
    out["median_hh_income"] = T["b19013"]["B19013_E001"]
    rb = T["b25070"]
    out["pct_rent_burdened"] = share(rb[["B25070_E007", "B25070_E008", "B25070_E009", "B25070_E010"]].sum(axis=1),
                                     rb.B25070_E001 - rb.B25070_E011)

    gz = fetch(GAZ, "gaz_tracts.zip")
    with zipfile.ZipFile(gz) as z:
        g = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep="\t", dtype={"GEOID": str})
    g.columns = g.columns.str.strip()
    g = g.set_index("GEOID")
    out["land_sqmi"] = g.ALAND_SQMI.reindex(out.index)
    out["pop_density"] = (out["pop"] / out.land_sqmi.where(out.land_sqmi > 0)).round(1)

    out.reset_index().to_parquet(DATA / "acs_tract_demographics.parquet", index=False)
    print(f"  tracts: {len(out):,}; with population: {out['pop'].notna().sum():,}; with land area: {out.land_sqmi.notna().sum():,}")


if __name__ == "__main__":
    main()
