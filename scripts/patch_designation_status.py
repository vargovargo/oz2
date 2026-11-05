#!/usr/bin/env python3
"""Add the `designation` block to state_metadata.yaml from Treasury's final list.

Re-runnable and idempotent, same convention as patch_nomination_status.py.
Run after scripts/ingest_designated_tracts.py, ingest_oz1_tracts.py and
analyze_designations.py.

Schema
------
designation:
  published: 'YYYY-MM-DD'      # date on Treasury's designation file
  eligible_final: int          # eligible LICs on Treasury's October 30 list
  designated: int              # 2027 QOZs designated
  designated_rural: int        # of which rural (QROF treatment)
  cap: int                     # max(25, ceil(25% of eligible_final))
  oz1_redesignated: int        # designated tracts that were ≥50% in a 2018 QOZ
  oz1_lost: int                # 2020 tracts ≥50% in a 2018 QOZ that were not designated
  counties_designated: int
  source_url: str

Also:
  * nomination.status → 'certified' and nomination.tract_count → the designated count.
    The 'filed_confirmed' entries recorded what a state *said* it filed; the certified
    count is what Treasury designated. Where they differ (AZ 125 → 127, TX 605 → 608)
    the state's figure is kept in nomination.source_note.
  * max_designations is NOT overwritten: it records the April-list cap the state planned
    against. designation.cap is the cap on the final list.
"""

import json
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "state_metadata.yaml"
PUBLISHED = "2026-10-30"
SOURCE = "https://home.treasury.gov/policy-issues/tax-policy/data-transparency/qualified-opportunity-zones"
CHECKED = "2026-11-05"


def main() -> None:
    data = yaml.safe_load(META.read_text())
    analysis = json.loads((ROOT / "data" / "designation_analysis.json").read_text())
    by_state = json.loads((ROOT / "data" / "designations_by_state.json").read_text())
    prof = {p["fips"]: p for p in analysis["states"]}

    for slug, s in data.items():
        p = prof[s["fips"]]
        oz1_kept = sum(1 for t in by_state[s["fips"]]["tracts"] if "oz1" in t["tags"])
        s["designation"] = {
            "published": PUBLISHED,
            "eligible_final": p["eligible"],
            "designated": p["designated"],
            "designated_rural": p["designated_rural"],
            "cap": max(25, math.ceil(0.25 * p["eligible"])),
            "oz1_redesignated": oz1_kept,
            "oz1_lost": by_state[s["fips"]]["oz1_lost"],
            "counties_designated": p["counties_designated"],
            "source_url": SOURCE,
        }
        nom = s["nomination"]
        if nom.get("status") != "certified":
            if nom.get("tract_count") not in (None, p["designated"]):
                note = f"State reported {nom['tract_count']} tracts filed; Treasury certified {p['designated']}."
                nom["source_note"] = (nom.get("source_note") + " " if nom.get("source_note") else "") + note
            nom["status"] = "certified"
            nom["tract_count"] = p["designated"]
        nom["last_checked"] = CHECKED

    META.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False, width=88, allow_unicode=True))
    print(f"patched {len(data)} states")


if __name__ == "__main__":
    main()
