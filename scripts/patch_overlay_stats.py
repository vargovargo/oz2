"""
Compute per-state overlay stats from parquet files and patch state_metadata.yaml.

Sources
-------
  data/dci.parquet               — tract-level DCI scores (from ingest_dci.py)
  data/persistent_poverty.parquet — county-level PP flags (from ingest_persistent_poverty.py)
  data/cdfi_nmtc.parquet         — NMTC projects in eligible OZ tracts (from ingest_cdfi_counts.py)
  data/cra_lmi_overlap.parquet   — CRA LMI tract flags (from ingest_cra_lmi.py)
  data/eligible_tracts.parquet   — 25,332 eligible OZ tracts with state_fips

New fields patched into state_metadata.yaml
-------------------------------------------
  dci_q1_tracts   int | null  Eligible tracts in DCI quintile 1 (most distressed)
  pp_county_count int | null  Counties with eligible tracts flagged as USDA persistent poverty
  nmtc_projects   int | null  NMTC projects in eligible OZ tracts (distinct from CDEs)
  cra_lmi_tracts  int | null  Eligible tracts also carrying a CRA LMI designation
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
    required = {
        "dci":  DATA_DIR / "dci.parquet",
        "pp":   DATA_DIR / "persistent_poverty.parquet",
        "nmtc": DATA_DIR / "cdfi_nmtc.parquet",
        "elig": DATA_DIR / "eligible_tracts.parquet",
    }
    optional = {
        "cra":       DATA_DIR / "cra_lmi_overlap.parquet",
        "ui_invest": DATA_DIR / "urban_investability.parquet",
    }
    missing = [k for k, p in required.items() if not p.exists()]
    if missing:
        sys.exit(f"Missing parquet files: {', '.join(missing)}. Run ingest scripts first.")

    dci  = pd.read_parquet(required["dci"])
    pp   = pd.read_parquet(required["pp"])
    nmtc = pd.read_parquet(required["nmtc"])
    elig = pd.read_parquet(required["elig"], columns=["geoid", "state_fips"])

    cra = None
    if optional["cra"].exists():
        cra = pd.read_parquet(optional["cra"])
    else:
        print("  Note: cra_lmi_overlap.parquet not found — run ingest_cra_lmi.py to populate cra_lmi_tracts")

    ui_invest = None
    if optional["ui_invest"].exists():
        ui_invest = pd.read_parquet(optional["ui_invest"],
                                    columns=["geoid", "ui_invest_quintile"])
    else:
        print("  Note: urban_investability.parquet not found — run ingest_urban_investability.py to populate ui_invest_q1_tracts")

    return dci, pp, nmtc, elig, cra, ui_invest


def compute_stats(dci, pp, nmtc, elig, cra=None, ui_invest=None):
    """Return dict[state_fips → {dci_q1_tracts, pp_county_count, nmtc_projects, cra_lmi_tracts}]"""
    stats: dict[str, dict] = {fips: {} for fips in FIPS_TO_SLUG}

    # --- DCI: Q1 tract count per state ---
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

    # --- CRA LMI: eligible tracts also CRA LMI-designated per state ---
    # Only populated when cra parquet is available (from ingest_cra_lmi.py).
    # When cra is None, cra_lmi_tracts is NOT added to stats so patch_yaml
    # will leave any existing null values in state_metadata.yaml untouched.
    if cra is not None:
        cra_lmi = cra[cra["is_cra_lmi"] == True]
        cra_by_state = cra_lmi.groupby("state_fips").size()
        for fips in stats:
            stats[fips]["cra_lmi_tracts"] = int(cra_by_state.get(fips, 0))

    # --- Urban Institute investability: Q1 tract count per state ---
    if ui_invest is not None:
        ui_with_state = ui_invest.merge(elig[["geoid", "state_fips"]], on="geoid", how="left")
        ui_q1 = ui_with_state[ui_with_state["ui_invest_quintile"] == 1]
        ui_q1_by_state = ui_q1.groupby("state_fips").size()
        for fips, count in ui_q1_by_state.items():
            if fips in stats:
                stats[fips]["ui_invest_q1_tracts"] = int(count)

    return stats


OVERLAY_FIELDS = ("dci_q1_tracts", "pp_county_count", "nmtc_projects", "cra_lmi_tracts", "ui_invest_q1_tracts")


def patch_yaml(stats: dict[str, dict]) -> None:
    text = YAML_PATH.read_text()
    lines = text.splitlines(keepends=True)

    current_slug: str | None = None
    current_fips: str | None = None
    updated = {f: 0 for f in OVERLAY_FIELDS}

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped.endswith(":") and not line.startswith(" "):
            slug = stripped[:-1]
            current_slug = slug
            current_fips = SLUG_TO_FIPS.get(slug)

        if current_fips and current_fips in stats:
            s = stats[current_fips]
            indent = len(line) - len(line.lstrip())
            ind = " " * indent

            for field in OVERLAY_FIELDS:
                if re.match(rf"^\s+{field}:", line):
                    if field not in s:
                        # Data not available for this field — leave existing YAML value
                        continue
                    val = s[field]
                    lines[i] = ind + f"{field}: {val}\n"
                    updated[field] += 1

    YAML_PATH.write_text("".join(lines))
    for field, n in updated.items():
        print(f"  Patched {n} {field} fields")


def ensure_yaml_fields() -> None:
    """
    Add overlay stub fields to any state block that doesn't already have them.
    Inserted after nmtc_projects (or state_cdfi_count as fallback anchor).
    """
    text = YAML_PATH.read_text()
    lines = text.splitlines(keepends=True)

    new_lines = []
    i = 0
    inserted_cra = 0
    inserted_ui = 0
    inserted_all = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # After nmtc_projects, insert cra_lmi_tracts stub if not already present.
        if re.match(r"^\s+nmtc_projects:", line):
            indent = " " * (len(line) - len(line.lstrip()))
            lookahead = "".join(lines[i+1:i+4])
            if "cra_lmi_tracts:" not in lookahead:
                new_lines.append(indent + "cra_lmi_tracts: null\n")
                inserted_cra += 1

        # After cra_lmi_tracts, insert ui_invest_q1_tracts stub if not already present.
        elif re.match(r"^\s+cra_lmi_tracts:", line):
            indent = " " * (len(line) - len(line.lstrip()))
            lookahead = "".join(lines[i+1:i+3])
            if "ui_invest_q1_tracts:" not in lookahead:
                new_lines.append(indent + "ui_invest_q1_tracts: null\n")
                inserted_ui += 1

        # After state_cdfi_count, insert all overlay fields if none present (older YAML)
        elif re.match(r"^\s+state_cdfi_count:", line):
            indent = " " * (len(line) - len(line.lstrip()))
            lookahead = "".join(lines[i+1:i+10])
            if "dci_q1_tracts:" not in lookahead:
                new_lines.append(indent + "dci_q1_tracts: 0\n")
                new_lines.append(indent + "pp_county_count: 0\n")
                new_lines.append(indent + "nmtc_projects: 0\n")
                new_lines.append(indent + "cra_lmi_tracts: null\n")
                new_lines.append(indent + "ui_invest_q1_tracts: null\n")
                inserted_all += 1

        i += 1

    if inserted_cra > 0 or inserted_ui > 0 or inserted_all > 0:
        YAML_PATH.write_text("".join(new_lines))
        if inserted_cra:
            print(f"  Inserted cra_lmi_tracts stub for {inserted_cra} state blocks")
        if inserted_ui:
            print(f"  Inserted ui_invest_q1_tracts stub for {inserted_ui} state blocks")
        if inserted_all:
            print(f"  Inserted all overlay stubs for {inserted_all} state blocks")
    else:
        print("  All state blocks already have overlay fields")


def main():
    print("=== patch_overlay_stats.py ===")

    print("\nLoading parquet files …")
    dci, pp, nmtc, elig, cra, ui_invest = load_parquets()
    print(f"  DCI:  {len(dci):,} tracts")
    print(f"  PP:   {len(pp):,} counties")
    print(f"  NMTC: {len(nmtc):,} projects")
    print(f"  Elig: {len(elig):,} tracts")
    if cra is not None:
        print(f"  CRA:  {len(cra):,} tracts ({int(cra['is_cra_lmi'].sum()):,} LMI)")
    if ui_invest is not None:
        print(f"  UI:   {len(ui_invest):,} scored tracts")

    print("\nComputing per-state stats …")
    stats = compute_stats(dci, pp, nmtc, elig, cra, ui_invest)

    # Summary
    total_q1 = sum(s.get("dci_q1_tracts", 0) for s in stats.values())
    total_pp = sum(s.get("pp_county_count", 0) for s in stats.values())
    total_nmtc = sum(s.get("nmtc_projects", 0) for s in stats.values())
    total_cra = sum(s.get("cra_lmi_tracts", 0) for s in stats.values())
    total_ui = sum(s.get("ui_invest_q1_tracts", 0) for s in stats.values())
    print(f"  Total Q1 tracts:     {total_q1:,}")
    print(f"  Total PP counties:   {total_pp:,}")
    print(f"  Total NMTC projects: {total_nmtc:,}")
    if cra is not None:
        print(f"  Total CRA LMI tracts:{total_cra:,}")
    if ui_invest is not None:
        print(f"  Total UI Q1 tracts:  {total_ui:,}")

    print("\nEnsuring YAML fields exist …")
    ensure_yaml_fields()

    print("\nPatching YAML …")
    patch_yaml(stats)

    print("\nDone.")


if __name__ == "__main__":
    main()
