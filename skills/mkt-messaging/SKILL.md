---
name: mkt-messaging
description: >
  Write the messaging of a product or a launch: the audience it speaks to, the promise, the
  proof points with their sources, the sections of a landing page with purpose, headline, body,
  demo and call to action, taglines and words to avoid, every claim traced to a research
  brief, a product artifact, a measurement or the user's words. Use this skill when someone
  asks for landing page copy, a value proposition, taglines, "what should the site say", a
  launch message or the sections of a marketing page, before that page is designed. It never
  invents a number, a customer or a comparison; what has no source becomes a question or is
  left out. Not for the visual design of the page (design-brief), for positioning research
  (core-research, biz-icp-positioning) or for publishing (mkt-publish).
license: MIT
metadata:
  area: marketing
  kind: capability
  inputs: [docs/product/prd.md, docs/business/positioning.md, docs/workbench/research/<topic>.md, docs/brand/voice.md, docs/product/specs/<feature>.md, docs/workbench/state.md]
  outputs: [docs/marketing/messaging.md]
  requires: []
  side_effects: []
  version: "0.1"
---

# Messaging

## Purpose

Decide what the product says about itself before anyone draws the page that says it: who is addressed, what is promised, what proves it, and how the landing page is sectioned so that each section carries one proof. The output feeds `design-brief` (sections and copy) and, later, `mkt-launch-plan` and `mkt-content`.

## When not to use

- The audience or the positioning is undecided: `core-clarify`, `core-research` or `biz-icp-positioning` first; copy for an undecided audience is noise.
- The page layout and visuals: `design-brief`, which consumes this document, and `design-execute`, which runs it in a design tool.
- A single post or email: `mkt-content`.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| `docs/product/prd.md` (users, features, metrics) | yes | Route to `product-prd`. |
| Positioning: `docs/business/positioning.md` or a research brief with competitor facts | yes for comparisons | Make no comparison; say why. |
| `docs/brand/voice.md` | no | Derive the voice from the product's own texts (README, documentation) and state the three rules you derived, labelled `derived`. |
| The product's own facts: README, documentation, changelog, measured numbers | yes | Ask the user for the facts; never fill from memory of similar products. |
| A reference page the user named as inspiration | no | Use only its structure (section order and kinds), never its copy. |
| `docs/workbench/state.md` | no | Skip the decision check; do not register the artifact. |

## Procedure

Progress:
- [ ] Step 1: Ground. Read the PRD (users, goal, features of the landing), the positioning or research brief, the brand voice or the product's own texts, the specs of the page, and the reference page's structure when the user named one. Write the Sources list. Every fact you will use is copied here with its source before writing a line of copy.
- [ ] Step 2: Audience and promise. One line per user group from the PRD: what they are trying to do and what they fear. One promise sentence for the whole page, in the product's own words where they exist. Read [references/copy-rules.md](references/copy-rules.md) for the rules on claims, numbers and tone.
- [ ] Step 3: Proof points. One `PROOF-n` per claim the page will make: the claim in one sentence, the evidence (a measurement with its method and date, a documented behaviour with its file, a research citation), `Source:`. A claim without evidence is not written; a comparison without a measured or cited number is not written.
- [ ] Step 4: Sections. One `SECTION-n` per block of the page, in order: purpose (what the reader must believe after it), the proof points it carries, headline, body (at most three sentences), the demo or visual it needs (described, for design-brief), the call to action when it has one, `Source:` for its facts. The first section carries the promise; every later section carries at least one proof point; a section with no proof is removed.
- [ ] Step 5: Taglines and words. Three tagline candidates with the promise, a list of words to use (the product's own vocabulary) and to avoid (hype and unsourced superlatives), `Source:` for the vocabulary.
- [ ] Step 6: Ask what only the user can decide (a claim they may not want to make, a comparison to name, the tone), at most three questions with a recommended answer.
- [ ] Step 7: Lint: `python3 scripts/lint_messaging.py --file docs/marketing/messaging.md`. It checks sections, that every PROOF has evidence and a source, that every SECTION has purpose, headline, body, demo or CTA and a source, that every number in a headline or body appears in a PROOF, and that no word from the avoid list appears in the copy. Fix until `ok` is true.
- [ ] Step 8: Register `docs/marketing/messaging.md` in `docs/workbench/state.md` (owner `mkt-messaging`, status `draft`) when the state file exists, and report with the template.
- [ ] Step 9: Self-check against "Quality criteria".

## Output template

See [assets/messaging-template.md](assets/messaging-template.md). The report:

```markdown
## Messaging: <product or launch> → docs/marketing/messaging.md

- Audience: <U ids>; promise: <one line>
- Proof points: <n> (<n> measured, <n> documented, <n> cited); sections: <n>
- Comparisons: <named products, or none>
- Open questions: <n>
Next: design-brief for the landing | the questions above
```

## Quality criteria

Approve the messaging only if all of the following hold:

- Every claim on the page is a PROOF with evidence and a source; every number in the copy appears in a PROOF with its method and date.
- Every section carries at least one proof point and states the demo or visual it needs.
- Comparisons name only products with measured or cited numbers from a research brief, with the method stated.
- The copy uses the product's own vocabulary and no word from the avoid list.
- The reference page, when any, contributed structure only; no sentence was copied from it.
- `lint_messaging.py` reports `ok: true`.

## Gotchas

- "Lightweight", "fast" and "modern" without a number are what every competitor says; the number with its method is what only this product can say.
- A comparison is a promise to be checked by the reader; publish the method next to it or do not make it.
- The product's README and docs already contain its voice; copy that voice, not a marketing register.
- Section order is an argument: promise, then the proof the reader is most likely to doubt, then the rest, then the install.
- Placeholders for facts you do not have ("used by N teams") do not belong in a messaging document; leave the section out and ask.
