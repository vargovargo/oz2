"""
Identify eligible OZ 2.0 tracts with tribal overlap → data/tribal_overlap.parquet

Sources
-------
1. Census ACS 5-year estimates (2022 vintage), Table B02001 — Race:
   https://api.census.gov/data/2022/acs/acs5
   - B02001_001E  Total population
   - B02001_004E  American Indian and Alaska Native alone population
   No API key required for unauthenticated requests (up to 500/day).

2. Census TIGER/Line 2023 — American Indian / Alaska Native / Native Hawaiian Areas:
   https://www2.census.gov/geo/tiger/TIGER2023/AIANNH/tl_2023_us_aiannh.zip
   Includes federally recognised reservations, off-reservation trust land, tribal
   designated statistical areas (TDSAs), state-designated tribal statistical areas
   (SDTSAs), and Oklahoma tribal statistical areas (OTSAs).

3. Census TIGER/Line 2022 — Census Tracts (national):
   https://www2.census.gov/geo/tiger/TIGER2022/TRACT/tl_2022_us_census_tract.zip
   Used only when geopandas is available to supply tract geometries for the
   spatial join.

Methodology
-----------
Primary path (requires geopandas):
  a. Download AIANNH polygon shapefile.
  b. Download national tract centroid shapefile (or compute centroids from full
     tract polygons).  Because downloading all ~74 k tract polygons (~800 MB) is
     slow, we use the per-state TIGER tract files filtered to eligible GEOIDs only.
     Actually, to avoid per-state loops, we spatially join AIANNH boundaries with
     all census tracts using geopandas overlay/sjoin, then inner-join to the
     eligible set.
  c. For each eligible tract that intersects an AIANNH polygon:
     - Record NAMELSAD (tribal area name).
     - If a tract overlaps multiple tribal areas, record all names pipe-separated
       ordered by descending overlap area; flag with the largest-overlap name as
       tribal_area_name.
  d. is_tribal_overlap = True where any spatial overlap exists OR aian_pct >= 0.25.
  e. overlap_method = "spatial" for rows identified by step (c);
     overlap_method = "demographic_proxy" for rows identified only by aian_pct >= 0.25.

Fallback path (geopandas unavailable):
  Skip spatial join. Flag tracts where aian_pct >= 0.25 as tribal_overlap.
  tribal_area_name = null for all rows.
  overlap_method = "demographic_proxy" for all flagged rows.

Output schema (data/tribal_overlap.parquet)
-------------------------------------------
Rows: eligible tracts only (inner join on geoid with eligible_tracts.parquet).

  geoid             str   11-digit census tract GEOID
  aian_pop          int   AIAN alone population (ACS B02001_004E)
  aian_pct          float fraction 0–1 (0 where total pop = 0)
  tribal_area_name  str   AIANNH NAMELSAD (pipe-separated if multiple); null if none
  is_tribal_overlap bool  True if spatial overlap OR aian_pct >= 0.25
  overlap_method    str   "spatial" | "demographic_proxy" | "none"
  fetched_at        str   ISO date this script was run

Notes
-----
- The demographic proxy (aian_pct >= 0.25) is a coarse signal; prefer the spatial
  path when possible.
- TIGER 2023 AIANNH excludes Alaska Native Regional Corporations (ANRCs); those are
  in a separate TIGER layer (tl_2023_us_anrc.zip) and are not included here.
- For memory efficiency, tract geometries are fetched state-by-state and concatenated
  before the spatial join.
"""

import io
import sys
import zipfile
import tempfile
import shutil
from datetime import date
from pathlib import Path

import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACS_URL = (
    "https://api.census.gov/data/2022/acs/acs5"
    "?get=B02001_001E,B02001_004E&for=tract:*&in=state:*"
)
AIANNH_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2023/AIANNH/tl_2023_us_aiannh.zip"
)
# National tract shapefile — lighter centroid file via TIGER cartographic boundaries
TRACT_CART_URL_TMPL = (
    "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_{state_fips}_tract_500k.zip"
)

DATA_DIR = Path(__file__).parent.parent / "data"
ELIGIBLE_PARQUET = DATA_DIR / "eligible_tracts.parquet"
OUT_PARQUET = DATA_DIR / "tribal_overlap.parquet"

TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch_bytes(url: str, desc: str = "") -> bytes:
    label = desc or url
    print(f"  Fetching {label} …")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    print(f"    {len(r.content):,} bytes")
    return r.content


class NetworkUnavailable(RuntimeError):
    pass


def fetch_acs_aian(eligible_geoids: set) -> pd.DataFrame:
    """
    Fetch ACS B02001 AIAN population for all tracts; filter to eligible.

    The Census API returns all tracts in a single call using wildcard syntax.
    If the API is unreachable (e.g. network restrictions in CI/sandbox), returns
    an empty DataFrame with the correct schema so the caller can fall back to
    producing a stub output.
    """
    print("Fetching ACS B02001 AIAN population …")
    try:
        r = requests.get(ACS_URL, timeout=120)
        r.raise_for_status()
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
        print(f"  WARNING: Census ACS API unavailable ({exc})")
        print("  Returning empty ACS frame — tribal overlap will be all null/zero")
        return pd.DataFrame(columns=["geoid", "aian_pop", "aian_pct"])

    raw = r.json()
    headers = raw[0]
    rows = raw[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Build 11-digit GEOID
    df["geoid"] = (
        df["state"].str.zfill(2)
        + df["county"].str.zfill(3)
        + df["tract"].str.zfill(6)
    )
    df["aian_pop"] = pd.to_numeric(df["B02001_004E"], errors="coerce").fillna(0).astype(int)
    df["total_pop"] = pd.to_numeric(df["B02001_001E"], errors="coerce").fillna(0).astype(int)
    df["aian_pct"] = df.apply(
        lambda r: r["aian_pop"] / r["total_pop"] if r["total_pop"] > 0 else 0.0,
        axis=1,
    )

    df = df[df["geoid"].isin(eligible_geoids)][["geoid", "aian_pop", "aian_pct"]]
    print(f"  {len(df):,} eligible tracts have ACS data")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Spatial path (geopandas)
# ---------------------------------------------------------------------------


def spatial_join(eligible_geoids: set, tmpdir: Path):
    """
    Download AIANNH shapefile and per-state tract cartographic boundaries,
    spatial-join tracts to tribal areas, return DataFrame with columns
    [geoid, tribal_area_name, overlap_method].
    """
    import geopandas as gpd
    from shapely.errors import GEOSException

    # --- Download AIANNH ---
    print("Downloading AIANNH tribal boundaries …")
    try:
        aiannh_bytes = fetch_bytes(AIANNH_URL, "TIGER AIANNH 2023")
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
        raise NetworkUnavailable(f"Cannot fetch AIANNH shapefile: {exc}") from exc
    aiannh_zip = tmpdir / "aiannh.zip"
    aiannh_zip.write_bytes(aiannh_bytes)
    with zipfile.ZipFile(aiannh_zip, "r") as zf:
        zf.extractall(tmpdir / "aiannh")
    shp_files = list((tmpdir / "aiannh").glob("*.shp"))
    assert shp_files, "No .shp in AIANNH zip"
    aiannh = gpd.read_file(shp_files[0])
    aiannh = aiannh.to_crs("EPSG:5070")  # Albers Equal Area for area calcs
    aiannh = aiannh[["NAMELSAD", "geometry"]].copy()
    print(f"  Loaded {len(aiannh):,} AIANNH features")

    # --- Fetch tract geometries state by state ---
    # Derive unique state FIPS from eligible geoids
    state_fips_list = sorted({g[:2] for g in eligible_geoids})
    tract_frames = []

    print(f"Downloading tract boundaries for {len(state_fips_list)} states …")
    for sf in state_fips_list:
        url = TRACT_CART_URL_TMPL.format(state_fips=sf)
        try:
            raw = fetch_bytes(url, f"tracts state {sf}")
        except requests.HTTPError as exc:
            print(f"    WARNING: could not fetch tracts for state {sf}: {exc}")
            continue
        zpath = tmpdir / f"tract_{sf}.zip"
        zpath.write_bytes(raw)
        exdir = tmpdir / f"tract_{sf}"
        exdir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(exdir)
        shp = list(exdir.glob("*.shp"))
        if not shp:
            print(f"    WARNING: no shapefile found for state {sf}")
            continue
        gdf = gpd.read_file(shp[0])
        # Keep only eligible tracts
        if "GEOID" in gdf.columns:
            gdf = gdf[gdf["GEOID"].isin(eligible_geoids)][["GEOID", "geometry"]]
        elif "GEOID20" in gdf.columns:
            gdf = gdf[gdf["GEOID20"].isin(eligible_geoids)][["GEOID20", "geometry"]]
            gdf = gdf.rename(columns={"GEOID20": "GEOID"})
        else:
            print(f"    WARNING: unexpected columns in tract file for {sf}: {list(gdf.columns)}")
            continue
        tract_frames.append(gdf)

    if not tract_frames:
        raise RuntimeError("No tract geometries loaded; cannot do spatial join")

    tracts = pd.concat(tract_frames, ignore_index=True)
    tracts = gpd.GeoDataFrame(tracts, geometry="geometry", crs="EPSG:4269")
    tracts = tracts.to_crs("EPSG:5070")
    print(f"  Loaded {len(tracts):,} eligible tract geometries")

    # --- Spatial join: intersect tracts with AIANNH ---
    print("Running spatial join (intersection) …")
    joined = gpd.overlay(tracts, aiannh, how="intersection", keep_geom_type=False)
    if joined.empty:
        print("  No intersections found (unexpected) — falling back to demographic proxy")
        return None

    joined["overlap_area"] = joined.geometry.area

    # Aggregate by GEOID: collect all tribal area names ordered by area desc
    def agg_names(grp):
        sorted_grp = grp.sort_values("overlap_area", ascending=False)
        names = "|".join(sorted_grp["NAMELSAD"].dropna().unique())
        return pd.Series({"tribal_area_name": names or None})

    agg = joined.groupby("GEOID").apply(agg_names, include_groups=False).reset_index()
    agg.columns = ["geoid", "tribal_area_name"]
    agg["overlap_method"] = "spatial"

    print(f"  Spatial join identified {len(agg):,} eligible tracts with tribal overlap")
    return agg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load eligible tracts
    print(f"Loading {ELIGIBLE_PARQUET} …")
    eligible = pd.read_parquet(ELIGIBLE_PARQUET)
    eligible_geoids = set(eligible["geoid"])
    print(f"  {len(eligible_geoids):,} eligible tracts")

    # Step 1 — ACS AIAN population
    acs_df = fetch_acs_aian(eligible_geoids)

    # Step 2 — Spatial join (or fallback)
    spatial_df = None
    tmpdir = Path(tempfile.mkdtemp(prefix="tribal_overlap_"))
    try:
        try:
            import geopandas  # noqa: F401
            print("\nGeopandas available — attempting spatial join …")
            spatial_df = spatial_join(eligible_geoids, tmpdir)
        except ImportError:
            print("Geopandas not available — using demographic proxy only")
        except NetworkUnavailable as exc:
            print(f"  Network unavailable ({exc}) — using demographic proxy only")
        except Exception as exc:
            print(f"Spatial join failed ({exc}) — using demographic proxy only")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Step 3 — Merge and build output
    # Start from full eligible set so every eligible tract gets a row
    df = eligible[["geoid"]].copy()

    acs_available = len(acs_df) > 0
    if acs_available:
        df = df.merge(acs_df, on="geoid", how="left")
    else:
        print(
            "\n  WARNING: ACS data unavailable. The output parquet will contain "
            "all eligible tracts\n  with aian_pop=0, aian_pct=0, "
            "is_tribal_overlap=False, overlap_method='unavailable'.\n"
            "  Re-run this script with Census API access to populate real values."
        )
        df["aian_pop"] = 0
        df["aian_pct"] = 0.0

    df["aian_pop"] = df["aian_pop"].fillna(0).astype(int)
    df["aian_pct"] = df["aian_pct"].fillna(0.0)

    if not acs_available and spatial_df is None:
        # No data at all — produce stub with schema-correct columns
        df["tribal_area_name"] = None
        df["is_tribal_overlap"] = False
        df["overlap_method"] = "unavailable"
    elif spatial_df is not None:
        df = df.merge(spatial_df, on="geoid", how="left")
        # Rows without spatial overlap but high AIAN share get demographic_proxy
        no_spatial = df["overlap_method"].isna()
        high_aian = df["aian_pct"] >= 0.25

        df.loc[no_spatial & high_aian, "overlap_method"] = "demographic_proxy"
        df.loc[no_spatial & ~high_aian, "overlap_method"] = "none"
        df["is_tribal_overlap"] = df["overlap_method"].isin(["spatial", "demographic_proxy"])
    else:
        # ACS available, no spatial join
        df["tribal_area_name"] = None
        high_aian = df["aian_pct"] >= 0.25
        df["overlap_method"] = high_aian.map({True: "demographic_proxy", False: "none"})
        df["is_tribal_overlap"] = high_aian

    df["tribal_area_name"] = df["tribal_area_name"].where(df["tribal_area_name"].notna(), other=None)
    df["fetched_at"] = TODAY

    # Enforce column order
    df = df[[
        "geoid", "aian_pop", "aian_pct",
        "tribal_area_name", "is_tribal_overlap", "overlap_method", "fetched_at",
    ]]

    # Save
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"\nSaved → {OUT_PARQUET}")

    # Summary
    total_overlap = df["is_tribal_overlap"].sum()
    spatial_count = (df["overlap_method"] == "spatial").sum()
    demo_count = (df["overlap_method"] == "demographic_proxy").sum()
    none_count = (df["overlap_method"] == "none").sum()
    unavail_count = (df["overlap_method"] == "unavailable").sum()

    print("\n--- Tribal overlap summary ---")
    print(f"  Total eligible tracts:             {len(df):,}")
    if unavail_count == len(df):
        print(f"  Data unavailable (stub output):    {unavail_count:,} rows")
        print("  Re-run with network access to populate real ACS + spatial data.")
    else:
        print(f"  Tracts with tribal overlap:        {total_overlap:,}")
        print(f"    — spatial join:                  {spatial_count:,}")
        print(f"    — demographic proxy (≥25% AIAN): {demo_count:,}")
        print(f"  No overlap:                        {none_count:,}")
        if spatial_count == 0:
            print("\n  NOTE: spatial join produced 0 results; overlap flagged by")
            print("  demographic proxy (aian_pct >= 0.25) only.")


if __name__ == "__main__":
    main()
