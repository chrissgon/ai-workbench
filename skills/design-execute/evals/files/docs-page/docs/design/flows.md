# UX flows: Marlow documentation site, phase P-1

- Owner: design-ux-flows
- Status: approved
- Date: 2026-09-14
- PRD: docs/product/prd.md
- Phase covered: P-1

## Summary

Three nodes, two screens and one flow. A developer lands, opens the guide and reads one page with its code samples. Copy, colours and layout are not decided here.

## Sources

- docs/product/prd.md (2026-09-10): U-1, F-1 to F-3

## Information architecture

- IA-1: Landing. Parent: none. URL: `/`. Filled by: static page. Source: PRD F-1.
- IA-2: Guide. Parent: none. URL: `/guide/<slug>`. Filled by: content pages getting-started, defining-jobs, retries-and-backoff, scheduling, monitoring. Source: PRD F-2.
- IA-3: Reference. Parent: none. URL: `/reference/<slug>`. Filled by: content pages queue-options, job-options, command-line. Source: PRD F-3.

## Screens

- SCREEN-1: Landing. Purpose: let a developer understand Marlow and enter the guide. Regions: value proposition, install command with copy control, link to the guide, footer. States: default; copied (copy control feedback). Breakpoints: single column on a 360 px wide screen. Source: PRD F-1.
- SCREEN-2: Documentation page. Purpose: read one page of the guide or the reference with its code samples and move to any other page. Regions: site header (logo, guide link, reference link, repository link), sidebar navigation (sections Guide and Reference, current page marked), page header (title and description), content with code blocks (copy control), on-page headings list, previous and next page links. States: default; copied (copy control feedback for 2 seconds); narrow (sidebar behind a menu control). Breakpoints: below 900 px the sidebar becomes a panel behind a menu control and the on-page headings list is hidden. Source: PRD F-2, F-3.

## Flows

- FLOW-1: Read a guide page and copy a sample. Actor: U-1. Trigger: the developer opens a guide page from the landing or a search engine. Steps: 1. on SCREEN-2: read the page header → knows what the page covers; 2. on SCREEN-2: activate the copy control of a code block → the sample is in the clipboard and the control reads "Copied"; 3. on SCREEN-2: activate the next page link → the next page opens. End: the developer has the sample and is on the next page. Failures: step 2 without clipboard access: the code is shown selected. Keyboard: Tab to the copy control, Enter; Tab to the next page link, Enter. Source: PRD F-2.
