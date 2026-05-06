# Claude Code Project Instructions — OZ 2.0 State-Specific Resource

You are working on a state-by-state Opportunity Zone 2.0 resource for local
planners and nonprofits. The full spec is in SPEC.md; the bibliography is
in references.md. Read both before substantive edits.

## Where things stand (as of 2026-05-05)

**Data bootstrap done:**
- `data/eligible_tracts.parquet` — 25,332 eligible tracts from IRS Rev. Proc. 2026-14
- `data/state_summaries.csv` — per-state totals, rural splits, top-10 counties
- `scripts/ingest_irs_appendix.py` — fetches the IRS appendix XLSX, re-runnable

**Site scaffold done:**
- Astro + Tailwind, Node 22 (`.nvmrc`), Vercel target
- `npm run dev` to start, `npm run build` to verify
- All routes stubbed per SPEC; 3 state pages live (alabama, alaska, arizona)

**Next priorities (in order):**
1. `state_metadata.yaml` — drives all 51 state pages; schema in SPEC.md
2. Data overlays: `data/dci.parquet` (EIG DCI), `data/persistent_poverty.parquet` (USDA ERS), `data/tribal_overlap.parquet` (BIA)
3. Fill stub pages: how-to-advocate, capital-stack, oz1-retrospective, off-list-nominations
4. Vercel deploy — connect repo, zero config for Astro static

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