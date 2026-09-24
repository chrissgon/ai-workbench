---
name: design-ui
description: >
  Design one screen from the flows and the design system: a screen document that places every
  region with layout tokens, names the component instance and text style of every element,
  binds every colour to a token, covers every state and breakpoint the flows list, marks copy
  placeholders where the messaging step has not run, and, when a design-tool integration is
  available, builds the screen in the design tool from the file's own variables and components
  and validates it by screenshot; when the screen needs exploration the integration cannot
  compose, it writes a self-contained brief for an external AI design tool. Use this skill
  after design-ux-flows and design-system, when someone asks to design, mock up, draw or
  generate a page, screen, dialog or layout, to update one, or to brief a design tool; one
  screen per run. It never invents a colour, a size or a component the design system does not
  define. Not for flows (design-ux-flows), tokens (design-system) or engineering specs of a
  screen (design-handoff).
license: MIT
metadata:
  area: design
  kind: capability
  inputs: [docs/design/flows.md, docs/design/design-system.md, docs/product/specs/<feature>.md, docs/marketing/messaging.md, docs/workbench/state.md]
  outputs: [docs/design/screens/<screen>.md, docs/design/briefs/<screen>.md]
  requires: []
  side_effects: []
  version: "0.2"
---

# Screen design

## Purpose

Turn one SCREEN of the flows into a concrete layout that engineering can build and a reviewer can check: which region sits where at each breakpoint, in which size and spacing tokens, with which component instances, text styles and colour tokens, in every state. The document is written before any drawing, so the drawing is a rendering of decisions, not the place they are made. When the screen needs a visual direction that composing the design system's parts cannot give, the same decisions become a brief for an external design tool, and the tool's proposals come back to be reviewed against it.

## When not to use

- The screen is not in `docs/design/flows.md`: add it there first; a screen without a flow has no regions or states to design.
- Tokens or components are missing: `design-system` first.
- The engineering hand-off (measurements per breakpoint, states as CSS, assets): `design-handoff`.
- Reviewing what an external tool returned: `core-critique` against the brief's evaluation criteria; this skill records the outcome.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| `docs/design/flows.md` with the SCREEN to design | yes | Route to `design-ux-flows`. |
| `docs/design/design-system.md` | yes | Route to `design-system`. |
| The feature specs the screen serves | yes for `must` features | Design from the flows only and mark requirements `spec pending`. |
| `docs/marketing/messaging.md` (sections and copy for the landing) | when the screen carries marketing copy; always for a brief | Use placeholders in the form `[copy: what the text must say]`; never write final copy. A brief is not written without it: the tool would invent copy. |
| `docs/workbench/state.md` | no | Skip the decision check; do not register the artifact. |

## Procedure

Progress:
- [ ] Step 1: Ground. Read the SCREEN entry (purpose, regions in priority order, states, breakpoints), the flows that cross it, the specs' requirements it serves, and the design system (tokens, type roles, layout, components). Write the Sources list and the screen id.
- [ ] Step 2: Variants to produce. Default: the widest breakpoint of the design system's layout table and the narrowest (for example 1280 and 360), each in light and dark mode; plus one frame per state the flows list that changes the layout (empty, no results, notice, open panel). Say which and why.
- [ ] Step 3: Layout table. One row per region, in the flows' priority order: placement at each breakpoint (column, order, width in layout tokens or `fill`), the component used (library component name and variant, or a site component from the design system's table), the text style of each text, the colour tokens of fills, strokes and text, the spacing tokens between and inside. Every value is a token name from the design system; a value that is not a token is a finding to send back to `design-system`, not a number to type here.
- [ ] Step 4: Copy. Where a messaging artifact exists, use its text; otherwise `[copy: …]` placeholders that state what the text must achieve. Labels of controls and navigation names come from the flows and the specs.
- [ ] Step 5: States. For each state of the SCREEN: what changes (which regions appear, hide or change tokens), written as a diff against the default.
- [ ] Step 6: Accessibility check against the design system: every text-on-background pair used is in the Contrast table with `pass`, or the pair is added there first; interactive targets meet the target token; focus is visible in every state; reading order equals the priority order.
- [ ] Step 7: Design tool route. Pick one and say why:
  - Compose: a design-tool integration is available and the screen is a composition of the design system's parts (documentation page, dialog, shell, settings). Build the variants of step 2 in the tool from the layout table, following the tool's own guidance for composing screens: one wrapper frame per variant on the agreed page, sections in order, the file's own component instances with their properties set, fills and spacing bound to the file's variables, text styles applied; one screenshot per variant, targeted fixes, one post-fix screenshot; record the frame ids and the page.
  - Explore: the screen needs a visual direction the parts do not give (a landing, a campaign page, anything the user calls creative), the user asks for exploration in a design tool, or the review of a composed frame says it is structurally right and visually flat. Write `docs/design/briefs/<screen>.md` from the brief template: the product in two paragraphs a stranger can act on; audience, voice, words to use and avoid; what the previous version got wrong and what to take from the references as attitudes, never as layouts; three named directions to explore; identity hooks; every colour, type, space and radius value written out in light and dark, because the tool cannot read the design system; the real markup of the components the demos use; the page structure with the messaging copy verbatim and the motion per section; constraints (values only from the brief, real demos, copy verbatim, contrast, targets, focus, narrow first viewport, reduced motion, no-JavaScript state, fixed shell, buildability); deliverables per round; at least five evaluation criteria a reviewer can check on a screen; how to run the tool; the short prompt to paste. Hand it to the user with the run steps. The results come back for a critique against the criteria; the chosen direction, its frame or file and the review are recorded in the screen document's Design tool section, and the screen document stays the source of truth for tokens.
  - Neither: no integration and no exploration asked; say so; the document is the deliverable.
- [ ] Step 8: Lint: `python3 scripts/lint_screen.py --file docs/design/screens/<screen>.md --flows docs/design/flows.md --design-system docs/design/design-system.md --screen SCREEN-n`. It checks sections, that every region and state of the SCREEN in the flows has a row, that every text style and token named exists in the design system, that no raw colour or pixel value appears outside the Sources, and that copy placeholders are marked. When a brief was written: `python3 scripts/lint_brief.py --file docs/design/briefs/<screen>.md --messaging docs/marketing/messaging.md`. It checks sections, that no repository path is referenced where the tool would have to follow it, that the values are written out, that every messaging section and headline is in the brief verbatim, the criteria, the prompt length and leftover placeholders. Fix until both report `ok` true.
- [ ] Step 9: Register `docs/design/screens/<screen>.md` and, when written, `docs/design/briefs/<screen>.md` in `docs/workbench/state.md` (owner `design-ui`, status `draft`) when the state file exists, and report with the template.
- [ ] Step 10: Self-check against "Quality criteria".

## Output template

See [assets/screen-template.md](assets/screen-template.md) and, for the explore route, [assets/brief-template.md](assets/brief-template.md). The report:

```markdown
## Screen: <SCREEN-n name> → docs/design/screens/<screen>.md

- Variants: <list of breakpoint × mode × state frames>
- Regions: <n> placed; components: <n> library instances, <n> site components; copy placeholders: <n>
- Accessibility: <n> pairs checked, <n> targets checked, focus visible in <n> states
- Design tool: <page and frame ids, screenshots reviewed | none available>
- Brief: <docs/design/briefs/<screen>.md for <tool>, round 1 asks for <n> directions | none>
- Findings for design-system: <tokens or components missing, or none>
Next: <design-ui for SCREEN-m | design-handoff for this screen | run the brief and bring the results to core-critique | the questions above>
```

## Quality criteria

Approve the screen only if all of the following hold:

- Every region and state of the SCREEN in the flows appears in the document, in the flows' priority order.
- Every fill, stroke, text colour, spacing, radius and text is a named token or text style of the design system; no raw hex or pixel value appears outside citations.
- Every component is a library component the design system lists, a site component it lists, or a finding sent to `design-system`.
- Copy is either from the messaging artifact or a marked placeholder; no final copy was invented.
- Every text-on-background pair used is in the design system's Contrast table with `pass`.
- When a design tool was used, each variant has a frame id and a reviewed screenshot, and no visible defect remains.
- When a brief was written, a stranger with only the brief can produce the page: every value is written out, the copy is the messaging artifact's verbatim, the directions are named, and the criteria can be checked on a screen.
- `lint_screen.py` reports `ok: true`, and `lint_brief.py` too when a brief exists.

## Gotchas

- The layout table comes before the drawing; a drawing made first hides decisions in pixel positions nobody can review.
- Priority order is reading order: the first region in the flows is the first thing on the screen at every breakpoint.
- Placeholders that read like copy get shipped; write what the text must do, not a plausible sentence.
- A component with the right look but the wrong property model (a library button with no "label" property) is a finding, not a reason to draw a fake button.
- Dark mode is not an inversion; it is the same tokens in the other mode, so a screen built with bound variables costs nothing to switch, and one built with hex values costs the whole screen.
- Building in a design tool is sequential writes with one screenshot per variant; targeted fixes, never a rebuild.
- Composition through an integration gives a correct page, not a memorable one: it cannot invent an illustration, a scale contrast or motion. When the user wants creative, route to explore before building the second variant.
- A brief that names tokens without values is useless outside the repository; the brief carries the values and the screen document carries the names. The two must agree, so the brief is written from the design system, never from memory.
- A brief that asks for "something creative" gets a generic page; name the directions, the drama the hero must have and the criteria the result is judged on.
