#!/usr/bin/env python3
"""
Certified CDFIs (flagging Native CDFIs), geocoded to 2020 tracts and Native lands.

    → data/cdfis_certified.parquet

Source
------
CDFI Fund, "List of Certified CDFIs" (manual list, dated in the file name; linked from
https://www.cdfifund.gov/programs-training/certification/cdfi). Columns used: Organization
Name, Date Certified, Financial Institution Type, Native CDFI (Y/N), City, State, Zipcode,
Address, Organization Website.

Geocoding: Census Geocoder batch API (geographies/addressbatch, benchmark Public_AR_Current,
vintage Current_Current — current tract geography, i.e. 2020 tracts with Connecticut's 2022
planning-region codes, matching data/oz2_tracts.parquet). Most unmatched rows are PO boxes;
they fall back to the city's Census place point (2024 Gazetteer, places), then to the ZIP code's
ZCTA point (2024 Gazetteer, ZCTAs), and are assigned to the 2024 cartographic tract containing
that point. `match` records which: Exact / Non_Exact (street), Place, ZIP, or null.

Headquarters location only. A Native CDFI usually serves a whole reservation or region, so
"based in a designated tract" is a signal of local presence, not of service area.

Output columns
--------------
  name, cdfi_type, native (bool), certified (date), city, state, zip, address, website,
  geoid (11-digit tract or null), match (Exact / Non_Exact / No_Match / Tie),
  lon, lat, aiannh_name (AIANNH feature containing the HQ point, any class), aiannh_class
"""

import io
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw" / "cdfi"
LIST_URL = "https://www.cdfifund.gov/sites/default/files/100/CDFI-Cert-List-Manual-11-16-2026.xlsx"
GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch"
AIANNH = DATA / "raw" / "native" / "tl_2024_us_aiannh.zip"
TRACTS = DATA / "raw" / "native" / "cb_2024_us_tract_500k.zip"
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_{k}_national.zip"
CLASS = {"D2": "federal", "D3": "federal", "D5": "federal", "D8": "federal", "F1": "hhl", "D4": "state_res",
         "D0": "otsa", "D6": "otsa", "E1": "anvsa", "D9": "sdtsa"}


def load_list() -> pd.DataFrame:
    path = RAW / "cert-list.xlsx"
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        r = requests.get(LIST_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
    raw = pd.read_excel(path, sheet_name=0, header=None)
    hdr = raw.index[raw[1].astype(str).eq("Organization Name")][0]
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(c) for c in raw.iloc[hdr]]
    df = df[df["Organization Name"].notna()]
    out = pd.DataFrame({
        "name": df["Organization Name"].str.strip(),
        "certified": pd.to_datetime(df["Date Certified"], errors="coerce").dt.date.astype(str),
        "cdfi_type": df["Financial Institution Type"],
        "native": df["Native CDFI (Y/N)"].astype(str).str.upper().str.startswith("Y"),
        "city": df["City"].astype(str).str.title(),
        "state": df["State"],
        "zip": df["Zipcode"].astype(str).str[:5],
        "address": df["Address"].astype(str).str.strip(),
        "website": df["Organization Website"],
    }).reset_index(drop=True)
    return out


def geocode(df: pd.DataFrame) -> pd.DataFrame:
    cache = RAW / "geocoded.csv"
    if not cache.exists():
        buf = io.StringIO()
        df[["address", "city", "state", "zip"]].to_csv(buf, header=False)
        r = requests.post(GEOCODER, files={"addressFile": ("a.csv", buf.getvalue())},
                          data={"benchmark": "Public_AR_Current", "vintage": "Current_Current"}, timeout=600)
        r.raise_for_status()
        cache.write_text(r.text)
    g = pd.read_csv(cache, header=None, dtype=str, names=list(range(12)))
    g = g.rename(columns={0: "id", 2: "status", 3: "match", 5: "coords", 8: "st", 9: "co", 10: "tr"})
    g["id"] = g.id.astype(int)
    g = g.set_index("id").reindex(df.index)
    out = df.copy()
    out["match"] = g.match.where(g.status.eq("Match"), g.status)
    xy = g.coords.str.split(",", expand=True)
    out["lon"] = pd.to_numeric(xy[0], errors="coerce")
    out["lat"] = pd.to_numeric(xy[1], errors="coerce")
    ok = g.st.notna() & g.co.notna() & g.tr.notna()
    out["geoid"] = (g.st + g.co + g.tr).where(ok)
    return out


def gazetteer(kind: str) -> pd.DataFrame:
    import zipfile
    path = RAW / f"gaz_{kind}.zip"
    if not path.exists():
        r = requests.get(GAZ.format(k=kind), timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    with zipfile.ZipFile(path) as z:
        g = pd.read_csv(z.open(z.namelist()[0]), sep="\t", dtype=str, encoding="latin-1")
    g.columns = g.columns.str.strip()
    return g


def fallback(df: pd.DataFrame) -> pd.DataFrame:
    """City place point, then ZCTA point, for rows the street geocoder missed."""
    miss = df.lon.isna()
    pl = gazetteer("place")
    pl["key"] = (pl.USPS + "|" + pl.NAME.str.replace(r" (city|town|village|CDP|borough|municipality)$", "",
                                                     regex=True).str.lower())
    pl = pl.drop_duplicates("key").set_index("key")
    key = df.state + "|" + df.city.str.lower()
    hit = miss & key.isin(pl.index)
    df.loc[hit, "lat"] = pd.to_numeric(key[hit].map(pl.INTPTLAT))
    df.loc[hit, "lon"] = pd.to_numeric(key[hit].map(pl.INTPTLONG))
    df.loc[hit, "match"] = "Place"
    z = gazetteer("zcta").set_index("GEOID")
    miss = df.lon.isna() & df.zip.isin(z.index)
    df.loc[miss, "lat"] = pd.to_numeric(df.zip[miss].map(z.INTPTLAT))
    df.loc[miss, "lon"] = pd.to_numeric(df.zip[miss].map(z.INTPTLONG))
    df.loc[miss, "match"] = "ZIP"
    need = df.geoid.isna() & df.lon.notna()
    t = gpd.read_file(f"zip://{TRACTS}")[["GEOID", "geometry"]]
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(df.lon[need], df.lat[need]), index=df.index[need], crs="EPSG:4269")
    j = gpd.sjoin(pts.to_crs(t.crs), t, predicate="within", how="left")
    j = j[~j.index.duplicated()]
    df.loc[need, "geoid"] = j.GEOID.reindex(df.index[need])
    return df


def main() -> None:
    df = fallback(geocode(load_list()))
    a = gpd.read_file(f"zip://{AIANNH}")[["NAME", "NAMELSAD", "CLASSFP", "geometry"]]
    pts = gpd.GeoDataFrame(df[["lon", "lat"]], geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4269")
    pts = pts[df.lon.notna()].to_crs(a.crs)
    hit = gpd.sjoin(pts, a, predicate="within", how="left")
    hit["cls"] = hit.CLASSFP.map(CLASS)
    hit["rank"] = hit.cls.map({"federal": 0, "hhl": 1, "state_res": 2, "anvsa": 3, "otsa": 4, "sdtsa": 5})
    hit = hit.sort_values("rank").groupby(level=0).first()
    df["aiannh_name"] = hit.NAME.reindex(df.index)
    df["aiannh_class"] = hit.cls.reindex(df.index)
    df.to_parquet(DATA / "cdfis_certified.parquet", index=False)
    n = df[df.native]
    print(f"  {len(df):,} certified CDFIs, {len(n)} Native; geocoded to a tract: {df.geoid.notna().sum():,} "
          f"(Native: {n.geoid.notna().sum()})")
    print(n.match.value_counts(dropna=False).to_string())
    print(n.aiannh_class.value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
