#!/usr/bin/env python3
"""
Build per-state GeoJSON files for OZ 2.0 tract map visualization.

For each of 56 state/territory FIPS codes, downloads Census TIGER/Line 2022
tract boundaries, filters to OZ-eligible tracts, joins all overlay data, and
writes public/geo/{fips}.geojson.

Dependencies:
    pip install geopandas shapely fiona pyproj pandas pyarrow requests

    geopandas requires GDAL:
    - macOS:  brew install gdal
    - Ubuntu: apt-get install gdal-bin libgdal-dev python3-gdal
    - Conda:  conda install geopandas  (easiest, handles GDAL automatically)

Usage:
    python3 scripts/build_state_geo.py                # all states
    python3 scripts/build_state_geo.py --state 01     # Alabama only
    python3 scripts/build_state_geo.py --skip-existing
"""

import argparse
import sys
import tempfile
import traceback
import urllib.request
import zipfile
from pathlib import Path

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point
except ImportError:
    print("ERROR: geopandas not installed.")
    print("Run: pip install geopandas shapely fiona pyproj")
    print("  or: conda install geopandas")
    sys.exit(1)

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR  = REPO_ROOT / "data"
OUT_DIR   = REPO_ROOT / "public" / "geo"
RAW_DIR   = DATA_DIR / "raw" / "tiger"   # cached downloads (gitignored)

# GENZ 500k cartographic boundaries — already simplified, preferred for states + PR
GENZ_TRACT_URL  = "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_{fips}_tract_500k.zip"
GENZ_PLACE_URL  = "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_{fips}_place_500k.zip"

# Full TIGER/Line for territories without GENZ coverage
TIGER_TRACT_URL = "https://www2.census.gov/geo/tiger/TIGER2022/TRACT/tl_2022_{fips}_tract.zip"
TIGER_PLACE_URL = "https://www2.census.gov/geo/tiger/TIGER2022/PLACE/tl_2022_{fips}_place.zip"

# Territories that need full TIGER (no GENZ 500k available)
FULL_TIGER_FIPS = {"60", "66", "69", "78"}  # AS, GU, CNMI, USVI

STATE_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR",
    "78": "VI",
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def download_cached(url: str, dest: Path) -> Path:
    """Download url to dest if not already cached. Returns dest."""
    if dest.exists():
        print(f"    (cached) {dest.name}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"    Downloading {url.split('/')[-1]} ...", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f" {dest.stat().st_size // 1024} KB")
    except Exception as e:
        print(f" FAILED: {e}")
        if dest.exists():
            dest.unlink()
        raise
    return dest


def extract_shp(zip_path: Path, extract_dir: Path) -> Path | None:
    """Extract a zip and return the first .shp found."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    shp_files = list(extract_dir.glob("*.shp"))
    return shp_files[0] if shp_files else None


def load_shp(zip_path: Path, tmpdir: Path, suffix: str) -> gpd.GeoDataFrame | None:
    """Load a shapefile from a cached zip into a GeoDataFrame (EPSG:4326)."""
    extract_dir = tmpdir / suffix
    shp_path = extract_shp(zip_path, extract_dir)
    if shp_path is None:
        print(f"    WARNING: No .shp found in {zip_path.name}")
        return None
    gdf = gpd.read_file(shp_path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


# -------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------

def load_overlays() -> pd.DataFrame:
    """Join all parquet overlays into a single master DataFrame keyed on geoid."""
    print("Loading overlay parquets ...")

    elig   = pd.read_parquet(DATA_DIR / "eligible_tracts.parquet",
                             columns=["geoid", "state_fips", "county_fips",
                                      "state_name", "county_name", "is_rural"])
    dci    = pd.read_parquet(DATA_DIR / "dci.parquet",
                             columns=["geoid", "dci_score", "dci_quintile"])
    cra    = pd.read_parquet(DATA_DIR / "cra_lmi_overlap.parquet",
                             columns=["geoid", "income_level", "is_cra_lmi"])
    pp     = pd.read_parquet(DATA_DIR / "persistent_poverty.parquet",
                             columns=["county_fips", "is_persistent_poverty"])
    tribal = pd.read_parquet(DATA_DIR / "tribal_overlap.parquet",
                             columns=["geoid", "aian_pct", "tribal_area_name",
                                      "is_tribal_overlap"])
    cdfi   = pd.read_parquet(DATA_DIR / "cdfi_nmtc.parquet",
                             columns=["geoid", "cde_name", "qlici_amount"])

    # Aggregate NMTC per tract
    nmtc = (
        cdfi.groupby("geoid")
        .agg(nmtc_projects=("cde_name", "count"),
             nmtc_total_usd=("qlici_amount", "sum"))
        .reset_index()
    )
    nmtc["has_nmtc"] = True

    # Build master table
    master = elig.copy()
    master = master.merge(dci,    on="geoid",      how="left")
    master = master.merge(cra,    on="geoid",      how="left")
    master = master.merge(pp,     on="county_fips", how="left")
    master = master.merge(tribal, on="geoid",       how="left")
    master = master.merge(nmtc,   on="geoid",       how="left")

    # Optional: Urban Institute investability scores (requires ingest_urban_investability.py)
    ui_invest_path = DATA_DIR / "urban_investability.parquet"
    if ui_invest_path.exists():
        ui_invest = pd.read_parquet(ui_invest_path,
                                    columns=["geoid", "ui_invest_score", "ui_invest_quintile"])
        master = master.merge(ui_invest, on="geoid", how="left")
        print(f"  Urban Institute investability: {ui_invest['geoid'].nunique():,} scored tracts merged")
    else:
        master["ui_invest_score"] = None
        master["ui_invest_quintile"] = None
        print("  Note: urban_investability.parquet not found — ui_invest columns will be null")

    # Fill nulls for boolean/count columns
    for col in ("is_cra_lmi", "is_persistent_poverty", "is_tribal_overlap", "has_nmtc"):
        master[col] = master[col].fillna(False).astype(bool)
    master["nmtc_projects"] = master["nmtc_projects"].fillna(0).astype(int)
    master["nmtc_total_usd"] = master["nmtc_total_usd"].fillna(0.0).round(0)

    print(f"  {len(master):,} eligible tracts across "
          f"{master['state_fips'].nunique()} state/territory FIPS codes")
    return master


# -------------------------------------------------------------------
# Per-state build
# -------------------------------------------------------------------

def build_state(fips: str, state_rows: pd.DataFrame, tmpdir: Path) -> bool:
    """
    Download TIGER, filter, join overlays, spatial-join places, write GeoJSON.
    Returns True on success.
    """
    abbr       = STATE_ABBR.get(fips, fips)
    state_name = state_rows["state_name"].iloc[0]
    n_tracts   = len(state_rows)
    out_path   = OUT_DIR / f"{fips}.geojson"
    use_full_tiger = fips in FULL_TIGER_FIPS

    print(f"\n[{abbr}] {state_name}  ({n_tracts} eligible tracts)")

    # ------------------------------------------------------------------
    # 1. Download + load tract boundaries
    # ------------------------------------------------------------------
    tract_url = (TIGER_TRACT_URL if use_full_tiger else GENZ_TRACT_URL).format(fips=fips)
    tract_zip = RAW_DIR / f"tract_{fips}.zip"
    try:
        download_cached(tract_url, tract_zip)
    except Exception:
        print(f"  [{abbr}] Cannot download tract boundaries — skipping")
        return False

    gdf = load_shp(tract_zip, tmpdir / fips, "tract")
    if gdf is None:
        return False

    # Normalize GEOID column name (TIGER2022 uses GEOID, GENZ may use GEOID20)
    geoid_col = next((c for c in ("GEOID", "GEOID20") if c in gdf.columns), None)
    if geoid_col is None:
        print(f"  [{abbr}] No GEOID column found in shapefile — skipping")
        return False
    gdf = gdf.rename(columns={geoid_col: "geoid"})
    gdf["geoid"] = gdf["geoid"].astype(str).str.zfill(11)

    # Compute state outline from ALL tract boundaries (before filtering to eligible tracts)
    # This gives the full state boundary, not just the union of eligible tracts.
    state_union = gdf.geometry.unary_union

    # Filter to OZ-eligible tracts
    eligible_geoids = set(state_rows["geoid"])
    gdf = gdf[gdf["geoid"].isin(eligible_geoids)].copy()
    if gdf.empty:
        print(f"  [{abbr}] No eligible tracts matched in shapefile — skipping")
        return False

    # Simplify full TIGER files (GENZ 500k is already simplified)
    if use_full_tiger:
        gdf["geometry"] = gdf.geometry.simplify(0.001, preserve_topology=True)

    # ------------------------------------------------------------------
    # 2. Spatial-join tract centroids → Census Places (municipality name)
    # ------------------------------------------------------------------
    place_url = (TIGER_PLACE_URL if use_full_tiger else GENZ_PLACE_URL).format(fips=fips)
    place_zip = RAW_DIR / f"place_{fips}.zip"
    place_name_series = pd.Series(index=gdf["geoid"], dtype="object", name="place_name")

    try:
        download_cached(place_url, place_zip)
        places = load_shp(place_zip, tmpdir / fips, "place")
        if places is not None:
            name_col = next((c for c in ("NAME", "NAMELSAD") if c in places.columns), None)
            if name_col:
                places = places[[name_col, "geometry"]].copy()

                # Compute centroids as a separate GeoDataFrame
                centroids = gpd.GeoDataFrame(
                    {"geoid": gdf["geoid"].values},
                    geometry=gdf.geometry.centroid,
                    crs="EPSG:4326",
                )
                joined = centroids.sjoin(
                    places[["geometry", name_col]],
                    how="left",
                    predicate="within",
                )
                # Keep first match per geoid (sjoin can produce duplicates)
                joined = joined.groupby("geoid")[name_col].first()
                place_name_series = joined.rename("place_name")
    except Exception as e:
        print(f"  [{abbr}] Places unavailable ({e}); place_name will be null")

    # ------------------------------------------------------------------
    # 3. Join all overlay attributes
    # ------------------------------------------------------------------
    keep_cols = [
        "geoid", "county_name", "is_rural",
        "ui_invest_score", "ui_invest_quintile",
        "dci_score", "dci_quintile",
        "is_cra_lmi", "income_level",
        "is_persistent_poverty",
        "is_tribal_overlap", "tribal_area_name", "aian_pct",
        "has_nmtc", "nmtc_projects", "nmtc_total_usd",
    ]
    attrs = state_rows[keep_cols].set_index("geoid")
    gdf = gdf.set_index("geoid").join(attrs, how="left").join(place_name_series, how="left")
    gdf = gdf.reset_index()

    # Add state metadata
    gdf["state_abbr"] = abbr
    gdf["state_name"] = state_name

    # Round numeric columns for smaller output
    if "ui_invest_score" in gdf.columns:
        gdf["ui_invest_score"] = gdf["ui_invest_score"].round(2)
    if "dci_score" in gdf.columns:
        gdf["dci_score"] = gdf["dci_score"].round(1)
    if "aian_pct" in gdf.columns:
        gdf["aian_pct"] = gdf["aian_pct"].round(4)

    # ------------------------------------------------------------------
    # 4. Select final columns and write GeoJSON
    # ------------------------------------------------------------------
    output_props = [
        "geometry", "geoid", "county_name", "place_name", "state_name", "state_abbr",
        "is_rural", "ui_invest_score", "ui_invest_quintile",
        "dci_score", "dci_quintile",
        "is_cra_lmi", "income_level",
        "is_persistent_poverty",
        "is_tribal_overlap", "tribal_area_name", "aian_pct",
        "has_nmtc", "nmtc_projects", "nmtc_total_usd",
    ]
    out_cols = [c for c in output_props if c in gdf.columns]
    gdf = gdf[out_cols]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out_path, driver="GeoJSON")

    size_kb = out_path.stat().st_size // 1024
    print(f"  → {out_path.name}  {size_kb} KB  ({len(gdf)} tracts)")

    # Write lightweight state outline file (union of all tract boundaries, not just eligible)
    try:
        outline_gdf = gpd.GeoDataFrame(
            [{"state_fips": fips, "state_abbr": abbr, "state_name": state_name}],
            geometry=[state_union],
            crs="EPSG:4326",
        )
        outline_path = OUT_DIR / f"state-{fips}-outline.geojson"
        outline_gdf.to_file(outline_path, driver="GeoJSON")
        print(f"  → {outline_path.name}  {outline_path.stat().st_size // 1024} KB  (state outline)")
    except Exception as e:
        print(f"  [{abbr}] State outline failed: {e}")

    return True


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build per-state OZ 2.0 tract GeoJSON files for the map visualization.")
    parser.add_argument("--state", metavar="FIPS",
                        help="Process a single state FIPS (e.g. 01 for Alabama)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip states that already have an output GeoJSON")
    args = parser.parse_args()

    master = load_overlays()

    fips_list = [args.state] if args.state else sorted(master["state_fips"].unique())

    failures = []

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        for fips in fips_list:
            out_path = OUT_DIR / f"{fips}.geojson"
            if args.skip_existing and out_path.exists():
                abbr = STATE_ABBR.get(fips, fips)
                print(f"[{abbr}] Skipping (exists: {out_path.stat().st_size // 1024} KB)")
                continue

            state_rows = master[master["state_fips"] == fips].copy()
            if state_rows.empty:
                print(f"[{fips}] No data — skipping")
                continue

            try:
                ok = build_state(fips, state_rows, tmpdir)
            except Exception as e:
                abbr = STATE_ABBR.get(fips, fips)
                print(f"  [{abbr}] ERROR: {e}")
                traceback.print_exc()
                ok = False

            if not ok:
                failures.append(fips)

    # Summary
    produced = list(OUT_DIR.glob("*.geojson"))
    total_kb = sum(f.stat().st_size for f in produced) // 1024
    print(f"\n{'='*60}")
    print(f"Done. {len(produced)} files in {OUT_DIR}  ({total_kb:,} KB total)")
    if failures:
        abbrs = [STATE_ABBR.get(f, f) for f in failures]
        print(f"Failed states: {', '.join(abbrs)}")
    print(f"\nNext steps:")
    print(f"  1. npm run dev — open /states/alabama to verify the map")
    print(f"  2. git add public/geo/ && git commit -m 'Add per-state OZ tract GeoJSON'")


if __name__ == "__main__":
    main()
