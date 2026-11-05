#!/usr/bin/env python3
"""
Fetch Treasury's final 2027 QOZ designations and the updated eligible-tract file.

    → data/designated_tracts.parquet   (6,576 designated 2027 QOZs)
    → data/oz2_tracts.parquet          (every eligible LIC, with designation flag
                                        and Treasury's own income/poverty fields)

Source
------
Treasury Office of Tax Policy, "Qualified Opportunity Zones" data-transparency page
https://home.treasury.gov/policy-issues/tax-policy/data-transparency/qualified-opportunity-zones

  OZ2-Designations-2027-Data-Transparency-10302026.xlsx
      sheet oz2_designations — Census Tract Number, QOZID, State or Territory,
      County or County-Equivalent Entity, Rural QOZ ("Rural" | "Non-Rural").
      QOZID = R|N + 11-digit GEOID + "27".

  OZ2-Eligible-Tracts-Data-Transparency-10302026.xlsx
      sheet oz2_for_data_transparency — every 2020 census tract (85,529 rows) with
      poverty_rate, mfi, state/cbsa/area MFI, mfi_ratio, mfi_ub(_ratio),
      temp_displacement_elig, post_surv_occ_elig, eligible_lic (0/1),
      rural_status (0/1). ACS 2020–2024 5-year.

Both files are dated October 30, 2026. The eligible file supersedes the April 6
Rev. Proc. 2026-14 appendix (data/eligible_tracts.parquet, 25,332 tracts): it lists
25,462 eligible LICs — the April list plus 130 tracts, none removed. Every
designated tract is on the October list; there are no off-list designations.

data/eligible_tracts.parquet is left untouched as the record of the April list,
since every overlay (CRA, DCI, Urban, tribal) was keyed to it.

Output schema
-------------
designated_tracts.parquet
  geoid, qozid, state_fips, county_fips, state_name, county_name, is_rural

oz2_tracts.parquet  (eligible_lic == 1 only)
  geoid, state_fips, county_fips, state_name, county_name, cbsa,
  poverty_rate, mfi, area_mfi, mfi_ratio, mfi_ub_ratio,
  lic_basis            "mfi70" | "poverty20" | "missing_data_rule"
  is_rural             bool (Treasury rural_status)
  in_april_list        bool (on the Rev. Proc. 2026-14 appendix)
  is_designated        bool
  qozid                str | null
  fetched_at

Usage
-----
    python3 scripts/ingest_designated_tracts.py           # download (cached in data/raw/treasury)
    python3 scripts/ingest_designated_tracts.py --refresh # force re-download
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = "https://home.treasury.gov/system/files/131/"
DESIGNATIONS_FILE = "OZ2-Designations-2027-Data-Transparency-10302026.xlsx"
ELIGIBLE_FILE = "OZ2-Eligible-Tracts-Data-Transparency-10302026.xlsx"

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw" / "treasury"


def fetch(name: str, refresh: bool) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / name
    if dest.exists() and not refresh:
        return dest
    print(f"  downloading {name}")
    r = requests.get(BASE + name, headers={"User-Agent": "oz2-ingest/1.0"}, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    today = date.today().isoformat()

    des = pd.read_excel(fetch(DESIGNATIONS_FILE, args.refresh), sheet_name="oz2_designations", dtype=str)
    des.columns = ["geoid", "qozid", "state_name", "county_name", "rural_label"]
    des["geoid"] = des.geoid.str.strip().str.zfill(11)
    des["county_name"] = des.county_name.str.strip()
    des["state_fips"] = des.geoid.str[:2]
    des["county_fips"] = des.geoid.str[:5]
    des["is_rural"] = des.rural_label.eq("Rural")
    des = des[["geoid", "qozid", "state_fips", "county_fips", "state_name", "county_name", "is_rural"]]
    assert des.geoid.is_unique

    el = pd.read_excel(
        fetch(ELIGIBLE_FILE, args.refresh), sheet_name="oz2_for_data_transparency",
        dtype={"census_tract_number": str},
    )
    el = el[el.eligible_lic == 1].copy()
    el["geoid"] = el.census_tract_number.str.zfill(11)
    el["county_name"] = el.county.str.strip()
    el["state_name"] = el.state
    el["state_fips"] = el.geoid.str[:2]
    el["county_fips"] = el.geoid.str[:5]
    el["is_rural"] = el.rural_status.eq(1)

    def basis(r) -> str:
        if pd.notna(r.mfi_ratio) and r.mfi_ratio <= 70:
            return "mfi70"
        if pd.notna(r.poverty_rate) and r.poverty_rate >= 20 and (pd.isna(r.mfi_ratio) or r.mfi_ratio <= 125):
            return "poverty20"
        return "missing_data_rule"

    el["lic_basis"] = el.apply(basis, axis=1)

    april = pd.read_parquet(DATA / "eligible_tracts.parquet", columns=["geoid"])
    el["in_april_list"] = el.geoid.isin(set(april.geoid))

    el = el.merge(des[["geoid", "qozid"]], on="geoid", how="left")
    el["is_designated"] = el.qozid.notna()
    el["fetched_at"] = today

    missing = set(des.geoid) - set(el.geoid)
    if missing:
        sys.exit(f"ERROR: {len(missing)} designated tracts are not on the eligible list: {sorted(missing)[:5]}")
    mismatch = (el.loc[el.is_designated].set_index("geoid").is_rural
                != des.set_index("geoid").is_rural).sum()
    if mismatch:
        sys.exit(f"ERROR: {mismatch} designated tracts disagree on rural status between files")

    cols = ["geoid", "state_fips", "county_fips", "state_name", "county_name", "cbsa",
            "poverty_rate", "mfi", "area_mfi", "mfi_ratio", "mfi_ub_ratio", "lic_basis",
            "is_rural", "in_april_list", "is_designated", "qozid", "fetched_at"]
    el[cols].to_parquet(DATA / "oz2_tracts.parquet", index=False)
    des.assign(fetched_at=today).to_parquet(DATA / "designated_tracts.parquet", index=False)

    print(f"  eligible LICs:        {len(el):,}  (April list {el.in_april_list.sum():,}; added {(~el.in_april_list).sum():,})")
    print(f"  designated:           {len(des):,}  (rural {des.is_rural.sum():,})")
    print(f"  designated share:     {len(des) / len(el):.1%}")
    print(f"  wrote data/oz2_tracts.parquet, data/designated_tracts.parquet")


if __name__ == "__main__":
    main()
