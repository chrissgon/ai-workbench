# Feature specification: search

- Owner: product-feature-spec
- Status: approved
- Date: 2026-09-24
- Feature of: docs/product/prd.md, phase P-2 (Plinth UI documentation site, plinthui.example)

## Summary

A visitor of the documentation site finds a page or a heading by typing in a search box, without leaving the page.

## Goal and users

- Problem: visitors look for a component or an option by name and have only the sidebar. Source: brief decision 6
- Users: developers who use Plinth UI. Source: brief
- Success: a visitor reaches the page of a component by typing its name and pressing Enter.

## Scope

- In: a search box in the header, an index built with the site, results by page and heading.
- Out: search across versions, analytics of queries. Source: brief decision 6

## Sources

- docs/workbench/briefs/docs-site.md (decision 6)
- User answers of 2026-09-22

## Functional requirements

- REQ-1: The build writes a search index with the title, headings and first paragraph of every documentation page. Source: brief decision 6
- REQ-2: The header shows a search box on every page; the `/` key focuses it. Source: user answer 2026-09-22
- REQ-3: Typing at least 2 characters lists up to 8 results, each with the page title and the matching heading. Source: user answer 2026-09-22
- REQ-4: Arrow keys move through the results and Enter opens the selected one. Source: user answer 2026-09-22
- REQ-5: A query with no match shows "No results for <query>". Source: user answer 2026-09-22

## Non-functional requirements

- NFR-1: The search index weighs under 50 kB gzip for 60 pages. Source: user answer 2026-09-22
- NFR-2: Results appear within 100 ms of a keystroke on the index already loaded. Source: user answer 2026-09-22

## Constraints

- technical: no server; the index is a static file. Source: brief decision 6

## Edge cases

- EDGE-1: The index fails to load → the box shows "Search is unavailable" and the sidebar keeps working.
- Categories skipped: permissions, because the site is public.

## Acceptance criteria

- AC-1:
  Given the built site
  When a visitor types "but" in the search box
  Then the Button page is in the results with its title
  Covers: REQ-1, REQ-3
- AC-2:
  Given any page
  When the visitor presses `/`, types a query, presses the down arrow and Enter
  Then the first result's page opens
  Covers: REQ-2, REQ-4
- AC-3:
  Given the query "zzzz"
  When the results render
  Then the list shows "No results for zzzz"
  Covers: REQ-5
- AC-4:
  Given 60 pages
  When the build runs
  Then the index weighs under 50 kB gzip
  Covers: NFR-1
- AC-5:
  Given the index already loaded
  When the visitor types one more character of a query
  Then the results update within 100 ms
  Covers: NFR-2

## Assumptions

- none

## Open questions

- none

## Readiness

- Ready for architecture: yes
