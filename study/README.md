# OZ Finance Tutor — Claude Project pack

A prepared system prompt and knowledge base for studying the finance side of Opportunity
Zone 2.0 conversationally: the tax incentive, capital stacks, banks and CRA, CDFIs, deal
economics, and what the OZ 1.0 evidence actually shows.

The companion curriculum lives on the site at **[/learn](https://oz2.vargo.city/learn)**.
The page teaches; this pack is the tutor you argue with afterward.

---

## Why a Project rather than a chat window on the site

The site is a static Astro build on Vercel. A page served from it cannot call a model —
that would need a serverless function holding an API key, plus rate limiting and abuse
handling on a public URL, plus per-token cost. A Claude Project gets you a real
conversational tutor with no infrastructure at all, and lets the knowledge base be a set of
files you can see and correct.

## Setup — about five minutes

1. Go to [claude.ai](https://claude.ai) → **Projects** → **Create project**. Name it
   something like *OZ Finance Tutor*.
2. Open the project's **Custom instructions** and paste the entire contents of
   [`project-instructions.md`](./project-instructions.md).
3. Add every file in [`knowledge/`](./knowledge) to the project's knowledge:
   - `00-how-to-use.md` — orientation and precedence rules
   - `01-oz-finance-primer.md` — the six-module curriculum
   - `02-capital-stack.md` — program-by-program stacking detail
   - `03-cra-oz-overlap-brief.md` — the CRA/OZ overlap data brief
   - `04-key-figures.md` — verified numbers with sources
   - `05-references-finance.md` — the finance bibliography
   - `06-glossary.md` — acronyms and terms
4. Start a conversation with any prompt from [`prompts.md`](./prompts.md).

Good first message if you want to be placed rather than choosing:

> I'm a planner, not a finance person. I understand what OZ designation is but not how the
> money actually works. Figure out where my gaps are and tell me which module to start
> with.

## What is in the pack

| File | Hand-written or generated |
|---|---|
| `project-instructions.md` | Hand-written. Composed from `agents/sme-oz2.md`, `skills/oz2-impact-investor/SKILL.md`, and the ground-truth rules in `CLAUDE.md`. |
| `prompts.md` | **Generated** from `data/study_prompts.yaml` |
| `knowledge/00-how-to-use.md` | Hand-written |
| `knowledge/01-oz-finance-primer.md` | **Generated** from the built `/learn` page |
| `knowledge/02-capital-stack.md` | **Generated** from the built `/capital-stack` page |
| `knowledge/03-cra-oz-overlap-brief.md` | **Generated** — copied from `docs/cra-oz-overlap-brief.md` |
| `knowledge/04-key-figures.md` | Hand-written. The anti-hallucination sheet. |
| `knowledge/05-references-finance.md` | **Generated** from `references.md` §§ 1, 6, 7, 8, 14 |
| `knowledge/06-glossary.md` | **Generated** from `data/glossary.yaml` |

## Regenerating

The generated files are derived, not authored. Edit the source, then rebuild and re-export:

```sh
npm run build                          # the exporter reads dist/ for the two page exports
python3 scripts/export_study_pack.py
```

Sources to edit instead of the generated output:

- prompts → `data/study_prompts.yaml`
- glossary → `data/glossary.yaml`
- the primer → `src/pages/learn.astro`
- capital stack detail → `src/pages/capital-stack.astro`
- the CRA brief → `docs/cra-oz-overlap-brief.md`
- the bibliography → `references.md`

Re-upload the changed files to the Project afterward — Claude Projects do not track this
repository.

## Known limits

- **The knowledge base ends in mid-2026.** State nomination processes and deadlines move
  faster than this pack; use the state pages on the site for those.
- **Nothing here is tract-level.** Whether a specific tract is eligible, rural, or
  CRA-designated needs the Rev. Proc. 2026-14 appendix and the FFIEC tract search tool.
- **A tutor is not a citation.** Every number in `04-key-figures.md` traces to a source;
  anything the model says beyond that sheet should be checked before it goes in a memo.
