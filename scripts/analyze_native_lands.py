#!/usr/bin/env python3
"""
The 2027 designations through the lens of Native lands and Native communities.

Inputs
    data/native_lands.parquet          ingest_native_lands.py
    everything analyze_designations.py loads (reused via its load())

    data/cdfis_certified.parquet       ingest_native_cdfis.py (Native CDFI flag, HQ tract, HQ AIANNH)
    data/cdfi_nmtc.parquet             ingest_cdfi_counts.py (NMTC projects by tract and CDE)

Output
    data/native_lands_analysis.json    national findings, per-reservation and per-state tables
                                        (for /designations#native-lands and state pages)

Two lenses, kept separate because they answer different questions:

  Land    — ≥50% of the tract's 2020 residents live on federally recognized reservation /
            off-reservation trust land, or (Hawaii) ≥10% on Hawaiian Home Land. Homestead
            communities are small relative to tracts, so a lower threshold is needed to capture
            any tract at all. Area share (≥50% of land) is kept as a sensitivity check.
            Rules live in native_rules.py.
  People  — Native residents ≥20% of the tract (AIAN alone; in Hawaii, AIAN + NHPI alone).
            "Majority Native" = ≥50%.

Statistical areas (Oklahoma OTSAs, Alaska ANVSAs, state-designated SDTSAs) are reported
for context only. They are Census tabulation areas, not land held by or for a tribe; the
Oklahoma OTSAs alone cover most of eastern Oklahoma, Tulsa included.

Method is the same as analyze_designations.py: comparisons are within-state ("lift" =
observed designations ÷ the number expected if each state picked at its own overall rate),
and the six jurisdictions that designated every eligible tract are excluded from lift and
model figures (Wyoming, with the Wind River Reservation, is one of them).
"""

import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from analyze_designations import load, r1  # noqa: E402
from native_rules import LAND_FED, LAND_HHL, POP_MAJ, POP_SUB, add_flags  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def flags(df: pd.DataFrame) -> pd.DataFrame:
    n = add_flags(pd.read_parquet(DATA / "native_lands.parquet"))
    df = df.drop(columns=[c for c in n.columns if c != "geoid" and c in df.columns]).merge(n, on="geoid", how="left")
    for c in [c for c in n.columns if c.endswith("_share")]:
        df[c] = df[c].fillna(0.0)
    for c in ["land_area", "land_res", "land_hhl", "native_land", "native_pop", "native_maj", "tribal_tag"]:
        df[c] = df[c].fillna(False).astype(bool)
    df["is_hi"] = df.state_fips == "15"
    df["either"] = df.native_land | df.native_pop
    df["native_n"] = (df.aian_alone.fillna(0) + df.nhpi_alone.where(df.is_hi, 0).fillna(0))
    return df


def lift(sel: pd.DataFrame, mask: pd.Series) -> dict:
    rate = sel.groupby("state_fips").y.transform("mean")
    obs = int(sel.loc[mask, "y"].sum())
    exp = float(rate[mask].sum())
    return {
        "n_eligible": int(mask.sum()),
        "n_designated": obs,
        "rate": r1(sel.loc[mask, "y"].mean() * 100) if mask.any() else None,
        "expected": r1(exp, 1),
        "lift": r1(obs / exp, 2) if exp else None,
    }


def counts(g: pd.DataFrame, mask: pd.Series) -> dict:
    return {"eligible": int(mask.sum()), "designated": int(g.loc[mask, "y"].sum())}


def run_logit(sel: pd.DataFrame) -> dict:
    """Same specification as analyze_designations.run_logit, plus the two Native lenses."""
    import statsmodels.formula.api as smf

    m = sel.copy()
    m["log_density"] = np.log1p(m.pop_density)
    num = ["poverty_rate", "mfi_ratio", "pop", "log_density", "unemp_rate", "pct_ba_plus",
           "pct_renter", "vacancy_rate", "median_home_value", "pct_nonwhite"]
    m = m.dropna(subset=num + ["ui_invest_score"])
    for c in num:
        m[c + "_z"] = (m[c] - m[c].mean()) / m[c].std()
    bins = ["native_land", "native_pop", "is_oz1", "has_nmtc", "is_rural", "is_cra_lmi", "ui_tier1", "ui_tier3"]
    for c in bins:
        m[c] = m[c].astype(int)
    terms = [c + "_z" for c in num] + bins
    groups = m.county_fips.astype("category").cat.codes

    def fit(ts):
        return smf.logit("y ~ " + " + ".join(ts) + " + C(state_fips)", data=m).fit(
            disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": groups})

    res = fit(terms)
    ame = res.get_margeff(at="overall").summary_frame()
    ci = res.conf_int()
    out = {}
    for t in ["native_land", "native_pop"]:
        out[t] = {"odds_ratio": r1(math.exp(res.params[t]), 2),
                  "ci": [r1(math.exp(ci.loc[t, 0]), 2), r1(math.exp(ci.loc[t, 1]), 2)],
                  "ame_pp": r1(ame.loc[t, "dy/dx"] * 100, 1), "p": float(f"{res.pvalues[t]:.2g}")}
    # Robustness: native_pop overlaps with "residents of color" and with native_land.
    variants = {
        "without residents of color": [t for t in terms if t != "pct_nonwhite_z"],
        "population lens only": [t for t in terms if t != "native_land"],
        "population lens only, without residents of color": [t for t in terms if t not in ("native_land", "pct_nonwhite_z")],
        "land lens only": [t for t in terms if t != "native_pop"],
    }
    out["robustness"] = []
    for label, ts in variants.items():
        r = fit(ts)
        out["robustness"].append({"spec": label, **{t: {"odds_ratio": r1(math.exp(r.params[t]), 2),
                                                        "p": float(f"{r.pvalues[t]:.2g}")}
                                                    for t in ("native_land", "native_pop") if t in ts}})
    out["n"] = int(res.nobs)
    out["n_native_land"] = int(m.native_land.sum())
    out["n_native_pop"] = int(m.native_pop.sum())
    out["note"] = ("Logit with state fixed effects and county-clustered SEs; same controls as the main "
                   "model on /designations (poverty, income, population, density, unemployment, education, "
                   "renters, vacancy, home value, residents of color, OZ 1.0, NMTC, rural, CRA, Urban tiers).")
    return out


def main() -> None:
    df = flags(load())
    st = df.groupby("state_fips").agg(elig=("y", "size"), des=("y", "sum"))
    full = set(st.index[st.des == st.elig])
    sel = df[~df.state_fips.isin(full)].copy()
    with_pop = df[df.total_pop.notna()]

    # ---- National ------------------------------------------------------------------
    d = df[df.y == 1]
    national = {
        "eligible": int(len(df)),
        "designated": int(df.y.sum()),
        "land": counts(df, df.native_land),
        "land_res": counts(df, df.land_res),
        "land_hhl": counts(df, df.land_hhl),
        "land_area": counts(df, df.land_area),
        "land_by_pop_not_area": counts(df, df.land_res & ~df.land_area),
        "land_by_area_not_pop": counts(df, df.land_area & ~df.land_res),
        "native_on_land_eligible": int(df.native_on_land2020.fillna(0).sum()),
        "native_on_land_designated": int(d.native_on_land2020.fillna(0).sum()),
        "pop": counts(df, df.native_pop),
        "maj": counts(df, df.native_maj),
        "either": counts(df, df.either),
        "both": counts(df, df.native_land & df.native_pop),
        "land_only": counts(df, df.native_land & ~df.native_pop),
        "pop_only": counts(df, df.native_pop & ~df.native_land),
        "native_residents_eligible": int(with_pop.native_n.sum()),
        "native_residents_designated": int(d.native_n.sum()),
        "residents_eligible": int(with_pop.total_pop.sum()),
        "residents_designated": int(d.total_pop.sum()),
        "land_oz1": counts(df, df.native_land & df.is_oz1),
        "land_designated_rural": int((df.native_land & df.is_rural & (df.y == 1)).sum()),
        "pop_oz1": counts(df, df.native_pop & df.is_oz1),
        "rural_share_land": r1(df.loc[df.native_land, "is_rural"].mean() * 100),
        "poverty_median_land": r1(df.loc[df.native_land, "poverty_rate"].median()),
        "poverty_median_all": r1(df.poverty_rate.median()),
        "states_with_land": int(df.loc[df.native_land, "state_fips"].nunique()),
        "states_with_pop": int(df.loc[df.native_pop, "state_fips"].nunique()),
    }
    national["native_resident_share_designated"] = r1(
        national["native_residents_designated"] / national["native_residents_eligible"] * 100)
    national["resident_share_designated"] = r1(
        national["residents_designated"] / national["residents_eligible"] * 100)

    selection = {
        "states": int(sel.state_fips.nunique()),
        "excluded": sorted(df.loc[df.state_fips.isin(full), "state_abbr"].unique().tolist()),
        "land": lift(sel, sel.native_land),
        "land_res": lift(sel, sel.land_res),
        "land_area": lift(sel, sel.land_area),
        "pop": lift(sel, sel.native_pop),
        "maj": lift(sel, sel.native_maj),
        "both": lift(sel, sel.native_land & sel.native_pop),
        "land_only": lift(sel, sel.native_land & ~sel.native_pop),
        "pop_only": lift(sel, sel.native_pop & ~sel.native_land),
        "rural_not_native": lift(sel, sel.is_rural & ~sel.either),
        "logit": run_logit(sel),
    }
    # Did states that published a tribal consultation framework (state_metadata.yaml
    # tribal_consultation.framework) designate Native tracts differently? Descriptive only.
    import yaml
    meta = yaml.safe_load((ROOT / "state_metadata.yaml").read_text())
    meta = meta.get("states", meta) if isinstance(meta, dict) else meta
    rows = meta.values() if isinstance(meta, dict) else meta
    fw = {str(r["fips"]).zfill(2) for r in rows if (r.get("tribal_consultation") or {}).get("framework")}
    has_fw = sel.state_fips.isin(fw)
    selection["consultation"] = {
        "with_framework": lift(sel, sel.either & has_fw) | {"states": sorted(sel.loc[sel.either & has_fw, "state_abbr"].unique().tolist())},
        "without_framework": lift(sel, sel.either & ~has_fw),
        "note": "Native land or community tracts, by whether the state's tribal_consultation.framework is populated.",
    }
    # Within-state percentile of Native share among designated tracts, in states with a
    # meaningful Native population (≥5 tracts at ≥20%). 50 = no preference.
    big = sel.groupby("state_fips").native_pop.sum()
    big = big[big >= 5].index
    sb = sel[sel.state_fips.isin(big)]
    pr = sb.groupby("state_fips").native_pct.rank(pct=True) * 100
    selection["native_pct_percentile"] = {"states": int(len(big)), "designated_percentile": r1(pr[sb.y == 1].mean())}

    context = {
        k: counts(df, df[f"{k}_share"] >= 0.5) | {"states": sorted(df.loc[df[f"{k}_share"] >= 0.5, "state_abbr"].unique().tolist())}
        for k in ["otsa", "anvsa", "sdtsa"]
    }

    # ---- Native CDFIs and NMTC ------------------------------------------------------
    cd = pd.read_parquet(DATA / "cdfis_certified.parquet")
    cd = cd[cd.native].copy()
    tr_status = df.set_index("geoid")[["y", "native_land", "state_fips"]]
    cd["hq_eligible"] = cd.geoid.isin(tr_status.index)
    cd["hq_designated"] = cd.geoid.map(tr_status.y).fillna(0).astype(bool)
    cd["on_land"] = cd.aiannh_class.isin(["federal", "hhl"])
    nm = pd.read_parquet(DATA / "cdfi_nmtc.parquet")
    native_cde = nm.cde_name.str.contains(r"Native|Tribal|Chickasaw|Alaska Growth", case=False, regex=True)
    nm_land = nm[nm.geoid.isin(df.loc[df.native_land, "geoid"])]
    cdfis = {
        "native_cdfis": int(len(cd)),
        "hq_on_land": int(cd.on_land.sum()),
        "hq_in_statistical_area": int(cd.aiannh_class.isin(["otsa", "anvsa", "sdtsa"]).sum()),
        "hq_in_eligible_tract": int(cd.hq_eligible.sum()),
        "hq_in_designated_tract": int(cd.hq_designated.sum()),
        "match": cd.match.value_counts().to_dict(),
        "nmtc_projects_land_tracts": int(len(nm_land)),
        "nmtc_usd_land_tracts": int(nm_land.qlici_amount.sum()),
        "nmtc_land_tracts_with_project": int(nm_land.geoid.nunique()),
        "nmtc_land_tracts_with_project_designated": int(df.loc[df.geoid.isin(nm_land.geoid), "y"].sum()),
        "native_cdes": sorted(nm.loc[native_cde, "cde_name"].unique().tolist()),
        "native_cde_projects": int(native_cde.sum()),
        "native_cde_usd": int(nm.loc[native_cde, "qlici_amount"].sum()),
        "list_date": "2026-11-16",
    }
    by_res = cd[cd.aiannh_class == "federal"].groupby("aiannh_name").name.apply(sorted).to_dict()

    # ---- Reservations --------------------------------------------------------------
    res = []
    for name, g in df[df.land_res].groupby("federal_name"):
        res.append({
            "name": name,
            "states": sorted(g.state_abbr.unique().tolist()),
            "eligible": int(len(g)), "designated": int(g.y.sum()),
            "native_residents": int(g.native_n.sum()),
            "full_state": bool(g.state_fips.isin(full).all()),
            "cdfis": by_res.get(name, []),
        })
    res.sort(key=lambda r: (-r["eligible"], r["name"]))
    n_res = len(res)
    n_any = sum(r["designated"] > 0 for r in res)
    n_none_selected = sum(r["designated"] == 0 and not r["full_state"] for r in res)
    sel_res = [r for r in res if not r["full_state"]]
    with_c = [r for r in sel_res if r["cdfis"]]
    cdfis["reservations_with_local_cdfi"] = len(with_c)
    cdfis["reservations_with_local_cdfi_designated"] = sum(r["designated"] > 0 for r in with_c)
    cdfis["reservations_without_local_cdfi"] = len(sel_res) - len(with_c)
    cdfis["reservations_without_local_cdfi_designated"] = sum(r["designated"] > 0 for r in sel_res if not r["cdfis"])
    reservations = {
        "n": n_res, "with_designation": n_any, "without_designation": n_none_selected,
        "list": res,
        "note": "Federally recognized reservations and off-reservation trust land with at least one eligible "
                "tract ≥50% inside it. A tract is attributed to the entity holding the most land in it.",
    }

    # ---- States --------------------------------------------------------------------
    states = {}
    for fips, g in df.groupby("state_fips"):
        any_native = g.either.any() or (g[["otsa_share", "anvsa_share", "sdtsa_share"]] >= 0.5).any().any()
        if not any_native and not cd.state.eq(g.state_abbr.iloc[0]).any():
            continue
        gd = g[g.y == 1]
        gp = g[g.total_pop.notna()]
        rate = g.y.mean()
        s = {
            "abbr": g.state_abbr.iloc[0], "name": g.state_name.iloc[0],
            "eligible": int(len(g)), "designated": int(g.y.sum()), "rate": r1(rate * 100),
            "full_designation": fips in full,
            "land": counts(g, g.native_land), "land_hhl": counts(g, g.land_hhl),
            "pop": counts(g, g.native_pop), "maj": counts(g, g.native_maj),
            "either": counts(g, g.either),
            "land_oz1": counts(g, g.native_land & g.is_oz1),
            "land_designated_rural": int((g.native_land & g.is_rural & (g.y == 1)).sum()),
            "otsa": counts(g, g.otsa_share >= 0.5), "anvsa": counts(g, g.anvsa_share >= 0.5),
            "sdtsa": counts(g, g.sdtsa_share >= 0.5),
            "native_residents_eligible": int(gp.native_n.sum()),
            "native_residents_designated": int(gd.native_n.sum()),
            "residents_eligible": int(gp.total_pop.sum()),
            "residents_designated": int(gd.total_pop.sum()),
            "native_share_eligible": r1(gp.native_n.sum() / gp.total_pop.sum() * 100) if gp.total_pop.sum() else None,
            "native_share_designated": r1(gd.native_n.sum() / gd.total_pop.sum() * 100) if gd.total_pop.sum() else None,
            "reservations": sorted(
                ({"name": nm, "eligible": int(len(rg)), "designated": int(rg.y.sum())}
                 for nm, rg in g[g.land_res].groupby("federal_name")),
                key=lambda r: (-r["eligible"], r["name"])),
            "nmtc_projects_land": int(nm_land.geoid.str[:2].eq(fips).sum()),
            "cdfis": [{"name": c.name, "city": c.city, "type": c.cdfi_type,
                       "on": c.aiannh_name if isinstance(c.aiannh_name, str) else None,
                       "on_class": c.aiannh_class if isinstance(c.aiannh_class, str) else None,
                       "hq_designated": bool(c.hq_designated), "hq_eligible": bool(c.hq_eligible),
                       "approx": c.match in ("Place", "ZIP"), "website": c.website if isinstance(c.website, str) else None}
                      for c in cd[cd.state == g.state_abbr.iloc[0]].sort_values("name").itertuples()],
        }
        if fips not in full and s["either"]["eligible"]:
            s["expected_either"] = r1(rate * s["either"]["eligible"], 1)
        states[fips] = s

    out = {
        "meta": {
            "generated": date.today().isoformat(),
            "definitions": {
                "land": f"≥{int(LAND_FED*100)}% of 2020 residents live on federally recognized reservation or "
                        f"off-reservation trust land, or (Hawaii) ≥{int(LAND_HHL*100)}% on Hawaiian Home Lands",
                "land_area": f"≥{int(LAND_FED*100)}% of tract area in reservation or trust land (sensitivity check)",
                "pop": f"Native residents ≥{int(POP_SUB*100)}% of population (AIAN alone; in Hawaii, AIAN + NHPI alone)",
                "maj": f"Native residents ≥{int(POP_MAJ*100)}%",
            },
            "sources": {
                "boundaries": "Census TIGER/Line 2024 AIANNH; 2024 cartographic boundary tracts (500k)",
                "population": "ACS 2020–2024 5-year, tables B02001, B02010, B02012",
                "blocks": "2020 Census PL 94-171 redistricting file, block level (AIANHH code, P1)",
            },
        },
        "national": national, "selection": selection, "context": context,
        "reservations": reservations, "states": states, "cdfis": cdfis,
    }
    (DATA / "native_lands_analysis.json").write_text(json.dumps(out, indent=1, allow_nan=False))
    print(json.dumps({k: out[k] for k in ("national", "selection", "context")}, indent=1))
    print(json.dumps(cdfis, indent=1))
    print(f"reservations: {n_res}, with ≥1 designated: {n_any}, none (selection states): {n_none_selected}")


if __name__ == "__main__":
    main()
