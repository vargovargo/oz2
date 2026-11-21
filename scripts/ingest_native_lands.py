#!/usr/bin/env python3
"""
Native lands and Native populations for every OZ 2.0 eligible tract.

    → data/native_lands.parquet

This replaces data/tribal_overlap.parquet for designation work. That older file used the
April eligible list, the 2018–2022 ACS, and flagged a tract if *any* sliver touched *any*
AIANNH polygon, mixing reservations with Oklahoma and Alaska statistical areas. Here the
two questions are kept apart:

  Lens 1 — land.  What share of the tract's area is reservation or trust land?
           Federally recognized reservations and off-reservation trust land are measured
           separately from Hawaiian Home Lands, state reservations, and the purely
           statistical areas (OTSAs, ANVSAs, SDTSAs), which are not land held by or for a
           tribe and in Oklahoma's case cover most of the eastern half of the state.
  Lens 2 — people. What share of residents are American Indian / Alaska Native (and, in
           Hawaii, Native Hawaiian / Pacific Islander)? ACS 2020–2024, the same vintage
           Treasury used for eligibility.

Sources (no API key needed)
---------------------------
  TIGER/Line 2024 AIANNH:  https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip
  Cartographic boundary 2024 tracts (500k, shoreline-clipped):
                           https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_tract_500k.zip
  ACS 2020–2024 5-year table-based Summary File, tables B02001, B02010, B02012:
                           https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/

Method
------
  * AIANNH features are classed by CLASSFP:
        federal  D2, D3, D5, D8  federally recognized reservation / off-reservation trust land
        hhl      F1              Hawaiian Home Land
        state    D4              state-recognized reservation
        otsa     D0, D6          Oklahoma tribal statistical area (incl. joint-use) and the
                                 few tribal designated statistical areas (TDSAs), e.g. Cayuga Nation
        anvsa    E1              Alaska Native village statistical area
        sdtsa    D9              state-designated tribal statistical area
    Each class is dissolved before intersecting, so overlapping features (joint-use areas,
    trust land inside a reservation) are not double-counted.
  * Shares are of the cartographic tract polygon's area in an equal-area projection
    (EPSG:6933). Cartographic tracts are clipped to the shoreline, so the share is close
    to a land-area share. It is an area share, not a population share: a large rural tract
    can be mostly reservation by area while most residents live in an off-reservation town.
  * `native_pct` = AIAN alone (any ethnicity) ÷ total population; in Hawaii it adds NHPI
    alone. "Alone" categories are mutually exclusive, so the sum does not double-count.
    The alone-or-in-combination counts are kept for sensitivity checks.
  * The Island Areas (AS, GU, MP, VI) are not in the ACS; their population columns are null.
  * Population-weighted shares (added 2026-11-21) answer the area share's blind spot: what
    share of the tract's *residents* live on reservation, trust or Home Land. Source is the
    2020 Census PL 94-171 redistricting file, block level (SUMLEV 750). Each block row carries
    its AIANNH code (AIANHH; 0001–4999 federal reservation/trust land, 5000–5499 Hawaiian Home
    Land) and P1 race counts. Block GEOIDs roll up to 2020 tracts; Connecticut's 2022
    planning-region tracts are matched on tract code. Only the states with an eligible tract
    touching federal or Home Land are downloaded (≈30 files, ~1 GB, cached in data/raw/pl2020).
    Population is 2020 decennial; the ACS columns are 2020–2024 — they will not sum exactly.

Output columns
--------------
  geoid
  federal_share, hhl_share, state_res_share, otsa_share, anvsa_share, sdtsa_share   (0–1)
  federal_name   federally recognized entity with the most land in the tract (AIANNH NAME,
                 reservation + trust land combined), else null
  native_area_name  largest AIANNH feature of any class in the tract, else null
  total_pop, aian_alone, aian_aoic, nhpi_alone, nhpi_aoic                          (ACS counts)
  aian_pct, aian_aoic_pct, nhpi_pct, native_pct                                    (0–1)
  pop2020        2020 Census population (blocks in the tract; only states downloaded, else null)
  federal_pop_share, hhl_pop_share   share of 2020 residents in federal / Home Land blocks (0–1)
  native2020, native_on_land2020     AIAN alone (+ NHPI alone in HI), all blocks / federal+HHL blocks
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw" / "native"
RAW_ACS = DATA / "raw" / "acs2024"
AIANNH = "https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip"
TRACTS = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_tract_500k.zip"
ACS = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-{t}.dat"

CLASSES = {
    "federal": ["D2", "D3", "D5", "D8"],
    "hhl": ["F1"],
    "state_res": ["D4"],
    "otsa": ["D0", "D6"],
    "anvsa": ["E1"],
    "sdtsa": ["D9"],
}
EQUAL_AREA = "EPSG:6933"
PL = ("https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/"
      "{name}/{st}2020.pl.zip")
RAW_PL = DATA / "raw" / "pl2020"
STATE_NAMES = {
    "04": ("Arizona", "az"), "06": ("California", "ca"), "08": ("Colorado", "co"), "09": ("Connecticut", "ct"),
    "12": ("Florida", "fl"), "15": ("Hawaii", "hi"), "16": ("Idaho", "id"), "18": ("Indiana", "in"),
    "19": ("Iowa", "ia"), "20": ("Kansas", "ks"), "22": ("Louisiana", "la"), "23": ("Maine", "me"),
    "25": ("Massachusetts", "ma"), "26": ("Michigan", "mi"), "27": ("Minnesota", "mn"),
    "28": ("Mississippi", "ms"), "30": ("Montana", "mt"), "31": ("Nebraska", "ne"), "32": ("Nevada", "nv"),
    "35": ("New_Mexico", "nm"), "36": ("New_York", "ny"), "37": ("North_Carolina", "nc"),
    "38": ("North_Dakota", "nd"), "40": ("Oklahoma", "ok"), "41": ("Oregon", "or"),
    "44": ("Rhode_Island", "ri"), "45": ("South_Carolina", "sc"), "46": ("South_Dakota", "sd"),
    "47": ("Tennessee", "tn"), "48": ("Texas", "tx"), "49": ("Utah", "ut"), "51": ("Virginia", "va"),
    "53": ("Washington", "wa"), "55": ("Wisconsin", "wi"), "56": ("Wyoming", "wy"), "02": ("Alaska", "ak"),
}


def fetch(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        print(f"  downloading {dest.name}")
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return dest


def load_acs(t: str, geoids: set[str]) -> pd.DataFrame:
    path = fetch(ACS.format(t=t), RAW_ACS / f"{t}.dat")
    chunks = []
    for ch in pd.read_csv(path, sep="|", dtype=str, chunksize=200_000):
        ch = ch[ch.GEO_ID.str.startswith("1400000US")]
        ch["geoid"] = ch.GEO_ID.str[9:]
        ch = ch[ch.geoid.isin(geoids)]
        est = [c for c in ch.columns if "_E" in c]
        chunks.append(ch[["geoid"] + est])
    df = pd.concat(chunks).set_index("geoid").apply(pd.to_numeric, errors="coerce")
    return df.where(df >= 0)


def land_shares(geoids: set[str]) -> pd.DataFrame:
    a = gpd.read_file(f"zip://{fetch(AIANNH, RAW / 'tl_2024_us_aiannh.zip')}").to_crs(EQUAL_AREA)
    t = gpd.read_file(f"zip://{fetch(TRACTS, RAW / 'cb_2024_us_tract_500k.zip')}")
    t = t[t.GEOID.isin(geoids)][["GEOID", "geometry"]].to_crs(EQUAL_AREA)
    t["geometry"] = t.geometry.make_valid()
    a["geometry"] = a.geometry.make_valid()
    t["tract_area"] = t.geometry.area
    print(f"  {len(t):,} eligible tracts with geometry; {len(a):,} AIANNH features")

    out = pd.DataFrame(index=sorted(geoids))
    out.index.name = "geoid"
    for cls, codes in CLASSES.items():
        sub = a[a.CLASSFP.isin(codes)]
        diss = gpd.GeoDataFrame(geometry=[sub.union_all()], crs=EQUAL_AREA)
        cand = t[t.intersects(diss.geometry.iloc[0])]
        inter = gpd.overlay(cand, diss, how="intersection", keep_geom_type=True)
        share = (inter.geometry.area / inter.tract_area).groupby(inter.GEOID).sum().clip(upper=1.0)
        out[f"{cls}_share"] = share.reindex(out.index).fillna(0.0).round(4)
        print(f"    {cls:10s} {int((out[f'{cls}_share'] > 0.01).sum()):>5,} tracts >1%   "
              f"{int((out[f'{cls}_share'] >= 0.5).sum()):>5,} tracts ≥50%")

    # Names: the largest overlapping feature, overall and among federal land.
    a["cls"] = a.CLASSFP.map({c: k for k, v in CLASSES.items() for c in v})
    # Federal names group by NAME, so a reservation and its off-reservation trust land
    # ("Navajo Nation Reservation" + "Navajo Nation Off-Reservation Trust Land") count as one.
    inter = gpd.overlay(t, a[["NAME", "NAMELSAD", "cls", "geometry"]], how="intersection", keep_geom_type=True)
    inter["share"] = inter.geometry.area / inter.tract_area
    inter = inter[inter.share >= 0.01].sort_values("share", ascending=False)
    out["native_area_name"] = inter.drop_duplicates("GEOID").set_index("GEOID").NAMELSAD.reindex(out.index)
    fed = (inter[inter.cls == "federal"].groupby(["GEOID", "NAME"]).share.sum().reset_index()
           .sort_values("share", ascending=False).drop_duplicates("GEOID").set_index("GEOID"))
    out["federal_name"] = fed.NAME.reindex(out.index)
    return out


def pl_blocks(fips: str) -> pd.DataFrame:
    """2020 PL 94-171 blocks for one state: tract, AIANNH code, total / AIAN / NHPI population."""
    import zipfile
    name, st = STATE_NAMES[fips]
    z = zipfile.ZipFile(fetch(PL.format(name=name, st=st), RAW_PL / f"{st}2020.pl.zip"))
    geo = pd.read_csv(z.open(f"{st}geo2020.pl"), sep="|", header=None, dtype=str, encoding="latin-1",
                      usecols=[2, 7, 9, 35])
    geo = geo[geo[2] == "750"].rename(columns={7: "logrecno", 9: "geocode", 35: "aianhh"})
    seg = pd.read_csv(z.open(f"{st}000012020.pl"), sep="|", header=None, dtype=str, usecols=[4, 5, 9, 11])
    seg.columns = ["logrecno", "pop", "aian", "nhpi"]
    b = geo.merge(seg, on="logrecno")
    for c in ["pop", "aian", "nhpi"]:
        b[c] = b[c].astype(int)
    code = pd.to_numeric(b.aianhh, errors="coerce")
    b["federal"] = code.between(1, 4999)
    b["hhl"] = code.between(5000, 5499)
    b["tract"] = b.geocode.str[:11]
    b["native"] = b.aian + (b.nhpi if fips == "15" else 0)
    return b


def pop_shares(out: pd.DataFrame) -> pd.DataFrame:
    need = sorted({g[:2] for g in out.index[(out.federal_share > 0) | (out.hhl_share > 0)]})
    rows = []
    for fips in need:
        b = pl_blocks(fips)
        b["land"] = b.federal | b.hhl
        agg = b.groupby("tract").apply(lambda g: pd.Series({
            "pop2020": g["pop"].sum(),
            "federal_pop": g.loc[g.federal, "pop"].sum(),
            "hhl_pop": g.loc[g.hhl, "pop"].sum(),
            "native2020": g.native.sum(),
            "native_on_land2020": g.loc[g.land, "native"].sum(),
        }), include_groups=False)
        if fips == "09":  # 2022 planning-region GEOIDs: match on the (statewide-unique) tract code
            ct = pd.Series([i for i in out.index if i[:2] == "09"])
            m = dict(zip(ct.str[5:], ct))
            agg = agg[agg.index.str[5:].isin(m)]
            agg.index = agg.index.str[5:].map(m)
        rows.append(agg)
        print(f"    {fips}: {len(b):,} blocks, {int(b.federal.sum()):,} federal, {int(b.hhl.sum()):,} HHL")
    p = pd.concat(rows)
    p = p[p.index.isin(out.index)]
    out["pop2020"] = p.pop2020.reindex(out.index)
    den = out.pop2020.where(out.pop2020 > 0)
    out["federal_pop_share"] = (p.federal_pop.reindex(out.index) / den).round(4)
    out["hhl_pop_share"] = (p.hhl_pop.reindex(out.index) / den).round(4)
    out["native2020"] = p.native2020.reindex(out.index)
    out["native_on_land2020"] = p.native_on_land2020.reindex(out.index)
    # Tracts in states with no federal or Home Land blocks among eligible tracts: zero by definition.
    for c in ["federal_pop_share", "hhl_pop_share"]:
        out[c] = out[c].where(out.index.str[:2].isin(need), 0.0)
    return out


def main() -> None:
    tracts = pd.read_parquet(DATA / "oz2_tracts.parquet", columns=["geoid", "state_fips"])
    ids = set(tracts.geoid)
    out = land_shares(ids)
    print("  2020 block populations …")
    out = pop_shares(out)

    r = load_acs("b02001", ids)
    out["total_pop"] = r.B02001_E001
    out["aian_alone"] = r.B02001_E004
    out["nhpi_alone"] = r.B02001_E006
    out["aian_aoic"] = load_acs("b02010", ids).B02010_E001
    out["nhpi_aoic"] = load_acs("b02012", ids).B02012_E001
    den = out.total_pop.where(out.total_pop > 0)
    out["aian_pct"] = (out.aian_alone / den).round(4)
    out["aian_aoic_pct"] = (out.aian_aoic / den).round(4)
    out["nhpi_pct"] = (out.nhpi_alone / den).round(4)
    hi = pd.Series(out.index.str[:2] == "15", index=out.index)
    out["native_pct"] = ((out.aian_alone + out.nhpi_alone.where(hi, 0)) / den).round(4)

    out.reset_index().to_parquet(DATA / "native_lands.parquet", index=False)
    print(f"  wrote {len(out):,} rows; with population: {out.total_pop.notna().sum():,}")
    print(f"  native_pct ≥20%: {int((out.native_pct >= 0.2).sum()):,}   ≥50%: {int((out.native_pct >= 0.5).sum()):,}")


if __name__ == "__main__":
    main()
