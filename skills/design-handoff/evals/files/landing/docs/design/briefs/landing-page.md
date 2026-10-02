# Design brief: landing-page

- Owner: design-brief
- Status: approved
- Date: 2026-03-03
- Type: screen
- For: SCREEN-1 (Landing) of docs/design/flows.md
- Values: loaded: the design system "Plinth UI site" in the design tool
- Direction: open: three directions
- Lint: ok (2026-03-03)

## Summary

Design the landing of the Plinth UI documentation site at 1280 px and 360 px in light mode, with the library's real components. The texts, the tokens and the regions are fixed; the composition and the treatment of the size claim are open.

## Sources

- docs/design/design-system.md (tokens, type, components, 2026-03-02)
- docs/design/flows.md (SCREEN-1 regions, states, breakpoints, 2026-03-02)
- docs/product/specs/landing.md (REQ-1 to REQ-7, 2026-03-01)

## Subject

Plinth UI is a CSS component library: buttons, cards, inputs and badges as plain classes, with no runtime dependency. Its documentation site has a landing page, a guide and one page per component.

The landing is where an evaluator decides whether to install it. Example: a developer comparing three libraries opens the landing, reads the measured size, copies the install command and opens the docs.

## Audience and voice

- Front-end developers who evaluate a component library for a new project; they fear a heavy dependency that is hard to remove.
- Voice: plain statements with a number; no superlatives; sentence case; no exclamation marks.
- Words to use: components, classes, bytes, measured. Words to avoid: blazing, lightweight, modern.

## Creative direction

No previous version.

- Direction A, "Stacked": the sections are stacked bands of the muted background; the size block is the widest band.
- Direction B, "Quiet proof": a plain page; the measured size sits next to the headline as the only large number, and the showcase does the rest.
- Direction C, "Specimen": the showcase leads, as a grid of live components; the value proposition is a caption above it.

Every direction keeps the library's components, `--plu-theme` as the only accent and the two typefaces. Not allowed: gradients, shadows, photographs, a second accent colour, any text not in the content source.

## Visual language

The design system is loaded in the tool; the values the directions depend on are restated here: the brand colour `--plu-theme` #0092CD (dark #07B6F0), the page background `--plu-bg` #FFFFFF, the text `--plu-text` #000000, the display size 48 px with weight 600, the section gap 96 px. Inter for text and Fira Code for code, both self-hosted.

## Content

- Regions, in priority order: value proposition (headline and one paragraph, from the landing content file); install command with copy control; primary call to action to the docs; size block with version and method; components showcase (at least 4 live examples); footer.
- States: default; copied (the control reads "Copied" for at least 1 second); no JavaScript (copy control absent, command still readable); reduced motion (no animation, everything visible at once).
- Breakpoints: at 360 px the value proposition, the install command and the primary call to action stay inside the first viewport and the showcase stacks in one column; from 768 px two columns; from 1280 px four.
- Motion: one entrance animation at most, opacity and transform only, at most 600 ms; none under reduced motion.

## Constraints

- C-1: Only tokens of the design system: the library's `--plu-*` tokens and the site tokens. `--plu-theme` is the only accent colour.
- C-2: Fonts are Inter and Fira Code, self-hosted. No request to a third-party host.
- C-3: Entrance motion at most 600 ms, opacity and transform only, none under reduced motion.
- C-4: Components are the library's markup (class prefix `plu`), never redrawn.

## Deliverables

- Round 1: one HTML export per direction at 1280 px and 360 px, light mode. Dark mode and 768 px are not part of this round.
- Round 2: the chosen direction at the same widths.

## Evaluation criteria

- CRIT-1: Value proposition, install command and primary call to action are inside the first viewport at 360 px.
- CRIT-2: Every colour is a token of the design system.
- CRIT-3: The showcase shows at least 4 live examples (landing spec REQ-5).
- CRIT-4: The texts are the content source's, verbatim; no other text appears.
- CRIT-5: The size claim is the visual focus of the first viewport, without a second accent colour.

## Attachments

- Send: this brief; library/logo.svg
- Do not send in round 1: any earlier landing design

## Prompt

```text
This is an exploration of the landing page of Plinth UI, a CSS component library with no runtime
dependency. A failure looks like a generic SaaS page: gradients, stock shapes, invented copy.

Use the design system "Plinth UI site" loaded in this project: only its tokens and its components,
--plu-theme (#0092CD) as the only accent. Inter for text, Fira Code for code, self-hosted: no font
request to another host. Entrance motion at most 600 ms, opacity and transform only, none with
reduced motion.

Regions, in order: value proposition, install command with a copy control, primary call to action to
/docs, size block with version and method, at least 4 live component examples, footer.
Widths: 1280 px and 360 px, light mode. At 360 px the first three regions fit in the first viewport.

Direction:

Deliver one HTML export. Then list what this result does that a plain version would not.
```

## Open questions

- none

## Readiness

- Ready for design-execute: yes
