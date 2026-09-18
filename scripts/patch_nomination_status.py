#!/usr/bin/env python3
"""Add and populate the `nomination` block in state_metadata.yaml.

Re-runnable and idempotent, same convention as patch_state_metadata.py.

The block records what a state did with its federal filing, which is a different
question from the `status_tier` / `state_deadline` fields (those describe the
state's own *input* process, which closed months before the federal window).

Schema
------
nomination:
  status: filed_confirmed | filed_assumed | unknown
  submitted_date: 'YYYY-MM-DD' | null   # date the state filed with Treasury
  tract_count: int | null               # tracts the state says it nominated
  off_list_count: int | null            # § 5.04 off-list tracts included
  list_published_url: str | null        # where the state published its slate
  source_url: str | null                # source for the above
  source_note: str | null               # confidence / provenance, shown nowhere
  last_checked: 'YYYY-MM-DD'

`filed_assumed` is the default once the federal window closes: every state is
presumed to have filed, because the statute gives them no reason not to, but
absent a public confirmation the site should not claim more than that.

Verification note (2026-09-18): WebFetch is blocked in the build sandbox, so the
two confirmed entries below were cross-referenced across multiple independent
WebSearch result snippets rather than by loading the source pages. Same bar as
the case-studies library. Re-verify from a local CLI where fetch works.
"""

import datetime as _dt
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "state_metadata.yaml"

CHECKED = "2026-09-18"

DEFAULT = {
    "status": "unknown",
    "submitted_date": None,
    "tract_count": None,
    "off_list_count": None,
    "list_published_url": None,
    "source_url": None,
    "source_note": None,
    "last_checked": CHECKED,
}

# Only states with a public, corroborated account of their federal filing.
CONFIRMED = {
    "arizona": {
        "status": "filed_confirmed",
        "submitted_date": "2026-07-09",
        "tract_count": 125,
        "off_list_count": 3,
        "source_url": "https://opportunityzones.com/2026/08/oz-live-392/",
        "source_note": (
            "125 tracts is exactly Arizona's 25% cap on 500 eligible tracts, which "
            "corroborates the reported figure. Off-list count is secondary-sourced; "
            "confirm against Treasury certification."
        ),
    },
    "texas": {
        "status": "filed_confirmed",
        "submitted_date": "2026-09-04",
        "tract_count": 605,
        "source_url": "https://www.jw.com/news/insights-texas-qualified-opportunity-zone-tracts/",
        "source_note": (
            "Governor Abbott finalized nominations 2026-09-04. Reported by Jackson Walker "
            "and corroborated by City of Arlington's announcement of five nominated tracts."
        ),
    },
}


def main() -> int:
    data = yaml.safe_load(META.read_text())
    if not isinstance(data, dict):
        print("state_metadata.yaml did not parse to a mapping", file=sys.stderr)
        return 1

    added = updated = 0
    for slug, state in data.items():
        block = dict(DEFAULT)
        # Preserve anything already recorded so a re-run never loses hand edits.
        existing = state.get("nomination")
        if isinstance(existing, dict):
            block.update({k: v for k, v in existing.items() if k in block})
        else:
            added += 1

        if slug in CONFIRMED:
            block.update(CONFIRMED[slug])
            block["last_checked"] = CHECKED
            updated += 1

        state["nomination"] = block

    META.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, width=88, allow_unicode=True)
    )
    print(f"nomination block: added to {added} states, populated for {updated}")
    print(f"as of {_dt.date.today().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
