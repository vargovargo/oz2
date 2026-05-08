"""
Compute per-state overlay stats from parquet files and patch state_metadata.yaml.

Sources
-------
  data/dci.parquet               — tract-level DCI scores (from ingest_dci.py)
  data/persistent_poverty.parquet — county-level PP flags (from ingest_persistent_poverty.py)
  data/cdfi_nmtc.parquet         — NMTC projects in eligible OZ tracts (from ingest_cdfi_counts.py)
  data/eligible_tracts.parquet   — 25,332 eligible OZ tracts with state_fips

New fields patched into state_metadata.yaml
-------------------------------------------
  dci_q1_tracts   int | null  Eligible tracts in DCI quintile 1 (most distressed)
  pp_county_count int | null  Counties with eligible tracts flagged as USDA persistent poverty
  nmtc_projects   int | null  NMTC projects in eligible OZ tracts (distinct from CDEs)
"""

import re
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
YAML_PATH = Path(__file__).parent.parent / "state_metadata.yaml"

ABBREV_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56", "AS": "60", "GU": "66", "MP": "69",
    "PR": "72", "VI": "78",
}
FIPS_TO_SLUG = {
    "01": "alabama", "02": "alaska", "04": "arizona", "05": "arkansas",
    "06": "california", "08": "colorado", "09": "connecticut", "10": "delaware",
    "11": "district-of-columbia", "12": "florida", "13": "georgia", "15": "hawaii",
    "16": "idaho", "17": "illinois", "18": "indiana", "19": "iowa", "20": "kansas",
    "21": "kentucky", "22": "louisiana", "23": "maine", "24": "maryland",
    "25": "massachusetts", "26": "michigan", "27": "minnesota", "28": "mississippi",
    "29": "missouri", "30": "montana", "31": "nebraska", "32": "nevada",
    "33": "new-hampshire", "34": "new-jersey", "35": "new-mexico", "36": "new-york",
    "37": "north-carolina", "38": "north-dakota", "39": "ohio", "40": "oklahoma",
    "41": "oregon", "42": "pennsylvania", "44": "rhode-island", "45": "south-carolina",
    "46": "south-dakota", "47": "tennessee", "48": "texas", "49": "utah",
    "50": "vermont", "51": "virginia", "53": "washington", "54": "west-virginia",
    "55": "wisconsin", "56": "wyoming", "60": "american-samoa", "66": "guam",
    "69": "northern-mariana-islands", "72": "puerto-rico", "78": "us-virgin-islands",
}
SLUG_TO_FIPS = {v: k for k, v in FIPS_TO_SLUG.items()}


def load_parquets():
    paths = {
        "dci":  DATA_DIR / "dci.parquet",
        "pp":   DATA_DIR / "persistent_poverty.parquet",
        "nmtc": DATA_DIR / "cdfi_nmtc.parquet",
        "elig": DATA_DIR / "eligible_tracts.parquet",
    }
    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        sys.exit(f"Missing parquet files: {', '.join(missing)}. Run ingest scripts first.")

    dci  = pd.read_parquet(paths["dci"])
    pp   = pd.read_parquet(paths["pp"])
    nmtc = pd.read_parquet(paths["nmtc"])
    elig = pd.read_parquet(paths["elig"], columns=["geoid", "state_fips"])
    return dci, pp, nmtc, elig


def compute_stats(dci, pp, nmtc, elig):
    """Return dict[state_fips → {dci_q1_tracts, pp_county_count, nmtc_projects}]"""
    stats: dict[str, dict] = {fips: {} for fips in FIPS_TO_SLUG}

    # --- DCI: Q1 tract count per state ---
    # Join dci → elig to get state_fips on each tract
    dci_with_state = dci.merge(elig[["geoid", "state_fips"]], on="geoid", how="left")
    dci_q1 = dci_with_state[dci_with_state["dci_quintile"] == 1]
    q1_by_state = dci_q1.groupby("state_fips").size()
    for fips, count in q1_by_state.items():
        if fips in stats:
            stats[fips]["dci_q1_tracts"] = int(count)

    # --- Persistent poverty: PP county count per state ---
    pp_flagged = pp[pp["is_persistent_poverty"] == True]
    pp_by_state = pp_flagged.groupby("state_fips").size()
    for fips, count in pp_by_state.items():
        if fips in stats:
            stats[fips]["pp_county_count"] = int(count)

    # --- NMTC: project count per state ---
    nmtc_by_state = nmtc.groupby("state_fips").size()
    for fips, count in nmtc_by_state.items():
        if fips in stats:
            stats[fips]["nmtc_projects"] = int(count)

    return stats


def patch_yaml(stats: dict[str, dict]) -> None:
    text = YAML_PATH.read_text()
    lines = text.splitlines(keepends=True)

    current_slug: str | None = None
    current_fips: str | None = None
    updated = {"dci_q1_tracts": 0, "pp_county_count": 0, "nmtc_projects": 0}

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Top-level state key (no leading spaces, ends with colon)
        if stripped.endswith(":") and not line.startswith(" "):
            slug = stripped[:-1]
            current_slug = slug
            current_fips = SLUG_TO_FIPS.get(slug)

        if current_fips and current_fips in stats:
            s = stats[current_fips]
            indent = len(line) - len(line.lstrip())
            ind = " " * indent

            for field in ("dci_q1_tracts", "pp_county_count", "nmtc_projects"):
                if re.match(rf"^\s+{field}:", line):
                    val = s.get(field, 0)
                    lines[i] = ind + f"{field}: {val}\n"
                    updated[field] += 1

    YAML_PATH.write_text("".join(lines))
    for field, n in updated.items():
        print(f"  Patched {n} {field} fields")


def ensure_yaml_fields() -> None:
    """
    Add dci_q1_tracts, pp_county_count, nmtc_projects stub fields to any
    state block that doesn't already have them (inserted after state_cdfi_count).
    """
    text = YAML_PATH.read_text()
    lines = text.splitlines(keepends=True)

    new_lines = []
    i = 0
    inserted = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        # After state_cdfi_count, insert the new fields if not present
        if re.match(r"^\s+state_cdfi_count:", line):
            indent = " " * (len(line) - len(line.lstrip()))
            # Look ahead to see if these fields already exist
            lookahead = "".join(lines[i+1:i+6])
            if "dci_q1_tracts:" not in lookahead:
                new_lines.append(indent + "dci_q1_tracts: 0\n")
                new_lines.append(indent + "pp_county_count: 0\n")
                new_lines.append(indent + "nmtc_projects: 0\n")
                inserted += 1
        i += 1

    if inserted > 0:
        YAML_PATH.write_text("".join(new_lines))
        print(f"  Inserted stub fields for {inserted} state blocks")
    else:
        print("  All state blocks already have overlay fields")


def main():
    print("=== patch_overlay_stats.py ===")

    print("\nLoading parquet files …")
    dci, pp, nmtc, elig = load_parquets()
    print(f"  DCI:  {len(dci):,} tracts")
    print(f"  PP:   {len(pp):,} counties")
    print(f"  NMTC: {len(nmtc):,} projects")
    print(f"  Elig: {len(elig):,} tracts")

    print("\nComputing per-state stats …")
    stats = compute_stats(dci, pp, nmtc, elig)

    # Summary
    total_q1 = sum(s.get("dci_q1_tracts", 0) for s in stats.values())
    total_pp = sum(s.get("pp_county_count", 0) for s in stats.values())
    total_nmtc = sum(s.get("nmtc_projects", 0) for s in stats.values())
    print(f"  Total Q1 tracts:     {total_q1:,}")
    print(f"  Total PP counties:   {total_pp:,}")
    print(f"  Total NMTC projects: {total_nmtc:,}")

    print("\nEnsuring YAML fields exist …")
    ensure_yaml_fields()

    print("\nPatching YAML …")
    patch_yaml(stats)

    print("\nDone.")


if __name__ == "__main__":
    main()
