#!/usr/bin/env python3
"""
Refresh the Native-lands properties in public/geo/*.geojson from data/native_lands.parquet.

    is_tribal_overlap   ≥10% reservation / trust land / Hawaiian Home Land, or ≥20% Native residents
                        (same rule as the "tribal" tag in analyze_designations.py)
    tribal_area_name    federally recognized entity with the most land in the tract, else the
                        largest AIANNH area of any kind (OTSA, ANVSA, SDTSA, HHL)
    native_land_share   share of tract area in federal reservation / trust land (0–1)
    hhl_share           share in Hawaiian Home Lands (0–1)
    aian_pct            Native share of residents (AIAN alone; in Hawaii AIAN + NHPI alone), ACS 2020–2024

Replaces the values written by build_state_geo.py from the older tribal_overlap.parquet.
Run after ingest_native_lands.py and after any patch_geo_designations.py that appends tracts.

Usage:
    python3 scripts/patch_geo_native.py
"""

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
GEO = ROOT / "public" / "geo"


def clean(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


def main() -> None:
    n = pd.read_parquet(ROOT / "data" / "native_lands.parquet").set_index("geoid")
    native_pop = n.native_pct.fillna(0) >= 0.20
    flag = (n.federal_share >= 0.10) | (n.hhl_share >= 0.10) | native_pop
    name = n.federal_name.fillna(n.native_area_name).where(flag)
    changed = total = 0
    for f in sorted(GEO.glob("[0-9][0-9].geojson")):
        gj = json.loads(f.read_text())
        for feat in gj["features"]:
            p = feat["properties"]
            g = p["geoid"]
            if g not in n.index:
                continue
            total += 1
            new = {
                "is_tribal_overlap": bool(flag[g]),
                "tribal_area_name": clean(name[g]),
                "native_land_share": round(float(n.federal_share[g]), 3),
                "hhl_share": round(float(n.hhl_share[g]), 3),
                "aian_pct": clean(None if pd.isna(n.native_pct[g]) else round(float(n.native_pct[g]), 4)),
            }
            if p.get("is_tribal_overlap") != new["is_tribal_overlap"]:
                changed += 1
            p.update(new)
        f.write_text(json.dumps(gj, separators=(",", ":")))
    print(f"  {total:,} features updated; tribal flag changed on {changed:,}; flagged now: {int(flag.sum()):,}")


if __name__ == "__main__":
    main()
