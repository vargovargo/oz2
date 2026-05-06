---
name: oz2-state-writer
description: |
  Use this skill to draft or update the selection-process narrative and
  contact section for a specific state's OZ 2.0 spotlight page. Invoke
  when the user asks you to write, fill in, or improve a state's process
  description, coalition guidance, or "who to contact" content. Takes a
  state slug (e.g. "kentucky", "north-carolina") as its argument.

  This skill researches the state's official agency pages live, reads the
  current state_metadata.yaml entry, and writes prose ready to paste into
  the `process` field and supporting YAML fields. It does not review or
  audit — it produces.
---

# OZ 2.0 State Process Writer

## Mission

Write the selection-process narrative for one state's OZ 2.0 spotlight page.
The output must be accurate enough for a planner to act on, specific enough
to be worth reading, and plain enough for a generalist with one hour to
spare.

## Before you write anything

1. **Read `state_metadata.yaml`** — find the state's entry. Note:
   - `status_tier` (public_process / contact_only / no_public_process)
   - `lead_agency` name, url, contact_email, contact_phone
   - `process` (current draft, if any)
   - `state_deadline`, `application_portal_url`, `scoring_rubric_url`
   - `notes`

2. **Read the relevant section of `references.md`** — Section 13 has the
   per-state agency page entries with last_checked dates.

3. **Fetch the lead agency URL** — visit it live. Then go one or two clicks
   deeper: look for a linked PDF (scoring rubric, nomination guidance),
   a linked form or portal, a FAQ, or a press release. If the page is thin,
   try the agency's news/press section for any OZ 2.0 announcement.

4. **If `scoring_rubric_url` or `application_portal_url` exist**, fetch
   those too — they often have the most actionable detail.

5. **Search for recent press coverage or local EDO announcements** if the
   official page is sparse. A regional chamber or COG may have summarized
   the state process better than the state itself.

## What to write

### For `public_process` states

Write a `process` field value of 3–5 sentences (HTML-safe, no Markdown
headers) covering:

1. **Who runs it** — the specific agency and division, not just the
   department name.
2. **What the process is** — online form? PDF submission by email? COG
   routing? Regional meetings?
3. **Timeline** — open date, deadline, what happens after.
4. **Scoring** — name the published criteria. If weights are published,
   include them. If a rubric PDF exists, say so and link it inline.
5. **Who can submit** — local governments only? EDOs? Tribes? Private
   landowners?
6. **Any limits** — tracts per applicant, counties per region, rural-only
   pools, etc.

Keep it in the voice of a colleague briefing another colleague, not a
press release. No superlatives. No marketing. State the facts in the order
a planner would need them.

### For `contact_only` states

Write a `process` field value of 2–3 sentences:

1. **What is known** — lead agency identified, no formal public process
   published as of the last-checked date.
2. **What a planner should do now** — a specific, actionable step. Name
   the contact (email or phone), and suggest the message: express interest,
   ask when community input will be accepted, offer to provide tract-level
   data.
3. **What to watch for** — any signal from the state (board meeting agenda,
   pending RFA, governor's budget language) that suggests a process is
   coming.

Do not write "stay tuned" or "check back." Write what to do today.

### For `no_public_process` states

Write a single sentence confirming the status and directing the planner to
`/how-to-advocate` for governor's office engagement steps.

---

## Also update these YAML fields if you find new information

- `state_deadline` — if a date is published on the agency site that differs
  from what's in the YAML
- `application_portal_url` — if a live form or portal URL is found
- `scoring_rubric_url` — if a rubric PDF or page is found
- `lead_agency.contact_email` / `contact_phone` — if a direct OZ contact
  is named on the agency page (prefer a named staff contact over a general
  inbox if both are available)
- `last_checked` — always update to today's date

---

## Voice rules

- **Audience**: a local planner or EDD director with limited capacity and no
  OZ expertise. Smart, busy, not an attorney.
- **Tone**: direct, factual, collegial. Like a colleague who read the
  documents so you don't have to.
- **No bullet lists** in the `process` prose field. Full sentences, flowing
  paragraphs.
- **No marketing language**: "exciting," "transformative," "powerful tool,"
  "unprecedented opportunity."
- **Dates must be specific**: not "spring 2026" — "May 29, 2026."
- **Contacts must be named** where possible: not "the agency" — "the
  Kansas Department of Commerce Business Development team."
- **Uncertainty must be labeled**: if a deadline is inferred, say so. If
  the agency page hasn't been updated since OZ 1.0, say so.

---

## Ground truth rules

- Do not state eligibility facts from memory. Eligible tract counts and
  rural flags come from `data/eligible_tracts.parquet` as summarized in
  `state_metadata.yaml`. Do not re-derive them.
- If you find information on the agency site that contradicts
  `state_metadata.yaml`, flag it explicitly before updating the YAML.
- Always cite `references.md` entries for any factual claim. If a new
  source is found, add it to `references.md` Section 13 before writing
  the prose.
- The rural definition is Notice 2025-50 Section 4.01 — do not use any
  other test.

---

## Output format

Return your work in three blocks:

### 1. Research findings
Brief (3–10 bullet points) of what you found on the agency page(s):
new URLs, deadline confirmation, rubric details, contacts, anything that
differs from the current YAML. Note the source URL for each finding.

### 2. YAML updates
The specific fields to change in `state_metadata.yaml`, shown as a diff
or as the new field values. Include `last_checked`.

### 3. Process prose
The final `process` field value, ready to paste. If it contains HTML
(links, `<strong>` tags), show it as HTML. If it's plain text, show it as
plain text.

---

## Anti-patterns

- Do not copy-paste text from the agency website. Synthesize it.
- Do not write a summary of what OZ 2.0 is — the state page template
  already handles that context.
- Do not include investor-facing framing (QOF mechanics, tax deferral
  amounts, step-up basis). That is a Phase 2 concern.
- Do not add content that is speculative or unverified. Prefer "not yet
  published" to guessing.
- Do not write prose longer than 5 sentences for `public_process` states —
  the state page template has other sections; the process field does not
  need to carry the whole page.
