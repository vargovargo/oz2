#!/usr/bin/env python3
"""
Designation post-mortem: which eligible tracts became 2027 QOZs, and what set them apart.

Inputs (all produced by other scripts in this directory)
    data/oz2_tracts.parquet               ingest_designated_tracts.py
    data/acs_tract_demographics.parquet   ingest_acs_tract_demographics.py
    data/oz1_overlap.parquet              ingest_oz1_tracts.py
    data/cra_lmi_overlap.parquet, dci.parquet, urban_investability.parquet,
    tribal_overlap.parquet, cdfi_nmtc.parquet, persistent_poverty.parquet
    public/geo/*.geojson                  (place names only)

Outputs
    data/designation_analysis.json        national + per-state findings (for /designations)
    data/designations_by_state.json       per-state tract and county tables (for state pages)
    public/data/oz2-designations-2027.csv every eligible tract, designated or not, with indicators

Method notes
    * Selection happens inside a state against a fixed cap, so every comparison is
      within-state. National medians are shown for orientation only.
    * Six jurisdictions designated every eligible tract (WY, VT, AS, GU, MP, VI). No
      selection took place there; they are excluded from the selection analysis.
    * "Lift" for a yes/no trait = designated tracts with the trait ÷ the number expected
      if each state had picked at its own overall rate. 1.0 = no preference.
    * "Percentile" for a continuous trait = the mean within-state percentile rank of the
      designated tracts on that trait. 50 = no preference.
    * The logit has state fixed effects and county-clustered standard errors. It is a
      description of what the selected set looks like, not a model of governors' intent.

Usage
    python3 scripts/analyze_designations.py
"""

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

STATE_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE",
    "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
    "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM",
    "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI",
}

# Thresholds for the project-signal tags on designated tracts. Kept deliberately simple
# and published on the page so a reader can see why a tract carries a tag.
TAG_RULES = {
    "qrof": "Rural QOZ — QROF treatment (30% step-up at 5 years, 50% improvement threshold)",
    "oz1": "Was an OZ 1.0 tract (≥50% of land area in a 2018 QOZ)",
    "nmtc": "Prior New Markets Tax Credit investment in the tract",
    "cra": "CRA-eligible (LMI or distressed/underserved middle-income)",
    "tribal": "Overlaps tribal land or has a significant AIAN population",
    "housing": "Housing pressure: ≥50% renters and ≥50% of renters cost-burdened",
    "vacancy": "High vacancy: ≥15% of housing units vacant",
    "sweetspot": "Urban Institute Tier 1 — likely to attract investment, with larger impact",
    "ppov": "In a USDA persistent-poverty county",
    "added": "Added to the eligible list in October 2026 under Treasury's missing-data rules",
}

CONTINUOUS = [
    ("poverty_rate", "Poverty rate"),
    ("mfi_ratio", "Median family income, % of area"),
    ("pop", "Population"),
    ("pop_density", "Population density"),
    ("unemp_rate", "Unemployment rate"),
    ("pct_ba_plus", "Adults with a BA or more"),
    ("pct_renter", "Renter-occupied share"),
    ("vacancy_rate", "Housing vacancy rate"),
    ("pct_rent_burdened", "Renters cost-burdened"),
    ("median_home_value", "Median home value"),
    ("pct_nonwhite", "Residents of color"),
    ("pct_black_nh", "Black residents"),
    ("pct_hispanic", "Hispanic residents"),
    ("dci_score", "EIG distress score (higher = more distressed)"),
]
BINARY = [
    ("is_oz1", "Was an OZ 1.0 tract"),
    ("has_nmtc", "Prior NMTC investment"),
    ("is_rural", "Rural (QROF)"),
    ("ui_tier1", "Urban Institute Tier 1"),
    ("ui_tier3", "Urban Institute Tier 3 (low probability)"),
    ("is_cra_lmi", "CRA-eligible"),
    ("is_persistent_poverty", "Persistent-poverty county"),
    ("is_tribal_overlap", "Tribal overlap"),
    ("added_oct", "Added in October (missing-data rule)"),
]


# (column, phrase when designated tracts score higher, phrase when they score lower)
LEANING_TRAITS = [
    ("is_oz1", "favored former OZ 1.0 tracts", "passed over former OZ 1.0 tracts"),
    ("is_rural", "favored rural tracts", "favored non-rural tracts"),
    ("has_nmtc", "favored tracts with prior NMTC deals", "passed over tracts with prior NMTC deals"),
    ("ui_tier1", "favored Urban Institute Tier 1 tracts", "passed over Urban Institute Tier 1 tracts"),
    ("poverty_rate", "favored higher-poverty tracts", "favored lower-poverty tracts"),
    ("pct_renter", "favored renter-heavy tracts", "favored owner-heavy tracts"),
    ("pop_density", "favored denser tracts", "favored less dense tracts"),
    ("pop", "favored more populous tracts", "favored less populous tracts"),
    ("pct_nonwhite", "favored tracts with more residents of color", "favored tracts with fewer residents of color"),
    ("vacancy_rate", "favored higher-vacancy tracts", "favored lower-vacancy tracts"),
]


def load() -> pd.DataFrame:
    t = pd.read_parquet(DATA / "oz2_tracts.parquet")
    a = pd.read_parquet(DATA / "acs_tract_demographics.parquet")
    o = pd.read_parquet(DATA / "oz1_overlap.parquet")
    cra = pd.read_parquet(DATA / "cra_lmi_overlap.parquet", columns=["geoid", "is_cra_lmi"])
    dci = pd.read_parquet(DATA / "dci.parquet", columns=["geoid", "dci_score", "dci_quintile"])
    ui = pd.read_parquet(DATA / "urban_investability.parquet", columns=["geoid", "ui_invest_score"])
    tr = pd.read_parquet(DATA / "tribal_overlap.parquet", columns=["geoid", "is_tribal_overlap", "tribal_area_name"])
    pp = pd.read_parquet(DATA / "persistent_poverty.parquet", columns=["county_fips", "is_persistent_poverty"])
    nm_raw = pd.read_parquet(DATA / "cdfi_nmtc.parquet")
    nm = nm_raw.groupby("geoid").agg(nmtc_n=("qlici_amount", "size"), nmtc_usd=("qlici_amount", "sum"),
                                     cde_names=("cde_name", lambda s: sorted(set(s)))).reset_index()

    places = {}
    for f in (ROOT / "public" / "geo").glob("[0-9][0-9].geojson"):
        for feat in json.loads(f.read_text())["features"]:
            p = feat["properties"]
            if p.get("place_name"):
                places[p["geoid"]] = p["place_name"]

    df = (t.merge(a, on="geoid", how="left").merge(o, on="geoid", how="left")
          .merge(cra, on="geoid", how="left").merge(dci, on="geoid", how="left")
          .merge(ui, on="geoid", how="left").merge(tr, on="geoid", how="left")
          .merge(nm, on="geoid", how="left").merge(pp, on="county_fips", how="left"))
    df["place_name"] = df.geoid.map(places)
    df["oz1_land_share"] = df.oz1_land_share.fillna(0.0)
    for c in ["is_oz1", "is_cra_lmi", "is_tribal_overlap", "is_persistent_poverty"]:
        df[c] = df[c].fillna(False).astype(bool)
    df["nmtc_n"] = df.nmtc_n.fillna(0).astype(int)
    df["nmtc_usd"] = df.nmtc_usd.fillna(0.0)
    df["has_nmtc"] = df.nmtc_n > 0
    df["ui_tier1"] = df.ui_invest_score.eq(1)
    df["ui_tier3"] = df.ui_invest_score.eq(3)
    df["added_oct"] = ~df.in_april_list
    df["state_abbr"] = df.state_fips.map(STATE_ABBR)
    df["y"] = df.is_designated.astype(int)
    return df


def tags_for(r) -> list[str]:
    t = []
    if r.is_rural: t.append("qrof")
    if r.is_oz1: t.append("oz1")
    if r.has_nmtc: t.append("nmtc")
    if r.is_cra_lmi: t.append("cra")
    if r.is_tribal_overlap: t.append("tribal")
    if (r.pct_renter or 0) >= 0.5 and (r.pct_rent_burdened or 0) >= 0.5: t.append("housing")
    if (r.vacancy_rate or 0) >= 0.15: t.append("vacancy")
    if r.ui_tier1: t.append("sweetspot")
    if r.is_persistent_poverty: t.append("ppov")
    if r.added_oct: t.append("added")
    return t


def r1(x, n=1):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


def binary_lift(sel: pd.DataFrame, col: str) -> dict:
    rate = sel.groupby("state_fips").y.transform("mean")
    has = sel[col].astype(bool)
    observed = int(sel.loc[has, "y"].sum())
    expected = float(rate[has].sum())
    return {
        "n_eligible": int(has.sum()),
        "n_designated": observed,
        "rate_with": r1(sel.loc[has, "y"].mean() * 100),
        "rate_without": r1(sel.loc[~has, "y"].mean() * 100),
        "lift": r1(observed / expected, 2) if expected else None,
    }


def continuous_pct(sel: pd.DataFrame, col: str) -> dict:
    pr = sel.groupby("state_fips")[col].rank(pct=True) * 100
    d, n = sel.y == 1, sel.y == 0
    return {
        "designated_percentile": r1(pr[d].mean()),
        "median_designated": r1(sel.loc[d, col].median(), 3),
        "median_not": r1(sel.loc[n, col].median(), 3),
    }


def decile_curve(sel: pd.DataFrame, col: str) -> list:
    """Designation rate by within-state decile of `col` — the shape of the preference."""
    dec = (sel.groupby("state_fips")[col].rank(pct=True) * 10).clip(upper=9.999).floordiv(1)
    return [r1(v * 100) for v in sel.groupby(dec).y.mean().reindex(range(10)).tolist()]


def run_logit(sel: pd.DataFrame) -> dict:
    import statsmodels.formula.api as smf

    m = sel.copy()
    m["log_density"] = np.log1p(m.pop_density)
    num = ["poverty_rate", "mfi_ratio", "pop", "log_density", "unemp_rate", "pct_ba_plus",
           "pct_renter", "vacancy_rate", "median_home_value", "pct_nonwhite"]
    m = m.dropna(subset=num + ["ui_invest_score"])
    for c in num:
        m[c + "_z"] = (m[c] - m[c].mean()) / m[c].std()
    for c in ["is_oz1", "has_nmtc", "is_rural", "is_cra_lmi", "ui_tier1", "ui_tier3"]:
        m[c] = m[c].astype(int)
    terms = [c + "_z" for c in num] + ["is_oz1", "has_nmtc", "is_rural", "is_cra_lmi", "ui_tier1", "ui_tier3"]
    res = smf.logit("y ~ " + " + ".join(terms) + " + C(state_fips)", data=m).fit(
        disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": m.county_fips.astype("category").cat.codes})
    ame = res.get_margeff(at="overall").summary_frame()
    out = []
    for t in terms:
        out.append({
            "term": t,
            "odds_ratio": r1(math.exp(res.params[t]), 2),
            "ame_pp": r1(ame.loc[t, "dy/dx"] * 100, 1),
            "p": float(f"{res.pvalues[t]:.2g}"),
        })
    return {"n": int(res.nobs), "pseudo_r2": r1(res.prsquared, 3), "terms": out,
            "note": "Logit with state fixed effects, county-clustered SEs. Continuous terms are per "
                    "1 SD; ame_pp = average marginal effect in percentage points of designation probability."}


def main() -> None:
    df = load()
    today = date.today().isoformat()

    st = df.groupby("state_fips").agg(elig=("y", "size"), des=("y", "sum"))
    full = st.index[st.des == st.elig].tolist()
    sel = df[~df.state_fips.isin(full)].copy()

    national = {
        "eligible": int(len(df)),
        "designated": int(df.y.sum()),
        "designated_rural": int(df.loc[df.is_designated, "is_rural"].sum()),
        "eligible_rural": int(df.is_rural.sum()),
        "added_oct": int(df.added_oct.sum()),
        "added_oct_designated": int(df.loc[df.added_oct, "y"].sum()),
        "jurisdictions": int(len(st)),
        "full_designation_jurisdictions": [STATE_ABBR[f] for f in full],
        "pop_designated": int(df.loc[df.is_designated, "pop"].sum()),
        "pop_eligible": int(df["pop"].sum()),
    }

    # OZ 1.0 continuity, counted across *all* 2020 tracts — including former OZs that are
    # no longer eligible at all under the 2020–2024 ACS.
    o_all = pd.read_parquet(DATA / "oz1_overlap.parquet")
    o_all = o_all[o_all.is_oz1]
    des_ids = set(df.loc[df.is_designated, "geoid"])
    elig_ids = set(df.geoid)
    national["oz1"] = {
        "oz1_2020_tracts": int(len(o_all)),
        "still_eligible": int(o_all.geoid.isin(elig_ids).sum()),
        "redesignated": int(o_all.geoid.isin(des_ids).sum()),
        "designated_that_were_oz1": int(df.loc[df.is_designated, "is_oz1"].sum()),
        "note": "OZ 1.0 used 2010 tracts; counts here are 2020 tracts with ≥50% of land area in a 2018 QOZ.",
    }

    analysis = {
        "binary": [{"key": k, "label": lbl, **binary_lift(sel, k)} for k, lbl in BINARY],
        "continuous": [{"key": k, "label": lbl, **continuous_pct(sel, k),
                        "deciles": decile_curve(sel, k)} for k, lbl in CONTINUOUS],
        "logit": run_logit(sel),
        "selection_states": int(sel.state_fips.nunique()),
    }

    # Per-state profile
    profiles = []
    for fips, g in df.groupby("state_fips"):
        d, n = g[g.y == 1], g[g.y == 0]
        rate = g.y.mean()
        prof = {
            "fips": fips, "abbr": STATE_ABBR[fips], "name": g.state_name.iloc[0],
            "eligible": len(g), "designated": int(g.y.sum()),
            "designated_rural": int(d.is_rural.sum()),
            "rural_share_eligible": r1(g.is_rural.mean() * 100),
            "rural_share_designated": r1(d.is_rural.mean() * 100),
            "oz1_share_eligible": r1(g.is_oz1.mean() * 100),
            "oz1_share_designated": r1(d.is_oz1.mean() * 100),
            "oz1_share_not": r1(n.is_oz1.mean() * 100) if len(n) else None,
            "rural_share_not": r1(n.is_rural.mean() * 100) if len(n) else None,
            "tier1_share_not": r1(n.ui_tier1.mean() * 100) if len(n) else None,
            "tier1_share_eligible": r1(g.ui_tier1.mean() * 100),
            "tier1_share_designated": r1(d.ui_tier1.mean() * 100),
            "nmtc_share_designated": r1(d.has_nmtc.mean() * 100),
            "poverty_median_designated": r1(d.poverty_rate.median()),
            "poverty_median_not": r1(n.poverty_rate.median()) if len(n) else None,
            "mfi_ratio_median_designated": r1(d.mfi_ratio.median()),
            "mfi_ratio_median_not": r1(n.mfi_ratio.median()) if len(n) else None,
            "nonwhite_designated": r1(d.pct_nonwhite.mean() * 100),
            "nonwhite_not": r1(n.pct_nonwhite.mean() * 100) if len(n) else None,
            "density_median_designated": r1(d.pop_density.median(), 0),
            "density_median_not": r1(n.pop_density.median(), 0) if len(n) else None,
            "counties_eligible": int(g.county_fips.nunique()),
            "counties_designated": int(d.county_fips.nunique()),
            "full_designation": fips in full,
            "added_oct": int(g.added_oct.sum()),
            "added_oct_designated": int(g.loc[g.added_oct, "y"].sum()),
            "pop_designated": int(d["pop"].sum()),
        }
        # Top distinguishing traits: within-state standardized mean differences.
        if 0 < rate < 1:
            traits = []
            for col, more, less in LEANING_TRAITS:
                x = g[col].astype(float)
                sd = x.std()
                if not sd or math.isnan(sd):
                    continue
                smd = (x[g.y == 1].mean() - x[g.y == 0].mean()) / sd
                traits.append((smd, more, less))
            traits.sort(key=lambda t: -abs(t[0]))
            prof["leaning"] = [{"smd": r1(smd, 2), "text": more if smd > 0 else less}
                               for smd, more, less in traits[:3] if abs(smd) >= 0.15]
        else:
            prof["leaning"] = []
        profiles.append(prof)
    analysis["states"] = profiles

    meta = {
        "generated": today,
        "sources": {
            "designations": "Treasury OTP, OZ2-Designations-2027-Data-Transparency-10302026.xlsx",
            "eligible": "Treasury OTP, OZ2-Eligible-Tracts-Data-Transparency-10302026.xlsx",
            "acs": "ACS 2020–2024 5-year, table-based Summary File",
            "oz1": "IRS Notice 2018-48 / 2019-42, Census 2020↔2010 tract relationship file",
        },
        "tag_rules": TAG_RULES,
    }
    (DATA / "designation_analysis.json").write_text(json.dumps(
        {"meta": meta, "national": national, **analysis}, indent=1, allow_nan=False))

    # ---- State page data -------------------------------------------------------------
    df["tags"] = df.apply(tags_for, axis=1)
    oz1_lost = o_all[~o_all.geoid.isin(des_ids)].copy()
    oz1_lost["county_fips"] = oz1_lost.geoid.str[:5]
    by_state = {}
    for fips, g in df.groupby("state_fips"):
        d = g[g.y == 1].sort_values(["county_name", "geoid"])
        tracts = [{
            "geoid": r.geoid, "county": r.county_name,
            "place": r.place_name if isinstance(r.place_name, str) else None,
            "rural": bool(r.is_rural), "pov": r1(r.poverty_rate), "mfi": r1(r.mfi_ratio),
            "pop": None if pd.isna(r["pop"]) else int(r["pop"]),
            "renter": r1(r.pct_renter * 100) if pd.notna(r.pct_renter) else None,
            "vac": r1(r.vacancy_rate * 100) if pd.notna(r.vacancy_rate) else None,
            "unemp": r1(r.unemp_rate * 100) if pd.notna(r.unemp_rate) else None,
            "hv": None if pd.isna(r.median_home_value) else int(r.median_home_value),
            "ui": None if pd.isna(r.ui_invest_score) else int(r.ui_invest_score),
            "nmtc_n": int(r.nmtc_n), "nmtc_usd": int(r.nmtc_usd),
            "cdes": r.cde_names if isinstance(r.cde_names, list) else [],
            "tribal": r.tribal_area_name if isinstance(r.tribal_area_name, str) else None,
            "tags": r.tags,
        } for _, r in d.iterrows()]

        counties = []
        for cf, cg in g.groupby("county_fips"):
            cd = cg[cg.y == 1]
            cdes = sorted({c for lst in cd.cde_names if isinstance(lst, list) for c in lst})
            counties.append({
                "fips": cf, "name": cg.county_name.iloc[0],
                "eligible": len(cg), "designated": len(cd),
                "rural": int(cd.is_rural.sum()),
                "oz1_kept": int(cd.is_oz1.sum()),
                "oz1_lost": int((oz1_lost.county_fips == cf).sum()),
                "pop": int(cd["pop"].fillna(0).sum()),
                "cdes": cdes,
            })
        counties.sort(key=lambda c: (-c["designated"], c["name"]))
        by_state[fips] = {"tracts": tracts, "counties": counties,
                          "oz1_lost": int(oz1_lost.geoid.str[:2].eq(fips).sum())}
    (DATA / "designations_by_state.json").write_text(json.dumps(by_state, separators=(",", ":"), allow_nan=False))

    # ---- Download --------------------------------------------------------------------
    out = df.assign(tags=df.tags.str.join(";"), cde_names=df.cde_names.apply(
        lambda v: "; ".join(v) if isinstance(v, list) else ""))
    cols = ["geoid", "qozid", "state_abbr", "state_name", "county_name", "place_name", "is_designated",
            "is_rural", "in_april_list", "lic_basis", "poverty_rate", "mfi_ratio", "pop", "pop_density",
            "pct_nonwhite", "pct_black_nh", "pct_hispanic", "unemp_rate", "pct_ba_plus", "pct_renter",
            "vacancy_rate", "pct_rent_burdened", "median_home_value", "median_gross_rent",
            "median_hh_income", "is_oz1", "oz1_land_share", "is_cra_lmi", "dci_score",
            "ui_invest_score", "is_persistent_poverty", "is_tribal_overlap", "tribal_area_name",
            "nmtc_n", "nmtc_usd", "cde_names", "tags"]
    (ROOT / "public" / "data").mkdir(parents=True, exist_ok=True)
    out[cols].sort_values("geoid").to_csv(ROOT / "public" / "data" / "oz2-designations-2027.csv",
                                          index=False, float_format="%.4g")

    print(json.dumps(national, indent=1))
    for b in analysis["binary"]:
        print(f"  {b['label']:45s} lift {b['lift']}  ({b['rate_with']}% vs {b['rate_without']}%)")
    for c in analysis["continuous"]:
        print(f"  {c['label']:45s} pctile {c['designated_percentile']}  deciles {c['deciles']}")
    print(json.dumps(analysis["logit"], indent=1))


if __name__ == "__main__":
    main()
