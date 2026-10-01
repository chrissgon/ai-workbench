# UX flows: plinthui documentation site, phase P-1

- Owner: design-ux-flows
- Status: draft
- Date: 2026-03-02
- PRD: docs/product/prd.md
- Phase covered: P-1 (release R-1, the 1.0 launch)

## Summary

Six nodes, five screens and three flows. At the 1.0 launch an evaluator lands, understands the library, copies the install command and reads a component page with live examples; a migrating user reaches the migration guide in one click; every reader searches the documentation and switches between light and dark mode. Copy, colours and layout are not decided here.

## Sources

- `docs/product/prd.md` (2026-02-24): U-1 and U-2, F-1 to F-6, P-1
- User answer, 2026-03-02: the site uses the plinthui library for every control the library has

## Information architecture

- IA-1: Landing. Parent: none. URL: `/`. Filled by: static. Source: F-1
- IA-2: Guide. Parent: none. URL: `/guide/<page>`. Filled by: content folder. Source: F-2
- IA-3: Components. Parent: none. URL: `/components/<name>`. Filled by: content folder. Source: F-3
- IA-4: Migration guide. Parent: IA-2. URL: `/guide/migration`. Filled by: content folder. Source: F-4
- IA-5: Search. Parent: none. URL: none (a dialog over any page). Filled by: generated. Source: F-5
- IA-6: Not found. Parent: none. URL: any unknown path. Filled by: static. Source: F-6

## Screens

- SCREEN-1: Landing. Purpose: say what the library is and get the install command copied. Regions: header (logo, navigation links, search trigger, mode switch), hero (headline, install command with copy control, two actions), feature cards, footer. States: default, install command copied. Breakpoints: navigation links collapse into a menu button below 768px. Source: F-1
- SCREEN-2: Guide page. Purpose: read one page of prose with code. Regions: header, sidebar navigation (two levels, current item), article (headings with links, prose, code blocks with copy control, callouts, tables), on-page contents, previous and next links, footer. States: default, code copied. Breakpoints: the sidebar becomes a drawer below 1024px; the on-page contents hide below 1280px. Source: F-2, F-4
- SCREEN-3: Component page. Purpose: see a component's examples and copy their code. Regions: header, sidebar navigation, article (title with a status badge, example blocks with preview and code tabs, a properties table), on-page contents, footer. States: default, code tab selected, code copied. Breakpoints: as SCREEN-2; the properties table scrolls sideways. Source: F-3
- SCREEN-4: Search dialog. Purpose: find a page from anywhere. Regions: search input, result list (title, section, excerpt), keyboard hints. States: closed, open and empty query, loading, results, no results, error. Breakpoints: full screen below 768px. Source: F-5
- SCREEN-5: Not found. Purpose: recover from an unknown address. Regions: header, message, a link to the landing, search trigger, footer. States: default. Breakpoints: none. Source: F-6

## Flows

- FLOW-1: Evaluate and install. Actor: U-1. Trigger: arrives at `/`. Steps: 1. on SCREEN-1: reads the hero, activates the copy control → the command is copied and the control says so; 2. on SCREEN-1: activates "Components" → SCREEN-3; 3. on SCREEN-3: selects the code tab of an example, copies it. End: the install command and one example are on the clipboard. Failures: step 1: the clipboard is refused, the command stays selectable. Keyboard: Tab to the copy control, Enter. Source: F-1, F-3
- FLOW-2: Migrate. Actor: U-2. Trigger: arrives at `/` from the release notes. Steps: 1. on SCREEN-1: activates "Migration guide" in the header → SCREEN-2 at `/guide/migration`; 2. on SCREEN-2: reads, copies code blocks. End: the guide is open at the first breaking change. Failures: none. Keyboard: Tab, Enter. Source: F-4
- FLOW-3: Search. Actor: U-1, U-2. Trigger: activates the search trigger or presses `/`. Steps: 1. on SCREEN-4: types a query → results; 2. on SCREEN-4: chooses a result → SCREEN-2 or SCREEN-3. End: the chosen page is open. Failures: step 1: the index fails to load, SCREEN-4 shows the error state with a retry. Keyboard: `/` opens, arrows move, Enter opens, Escape closes. Source: F-5

## Coverage

- F-1: FLOW-1, SCREEN-1
- F-2: SCREEN-2
- F-3: FLOW-1, SCREEN-3
- F-4: FLOW-2, SCREEN-2
- F-5: FLOW-3, SCREEN-4
- F-6: SCREEN-5

## Assumptions

- none

## Open questions

- none

## Readiness

- Ready for design-system and design-brief: yes: SCREEN-1 first, because FLOW-1 starts there
