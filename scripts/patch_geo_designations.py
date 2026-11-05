#!/usr/bin/env python3
"""
Add 2027 designation status to the per-state map GeoJSON in public/geo/.

For every feature:   is_designated (bool), qozid (str|null), is_oz1 (bool)
Missing tracts:      the 130 tracts Treasury added to the eligible list in October 2026
                     are not in the April-era GeoJSON. Their boundaries are pulled from the
                     same Census cartographic files build_state_geo.py uses and appended,
                     with null overlay fields (CRA, DCI, Urban, NMTC were joined to the
                     April list and have no values for them).

Cheaper than a full build_state_geo.py run and leaves every existing property untouched.

Usage:
    python3 scripts/patch_geo_designations.py
"""

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build_state_geo import (FULL_TIGER_FIPS, GENZ_TRACT_URL, RAW_DIR, STATE_ABBR,  # noqa: E402
                             TIGER_TRACT_URL, download_cached, load_shp)

ROOT = Path(__file__).parent.parent
GEO = ROOT / "public" / "geo"


def main() -> None:
    t = pd.read_parquet(ROOT / "data" / "oz2_tracts.parquet")
    oz1 = pd.read_parquet(ROOT / "data" / "oz1_overlap.parquet")
    oz1_ids = set(oz1.loc[oz1.is_oz1, "geoid"])
    qoz = dict(zip(t.geoid, t.qozid))
    info = t.set_index("geoid")

    added_total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for fips, g in t.groupby("state_fips"):
            path = GEO / f"{fips}.geojson"
            if not path.exists():
                print(f"  {fips}: no GeoJSON, skipped")
                continue
            fc = json.loads(path.read_text())
            have = {f["properties"]["geoid"] for f in fc["features"]}
            missing = sorted(set(g.geoid) - have)
            if missing:
                url = (TIGER_TRACT_URL if fips in FULL_TIGER_FIPS else GENZ_TRACT_URL).format(fips=fips)
                gdf = load_shp(download_cached(url, RAW_DIR / url.split("/")[-1]), Path(tmp), fips)
                col = next(c for c in ("GEOID", "GEOID20") if c in gdf.columns)
                gdf = gdf[gdf[col].isin(missing)]
                if fips in FULL_TIGER_FIPS:
                    gdf["geometry"] = gdf.geometry.simplify(0.001, preserve_topology=True)
                for _, row in gdf.iterrows():
                    r = info.loc[row[col]]
                    fc["features"].append({
                        "type": "Feature",
                        "properties": {
                            "geoid": row[col], "county_name": r.county_name, "place_name": None,
                            "state_name": r.state_name, "state_abbr": STATE_ABBR.get(fips),
                            "is_rural": bool(r.is_rural), "added_oct2026": True,
                        },
                        "geometry": json.loads(gpd_to_json(row.geometry)),
                    })
                added_total += len(gdf)
                if len(gdf) < len(missing):
                    print(f"  {fips}: {len(missing) - len(gdf)} added tracts had no boundary in {url.split('/')[-1]}")
            for f in fc["features"]:
                p = f["properties"]
                p["is_designated"] = qoz.get(p["geoid"]) is not None and not pd.isna(qoz.get(p["geoid"]))
                p["qozid"] = qoz.get(p["geoid"]) if p["is_designated"] else None
                p["is_oz1"] = p["geoid"] in oz1_ids
            path.write_text(json.dumps(fc, separators=(",", ":")))
    print(f"  appended {added_total} tracts added to the eligible list in October 2026")


def gpd_to_json(geom) -> str:
    from shapely.geometry import mapping
    return json.dumps(mapping(geom))


if __name__ == "__main__":
    main()
