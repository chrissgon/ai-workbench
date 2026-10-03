# UX flows: plinthui documentation site, phase P-1

- Owner: design-ux-flows
- Status: approved
- Date: 2026-09-23
- PRD: docs/product/prd.md
- Phase covered: P-1 (release R-1, the 1.0 launch)

## Summary

Eight nodes, three screens and two flows. At the 1.0 launch an evaluator lands, understands the library, reads its measured size, copies the install command and reads a component page with live examples; every reader switches mode and theme colour. Copy, colours and layout are not decided here.

## Sources

- `docs/product/prd.md` (2026-09-23): U-1 to U-3, F-1 to F-12, P-1, constraints
- `docs/product/specs/markdown-content-model.md`: REQ-1 (URLs), REQ-2 (frontmatter), REQ-4 (navigation from folders), REQ-7 (badges)
- `docs/product/specs/landing-and-site-shell.md`: REQ-1 to REQ-10, NFR-3, EDGE-1 to EDGE-9
- Library `docs/README.md` in the plinthui repository (accessed 2026-09-23): the sections and page titles of the documentation
- `docs/workbench/state.md` decisions of 2026-09-23: v1 content from the library's docs; landing texts from the messaging step; no brand phase; design-file link kept

## Information architecture

- IA-1: Landing. Parent: none. URL: `/`. Filled by: static page. Source: PRD F-3; landing spec REQ-1.
- IA-2: Documentation, latest version. Parent: none. URL: `/docs/v1` (index) and `/docs/v1/<section>/<slug>`. Filled by: content folder `content/v1/`, sections from numeric-prefixed folders. Source: content-model spec REQ-1, REQ-4.
- IA-3: Getting started. Parent: IA-2. URL: `/docs/v1/getting-started/<slug>`. Filled by: the pages "Installation", "TypeScript", "Tailwind CSS", "Migrating from 0.19", "License". Source: library `docs/README.md` (Getting Started).
- IA-4: Customization. Parent: IA-2. URL: `/docs/v1/customization/<slug>`. Filled by: the pages "Dark mode", "Theme colour". Source: library `docs/README.md` (Customization).
- IA-5: General. Parent: IA-2. URL: `/docs/v1/general/<slug>`. Filled by: the pages "Layout group", "Float". Source: library `docs/README.md` (General).
- IA-6: Components. Parent: IA-2. URL: `/docs/v1/components/<slug>`. Filled by: the pages "Accordion", "Badge", "Button", "Card", "Chip", "Dropdown", "List", "Modal", "Table", "Timeline", "Tooltip". Source: library `docs/README.md` (Components); PRD M-1.
- IA-7: Forms. Parent: IA-2. URL: `/docs/v1/forms/<slug>`. Filled by: the pages "Field group", "Input", "Input group", "Textarea", "Select", "Checkbox", "Radio", "Switch". Source: library `docs/README.md` (Forms).
- IA-8: Mode and theme controls. Parent: none (in the shell). URL: none. Filled by: the library's `setMode` and the `--plu-theme` variable. Source: landing spec REQ-7 to REQ-9.

## Screens

- SCREEN-1: Landing. Purpose: let an evaluator understand plinthui, trust its size, install it and enter the documentation in one screen. Regions: value proposition (sentence and paragraph, texts from the messaging step), install command with copy control, primary call to action to `/docs`, size block with version and method, components showcase (at least 4 live examples), migration call to action, footer. States: default; copied (copy control feedback for at least 1 second); no JavaScript (copy control, mode and theme controls absent or inert); reduced motion (no animation). Breakpoints: on a 360 px wide screen the value proposition, the install command and the primary call to action stay inside the first viewport and the showcase stacks in one column. Source: landing spec REQ-1 to REQ-6, NFR-3, EDGE-1 to EDGE-3; PRD F-3; state decision (messaging step).
- SCREEN-2: Documentation page. Purpose: read one page of one version with its examples and move to any other page of that version. Regions: page header (title, description, since or changed badge), content with example blocks (preview tab, code tab, copy), sidebar navigation of the version (sections in prefix order, current page marked), on-page headings list, previous and next page links. States: default; page with badges; page without headings (no on-page list); narrow (sidebar collapsed behind a control). Breakpoints: below the tablet width the sidebar becomes a toggleable panel and the on-page headings list collapses into the content. Source: content-model spec REQ-1 to REQ-4, REQ-7; PRD F-1, F-2, F-12.
- SCREEN-3: Site shell. Purpose: give every page the same header and footer with navigation, version label, external links, mode toggle, theme picker and the search entry point. Regions: header (logo with latest version label, docs link, search entry point, mode toggle, theme picker, repository and design-file links), footer (license, repository link). States: default; light and dark (from `data-plu-mode`); theme colour applied; search entry point absent when the build has no search. Breakpoints: below the tablet width the header keeps logo, search and mode toggle visible and moves the rest behind a menu control. Source: landing spec REQ-6 to REQ-9; state decision (design-file link kept).

## Flows

- FLOW-1: Evaluate and install. Actor: U-1. Trigger: the evaluator opens `/` from a search engine or a link. Steps: 1. on SCREEN-1: read the value proposition → knows what plinthui is; 2. on SCREEN-1: read the size block → sees the gzip numbers, the version and the method; 3. on SCREEN-1: activate the copy control → the command is in the clipboard and the control reads "copied"; 4. on SCREEN-1: activate the primary call to action → SCREEN-2 opens at the documentation index or first page. End: the evaluator is on a documentation page with the install command copied. Failures: step 3 without clipboard access: the command is shown selected for manual copy. Keyboard: Tab to the copy control, Enter; Tab to the primary call to action, Enter. Source: PRD F-3, U-1; landing spec REQ-1 to REQ-5, EDGE-9.
- FLOW-2: Read a component page and use an example. Actor: U-1. Trigger: the reader is on SCREEN-2 or arrives at a page URL. Steps: 1. on SCREEN-2: pick a page in the sidebar → the page opens, the sidebar marks it; 2. on SCREEN-2: read the header → sees the title, description and an "Added in" or "Changed in" badge when present; 3. on SCREEN-2: switch an example block to its code tab → the highlighted snippet is shown; 4. on SCREEN-2: copy the snippet → clipboard holds the example; 5. on SCREEN-2: use the on-page headings list → the page scrolls to the section. End: the reader has the snippet and knows where the section is. Failures: step 1 on a narrow screen: the sidebar is behind a control that must be opened first; step 4 without clipboard access: the code is shown selected. Keyboard: Tab through the sidebar links, Enter; Tab to the example tabs, Arrow keys switch tabs, Tab to copy, Enter. Source: PRD F-1, F-2, F-12; content-model spec REQ-3, REQ-4, REQ-7.

## Coverage

- F-1: FLOW-2, SCREEN-2
- F-2: FLOW-2, SCREEN-2
- F-3: FLOW-1, SCREEN-1
- F-8: SCREEN-3
- F-12: FLOW-2, SCREEN-2

## Open questions

- none

## Readiness

- Ready for design-system and design-brief: yes: SCREEN-3 (shell) first, because every other screen embeds it; then SCREEN-2, then SCREEN-1 after the messaging step.
