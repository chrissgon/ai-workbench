# Backlog: driftwood

- Owner: product-backlog
- Status: approved
- Updated: 2026-09-30

## Feature: reading-time (`T-rt`)

- Specification: docs/product/specs/reading-time.md
- Design: none (the specification has three requirements)
- Sources: docs/product/specs/reading-time.md

### Tasks

- T-rt-1: Reading-time helper
  Does: adds a build helper that counts the words of an article body and divides by 230, rounded up
  Delivers: REQ-1, NFR-1, AC-1
  Touches: build/reading-time.mjs
  Depends on: none
  Check: the Then of AC-1: an article of 1,000 words shows "5 min read" (acceptance criterion: AC-1)
  Size: S, because one file with one function
  Milestone: M1
- T-rt-2: Show the time on article pages
  Does: renders "<n> min read" under the article title
  Delivers: REQ-1, AC-1
  Touches: templates/article.html
  Depends on: T-rt-1
  Check: the Then of AC-1: the page shows "5 min read" under the title (acceptance criterion: AC-1)
  Size: S, because one template
  Milestone: M1
- T-rt-3: Show the time in the article list
  Does: renders "<n> min read" beside each title of the article list
  Delivers: REQ-2, AC-2
  Touches: templates/list.html
  Depends on: T-rt-1
  Check: the Then of AC-2: the row shows "5 min read" beside the title (acceptance criterion: AC-2)
  Size: S, because one template
  Milestone: M2

### Order

- Critical path: T-rt-1 → T-rt-2
- Parallel tracks: T-rt-3 alongside T-rt-2

### Milestones

- M1 times on articles: T-rt-1, T-rt-2 → usable state: every article page shows its reading time
- M2 times in the list: T-rt-3 → usable state: the article list shows a reading time per row

### Coverage

| Id | Delivered by |
|----|--------------|
| REQ-1 | T-rt-1, T-rt-2 |
| REQ-2 | T-rt-3 |
| NFR-1 | T-rt-1 |
| AC-1 | T-rt-1, T-rt-2 |
| AC-2 | T-rt-3 |

### Assumptions

- none

### Open questions

- none
