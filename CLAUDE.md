# Claude Code Project Instructions — OZ 2.0 State-Specific Resource

You are working on a state-by-state Opportunity Zone 2.0 resource for local
planners and nonprofits. The full spec is in SPEC.md; the bibliography is
in references.md. Read both before substantive edits.

## Where things stand (as of 2026-05-12)

**Data bootstrap done:**
- `data/eligible_tracts.parquet` — 25,332 eligible tracts from IRS Rev. Proc. 2026-14
- `data/state_summaries.csv` — per-state totals, rural splits, top-10 counties
- `scripts/ingest_irs_appendix.py` — fetches the IRS appendix XLSX, re-runnable

**State metadata done:**
- `state_metadata.yaml` — all 51 states populated; ~22 public_process, ~28 contact_only, 1 no_public_process (DC)
- `scripts/generate_state_metadata.py` — regenerates scaffold from CSV (re-runnable)
- `scripts/patch_state_metadata.py` — applies researched status/agency data (re-runnable, idempotent)
- `src/lib/states.ts` — typed loader; `getAllStates()`, `getState(slug)`, `getStateSlugs()`

**Site live:**
- Deployed at https://oz2-two.vercel.app (GitHub: vargovargo/oz2, branch: main)
- Working branch: `claude/add-anchor-links-jkfkF` — not yet merged to main
- All 51 state pages rendering from YAML — correct tier badges, lead agency contacts, deadlines, county tables
- "Input closed" logic: states with past deadlines show grey badge + prose note
- References page: styled with entry separators, clickable URLs, last_checked badges, section anchor links
- references.md section 13 added — per-state agency pages (49 entries, last_checked 2026-05-05)

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
1. Merge `claude/add-anchor-links-jkfkF` → main and verify Vercel deploy
2. oz1-retrospective and off-list-nominations pages — still stubs, need real content
3. Data overlays: `data/dci.parquet` (EIG DCI), `data/persistent_poverty.parquet` (USDA ERS), `data/tribal_overlap.parquet` (BIA)
4. EIG ArcGIS embeds — replace placeholder grey boxes on state pages with real iframes scoped by FIPS
5. State metadata upkeep — re-check tiers every two weeks; several windows close in June
6. Custom domain: oz2.vargo.city → Vercel

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

**Data bootstrap done:**
- `data/eligible_tracts.parquet` — 25,332 eligible tracts from IRS Rev. Proc. 2026-14
- `data/state_summaries.csv` — per-state totals, rural splits, top-10 counties
- `scripts/ingest_irs_appendix.py` — fetches the IRS appendix XLSX, re-runnable

**State metadata done:**
- `state_metadata.yaml` — all 51 states populated; 18 public_process, 32 contact_only, 1 no_public_process (DC)
- `scripts/generate_state_metadata.py` — regenerates scaffold from CSV (re-runnable)
- `scripts/patch_state_metadata.py` — applies researched status/agency data (re-runnable, idempotent)
- `src/lib/states.ts` — typed loader; `getAllStates()`, `getState(slug)`, `getStateSlugs()`

**Site live:**
- Deployed at https://oz2-two.vercel.app (GitHub: vargovargo/oz2, branch: main)
- All 51 state pages rendering from YAML — correct tier badges, lead agency contacts, deadlines, county tables
- "Input closed" logic: states with past deadlines show grey badge + prose note (Nebraska, Florida)
- References page: styled with entry separators, clickable URLs, last_checked badges
- references.md section 13 added — per-state agency pages (49 entries, last_checked 2026-05-05)

**Next priorities (in order):**
1. Fill stub cross-cutting pages: `how-to-advocate`, `capital-stack`, `oz1-retrospective`, `off-list-nominations`
2. Data overlays: `data/dci.parquet` (EIG DCI), `data/persistent_poverty.parquet` (USDA ERS), `data/tribal_overlap.parquet` (BIA)
3. EIG ArcGIS embeds — replace placeholder grey boxes on state pages with real iframes scoped by FIPS
4. State metadata upkeep — re-check tiers every two weeks; several states' windows close/open in May–June
5. Custom domain: oz2.vargo.city → Vercel

**Upcoming deadlines to watch (state nomination windows):**
- Missouri: May 17 | Kentucky: May 29 | Oregon: May 22 | Washington: May 28
- Mississippi: May 31 | Ohio: ~May 31 | Delaware: May 15
- South Carolina: June 1 | Kansas: June 1 | North Carolina: June 7
- Texas: June 26 | New Mexico: May 15 (COG submissions to EDNM) / July 1 (final state)

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
- State agency leads: HUD OZ portal + EIG OZ 2.0 Designation Leads map.
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
- Don't assume a state has published a public process. As of April 24,
  2026, only 17 of 56 jurisdictions had. Verify via state landing page.
- Don't use bullet-point dense formatting for state page narrative
  sections. Prose for selection-process and coalition-strategy writeups.

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