"""
Generate state_metadata.yaml scaffold from data/state_summaries.csv.

All 51 states + DC are stubbed with numeric data from the IRS appendix
and null placeholders for fields that require manual research.

Run: python scripts/generate_state_metadata.py
Output: state_metadata.yaml (project root)
"""

import pandas as pd
import yaml
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_YAML = Path(__file__).parent.parent / "state_metadata.yaml"
LAST_CHECKED = "2026-05-05"

# Territory FIPS — Phase 2, excluded here
TERRITORY_FIPS = {60, 66, 69, 72, 78}


def make_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "")


def parse_top10(fips_str, name_str, count_str) -> list:
    if not all(pd.notna(v) for v in [fips_str, name_str, count_str]):
        return []
    return [
        {"fips": f, "name": n, "eligible_count": int(c)}
        for f, n, c in zip(
            fips_str.split("|"),
            name_str.split("|"),
            count_str.split("|"),
        )
    ]


def build_entry(row) -> dict:
    return {
        "name": row["state_name"],
        "fips": str(int(row["state_fips"])).zfill(2),
        "slug": make_slug(row["state_name"]),
        "total_eligible": int(row["total_eligible"]),
        "rural_eligible": int(row["rural_eligible"]),
        "pct_rural": float(row["pct_rural"]),
        "max_designations": int(row["max_designations"]),
        "top10_counties": parse_top10(
            row["top10_county_fips"],
            row["top10_county_name"],
            row["top10_county_eligible_count"],
        ),
        "status_tier": "no_public_process",
        "last_checked": LAST_CHECKED,
        "lead_agency": {
            "name": None,
            "url": None,
            "contact_email": None,
            "contact_phone": None,
        },
        "process": None,
        "scoring_rubric_url": None,
        "state_deadline": None,
        "application_portal_url": None,
        "tribal_consultation": {
            "framework": None,
            "citation": None,
        },
        "regional_edds": [],
        "rural_partners": {
            "usda_rd_url": None,
            "rcap_regional": None,
            "rural_lisc": None,
        },
        "state_cdfi_count": None,
        "notes": None,
    }


def main():
    df = pd.read_csv(DATA_DIR / "state_summaries.csv")
    df = df[~df["state_fips"].isin(TERRITORY_FIPS)].copy()
    df = df.sort_values("state_name").reset_index(drop=True)

    metadata = {}
    for _, row in df.iterrows():
        entry = build_entry(row)
        metadata[entry["slug"]] = entry

    with open(OUT_YAML, "w") as f:
        yaml.dump(
            metadata,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    print(f"Wrote {len(metadata)} state entries → {OUT_YAML}")
    print("Slugs:", ", ".join(list(metadata.keys())[:5]), "...")


if __name__ == "__main__":
    main()
