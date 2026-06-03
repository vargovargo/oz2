# OZ 2.0 Handoff — New Resources Integration

**Branch**: `claude/oz-new-resources-integration-dJ8aU`
**Session date**: 2026-06-03
**Status**: Frontend + pipeline wired; Urban Institute data ingestion needs to run locally.

---

## What was done (remote cloud session)

Two new resources integrated:

### 1. Accelerator for America OZ Designation Toolkit (complete — no local action needed)

Links and callouts added to:
- `src/pages/how-to-advocate.astro` — bordered callout in "Building the case" section; sentence at end of "Scoring criteria"; footer reference link
- `src/pages/states/[state].astro` — toolkit link in all three "How to influence" branches (open window, closed window, no-process fallback)
- `references.md` — new Section 4 entry (description is a placeholder — update after reading the PDF)

**One remaining task**: read the PDF and update the placeholder descriptions. See [AFA content update](#afa-content-update) below.

### 2. Urban Institute Investability Data (pipeline wired; data ingestion deferred)

Frontend changes already live:
- **Map default**: investability choropleth is now the default color scheme on all state maps (sequential blue Q1→Q5, grey for unscored); radio toggle switches to DCI Distress
- **Filter**: "High investability (UI Q1–Q2)" checkbox added to filter panel
- **Popup**: "Predicted Investability" section in tract detail popup (shows "not scored" gracefully until data is loaded)
- **State data card**: `ui_invest_q1_tracts` card in the "Data context" section (hidden until data is loaded)
- **CSV export**: `ui_invest_score` and `ui_invest_quintile` columns added

Pipeline changes already in the scripts — they just need to run with the data file present.

---

## Local action required

### Step 1: Pull the branch

```bash
cd /Users/lauren/oz2
git fetch origin
git checkout claude/oz-new-resources-integration-dJ8aU
npm install
```

### Step 2: Run the Urban Institute ingest script

Your CSV is already in the right place at `data/raw/investability_urban.csv`. The script auto-detects it:

```bash
python3 scripts/ingest_urban_investability.py
```

**Watch the output carefully.** It will print:
- The column it detected as the GEOID (verify it matches the 11-digit Census tract ID)
- The column it detected as the investability score
- Whether a quintile column was found or auto-computed
- Coverage (how many of the 25,332 eligible tracts are scored)
- Quintile distribution

**Critical check — quintile direction**: If the script auto-computes quintiles (no quintile column in the CSV), it assigns Q1 to the *highest* scores (most investable). Confirm this matches Urban Institute's documentation. If their Q1 is the *lowest* scores, open `scripts/ingest_urban_investability.py` and change the labels on line ~112 from `[5, 4, 3, 2, 1]` to `[1, 2, 3, 4, 5]`, then re-run.

If the GEOID column or score column isn't auto-detected, the script will print all available column names and exit. Add the actual column name to the appropriate `*_CANDIDATES` list at the top of the script.

### Step 3: Rebuild all state GeoJSON files

```bash
python3 scripts/build_state_geo.py
```

- Downloads Census TIGER shapefiles per state to `data/raw/tiger/` (cached — re-runs skip downloads)
- Merges all overlays including the new `urban_investability.parquet`
- Outputs `public/geo/{fips}.geojson` — 56 files
- **First run**: ~15–40 min (downloading shapefiles). Subsequent runs: ~2 min (cache hits)
- Use `--state 39` (Ohio) for a fast single-state test first

```bash
# Fast test — Ohio only
python3 scripts/build_state_geo.py --state 39

# Then full run
python3 scripts/build_state_geo.py
```

Verify the new columns landed:
```bash
python3 -c "
import json
d = json.load(open('public/geo/39.geojson'))
p = d['features'][0]['properties']
print('ui_invest_score:', p.get('ui_invest_score'))
print('ui_invest_quintile:', p.get('ui_invest_quintile'))
"
```

### Step 4: Update state_metadata.yaml with per-state counts

```bash
python3 scripts/patch_overlay_stats.py
```

This reads `urban_investability.parquet`, counts Q1 tracts per state, and patches `ui_invest_q1_tracts` into every state block in `state_metadata.yaml`. The count will appear on the state data context card.

### Step 5: Test locally

```bash
npm run dev
```

Open `http://localhost:4321/states/ohio` (or any state). Verify:
- [ ] Map defaults to Investability choropleth (blue palette)
- [ ] Toggle to DCI Distress works and legend swaps
- [ ] Clicking a scored tract shows investability score + quintile in popup
- [ ] Clicking an unscored tract shows "not scored" message in grey
- [ ] "High investability (UI Q1–Q2)" filter narrows map correctly
- [ ] State data context card shows `ui_invest_q1_tracts` count
- [ ] `how-to-advocate` page shows Accelerator for America callout box
- [ ] Any state page shows toolkit link in "How to influence the nomination"

### Step 6: Commit and push

```bash
git add data/urban_investability.parquet public/geo/ state_metadata.yaml
git commit -m "Add Urban Institute investability data — ingest, GeoJSON rebuild, state stats"
git push
```

---

## AFA content update

The Accelerator for America references currently use placeholder descriptions. Once you've read the PDF (`data/raw/` — or wherever you have it), update two places:

**`src/pages/how-to-advocate.astro`** (~line 160) — the `<p>` inside the callout box:
```
A step-by-step guide for local planners on how to prioritize and document tracts for
nomination, including frameworks for community need documentation and investment readiness.
```
Replace with 1–2 sentences describing what the toolkit actually covers (chapters, key frameworks, what makes it distinctive from NADO/Sorenson guides).

**`references.md`** — Section 4, Accelerator for America entry:
```
[Description to be updated after full PDF review.]
```
Replace with a proper annotation (1–2 sentences on scope, audience, key content).

---

## Key files changed in this session

| File | What changed |
|---|---|
| `src/components/TractMap.astro` | Investability choropleth as default; radio toggle; filter checkbox; popup section; CSV export columns |
| `src/pages/states/[state].astro` | Investability data card; toolkit links in all "How to influence" branches |
| `src/pages/how-to-advocate.astro` | Accelerator for America callout + scoring criteria sentence + footer link |
| `src/lib/states.ts` | Added `ui_invest_q1_tracts: number \| null` to StateMetadata |
| `state_metadata.yaml` | `ui_invest_q1_tracts: null` stubs in all 51 state blocks (values populated by Step 4) |
| `scripts/ingest_urban_investability.py` | **New** — reads CSV/xlsx, outputs parquet |
| `scripts/build_state_geo.py` | Optional Urban Institute merge; `ui_invest_score/quintile` in output columns |
| `scripts/patch_overlay_stats.py` | `ui_invest_q1_tracts` stats + YAML stub insertion |
| `references.md` | Urban Institute entry expanded; Accelerator for America entry added |

---

## Caveats

- **Quintile direction**: must be verified against Urban Institute's methodology documentation before the map goes live. The legend says Q1 = most investable — confirm that's correct.
- **Coverage**: The UI dataset scores tracts that had OZ 1.0 investment activity. Expect partial coverage (likely 40–70% of 25,332 tracts). Unscored tracts render grey on the map with an explanatory note.
- **Accelerator PDF**: content descriptions are placeholders. Don't push to main without updating them.
- **GeoJSON files** (`public/geo/`): not committed to git (gitignored). Vercel needs them to be built during deploy, or they need to be committed. Check how the existing GeoJSON files get onto Vercel — if they're committed, commit the rebuilt ones too; if they're built in CI, the CI environment needs the parquet files.
