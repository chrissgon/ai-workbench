# Design brief: landing-page

- Owner: design-brief
- Status: approved
- Date: 2026-03-03
- Type: screen
- For: SCREEN-1 (Landing) of docs/design/flows.md
- Values: loaded (the design system "Plinth UI site" in the design tool)

## Summary

Design the landing of the Plinth UI documentation site at 1280 px and 360 px in light mode, with the library's real components.

## Sources

- docs/design/design-system.md, docs/design/flows.md, docs/product/specs/landing.md

## Constraints

- C-1: Only tokens of docs/design/design-system.md: the library's `--pui-*` tokens and the site tokens. `--pui-theme` is the only accent colour.
- C-2: Fonts are Inter and Fira Code, self-hosted. No request to a third-party host.
- C-3: Entrance motion at most 600 ms, opacity and transform only, none under reduced motion.
- C-4: Components are the library's markup (class prefix `pui`), never redrawn.

## Deliverables

- Widths: 1280 px and 360 px. Mode: light. Dark mode and 768 px are not part of this round.
- One HTML export per direction.

## Criteria

- CRIT-1: Value proposition, install command and primary call to action are inside the first viewport at 360 px.
- CRIT-2: Every colour is a token of the design system.
- CRIT-3: The showcase shows at least 4 live examples (landing spec REQ-5).
