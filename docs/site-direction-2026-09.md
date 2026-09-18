# Where this site goes after the map lands

*Written 2026-09-18, ten days before the federal nomination window closes.*

## The problem with the current framing

The site was built to answer one question: **how do I get my tract nominated?** Every
structural choice follows from that — the status tiers, the deadline countdowns, the coalition
playbook, the off-list explainer, the "how to influence the nomination" block on all 51 state
pages. It was the right build for February through August 2026.

That question is now closed. The determination period ends September 28 (October 28 for any
state taking the extension), Treasury certifies by late December at the outside, and
designations run January 1, 2027 through December 31, 2036. Nothing a local planner does
between now and then changes the map.

If the site keeps answering the nomination question, it becomes an archive within weeks. The
evidence for that is already in the repo: three consecutive sessions (May, June, July) spent
significant time sweeping for stale tense — "the window opens July 1," "deadlines close in the
coming weeks," a countdown tile that had gone negative. That was a symptom of the framing, not
of sloppiness.

## What the usage signal says

The two pages in heaviest use are the **OZ 1.0 retrospective** and the **case studies library**.
Neither is about nomination. Both are about *evidence* — what the program actually did, and
what real deals looked like. They get used because they answer questions that don't expire:

- Does this thing work?
- What has it financed before?
- What should I expect if capital shows up in my town?

That is the durable franchise. Everything built for the nomination sprint was scaffolding
around it.

## The reframe

**From:** a nomination-advocacy resource for local planners.
**To:** the place that tracks whether OZ 2.0 delivers better than OZ 1.0 did, tract by tract,
and helps communities act on the answer.

This is not a pivot away from the audience. It is the same local planner, six months later,
asking a harder question. And it is the one thing the OZ industry press will not do, because
their readers are investors and fund sponsors, not the places receiving the capital.

### Why this is newly possible

The single largest failure of OZ 1.0 was that nobody could see where the money went. The first
usable tract-level data arrived years in, far too late to change program design.

OBBBA fixed that. IRC §§ 6039K and 6039L require QOFs to report annually — census tracts
invested in, amount per qualified OZ business, NAICS codes, full-time employees, residential
units, owned versus leased property — with penalties under § 6726 behind it. Treasury must
publish annual reports starting in 2027, with expanded reports in years six and eleven.
REG-116506-25, proposed September 11, 2026, is the rule that implements it. **Comments close
October 26, 2026.**

So beginning in 2027 there will be a recurring public dataset about OZ 2.0 outcomes. This site
already has the analytical apparatus to use it: eligible tracts, rural flags, CRA two-track
overlap, NMTC history, DCI distress quintiles, Urban Institute investability scores, all joined
at the tract level, all reproducible from scripts. Nobody else has that assembled and pointed
at community outcomes rather than deal sourcing.

## What changed in this session

Implemented now:

1. **`src/lib/timeline.ts`** — one source of truth for program dates and phase. Every
   date-dependent string on the site derives from it. The site now re-frames itself at each
   boundary instead of needing a manual sweep. `OZ2_AS_OF=YYYY-MM-DD` renders a future date so
   phase copy can be checked before it goes live.
2. **`.github/workflows/scheduled-rebuild.yml`** — a static build freezes `new Date()`, so a
   daily rebuild is what makes the phase model actually work. *Needs a one-time setup step:
   create a Vercel Deploy Hook and save it as the repo secret `VERCEL_DEPLOY_HOOK_URL`.*
3. **`/whats-next`** — new page, in the nav. Certification mechanics, the Notice 2026-40
   transition rules, the reporting rule, and audience-specific guidance for the interim.
4. **`nomination` block in `state_metadata.yaml`** — records the federal filing (confirmed /
   assumed / unknown, tract count, off-list count, published list URL) separately from
   `status_tier`, which describes a state's own input process and is now history.
5. Reframed: home, about, how-to-advocate, off-list-nominations, capital-stack, case-studies,
   the retrospective's reporting section, and the state template.

## What to do next, in order

### 1. Comment on REG-116506-25 before October 26
Highest leverage item on this list by a wide margin, and it expires. The rule decides whether
tract-level OZ 2.0 data becomes *public* in a usable form or merely *filed with the IRS*. This
site is a credible commenter: it can point to a specific analytical use case and a specific
audience that was underserved by OZ 1.0's opacity. A short comment from a community-development
perspective is worth more than another page of content.

### 2. Build the certified-designation ingest before certification, not after
Treasury will publish the certified list somewhere between late November and December 27.
Write `scripts/ingest_designated_tracts.py` now against the Rev. Proc. 2026-14 appendix schema,
so that when the list drops it is a same-day update rather than a two-week project. The payoff
is real: for a week or two this would be one of the few places showing designated-versus-eligible
by state, with the rural, CRA, and distress overlays already joined.

Design the state page to answer, on day one: *which of my tracts got designated, which didn't,
and what does that mean for the projects I have in motion?*

### 3. Keep the retrospective as the spine, and give it a sequel
The retrospective is the most-used page because it is the honest one. Plan a companion — call it
an OZ 2.0 scorecard — that starts nearly empty in 2027 and fills as § 6039K data arrives. Stand
it up early and let it visibly accumulate; a page that says "here is what we do not yet know,
and here is when we will know it" is more useful than silence, and it makes the site the
obvious place to check each time Treasury publishes.

The framing to hold: OZ 1.0 concentrated 42% of capital in the top 1% of tracts and sent 8.5%
to rural areas. Those are the benchmarks. Every year OZ 2.0 data lands, the question is whether
those numbers moved.

### 4. Extend the case studies library forward
Twenty-two verified OZ 1.0 projects is the site's most differentiated asset. Two additions
worth making:

- **Transition-relevant entries.** Projects whose tracts are *not* renominated, documenting what
  happens to a half-built OZ deal when the designation lapses. Nobody is writing this up, and
  it is exactly the situation a local planner will be in.
- **The first OZ 2.0 deals**, starting in 2027. Same verification bar. The library's value
  compounds if it spans both programs — that is what lets anyone say whether the new rules
  changed deal composition.

Broadband remains the lightest sector tag.

### 5. Retire the nomination scaffolding deliberately
Do not delete it. `/how-to-advocate` and `/off-list-nominations` are now the written record of
how the 2026 round worked, and OBBBA made designation decennial — there is a next cycle. Both
now carry a banner marking them as historical. Revisit around 2034.

The `status_tier` field is the awkward case: it describes a process that no longer exists, and
it still drives the badge on every state page. It is superseded by `nomination.status` but not
yet removed, because it remains the only record of how each state ran its process. Once the
certified list lands, the badge should switch to designation counts and `status_tier` should
move into a `history` block.

## What to stop doing

- **Tracking state input deadlines.** They are all closed. The machinery still renders but has
  nothing live to show.
- **Two-week tier re-evaluation.** The CLAUDE.md instruction to re-check every state's tier
  every two weeks was right for the ramp and is now wasted effort. Replace with: re-check
  `nomination.status` when a state publishes its slate, and do a full pass when Treasury
  certifies.
- **Treating state announcements as authoritative.** States could revise filings until their
  window shut, and Treasury does not process early filings early. Only certification is final.

## The one-sentence version

The nomination question is answered; the site's remaining value is that it can tell a community
what OZ 2.0 actually does to it, starting with data that has never existed before — so the work
now is to be ready for that data rather than to keep explaining a process that has ended.
