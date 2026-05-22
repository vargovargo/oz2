# OZ 2.0 State Maps — Completed

**Merged to main**: 2026-05-22

---

## What was done (remote cloud session, 2026-05-21)

- `src/components/TractMap.astro` — MapLibre GL v5 interactive map component replacing the EIG ArcGIS iframe on every state page. Features: DCI quintile choropleth, 6-filter panel (rural/CRA/DCI/USDA/NMTC/tribal), rich click popup, graceful EIG fallback.
- `src/pages/states/[state].astro` — imports TractMap; iframe block replaced; eigMapUrl preserved for fallback and "View on EIG map" link.
- `src/layouts/Layout.astro` — added `<slot name="head" />` for future page-specific head injection.
- `maplibre-gl@5` installed to package.json/node_modules.
- `scripts/build_state_geo.py` — Python pipeline that builds the per-state GeoJSON files the map fetches.
- `public/geo/` — directory exists with `.gitkeep`; **GeoJSON files not yet generated** (needs geopandas + network).

The Astro build and TypeScript check pass. The map shows a loading spinner then gracefully falls back to the EIG iframe when `/geo/{fips}.geojson` is absent — so the site is fully functional right now, just without the custom maps until you run the build script.

---

## What to do on the home machine

### 1. Pull the branch

```bash
git pull origin claude/state-maps-tract-filtering-NnJut
npm install   # picks up maplibre-gl@5
```

### 2. Install Python geospatial dependencies

```bash
pip install geopandas shapely fiona pyproj pandas pyarrow

# If geopandas fails, install GDAL first:
#   macOS:   brew install gdal
#   Ubuntu:  sudo apt-get install gdal-bin libgdal-dev python3-gdal
#   Conda:   conda install geopandas  (easiest — handles GDAL automatically)
```

Verify: `python3 -c "import geopandas; print(geopandas.__version__)"` should print a version.

### 3. Run the build script

```bash
python3 scripts/build_state_geo.py
```

- Downloads Census TIGER 2022 tract + places shapefiles per state to `data/raw/tiger/` (cached — re-runs skip downloads)
- Joins all overlay parquets (dci, cra_lmi, persistent_poverty, tribal_overlap, cdfi_nmtc)
- Spatial-joins tract centroids with Census Places for municipality names
- Outputs `public/geo/{state_fips}.geojson` — one per state/territory (56 total)
- **Expected time**: 15–40 min first run (downloading ~112 ZIP files); subsequent runs ~2 min (cache hits)
- **Expected output**: 56 files, 100–600 KB each; CA/TX/FL may reach 1–2 MB

Flags:
```bash
python3 scripts/build_state_geo.py --state 01             # Alabama only (fast test)
python3 scripts/build_state_geo.py --skip-existing        # resume interrupted run
```

### 4. Verify output

```bash
ls -lh public/geo/ | sort -k5 -rh | head -10             # largest files
python3 -c "
import json
d = json.load(open('public/geo/01.geojson'))
print(len(d['features']), 'features')
print(d['features'][0]['properties'])
"
```

Expected properties on each feature:
`geoid, county_name, place_name, state_name, state_abbr, is_rural, dci_score, dci_quintile, is_cra_lmi, income_level, is_persistent_poverty, is_tribal_overlap, tribal_area_name, aian_pct, has_nmtc, nmtc_projects, nmtc_total_usd`

### 5. Test the map locally

```bash
npm run dev
# Open http://localhost:4321/states/alabama
# Open http://localhost:4321/states/california   (stress test: ~2,469 tracts)
```

Verify:
- Map renders with colored tracts (DCI quintile choropleth)
- Filter checkboxes dim non-matching tracts
- Clicking a tract opens a detailed popup with all overlay fields
- Popup shows county + municipality name where available
- Non-rural tracts: QROF section absent from popup
- States without GeoJSON (e.g., territories): EIG iframe fallback appears

### 6. Commit and push

```bash
git add public/geo/ package.json package-lock.json
git commit -m "Add per-state OZ tract GeoJSON and MapLibre GL map component"
git push -u origin claude/state-maps-tract-filtering-NnJut
```

---

## Key file locations

| File | Purpose |
|---|---|
| `scripts/build_state_geo.py` | Data pipeline — run this first |
| `src/components/TractMap.astro` | Map component (MapLibre GL, filters, popup) |
| `src/pages/states/[state].astro` | State page — uses TractMap |
| `public/geo/{fips}.geojson` | Generated GeoJSON (56 files, not committed yet) |
| `data/raw/tiger/` | TIGER download cache (gitignored) |

---

## Known caveats

- **Tribal data**: `tribal_overlap.parquet` was built when the Census ACS API was unreachable — `is_tribal_overlap` is False for all tracts. The "Tribal overlap" filter checkbox exists but has no effect until `scripts/ingest_tribal_overlap.py` is re-run with API access.
- **DCI gaps**: ~900 tracts (~3.6%) have no DCI data (rural tracts with PO Box–only ZIPs). These render in gray and show "data not available" in the popup.
- **Territories**: AS (60), GU (66), CNMI (69), USVI (78) use full TIGER/Line files (simplified with shapely). If their TIGER downloads fail, those 4 FIPS codes will be skipped; state pages fall back to EIG iframe.
- **data/raw/tiger/**: not gitignored by default — you may want to add it if files are large.

---

## Next priorities after maps

1. Re-run `ingest_tribal_overlap.py` with Census API access → rebuild tribal GeoJSON properties
2. Merge branch to main → verify Vercel deploy
3. oz1-retrospective and off-list-nominations pages — still stubs
