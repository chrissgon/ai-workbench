# UX flows: perfectui documentation site, phase P-1

- Owner: design-ux-flows
- Status: draft
- Date: 2026-09-23
- PRD: docs/product/prd.md
- Phase covered: P-1 (release R-1, the 1.0 launch); the version switch of P-2 is included where it shapes the information architecture

## Summary

Nineteen nodes, six screens and seven flows. At the 1.0 launch an evaluator lands, understands the library, reads its measured size, copies the install command and reads a component page with live examples; a migrating user reaches the migration guide in one click; every reader searches the version being read and switches mode and theme colour. Copy, colours and layout are not decided here.

## Sources

- `docs/product/prd.md` (2026-09-23): U-1 to U-3, F-1 to F-12, P-1, constraints
- `docs/product/roadmap.md`: R-1 order (content model, then shell, landing, guide, search)
- `docs/product/specs/markdown-content-model.md`: REQ-1 (URLs), REQ-2 (frontmatter), REQ-4 (navigation from folders), REQ-6 (switch fallback), REQ-7 (badges), EDGE-1
- `docs/product/specs/landing-and-site-shell.md`: REQ-1 to REQ-10, NFR-3, EDGE-1 to EDGE-9
- `docs/product/specs/search.md`: REQ-1 to REQ-8, EDGE-1 to EDGE-8
- `docs/product/specs/migration-guide.md`: REQ-1 to REQ-6, EDGE-1 to EDGE-5
- Library `docs/README.md` in the perfectui repository (accessed 2026-09-23): sections Getting Started (Installation, Typescript, Tailwind CSS, Migrating from 0.x, License), Customization (Dark Mode, Theme Color), General (Layout Group, Float), Components (Accordion, Badge, Button, Card, Chip, Dropdown, List, Modal, Table, Timeline, Tooltip), Forms (Field Group, Input, Input Group, Textarea, Select, Checkbox, Radio, Switch)
- `docs/engineering/architecture.md` (codebase map of the 0.23 site): landing, docs layout with sidebar navigation, search dialog opened with `/`, mode and theme controls in the header, 32 pages
- `docs/workbench/state.md` decisions of 2026-09-23: v1 content from the library's docs plus the site's own sections; landing texts from the messaging step; no brand phase; Figma link kept

## Information architecture

- IA-1: Landing. Parent: none. URL: `/`. Filled by: static page. Source: PRD F-3; landing spec REQ-1.
- IA-2: Documentation, latest version. Parent: none. URL: `/docs/v1` (index) and `/docs/v1/<section>/<slug>`; `/docs` and `/docs/<section>/<slug>` redirect here. Filled by: content folder `content/v1/`, sections from numeric-prefixed folders. Source: content-model spec REQ-1, REQ-4; state decision (final URL scheme, 2026-09-23).
- IA-3: Getting started. Parent: IA-2. URL: `/docs/v1/getting-started/<slug>`. Filled by: content pages installation, typescript, tailwind-css, migrating-from-0-23, license. Source: library `docs/README.md` (Getting Started); migration-guide spec REQ-1, OPEN-2.
- IA-4: Customization. Parent: IA-2. URL: `/docs/v1/customization/<slug>`. Filled by: content pages dark-mode, theme-color. Source: library `docs/README.md` (Customization).
- IA-5: General. Parent: IA-2. URL: `/docs/v1/general/<slug>`. Filled by: content pages layout-group, float. Source: library `docs/README.md` (General).
- IA-6: Components. Parent: IA-2. URL: `/docs/v1/components/<slug>`. Filled by: content pages accordion, badge, button, card, chip, dropdown, list, modal, table, timeline, tooltip. Source: library `docs/README.md` (Components); PRD M-1.
- IA-7: Forms. Parent: IA-2. URL: `/docs/v1/forms/<slug>`. Filled by: content pages field-group, input, input-group, textarea, select, checkbox, radio, switch. Source: library `docs/README.md` (Forms).
- IA-8: Site-specific sections. Parent: IA-2. URL: decided per page. Filled by: content pages the site adds beyond the library's docs (for example a page recommending Tailwind for utilities); the list is content work. Source: user answer 2026-09-23 (not limited to the library's files); ASSUMPTION-1.
- IA-9: Documentation index of a version. Parent: IA-2. URL: `/docs/<major>` for every version (`/docs` redirects to the current major's). Filled by: generated from the version's navigation tree, as its own page; also the landing target of a failed version switch. Source: content-model spec REQ-6, EDGE-1; user answer 2026-09-23 (own page).
- IA-10: Search. Parent: none (an overlay on every page). URL: none (dialog state; deep link to result anchors). Filled by: the index generated at build time for the version being read. Source: search spec REQ-1, REQ-4, REQ-6.
- IA-11: Version switch control. Parent: none (in the shell). URL: none. Filled by: the versions configuration. Source: content-model spec REQ-5; PRD F-6 (built in P-2; its slot in the shell is reserved in P-1).
- IA-12: Documentation, version v0 (P-2). Parent: none. URL: `/docs/v0` and `/docs/v0/<section>/<slug>`. Filled by: content folder `content/v0/` converted from the 32 pages on branch `main`. Source: PRD F-7; content-model spec REQ-1, REQ-11.
- IA-13: Mode and theme controls. Parent: none (in the shell). URL: none. Filled by: the library's `setMode` and the `--pui-theme` variable. Source: landing spec REQ-7 to REQ-9.
- IA-14: Repository, Figma and license links. Parent: none (shell header and footer). URL: external. Filled by: static links. Source: landing spec REQ-7; state decision (Figma link kept).
- IA-15: Install command. Parent: IA-1. URL: none. Filled by: the package name from configuration. Source: landing spec REQ-3.
- IA-16: Size block. Parent: IA-1. URL: none. Filled by: the build-time gzip measurement. Source: landing spec REQ-2.
- IA-17: Components showcase. Parent: IA-1. URL: none. Filled by: example blocks reused from documentation pages. Source: landing spec REQ-5.
- IA-18: Migration call to action. Parent: IA-1. URL: links to the migration guide page. Filled by: static. Source: landing spec REQ-4.
- IA-19: Page not found. Parent: none. URL: any unknown path. Filled by: static page. Source: ASSUMPTION-2 (a static host serves a 404 page; the PRD does not name it).

## Screens

- SCREEN-1: Landing. Purpose: let an evaluator understand perfectui, trust its size, install it and enter the documentation in one screen. Regions: value proposition (sentence and paragraph, texts from the messaging step), install command with copy control, primary call to action to `/docs`, size block with version and method, components showcase (at least 4 live examples), migration call to action, further sections from the messaging step, footer. States: default; copied (copy control feedback for at least 1 second); no JavaScript (copy control, mode and theme controls absent or inert); reduced motion (no animation). Breakpoints: on a 360 px wide screen the value proposition, the install command and the primary call to action stay inside the first viewport and the showcase stacks in one column. Source: landing spec REQ-1 to REQ-6, NFR-3, EDGE-1 to EDGE-3; PRD F-3; state decision (messaging step).
- SCREEN-2: Documentation page. Purpose: read one page of one version with its examples and move to any other page of that version. Regions: page header (title, description, since or changed badge), content with example blocks (preview tab, code tab, copy), sidebar navigation of the version (sections in prefix order, current page marked), on-page headings list, previous and next page links. States: default; page with badges; page without headings (no on-page list); narrow (sidebar collapsed behind a control). Breakpoints: below the tablet width the sidebar becomes a toggleable panel and the on-page headings list collapses into the content. Source: content-model spec REQ-1 to REQ-4, REQ-7; PRD F-1, F-2, F-12; codebase map (docs layout with sidebar as baseline).
- SCREEN-3: Site shell. Purpose: give every page the same header and footer with navigation, version label, external links, mode toggle, theme picker and the search entry point. Regions: header (logo with latest version label, docs link, search entry point, version switch slot, mode toggle, theme picker, GitHub and Figma links), footer (license, repository link). States: default; light and dark (from `data-pui-mode`); theme colour applied; search entry point absent when the build has no search. Breakpoints: below the tablet width the header keeps logo, search and mode toggle visible and moves the rest behind a menu control. Source: landing spec REQ-6 to REQ-9; search spec REQ-1; content-model spec REQ-5; state decision (Figma link kept).
- SCREEN-4: Search dialog. Purpose: find a page or section of the version being read as the reader types. Regions: input (focused on open), results list (page title, section heading, highlighted snippet, selected item marked), footer with the keyboard hints, close control. States: empty (input only); results; no results ("No results for <query>"); unavailable (index failed to load, with retry); loading the index on first open. Breakpoints: full-screen on narrow screens; centered dialog otherwise. Source: search spec REQ-1 to REQ-3, REQ-7, REQ-8, EDGE-2, EDGE-3.
- SCREEN-5: Version index with switch notice. Purpose: land a reader who switched to a version where the current page does not exist, and serve as each version's index. Regions: notice naming the page and the version in which it does not exist (only after a failed switch), version title and older-version mark when not latest, list of sections and pages of the version. States: index without notice; index with notice. Breakpoints: single column on narrow screens. Source: content-model spec REQ-6, EDGE-1; PRD F-6, F-7 (P-2; designed with P-1 so the shell reserves its slot).
- SCREEN-6: Migration guide page. Purpose: let a 0.23 user follow the migration inside the site. Regions: page header with the version range ("applies to 0.23.0 → <installed version>"), section list of the guide (Why, 1 to 8, Known trade-offs) as an on-page index, content with mapping tables and diff blocks, sidebar navigation. States: default; tables scrolling inside their box on narrow screens; 0.23 names as links (v0 present) or plain text (v0 absent). Breakpoints: same as SCREEN-2; tables scroll horizontally inside their box at 360 px. Source: migration-guide spec REQ-2 to REQ-5, NFR-1, EDGE-1, EDGE-2, EDGE-5.

## Flows

- FLOW-1: Evaluate and install. Actor: U-1. Trigger: the evaluator opens `/` from a search engine or a link. Steps: 1. on SCREEN-1: read the value proposition → knows what perfectui is; 2. on SCREEN-1: read the size block → sees the gzip numbers, the version and the method; 3. on SCREEN-1: scroll the showcase → sees at least 4 live components; 4. on SCREEN-1: activate the copy control → the command is in the clipboard and the control reads "copied"; 5. on SCREEN-1: activate the primary call to action → SCREEN-2 opens at the documentation index or first page. End: the evaluator is on a documentation page with the install command copied. Failures: step 4 without clipboard access (EDGE-9 of the landing spec): the command is shown selected for manual copy; step 4 without JavaScript: the control is absent and the command is still readable. Keyboard: Tab to the copy control, Enter; Tab to the primary call to action, Enter. Source: PRD F-3, U-1; landing spec REQ-1 to REQ-5, EDGE-9.
- FLOW-2: Read a component page and use an example. Actor: U-1. Trigger: the reader is on SCREEN-2 or arrives at a page URL. Steps: 1. on SCREEN-2: pick a page in the sidebar → the page opens, the sidebar marks it; 2. on SCREEN-2: read the header → sees the title, description and an "Added in" or "Changed in" badge when present; 3. on SCREEN-2: switch an example block to its code tab → the highlighted snippet is shown; 4. on SCREEN-2: copy the snippet → clipboard holds the example; 5. on SCREEN-2: use the on-page headings list → the page scrolls to the section. End: the reader has the snippet and knows where the section is. Failures: step 1 on a narrow screen: the sidebar is behind a control that must be opened first; step 4 without clipboard access: the code is shown selected. Keyboard: Tab through the sidebar links, Enter; Tab to the example tabs, Arrow keys switch tabs, Tab to copy, Enter. Source: PRD F-1, F-2, F-12; content-model spec REQ-3, REQ-4, REQ-7.
- FLOW-3: Search the version being read. Actor: U-1. Trigger: the reader presses `/` outside a text field or activates the search entry point on SCREEN-3. Steps: 1. on SCREEN-3: activate search → SCREEN-4 opens with the input focused, the index loads on first open; 2. on SCREEN-4: type `moda` → results appear as typed, restricted to the version being read; 3. on SCREEN-4: move the selection → the selected result is marked and announced; 4. on SCREEN-4: activate a result → SCREEN-2 opens scrolled to the matching section. End: the reader is on the matching section. Failures: step 2 with no match: "No results for <query>"; step 1 when the index fails to load: "Search is unavailable" with retry; step 1 without JavaScript: no entry point, the sidebar remains the way to find pages. Keyboard: `/`, type, ArrowDown, Enter; Escape closes and returns focus to the entry point. Source: PRD F-5; search spec REQ-1 to REQ-4, REQ-7, REQ-8, EDGE-1, EDGE-2.
- FLOW-4: Migrate from 0.23. Actor: U-2. Trigger: a 0.23 user opens `/` or a documentation page. Steps: 1. on SCREEN-1: activate the migration call to action → SCREEN-6 opens; 2. on SCREEN-6: read the version range in the header → knows which versions the guide covers; 3. on SCREEN-6: use the section index → jumps to "4. Components"; 4. on SCREEN-6: read the mapping table → finds the 1.0 class for a 0.23 class; 5. on SCREEN-6: follow a 0.23 name link (when v0 exists) → the v0 page opens on SCREEN-2 under `/docs/v0/`. End: the user knows the replacement and, in P-2, can read the old page. Failures: step 5 in P-1 (no v0): the name is plain text, no dead link; step 4 on a narrow screen: the table scrolls inside its box. Keyboard: Tab to the migration call to action, Enter; Tab through the section index, Enter; Tab to a table link, Enter. Source: PRD F-4, U-2; migration-guide spec REQ-2 to REQ-6, EDGE-1, EDGE-2, EDGE-5; landing spec REQ-4.
- FLOW-5: Switch version (P-2, shapes the P-1 shell). Actor: U-2. Trigger: the reader opens the version switch control on SCREEN-3. Steps: 1. on SCREEN-3: choose v0 → if the same path exists in v0, SCREEN-2 opens at `/docs/v0/<same path>`; 2. on SCREEN-2: read the older-version mark → knows this is 0.23; 3. on SCREEN-3: choose the latest → SCREEN-2 opens at `/docs/v1/<same path>`. End: the reader is on the same page in the chosen version. Failures: step 1 when the page does not exist in v0: SCREEN-5 opens with the notice naming the page and the version; step 1 with the search dialog open: results re-filter to the new version. Keyboard: Tab to the switch control, Enter, ArrowDown to a version, Enter. Source: PRD F-6, F-7; content-model spec REQ-6, EDGE-1; search spec EDGE-5.
- FLOW-6: Change mode and theme colour. Actor: U-1. Trigger: the reader activates the mode toggle or the theme picker on SCREEN-3. Steps: 1. on SCREEN-3: activate the mode toggle → `data-pui-mode` changes and every component and example follows; 2. on SCREEN-3: pick a colour in the theme picker → `--pui-theme` changes and every component and example follows without reload; 3. on SCREEN-2: reload → the mode persists (cookie) and the colour persists for the session. End: the site shows the chosen mode and colour. Failures: no stored mode: the site follows the operating system; step 2 with a low-contrast colour: applied anyway, the site's own text is unaffected. Keyboard: Tab to the toggle, Enter; Tab to the picker, Enter opens the native colour input. Source: PRD F-8; landing spec REQ-8, REQ-9, EDGE-4 to EDGE-6.
- FLOW-7: Arrive at a missing or moved page. Actor: U-1. Trigger: the reader opens an unknown URL. Steps: 1. on SCREEN-5: read the not-found message → sees the link to the latest index and the search entry point; 2. on SCREEN-3: search or navigate → SCREEN-2 opens. End: the reader reaches a page of the latest version. Failures: none beyond the not-found state itself. Keyboard: Tab to the index link, Enter. Source: ASSUMPTION-2; content-model spec REQ-1.

## Coverage

- F-1: FLOW-2, SCREEN-2
- F-2: FLOW-2, SCREEN-2
- F-3: FLOW-1, SCREEN-1
- F-4: FLOW-4, SCREEN-6
- F-5: FLOW-3, SCREEN-4
- F-8: FLOW-6, SCREEN-3
- F-9: no screen: page metadata is produced by the build (landing spec REQ-10), not shown in a screen
- F-10: no screen: authoring happens in the repository (content-model spec NFR-1), not in the site
- F-12: FLOW-2, SCREEN-2

## Assumptions

- ASSUMPTION-1: The site-specific sections (IA-8) are placed by the content work, inside the existing sections when they fit (a Tailwind recommendation under Getting started) and as a new section otherwise. Safe because: the user asked for them without fixing their place, and the navigation is derived from folders, so moving a page costs nothing.
- ASSUMPTION-2: A not-found page (IA-19, SCREEN-5's not-found state) exists because the static host serves one for unknown paths. Safe because: every static host does, and the PRD's fully prerendered constraint implies a static 404; its content is decided in design-ui.
- ASSUMPTION-3: The version switch control (IA-11) is designed in P-1 with the shell so that P-2 does not change the header, even though F-6 ships in R-2. Safe because: the roadmap orders F-6 right after R-1 and the control's slot costs nothing while it shows one version.

## Open questions

- OPEN-1 (resolved 2026-09-23): the version index is its own page at `/docs/<major>`, and every version is served under its own segment with unversioned paths redirecting to the current major (user). Blocks: nothing. Recommended: as decided.
- OPEN-2 (resolved 2026-09-23): the search entry point is an icon in the header on narrow screens (user). Blocks: nothing. Recommended: as decided.

## Readiness

- Ready for design-system and design-ui: yes: SCREEN-3 (shell) first, because every other screen embeds it; then SCREEN-2, then SCREEN-1 after the messaging step; no open question remains.
