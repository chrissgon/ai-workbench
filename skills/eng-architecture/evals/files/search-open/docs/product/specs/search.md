# Feature specification: search

- Owner: product-feature-spec
- Status: draft
- Date: 2026-03-12
- Feature of: Plinth UI documentation site, phase P-1, F-5 "Search"

## Summary

A reader opens a search dialog from any documentation page, types a few letters and jumps to the page
that matches.

## Goal and users

- Problem: readers who know a component's name still walk the sidebar to reach its page. Source: user, 2026-03-11
- Users: developers evaluating or using the library (PRD U-1, U-2)
- Success: a reader reaches a page by its name in 3 actions or fewer: open the dialog, type, choose.

## Scope

- In: a search dialog on every documentation page, searching page titles, headings and body text.
- Out: searching the library's source code; search analytics; suggestions when nothing matches.

## Sources

- docs/product/prd.md, F-5
- User answers, 2026-03-11

## Functional requirements

- REQ-1: Every documentation page has a control, and the `/` key, that open the search dialog. Source: PRD F-5
- REQ-2: Typing 2 or more characters lists up to 8 matching pages with title, section and an excerpt, best match first. Source: user answer 2026-03-11
- REQ-3: Choosing a result opens that page; Escape closes the dialog and returns focus to the control. Source: PRD F-5
- REQ-4: When the search cannot answer, the dialog shows "Search is unavailable. Try again." with a retry control. Source: user answer 2026-03-11

## Non-functional requirements

- NFR-1: Results appear within 200 ms of the last keystroke at the 95th percentile. Source: user answer 2026-03-11
- NFR-2: The search adds at most 30 KB of compressed JavaScript to a documentation page before the dialog is first opened. Source: user answer 2026-03-11

## Constraints

- technical: the site is static; nothing of ours runs on a server. Source: user, 2026-03-11

## Edge cases

- EDGE-1: The query matches nothing → the dialog shows "No results for <query>".
- EDGE-2: The search source fails to load or answer → the error state of REQ-4.
- EDGE-3: The query is 1 character → no search runs and the dialog shows the hint "Type at least 2 characters".
- Categories skipped: permissions (every page is public).

## Acceptance criteria

- AC-1:
  Given any documentation page
  When the reader presses `/` or activates the search control
  Then the dialog opens with focus in the input
  Covers: REQ-1
- AC-2:
  Given the dialog is open
  When the reader types "but"
  Then at most 8 results appear within 200 ms, the Button page first, each with title, section and excerpt
  Covers: REQ-2, NFR-1
- AC-3:
  Given results are listed
  When the reader presses Enter on the first result, or Escape
  Then the page opens, or the dialog closes and focus returns to the control
  Covers: REQ-3
- AC-4:
  Given the search source is unreachable
  When the reader types 2 characters
  Then the dialog shows "Search is unavailable. Try again." with a retry control
  Covers: REQ-4
- AC-5:
  Given a documentation page before the dialog was opened
  When its network requests are measured
  Then the JavaScript added by search is 30 KB compressed or less
  Covers: NFR-2

## Assumptions

- ASSUMPTION-1: The documentation stays below 100 pages in phase P-1. Safe because: the PRD plans fewer than 60 pages.

## Open questions

- OPEN-1: Which search provider answers the queries: an index generated at build time and searched in the browser, or a hosted search service that crawls the site? The choice decides where the index lives, what the site pays and whether reader queries leave the site. Blocks: REQ-2, REQ-4, NFR-1, NFR-2. Recommended: an index generated at build time and searched in the browser, because the site is static, has fewer than 100 pages and then sends no query to a third party.

## Readiness

- Ready for architecture: no, because OPEN-1 blocks REQ-2, REQ-4, NFR-1 and NFR-2
