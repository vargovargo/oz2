# CLAUDE.md — [oz2]
*Harness: data research post. Copied from vargo-research-ops/harnesses/data-post.md.*

> Fill in everything in [brackets] at kickoff. The two lines under "Session state"
> are the only things you update between sessions.

## Project

- **Slug:** [oz2]
- **Question:** [one-line research question]
- **Venue:** [vargo.city lab post]
- **Repos:** [users/lauren/oz2] ↔ [users/lauren/oz2], JSON contract at [????]

## Agent Library

Shared agents: `../vargo-research-ops/agents/`
Shared harnesses: `../vargo-research-ops/harnesses/`
Shared context: `../vargo-research-ops/shared-context/`

Agents active for this project:
- Methodology Advisor — `../vargo-research-ops/agents/methodology-advisor.md`
- ETL Engineer — `../vargo-research-ops/agents/etl-engineer.md`
- Data Scientist — `../vargo-research-ops/agents/data-scientist.md`
- SME Editor — `../vargo-research-ops/agents/sme-editor.md` (onboarding) →
  `./agents/sme-[project-slug].md` (initialized)
- Writer — `../vargo-research-ops/agents/writer.md`
- Style & Voice Reviewer — `../vargo-research-ops/agents/style-voice-reviewer.md`
- Viz Designer — `../vargo-research-ops/agents/viz-designer.md`
- Code Reviewer — `../vargo-research-ops/agents/code-reviewer.md`

## Pipeline (data research post)

Methodology Advisor → ETL Engineer → Data Scientist → SME onboarding →
SME Editor → Writer → Style & Voice Reviewer → Viz Designer → Code Reviewer →
publish

SME onboarding runs once, at the SME stage of the first post. Later posts in a
series reload the existing `./agents/oz2.md`.

## Handoffs

```
./handoffs/
  01-research-design.md     Methodology Advisor
  02-data-dictionary.md     ETL Engineer
  03-findings-summary.md    Data Scientist
  04-stress-test-memo.md    SME Editor
  05-draft-post.md          Writer
  06-review-comments.md     Style & Voice Reviewer
  07-viz-specs.md           Viz Designer (+ Graphic Designer composition)
  08-code-review.md         Code Reviewer
```

## Handoff contract (every stage ends with this)

```markdown
## Handoff: [Stage Name]
**From:** [Agent]
**To:** [Agent]
**Status:** complete | needs-revision | blocked
**Key outputs:** [files/artifacts]
**Open questions for next stage:** [numbered]
**Do not proceed until:** [explicit gate conditions]
```

## Session state  ← UPDATE THESE TWO LINES EACH SESSION

- **Current pipeline phase:** SME (onboarding complete → SME Editor active)
- **Last handoff:** ./agents/sme-shock-stress-shift.md (SME initialized 2026-06-09)

## Session opener (paste to Claude Code when resuming)

> Read CLAUDE.md, load the skill file for the current-phase agent, read the last
> handoff for context, and pick up from there. Update the two session-state lines
> before we close.
