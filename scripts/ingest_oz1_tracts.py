#!/usr/bin/env python3
"""
OZ 1.0 (2018) designations, crosswalked to 2020 census tracts.

    → data/oz1_tracts_2010.parquet  (8,764 designated 2018 QOZs, 2010 tract geography)
    → data/oz1_overlap.parquet      (every 2020 tract that overlaps a 2018 QOZ)

Why the crosswalk: OZ 1.0 was designated on 2010 census tracts; OZ 2.0 eligibility
and designation use 2020 tracts. About a quarter of tracts were split, merged or
redrawn in 2020, so a GEOID match alone undercounts renomination. We assign each
2020 tract the share of its land area that lay inside a 2018 QOZ.

Sources
-------
  IRS Notice 2018-48, IRB 2018-28 — table of 8,762 designated QOZs
      https://www.irs.gov/irb/2018-28_IRB
  IRS Notice 2019-42, IRB 2019-29 — two additional Puerto Rico tracts
      (72119130102, 72137122002)
      https://www.irs.gov/irb/2019-29_IRB
  Treasury, "Rural 2018 QOZs as Provided in Notice 2025-50" — 3,309 rural 2018 QOZs
      https://home.treasury.gov/system/files/131/QOZ-Rural-2018-Area-Zones-as-in-2025-50.xlsx
  Census Bureau 2020↔2010 tract relationship file
      https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt

Output schema
-------------
oz1_tracts_2010.parquet: geoid10, state_name, county_name, tract_type
                         ("Low-Income Community" | "Non-LIC Contiguous"), is_rural_2018
oz1_overlap.parquet:     geoid (2020), oz1_land_share (0–1), is_oz1 (share >= 0.5),
                         oz1_same_geoid (2020 GEOID was itself a 2018 QOZ)
"""

import re
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw" / "oz1"

URLS = {
    "irb2018.html": "https://www.irs.gov/irb/2018-28_IRB",
    "irb2019.html": "https://www.irs.gov/irb/2019-29_IRB",
    "rural2018.xlsx": "https://home.treasury.gov/system/files/131/QOZ-Rural-2018-Area-Zones-as-in-2025-50.xlsx",
    "rel.txt": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt",
    "ct_crosswalk.xlsx": "https://www2.census.gov/geo/docs/reference/ct_change/ct_cou_to_cousub_crosswalk.xlsx",
    "gaz_tracts_2024.zip": "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_tracts_national.zip",
}
PR_ADDITIONS = ["72119130102", "72137122002"]


def fetch(name: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / name
    if not dest.exists():
        print(f"  downloading {URLS[name]}")
        r = requests.get(URLS[name], headers={"User-Agent": "Mozilla/5.0 (oz2-ingest)"}, timeout=300)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def parse_2018_table(html: str) -> pd.DataFrame:
    """Rows of the Notice 2018-48 table: State | County | Tract | Tract Type | ACS source."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) >= 4 and re.fullmatch(r"\d{11}", cells[2]):
            rows.append(cells[:4])
    return pd.DataFrame(rows, columns=["state_name", "county_name", "geoid10", "tract_type"])


def connecticut_2022_geoids() -> dict[str, str]:
    """Map 2020 Connecticut tract GEOIDs (old counties) to 2022+ GEOIDs (planning regions).

    In 2022 Connecticut replaced its eight counties with nine planning regions as county
    equivalents. Tract numbers were kept; only the county portion of the GEOID changed.
    The 2020–2024 ACS and Treasury's OZ 2.0 files use the new GEOIDs; the 2020↔2010
    relationship file uses the old ones. Tract numbers are unique statewide except for a
    couple of codes, which are disambiguated with the Census county↔cousub crosswalk.
    """
    import io, zipfile
    with zipfile.ZipFile(fetch("gaz_tracts_2024.zip")) as z:
        g = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep="\t", dtype={"GEOID": str})
    new = [x for x in g.GEOID if x.startswith("09")]
    rel = pd.read_csv(fetch("rel.txt"), sep="|", dtype=str, encoding="utf-8-sig", usecols=["GEOID_TRACT_20"])
    old = sorted({x for x in rel.GEOID_TRACT_20 if x.startswith("09")})
    cw = pd.read_excel(fetch("ct_crosswalk.xlsx"), dtype=str)
    cw.columns = [c.split("\n")[0] for c in cw.columns]
    pairs = set(zip(cw.OLD_COUNTYFP, cw.NEW_COUNTYFP))
    mapping = {}
    for n in new:
        cands = [o for o in old if o[5:] == n[5:]]
        if len(cands) > 1:
            cands = [o for o in cands if (o[2:5], n[2:5]) in pairs]
        if len(cands) == 1:
            mapping[cands[0]] = n
    return mapping


def main() -> None:
    oz1 = parse_2018_table(fetch("irb2018.html").read_text())
    oz1 = pd.concat([oz1, pd.DataFrame({
        "state_name": "Puerto Rico", "county_name": None, "geoid10": PR_ADDITIONS,
        "tract_type": "Low-Income Community"})], ignore_index=True).drop_duplicates("geoid10")
    rural = pd.read_excel(fetch("rural2018.xlsx"), sheet_name="oz1rural", header=1, dtype=str)
    oz1["is_rural_2018"] = oz1.geoid10.isin(set(rural["Census Tract Number"]))
    assert len(oz1) == 8764, f"expected 8,764 OZ 1.0 tracts, got {len(oz1)}"
    oz1.to_parquet(DATA / "oz1_tracts_2010.parquet", index=False)

    rel = pd.read_csv(fetch("rel.txt"), sep="|", dtype=str, encoding="utf-8-sig",
                      usecols=["GEOID_TRACT_20", "GEOID_TRACT_10", "AREALAND_TRACT_20", "AREALAND_PART"])
    rel["part"] = rel.AREALAND_PART.astype(float)
    rel["land20"] = rel.AREALAND_TRACT_20.astype(float)
    rel["in_oz1"] = rel.GEOID_TRACT_10.isin(set(oz1.geoid10))
    rel["oz1_part"] = rel.part.where(rel.in_oz1, 0.0)
    g = rel.groupby("GEOID_TRACT_20").agg(land20=("land20", "first"),
                                         oz1_land=("oz1_part", "sum"),
                                         any_oz1=("in_oz1", "any"))
    g = g[g.any_oz1]
    # Water-only tracts have no land; fall back to "touches a 2018 QOZ".
    g["oz1_land_share"] = (g.oz1_land / g.land20.where(g.land20 > 0)).fillna(1.0).clip(0, 1)
    out = g.reset_index().rename(columns={"GEOID_TRACT_20": "geoid"})[["geoid", "oz1_land_share"]]
    ct = connecticut_2022_geoids()
    out["geoid"] = out.geoid.map(lambda x: ct.get(x, x))
    out["is_oz1"] = out.oz1_land_share >= 0.5
    out["oz1_same_geoid"] = g.index.isin(set(oz1.geoid10))
    out.to_parquet(DATA / "oz1_overlap.parquet", index=False)
    print(f"  OZ 1.0 tracts (2010 geography): {len(oz1):,} (rural {oz1.is_rural_2018.sum():,})")
    print(f"  2020 tracts >=50% inside a 2018 QOZ: {out.is_oz1.sum():,}")


if __name__ == "__main__":
    main()
