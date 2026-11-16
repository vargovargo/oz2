#!/usr/bin/env python3
"""
Recompute `place_name` for every tract in public/geo/*.geojson.

Repairs a bug in build_state_geo.py (fixed 2026-11-16, see assign_place_names there): the
tract→place spatial join paired each GEOID with another row's point, so place names on the
map popups, state-page tract finder and the national CSV were wrong — e.g. Marin County tract
06041112202 (San Rafael) was labelled "Long Beach".

This rewrites only `place_name`, using the tract geometry already in each GeoJSON and the same
Census cartographic place files build_state_geo.py uses. Every other property is untouched.

Usage:
    python3 scripts/patch_geo_places.py
Then re-run scripts/analyze_designations.py so data/designations_by_state.json and
public/data/oz2-designations-2027.csv pick up the corrected names.
"""

import json
import sys
import tempfile
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).parent))
from build_state_geo import (FULL_TIGER_FIPS, GENZ_PLACE_URL, RAW_DIR,  # noqa: E402
                             TIGER_PLACE_URL, assign_place_names, download_cached, load_shp)

GEO = Path(__file__).parent.parent / "public" / "geo"


def main() -> None:
    changed_total = n_total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(GEO.glob("[0-9][0-9].geojson")):
            fips = path.stem
            fc = json.loads(path.read_text())
            tracts = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
            url = (TIGER_PLACE_URL if fips in FULL_TIGER_FIPS else GENZ_PLACE_URL).format(fips=fips)
            places = load_shp(download_cached(url, RAW_DIR / f"place_{fips}.zip"), Path(tmp) / fips, "place")
            name_col = next(c for c in ("NAME", "NAMELSAD") if c in places.columns)
            names = assign_place_names(tracts, places, name_col)
            changed = 0
            for f in fc["features"]:
                p = f["properties"]
                new = names.get(p["geoid"])
                new = new if isinstance(new, str) else None
                if new != p.get("place_name"):
                    changed += 1
                p["place_name"] = new
            path.write_text(json.dumps(fc, separators=(",", ":")))
            print(f"  {fips}: {changed:,} of {len(fc['features']):,} place names corrected")
            changed_total += changed
            n_total += len(fc["features"])
    print(f"  total: {changed_total:,} of {n_total:,} tracts changed")


if __name__ == "__main__":
    main()
