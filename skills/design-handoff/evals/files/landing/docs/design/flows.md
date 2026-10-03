# UX flows: Plinth UI documentation site

- Owner: design-ux-flows
- Status: approved
- Date: 2026-03-02
- PRD: docs/product/prd.md

## Summary

Two screens and one flow for the launch: an evaluator lands, understands the library, reads its measured size, copies the install command and enters the documentation.

## Sources

- docs/product/specs/landing.md: REQ-1 to REQ-7

## Screens

- SCREEN-1: Landing. Purpose: let an evaluator understand Plinth UI, trust its size, install it and enter the documentation in one screen. Regions: value proposition (headline and one paragraph), install command with copy control, primary call to action to `/docs`, size block with version and method, components showcase (at least 4 live examples), footer. States: default; copied (copy control feedback for at least 1 second); no JavaScript (copy control absent, command still readable); reduced motion (no animation, everything visible at once). Breakpoints: on a 360 px wide screen the value proposition, the install command and the primary call to action stay inside the first viewport and the showcase stacks in one column; from 768 px the showcase has two columns; from 1280 px it has four. Source: landing spec REQ-1 to REQ-7.
- SCREEN-2: Site shell. Purpose: give every page the same header and footer. Regions: header (logo with version label, docs link, mode toggle, repository link), footer (license, repository link). States: default; light and dark (from `data-ui-mode`). Breakpoints: below 768 px the header keeps the logo and the mode toggle and moves the rest behind a menu control. Source: landing spec REQ-7.

## Flows

- FLOW-1: Evaluate and install. Actor: an evaluator. Trigger: opens `/`. Steps: 1. on SCREEN-1: read the value proposition; 2. on SCREEN-1: read the size block; 3. on SCREEN-1: activate the copy control → the command is in the clipboard and the control reads "Copied"; 4. on SCREEN-1: activate the primary call to action → the documentation opens. End: the evaluator is in the documentation with the install command copied. Keyboard: Tab to the copy control, Enter; Tab to the primary call to action, Enter. Source: landing spec REQ-1 to REQ-5.

## Open questions

- none
