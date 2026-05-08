# OZ 2.0 State-Specific Resource — Project Spec

**Last updated**: 2026-05-05
**Status**: Locked for Phase 1 MVP

## Mission

Help local planners, EDD staff, and community development directors in
every U.S. state figure out which OZ 2.0 tracts they have, who to convene
to advocate for nomination, and how OZ stacks with other federal rural
development capital. Ship before the nomination window opens July 1, 2026.

## Audiences

**Primary (MVP)**: Local official / planner trying to figure out which
tracts in their jurisdiction are eligible and how to organize for
nomination.

**Phase 2**: Impact investor scouting tracts likely to be designated;
community organization or matchmaker brokering between local government,
philanthropy, and project sponsors.

Audience selector lives on the home page; Phase 2 audiences see "Coming
soon" stubs at MVP launch.

## Scope — in

- 50 states + DC = 51 spotlight pages on launch
- Universal page template; depth varies by state activity tier
- Native/tribal callout on every state with federally recognized tribes
- Personalized "What to do" panel for local planners (rural toggle default)
- Cross-cutting pages: how-to-advocate, off-list nominations (Section
  5.04), capital stack, OZ 1.0 retrospective
- Bibliography (references.md)

## Scope — out

- Maps. Embed EIG ArcGIS dashboard or link IRS appendix; do not reproduce.
- 5 territories (PR, USVI, Guam, AS, MNP) — Phase 2 due to OZ 2.0 mechanics
  differing meaningfully (PR especially: 2027 expiration, blanket coverage
  gone).
- Status tracker — cite Frances Kern Mennone's PDF.
- Investor/fund discovery tooling — point at Novogradac's funds list.
- LULU/critical framing — lives in companion lab essay.

## Editorial stance

Neutral, evidence-based, useful to anyone advocating for tract nomination
regardless of political stance. Cites the academic OZ 1.0 evidence base
(Chen-Glaeser-Wessel, Arefeva et al., Freedman et al.) alongside government
assessments (CEA, HUD PD&R) and policy critique (NCRC, NLIHC). Voice is
factual and direct.

## Site architecture
/                                  → home, audience selector, national overview
/states/{state}/                   → state spotlight (51 pages)
/how-to-advocate/                  → coalition playbook
/off-list-nominations/             → Section 5.04 explainer
/capital-stack/                    → federal program stacking
/oz1-retrospective/                → evidence summary
/references/                       → bibliography
/methodology/                      → data sources, decisions, last-updated
/about/                            → project mission, maintainer

## State page template (universal)

Every state page renders these sections in order. Depth varies; structure
does not.

1. **Headline numbers**
   - Total eligible tracts | Max designations | Rural share | Days to
     nomination window
2. **Status banner**
   - Public process / Contact only / No public process yet
   - Last checked: {date}
3. **View toggle**
   - All eligible | Rural only | Non-rural only
   - Re-renders headline stats and contact section
4. **Eligible tracts**
   - Embed EIG ArcGIS dashboard scoped to state
   - Link to IRS appendix filtered to state
   - Top 10 counties by eligible count, with rural and non-rural splits
5. **The selection process**
   - Narrative: who runs it, what's published, what's expected
   - Scoring rubric if available
6. **Key dates**
   - State deadline, federal deadline, designation effective date
7. **How to influence the nomination**
   - Coalition checklist (rural-mode shows different partner list)
   - Pulls from `/how-to-advocate/` shared content
8. **Who to contact**
   - State lead agency: name, contact, URL
   - Regional EDDs / COGs by county
   - State CDFI list (filtered from CDFI Fund certified list)
   - State USDA RD office
   - State LISC / Rural LISC presence
   - Tribal economic development contacts (where applicable)
9. **Native / tribal callout** (where federally recognized tribes exist)
   - Federally recognized tribes in state
   - Tribal consultation framework (formal / informal / none)
   - Tribal CDFIs (Native CDFI Network filter)
   - Cross-program stacking (HUBZones, BIA NABDI grants, NAHASDA)
10. **For investors (post-designation)**
    - Brief; points to Novogradac's funds list
11. **Sources & last updated**
    - Citation list, last-checked date for each

## Personalization — "What to do" panel

Renders dynamically based on (state, county, tract type filter). Template
has slots for state-specific values: lead agency, contact, deadlines,
scoring rubric link, regional EDD/COG, rural partners, tribal applicability.
The static prose is shared across states; the variables are per-state and
per-county.

Defined in `pages/_what-to-do-template.md` with Jinja2-style placeholders.

## Data architecture

**Ground truth**:
- `data/eligible_tracts.parquet` — IRS Rev. Proc. 2026-14 appendix.
  Columns: GEOID, state_fips, county_fips, is_rural, mfi, poverty_rate,
  population.

**Overlays**:
- `data/dci.parquet` — EIG Distressed Communities Index, joined on GEOID
  via HUD ZIP-to-tract crosswalk. Columns: geoid, zip_code, dci_score,
  dci_quintile (1=most distressed, 5=least). Script: scripts/ingest_dci.py.
- `data/persistent_poverty.parquet` — USDA ERS County Typology Codes
  persistent-poverty flag, joined on county_fips. Columns: county_fips,
  county_name, state_fips, is_persistent_poverty. Script:
  scripts/ingest_persistent_poverty.py.
- `data/tribal_overlap.parquet` — Census ACS AIAN population share per
  eligible tract, cross-referenced against TIGER/Line federally recognized
  tribal statistical areas. Columns: geoid, aian_pop, aian_pct,
  tribal_area_name (null if no overlap), is_tribal_overlap. Script:
  scripts/ingest_tribal_overlap.py.
- `data/anchor_proximity.parquet` — NOT YET IMPLEMENTED. Spec below.

**Anchor proximity overlay spec** (Phase 2):

Goal: flag eligible tracts that contain or are adjacent to a major anchor
institution (hospital or college/university), as a forward-looking
investment-readiness signal complementary to the distress-focused DCI.

Data sources:
- Hospitals: HIFLD Open Data "Hospitals" feature layer
  (https://hifld-geoplatform.opendata.arcgis.com/datasets/hospitals)
  — nationwide, geocoded, includes bed count, trauma level, status.
  Filter: STATUS == "OPEN".
- Colleges/universities: IPEDS Institutional Characteristics
  (https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx)
  — IPEDS HD file has lat/lon + enrollment for every Title IV institution.
  Filter: ICLEVEL in (1,2) [4-year and 2-year], CLOSEDDATE == -2 (open).

Join method:
Use tract polygon boundaries (not centroids) for distance measurement.
Centroid-based distance is misleading for rural tracts, which can exceed
400 sq mi — the centroid may be miles from any settlement, and an anchor
inside the tract near its edge would be missed.

1. Download Census TIGER/Line tract polygons (not centroids).
2. Use geopandas sjoin_nearest against anchor point layers to get the
   distance from the nearest edge of each tract polygon to the nearest
   anchor point. In geopandas: sjoin_nearest(tracts, anchors,
   how="left", distance_col="dist_m").
3. Apply rural-aware thresholds using is_rural from eligible_tracts.parquet:
   - Urban tracts (is_rural=False): anchor_within_threshold = dist <= 1 mile
   - Rural tracts (is_rural=True):  anchor_within_threshold = dist <= 25 miles
   The 25-mile rural threshold reflects that a county-seat hospital 20 miles
   from a rural tract is still a real demand generator for that community.
4. Record the nearest anchor name, type, and actual distance in miles for
   both hospital and college separately.

Output schema (anchor_proximity.parquet):
  geoid                    str    11-digit tract GEOID
  is_rural                 bool   from eligible_tracts (join key for threshold)
  nearest_hospital_name    str    null if none found
  nearest_hospital_dist_mi float  distance from tract polygon edge, miles
  nearest_college_name     str    null if none found
  nearest_college_dist_mi  float  distance from tract polygon edge, miles
  anchor_within_threshold  bool   True if either anchor within rural/urban threshold
  threshold_miles_used     float  1.0 for urban, 25.0 for rural

Limitations:
- Proximity ≠ investment pipeline. A tract adjacent to a hospital is not
  automatically investment-ready; it means demand infrastructure exists.
- Does not capture private-sector anchors (manufacturing plants, retail
  corridors, port terminals). Those are not in any standardized open dataset.
- Comprehensive plan mentions and developer pipeline remain unresolvable
  from public data alone — the anchor flag is a proxy, not a substitute.
- Philadelphia Fed Anchor Economy Dashboard (BLS region level) is NOT
  suitable for tract-level joins; use HIFLD/IPEDS instead.

Script: scripts/ingest_anchor_proximity.py (not yet written).

**State metadata**: `state_metadata.yaml`. One root key per state. Per-state
fields:
  - `lead_agency`: name, url, contact email/phone
  - `status_tier`: public_process | contact_only | no_public_process
  - `last_checked`: date
  - `process`: narrative (Markdown)
  - `scoring_rubric_url`: optional
  - `state_deadline`: date | null
  - `application_portal_url`: optional
  - `tribal_consultation`: framework type, citation
  - `regional_edds`: list of {name, url, counties_served}
  - `rural_partners`: USDA RD state office, RCAP regional, Rural LISC
  - `state_cdfi_count`: integer (from CDFI Fund filter)
  - `notes`: free text

## Phasing

- **Phase 1 MVP (4–6 weeks, target mid-June 2026)**
  - All 50 states + DC pages, universal template
  - All cross-cutting pages
  - Bibliography committed
  - Three role skills wired into review workflow
- **Phase 2 (June–July 2026)**
  - 5 territories
  - State status weekly sync wired up
  - Phase 2 audience flows (investor, community matchmaker)
  - Lab essay published separately (LULU framing)
- **Phase 3 (post-designation, late 2026)**
  - Pivot to "now what" — actual designations, investor-facing content

## Open questions

- Static site framework: Hugo, Astro, or Eleventy? Default: Astro for
  vargo.city consistency. Decide first session.
- Rural-toggle implementation: client-side JS filter, or pre-rendered three
  versions per state? Lean pre-rendered for simplicity and SEO.
- State agency landing page extraction: manual review or LLM-assisted?
  Default: LLM-assisted via state_extractor.py with human review pass.
- County-level partner directory: where does this data come from for the 41
  states beyond the Western 9 prototype set?