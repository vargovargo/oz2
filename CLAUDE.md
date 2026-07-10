# Claude Code Project Instructions — OZ 2.0 State-Specific Resource


> Pipeline coordination for this project lives in ./HARNESS.md
> (agents, handoffs, session state). This file covers project specifics.

You are working on a state-by-state Opportunity Zone 2.0 resource for local
planners and nonprofits. The full spec is in SPEC.md; the bibliography is
in references.md. Read both before substantive edits.

## Where things stand (as of 2026-07-10)

**Completed in the 2026-07-10 session (branch: claude/site-fact-check-links-4stwsu):**

*Full-site fact check (links + claims), post-July-1 refresh.* WebFetch/curl blocked in this
sandbox (proxy 403s all external hosts); claims verified via WebSearch, links via built-HTML
crawl + search spot-checks. Findings and fixes:
- Federal window close date corrected to **September 28, 2026** (was "September 29" on
  off-list-nominations and how-to-advocate; oz1-retrospective had it too). Confirmed via
  Treasury press release sb0550 and CRS R48952 (90 days beginning July 1).
- Sitewide "window opens July 1" tense fixed now that the window is open: index hero, footer
  banner (now "open through September 28, 2026"), about, how-to-advocate, and six YAML
  process texts (ID, DE-notes, IL, IA, OK, TN).
- `[state].astro` 4th tile now shows "Days left in federal window" (counts down to 9/28,
  then "Closed") instead of days-to-July-1, which had gone negative.
- how-to-advocate tier counts updated 22/28 → 29/21 (mid-June review), "verified May 12" →
  June 16.
- **Massachusetts `state_deadline` nulled** — it held the *federal* 9/28 deadline, which the
  UI presented as an open state input deadline; secondary reporting suggests the Community
  Feedback Form window was ~June 30 (unconfirmed by mass.gov, so hedged in process text
  rather than marked closed).
- Open state deadlines re-verified 2026-07-10: OH 7/10 (4 p.m., confirmed), GA 7/15, AL 7/31
  (noon), WI 7/31, MD 8/7 — all confirmed via agency pages/search. NY re-checked: still no
  public process (contact_only stands). `last_checked` bumped to 2026-07-10 for those 7 states.
- References page **anchor-link bug fixed**: `linkIcon.replace('SLUG', '#' + slug)` produced
  `href="##..."` — all 15 section anchors were broken. Also added missing `public/favicon.svg`
  (was 404 on every page).
- capital-stack: deferral wording made precise (OZ 2.0 rolling deferral — earlier of sale or
  5th anniversary, 10% step-up standard / 30% QROF; was "Treasury-specified deadline").
  QROF 30%/50% mechanics, LIC thresholds (70% MFI or 20% poverty + 125% cap), and per-state
  counts (NY 1,702/426, OH 258, MD 113, MA 103/410) all externally confirmed correct.
- oz1-retrospective: K&W median investor AGI aligned to $741K (body said ~$730K, footnote
  $741K). Data cross-checks all pass: 25,332/8,334 (parquet), 18,968 = 17,378 T1 + 1,590 T2
  CRA (74.9%), 22 case studies, YAML sums 24,547/8,018 (territories excluded — documented on
  methodology page).
- Not done (needs local CLI with working fetch): HTTP status check of all 241 external URLs.
  Spot-checks (EIG guidance/resources, Urban data catalog, AFA toolkit, 6 state portals,
  IRS drop URLs) all resolved live via search.

*Deep-dive on capital-stack CRA section (same session, follow-up):*
- **CRA regulatory status corrected (again)**: the June 16 SME pass overshot — the 2023 CRA
  Final Rule was NOT "rescinded in 2025." Verified record: enjoined N.D. Tex. March 29, 2024
  (never took effect); agencies *proposed* rescission + 1995-framework reinstatement July 16,
  2025 (comments closed 8/18/25); no finalized rescission found as of 2026-07-10. Wording on
  capital-stack, references.md §14, and the practitioner brief now all say "enjoined 2024,
  rescission proposed 2025, pre-2023 framework applies in practice" — they previously
  contradicted each other ("rescinded" vs "under legal challenge").
- **`ffiec.cfpb.gov/tools/tract-search` does not exist** (the CFPB-hosted FFIEC platform has
  HMDA tools only — rate-spread, check-digit, LAR formatting). It was cited in 5 files incl.
  references.md with a last_checked date. Replaced with the real FFIEC Geocoding/Mapping
  System (ffiec.gov/geocode/) + D/U list (ffiec.gov/data/cra/distressed) in capital-stack,
  [state].astro, references.md, and the brief (handoffs/ left as historical record).
- FFIEC legacy URLs updated to the redesigned site: censusapp.htm → ffiec.gov/data/census;
  cra/craflatfiles.htm → ffiec.gov/data/census/flat-files.
- OCC "OZ resource directory" URL unverifiable post-reorg → swapped to the confirmed-live OCC
  Community Developments OZ fact sheet.
- [state].astro CRA footnote said "Flat File 2026" → corrected to 2025 (matches ingest).
- Track 2 definition on capital-stack now includes the net-migration-loss (≥5%) alternative.
- Verified clean: Track 1/Track 2 definitions vs FFIEC, 74.9%/17,378/1,590 vs data, rural
  69.7% / non-rural 77.4% / 2,525 no-CRA rural / 5,809 sweet-spot (all reproduce from
  parquet), state-page cities/ZIP claim (cra_lmi_places.json renders as described), EQ2 and
  CD-loan mechanics, CRA enacted 1977.

## Where things stood (as of 2026-06-16)

**Data bootstrap done:**
- `data/eligible_tracts.parquet` — 25,332 eligible tracts from IRS Rev. Proc. 2026-14
- `data/state_summaries.csv` — per-state totals, rural splits, top-10 counties
- `scripts/ingest_irs_appendix.py` — fetches the IRS appendix XLSX, re-runnable

**State metadata done:**
- `state_metadata.yaml` — all 51 states populated; 29 public_process, 21 contact_only, 1 no_public_process (DC)
  as of the 2026-06-16 public-process review (see session note below)
- `scripts/generate_state_metadata.py` — regenerates scaffold from CSV (re-runnable)
- `scripts/patch_state_metadata.py` — applies researched status/agency data (re-runnable, idempotent)
- `src/lib/states.ts` — typed loader; `getAllStates()`, `getState(slug)`, `getStateSlugs()`

**Site live:**
- Deployed at https://oz2-two.vercel.app (GitHub: vargovargo/oz2, branch: main)
- Anchor links, EIG audit, skills review, template fixes — merged (PRs #4–6)
- All 51 state pages rendering from YAML — correct tier badges, lead agency contacts, deadlines, county tables
- "Input closed" logic: states with past deadlines show grey badge + prose note
- References page: styled with entry separators, clickable URLs, last_checked badges, section anchor links
- references.md section 13 added — per-state agency pages (49 entries, last_checked 2026-05-05)
- Urban Institute investability layer + AFA toolkit resources — merged (PR #14, 2026-06-02)
- OZ 1.0 case studies library at `/case-studies` — 12 verified projects, nav-linked (branch
  `claude/oz-case-studies-library-rutjnp`, not yet merged — see 2026-06-16 session below)

**Completed in the 2026-06-16 session (branch: claude/oz-case-studies-library-rutjnp, not yet merged):**

*OZ 1.0 case studies library:* New `/case-studies` page, nav-linked (desktop + mobile) next
to OZ 1.0 Retrospective. Distinct from `oz1-retrospective.astro`, which stays aggregate-stats-only.
- `data/case_studies.yaml` — 12 hand-curated entries (id, title, state/state_slug, location,
  sector_tags, size_tag, investment_amount_usd, year, rural, summary, source_name, source_url,
  source_type, last_checked). Snowball-sampled from EIG's "Investments and Initiatives From
  Across the Country" and NCSHA's OZ affordable-housing case study series, cross-referenced
  against Novogradac's fund list (references.md section 6) for project-level detail.
  Geographic spread: MD, FL, OH, CA, CO (×2), MN, PA, TX, ME, OR, GA. All 8 sector tags
  represented (affordable_housing, small_business, broadband, healthcare, manufacturing,
  mixed_use, anchor_institution, rural_development).
- `src/lib/caseStudies.ts` — typed YAML loader mirroring `src/lib/states.ts`
  (`getAllCaseStudies()`, `getAllSectorTags()`).
- `src/pages/case-studies.astro` — card grid (same pattern as `states/all.astro`) with
  client-side tag-chip filtering (vanilla JS, `data-tags` + `Set`, OR logic across selected
  tags), state cross-links where `state_slug` is set, "Full details →" external link per card,
  `verified {last_checked}` badge.
- `references.md` section 15 — documents the EIG/NCSHA seed sources and sourcing methodology.

**Handoff note — finish this from local CLI, not the remote sandbox:**
The remote sandbox used for this session has WebFetch blocked (403 for every URL tested,
including trivial control URLs) — all 12 entries were verified by cross-referencing multiple
WebSearch result snippets per candidate instead of loading source pages directly. That's slower
and lower-confidence than a direct fetch. Local Claude Code sessions don't have this restriction.

User asked about adding ~10 more case studies; agreed sourcing isn't the bottleneck (EIG's
"Investments and Initiatives" list and the Novogradac fund directory both have more named
projects than were used), but verification is faster locally with working WebFetch. Pick up
by reading `data/case_studies.yaml` for the schema/convention, then continue snowball-sampling
from the same two seed sources (EIG, Novogradac) — the well-documented, NCSHA-profiled examples
are mostly used up, so expect to lean more on aggregator writeups and local press for the next
batch, and watch for repeat states since the easy geographic diversity wins are already claimed.
Target was originally 12-15 total; "10 more" would bring it to ~22, comfortably past that, which
is fine per the user's "doesn't have to be extensive" framing — just keep verifying each one
before adding it, same bar as the first batch.

**Completed in the 2026-06-16 session, part 2 (branch: claude/oz-case-studies-library-rutjnp):**

*Public-process review across all 51 states + DC:* User asked to review/update every state's
nomination-process status, prioritizing the 28 states tagged `contact_only`. Dispatched 6
parallel research agents (WebSearch only — WebFetch stayed blocked/403 in this sandbox) scoped
to ~8-9 states each, each reporting recommended tier, new process info, contact changes,
sourcing, and confidence level without editing files directly; findings were synthesized and
applied centrally in `state_metadata.yaml`, then verified with `npm run build`.

Tier changes (`contact_only` → `public_process`, 7 states): Alabama (ADECA portal live,
deadline noon CDT 2026-07-31), Georgia (live portal at gaoznominations.powerappsportals.com,
deadline 2026-07-15), Massachusetts (Community Feedback Form live, Treasury deadline
2026-09-28), Pennsylvania (DCED webinar + live Microsoft Forms portal, deadline "early June
2026" — imprecise, `state_deadline` left null), Wisconsin (WEDC/WHEDA joint window
2026-06-12 to 2026-07-31), Minnesota (DEED/MN Housing input request, deadline 2026-06-30),
Idaho confirmed at the prior `public_process` tier with a newly reported deadline added
(4:00 p.m. MT, 2026-06-30, restricted to cities/counties/tribes — flagged for direct
confirmation).

Deadline corrections on existing `public_process` states: North Carolina (June 7 → June 21,
per a June 4 NC Commerce extension announcement), South Carolina (June 1 → June 15), Maryland
(added DocuSign portal detail, county packets, `state_deadline` 2026-08-07), Arizona (confirmed
4:00 p.m. MT 2026-06-30, replacing "not yet set" language), Ohio (portal relaunched ~June 10,
new deadline ~2026-07-10, superseding the earlier unconfirmed ~May 31 estimate), Oklahoma
(added deadline 2026-06-19, hedged pending direct confirmation), Maine (added "input window
has closed" framing matching Virginia's established convention).

`contact_only` states enriched (process text updated, tier unchanged — info found didn't rise
to a full public nomination process): California (GO-Biz REDI OZ 2.0 office hours through
2026-06-30), Indiana (LISC/Fifth Third-backed portal "coming weeks," Bloomington example),
Louisiana (parish-level intake, Bossier Parish Police Jury example), Michigan (MEDC summer 2026
regional roundtables), Utah (Go Utah survey, named contact, 37/147 cap), Alaska (closed
April 16-30 public-notice period), Iowa (consolidated to opportunityiowa.gov domain), Rhode
Island (unconfirmed ~June 23 internal target noted but not promoted to `public_process` —
primary source unconfirmed).

Deliberately left unchanged (evidence too weak or conflicting to act on): Florida's "closed
before May 2026" framing, Washington's deadline (site says May 28; an agent surfaced conflicting
April 1–May 1 sourcing that couldn't be reconciled), Vermont's possible URL drift (low
confidence), New Jersey and Connecticut (their existing entries already covered the agents'
findings — no edit needed).

All 51 `last_checked` dates bumped to `2026-06-16`. Validated with `python3 -c "import yaml;
yaml.safe_load(...)"` and `npm run build` (61 pages, no errors) before commit.

**Completed in the 2026-06-12 session (PRs #17, #18):**

*CRA column verification:* Confirmed FFIEC data dictionary uses 1-based index — "index 15"
= `df[14]` (income indicator), "index 22" = `df[21]` (D/U flag) in pandas. The two flags
are mutually exclusive in the FFIEC file (no tract has both LMI and D/U set). OR logic is
correct and confirmed: 18,968 tracts (74.9%).

*Practitioner brief updated (PR #17):* `docs/cra-oz-overlap-brief.md` rewritten from
single-track 68.6% to two-track 74.9%, FFIEC 2023 → 2025 throughout. Full 56-row state
table regenerated from parquet. Rural figures corrected (69.7% rural, 77.4% non-rural;
rural-without-CRA drops from 4,110 to 2,525 with Track 2). Track 2 practitioner guidance
added. WV narrative corrected (44% → 65.2%).

*Data artifacts rebuilt (PR #18):* All three outputs replaced with two-track data.
  - `data/oz_cra_lmi_tracts.csv` — 18,968 rows (was 17,379 Track-1-only); adds `cra_track`
    (1 or 2) and `cra_label` columns; `scripts/generate_oz_cra_lmi_csv.py` is the
    reproducible generation script.
  - `data/arizona_oz2_nomination_report.pdf` — rebuilt via self-contained
    `scripts/build_az_report.py` (no `/tmp` dependency). Slate changes: Maricopa 56 (+5),
    La Paz 3 (+1 Track 2 D/U tract), Pima 25 (−3), Yavapai 1 (−1), Yuma 1 (−2). Apache,
    Santa Cruz, Navajo county narratives updated for Track 2 CRA tracts. FFIEC 2025 throughout.
  - `data/shoshone_bannock_oz2_brief.pdf` — new 3-page brief on Fort Hall Reservation (4
    tracts: 3 rural QROF, all 4 CRA-eligible, DCI Q5 data gap documented, 5 action
    recommendations). Script: `scripts/build_shoshone_bannock_brief.py`.

*SME initialized (2026-06-10):* `agents/sme-oz2.md` built via harness onboarding.
Community development perspective, Fed-style neutral tone. See harness.md for pipeline state.

*Branch cleanup:* All branches resolved. Deleted: `claude/cra-eligibility-overlap-2srcf8`,
`claude/site-pause-reactivation-dx1ypq`, `claude/state-maps-tract-filtering-NnJut`. Only
`main` remains.

**Completed in the 2026-06-10 session (branch: claude/cra-eligibility-overlap-2srcf8):**

*CRA eligibility fix — two-track logic:* `ingest_cra_lmi.py` now uses the FFIEC Census
Flat File (`CensusFlatFile2025.csv`, 87,276 rows, 1,212 cols, positional no-header format)
instead of the Census Tract List XLSX, which had income levels but no distressed/underserved
column. Key columns per `FFIEC_Census_File_Definitions_10JULY25.xlsx` (data dictionary):
  - Col 14: income indicator (1=Low, 2=Moderate, 3=Middle, 4=Upper, 0=N/A)
  - Col 21: meets current OR previous year's D/U criteria ('X' = yes, blank = no)

**Updated overlap figures:**
  - Track 1 (LMI only, L+M): 17,378 tracts — **68.6%** (unchanged)
  - Track 2 (non-LMI distressed/underserved middle-income): +1,590 tracts
  - Combined two-track CRA: 18,968 tracts — **74.9%**

Note: The earlier estimate of 83–84% was a misattribution; 74.9% is the correct figure
using the FFIEC's own definition (non-metropolitan middle-income tracts with D/U flag only).

**Files updated and pushed in this session:**
  - `scripts/ingest_cra_lmi.py` — CSV preferred over XLSX; new `_parse_local_csv()` handles
    positional format; `is_cra_lmi` = Track 1 (L+M) OR Track 2 (col 21 = 'X')
  - `data/cra_lmi_overlap.parquet` — regenerated with correct two-track logic
  - `public/geo/*.geojson` — rebuilt with updated `is_cra_lmi` flags
  - `state_metadata.yaml` — `cra_lmi_tracts` counts updated for all 51 states

**Completed in the 2026-06-02 session (PR #14):**

*Urban Institute investability layer:* Ingested Urban Institute "Data to Inform 2026 OZ Selections"
dataset (25,259 tracts, 3-tier categorical classification). All 56 state GeoJSON files rebuilt with
`ui_invest_score` and `ui_invest_quintile` columns. TractMap choropleth uses blue scale (Tier 1 =
sweet spot = dark, Tier 3 = low probability = light). Sweet-spot filter highlights only Tier 1 tracts.
Popups show full tier label. `ui_invest_q1_tracts` populated in `state_metadata.yaml` for all 50
states (5,688 Tier 1 tracts nationally).

*AFA toolkit resources:* Updated placeholder description on how-to-advocate page with accurate content
(5-step framework, anti-displacement guidance, co-authors). Added direct links to AFA scoring rubric
(Google Sheet) and tract dataset (xlsx) — URLs extracted from PDF. Added 3 new references.md entries
(rubric, dataset, research landscape scan).

**Completed in the 2026-05-12 session (branch: claude/add-anchor-links-jkfkF):**

*Anchor links:* Section headers on references, capital-stack, and how-to-advocate pages have
copyable anchor link icons (hover to reveal, click to copy URL, green flash on copy).

*EIG audit + corrections:* Compared site against EIG OZ 2.0 Designation Leads map.
Upgraded CO, MD to public_process; VA marked input-closed (deadline 2026-04-27 passed).

*Skills review:* Applied all three skills (oz2-local-planner, oz2-impact-investor,
oz2-community-matchmaker) to capital-stack, how-to-advocate, oz1-retrospective,
off-list-nominations, and 13 states with upcoming deadlines (DE, NM, MO, OR, WA, KY,
MS, OH, KS, SC, NC, TX, WV).

*Template fixes ([state].astro):*
- `daysToStateDeadline` counter: 4th headline tile shows days to state deadline
  (not July 1 federal window) when a state deadline is open and in the future.
- "How to influence the nomination": renders state-specific action steps (portal link,
  deadline, build-your-case checklist) for public_process states with open windows;
  "input closed, monitor for draft recommendations" for passed deadlines; generic
  how-to-advocate pointer for contact_only/no_public_process.
- Tribal section: always renders; when `tribal_consultation.framework` is null,
  shows a fallback guidance note instead of suppressing the section entirely.

*State data updates (13 states, all last_checked 2026-05-12):*
- DE: scarcity alert (23/25 slots filled), Nanticoke tribal note
- NM: fixed past-tense deadline error, added COG directory ref, Navajo Nation + 19 Pueblos tribal framework
- MO: Osage Nation tribal framework, clarified July advisory review period
- KY: RCAP corrected GLCAP → SERCAP, 800# moved to contact_phone, QROF framing added
- OR: tribal_consultation populated (9 OR tribes + Brian Plinski liaison)
- WA: ADO network guidance added to process text
- MS: archived past listening sessions, Mississippi Band of Choctaw Indians tribal framework
- OH: deadline uncertainty surfaced in process text, ODOD main line (614) 466-2317, Ohio SHPO tribal note
- KS: scoring rubric note clarified, application form status updated, Kickapoo/Iowa Tribe tribal framework
- SC: Catawba Indian Nation (York County) tribal framework, stale workshop hedge removed
- NC: EBCI + Lumbee Tribe/Robeson County tribal frameworks
- TX: FAQ link surfaced into process text, three TX federally recognized tribes, OZ 1.0 Harris Co. displacement context
- WV: RCAP corrected GLCAP → SERCAP, WVDED main line (304) 558-2234, inferred-criteria caveat, energy transition framing

*Cross-cutting page fixes:*
- capital-stack: new QROF mechanics section (rural bonus step-up, 50% improvement
  threshold, deal economics); CBA language tied to §6039K reporting; broken NMTC
  citation fixed; last reviewed updated to May 12, 2026.
- how-to-advocate: OZ 1.0 displacement context (NCRC/Urban Institute 2025 refs);
  residents and tenants named as coalition stakeholders; CBA/§6039K leverage;
  stale state count fixed (32→28); verified date updated to May 12, 2026.

**Next priorities (in order):**
1. ~~oz1-retrospective and off-list-nominations pages — still stubs, need real content~~ DONE: both pages are fully built.
2. ~~State metadata upkeep~~ DONE: PR #24 (2026-06-16) updated CO, PA, ID deadlines; all open-window states verified.
3. ~~SME Editor Mode B — stress-test pass on capital-stack CRA/NMTC sections using sme-oz2.md~~ DONE (2026-06-16): two edits — (a) CRA Final Rule status corrected (rescinded 2025, not "under legal challenge"); (b) NMTC deal-size floor added ($3–5M+ practical minimum limits rural applicability).
4. Census API key: store as Vercel env var so ingest_tribal_overlap.py can be re-run in CI
5. Case studies library expansion — 22 verified entries as of 2026-06-16 (PR #23); consider adding more with sector gaps (broadband is lightest) from local CLI where WebFetch works

**State deadlines remaining open (as of 2026-05-12):**
- Delaware: May 15 (ONLY 2 SLOTS REMAIN — 23/25 already nominated)
- New Mexico COG: May 15 → EDNM refines through June 15 → Governor submits July 1
- Missouri: May 17
- Oregon: May 22
- Washington: May 28
- Kentucky: May 29
- Mississippi: May 31
- Ohio: ~May 31 (unconfirmed — verify at opportunityzones.ohio.gov)
- South Carolina: June 1
- Kansas: June 1
- North Carolina: June 7
- Texas: June 26
- West Virginia: July 1 (same as federal window — treat June 15 as internal target)

**States that closed input (deadlines passed):**
- Nebraska, Florida: closed before May 2026
- Virginia: April 27, 2026 (now "Input closed")
- Delaware: May 15, 2026

## QROF mechanics (key facts — use these, don't invent others)

Rural-designated tracts (IRS Rev. Proc. 2026-14 / Notice 2025-50 §4.01) qualify for
Qualified Rural Opportunity Fund (QROF) treatment under P.L. 119-21 (OBBBA). Key mechanics:
- **Rural bonus step-up**: QROF investors holding 5+ years get a 30% basis step-up on
  the original deferred gain (permanently excludes 30% of the original gain, beyond the
  standard 10-year appreciation exclusion).
- **Reduced improvement threshold**: Rural QOZBs must improve existing property by 50%
  of adjusted basis (vs. 100% for standard/urban QOZBs).
- These apply to every tract flagged `rural_eligible` in the IRS appendix — communities
  cannot earn or lose this flag through advocacy.
Source: IRC §§ 1400Z-1, 1400Z-2 as amended by P.L. 119-21.

## Audience and stance

- **Primary audience (MVP)**: local officials, EDD staff, community
  development directors in rural-eligible jurisdictions.
- **Phase 2 audiences**: impact investors, community organizations /
  matchmakers, philanthropy. Skills exist for the first three; use them as
  reviewers, not generators.
- **Editorial stance**: neutral, evidence-based, useful regardless of
  political stance. The critical/editorial argument about OZ-financed LULUs
  lives in a companion lab essay on vargo.city, not here.

## Ground truth

- Eligibility and rural flag: **IRS Rev. Proc. 2026-14 appendix** (April 6,
  2026). This is the canonical source. Do not reimplement the rural test;
  Treasury already resolved it for every tract.
- Rural definition: **Notice 2025-50, Section 4.01**.
- State agency leads: EIG OZ 2.0 Designation Leads map (primary); HUD OZ portal
  (secondary, lags on process-specific updates — HUD pages are largely OZ 1.0 era).
- Always cite specific sources from references.md when stating facts. If a
  claim isn't in references.md, search and add the source.

## Workflow conventions

- Bibliography: every citation in the site links to an entry in
  references.md. Each entry has a `last_checked` date.
- State metadata: `state_metadata.yaml` is the data contract. Schema
  documented in SPEC.md.
- Page review: invoke the three project skills (`oz2-local-planner`,
  `oz2-impact-investor`, `oz2-community-matchmaker`) as quality gates after
  major page edits.
- Voice: neutral, evidence-based, direct. Not Jason's personal voice. Do
  not invoke jason-vargo-voice or jason-vargo-design-aesthetic for this
  project.

## Don't

- Don't reproduce eligibility maps. Embed or link EIG, IRS, or Novogradac
  instead.
- Don't introduce LULU framing or "designation as guardrail" arguments
  here. That content belongs in the lab essay.
- Don't rely on memory for OZ facts — always check Rev. Proc. 2026-14
  appendix or references.md.
- Don't assume a state has published a public process. As of mid-May 2026,
  ~22 of 51 jurisdictions had. Verify via state landing page.
- Don't use bullet-point dense formatting for state page narrative
  sections. Prose for selection-process and coalition-strategy writeups.
- Don't reference HUD OZ portal as primary source for state leads — those
  pages are largely OZ 1.0 (2017 era). Use EIG Designation Leads map instead.

## Tech stack assumptions

- Static site, Astro framework, Vercel hosting.
- Markdown content with YAML frontmatter; state data sourced from
  `state_metadata.yaml`.
- Python for data ingestion (`scripts/`).
- Supabase only if dynamic features are needed; prefer fully static for MVP.
- Embed EIG ArcGIS dashboards via iframe rather than reproducing maps.

## Status tiers (every state page declares one)

- **Public process** — state has published guidance, named contacts, set
  deadlines, defined scoring criteria.
- **Contact only** — lead agency identified, contact info available, no
  public process yet.
- **No public process yet** — universal information only; ask local
  planners to push the governor's office for engagement.

Re-evaluate every state's tier at least every two weeks during the May–July
nomination ramp.

