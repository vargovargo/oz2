"""
Shared definitions for the Native lands lens — used by analyze_designations.py,
analyze_native_lands.py and patch_geo_native.py so the thresholds cannot drift apart.

Input: rows of data/native_lands.parquet (columns as written by ingest_native_lands.py).

  land_res     ≥50% of 2020 residents live in federally recognized reservation or
               off-reservation trust land blocks. Tracts with no 2020 residents fall back to
               ≥50% of area.
  land_hhl     Hawaii only: ≥10% of 2020 residents live on Hawaiian Home Lands (homestead
               communities are small relative to tracts).
  native_land  land_res or land_hhl                                  ("land" lens)
  native_pop   Native residents ≥20% (ACS 2020–24; AIAN alone, + NHPI alone in Hawaii)
  native_maj   Native residents ≥50%
  land_area    area-based alternative to land_res (≥50% of area) — sensitivity check only
  tribal_tag   the broad finder/map flag: ≥10% of residents or area on reservation, trust or
               Home Land, or native_pop
"""

import pandas as pd

LAND_FED = 0.5
LAND_HHL = 0.10
POP_SUB = 0.20
POP_MAJ = 0.50
TAG_LAND = 0.10


def add_flags(n: pd.DataFrame) -> pd.DataFrame:
    n = n.copy()
    hi = n.geoid.str[:2] == "15"
    has_pop = n.pop2020.fillna(0) > 0
    fed_pop = n.federal_pop_share.fillna(0)
    hhl_pop = n.hhl_pop_share.fillna(0)
    n["land_area"] = n.federal_share >= LAND_FED
    n["land_res"] = (fed_pop >= LAND_FED).where(has_pop, n.land_area)
    n["land_hhl"] = hi & (hhl_pop >= LAND_HHL).where(has_pop, n.hhl_share >= LAND_HHL)
    n["native_land"] = n.land_res | n.land_hhl
    pct = n.native_pct.fillna(0)
    n["native_pop"] = pct >= POP_SUB
    n["native_maj"] = pct >= POP_MAJ
    n["tribal_tag"] = ((n.federal_share >= TAG_LAND) | (fed_pop >= TAG_LAND) | (n.hhl_share >= TAG_LAND)
                       | (hhl_pop >= TAG_LAND) | n.native_pop)
    return n
