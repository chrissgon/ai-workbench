# Feature specification: reading-time

- Owner: product-feature-spec
- Status: approved
- Date: 2026-09-30
- Feature of: docs/workbench/briefs/reading-time.md (Driftwood blog, driftwood.example)

## Summary

Readers of the Driftwood blog see how long an article takes to read, on the article and in the article list.

## Goal and users

- Problem: readers open long articles on a phone and leave after the first screen. Source: brief decision 1
- Users: readers of the blog. Source: brief
- Success: every article page and every row of the article list shows a reading time in minutes.

## Scope

- In: a reading time computed at build time, shown under the article title and beside each title of the list.
- Out: reading progress, a time per section. Source: brief decision 2

## Sources

- docs/workbench/briefs/reading-time.md (decisions 1 to 3)

## Functional requirements

- REQ-1: Each article page shows "<n> min read" under its title, n being the article's word count divided by 230, rounded up. Source: brief decision 3
- REQ-2: The article list shows the same "<n> min read" beside each article title. Source: brief decision 3

## Non-functional requirements

- NFR-1: Computing the reading times adds under 2 seconds to a build of 400 articles. Source: brief decision 3

## Constraints

- technical: the times are computed by the static build; the site runs no script for them. Source: brief decision 2

## Edge cases

- EDGE-1: An article of fewer than 230 words → it shows "1 min read".
- Categories skipped: permissions, because every article is public.

## Acceptance criteria

- AC-1:
  Given an article of 1,000 words
  When the site is built
  Then its page shows "5 min read" under the title, and a build of 400 articles takes under 2 seconds longer than before
  Covers: REQ-1, NFR-1
- AC-2:
  Given the same article
  When the article list is built
  Then its row shows "5 min read" beside the title
  Covers: REQ-2

## Assumptions

- none

## Open questions

- none

## Readiness

- Ready for architecture: yes
