# Backlog: driftwood

- Owner: product-backlog
- Status: draft
- Updated: 2026-09-30

## Feature: reading-time (`T-rt`)

- Specification: docs/product/specs/reading-time.md
- Design: none (the specification has three requirements)
- Sources: docs/product/specs/reading-time.md

### Tasks

- T-rt-1: Reading-time helper
  Does: adds a build helper that counts the words of an article body and divides by 230, rounded up
  Delivers: REQ-1
  Touches: build/reading-time.mjs
  Depends on: T-rt-2
  Check: `node --test test/reading-time.test.mjs` passes
  Size: S, because one file with one function
  Milestone: M1
- T-rt-2: Show the time on article pages and in the list
  Does: renders "<n> min read" under the article title and beside each title of the article list
  Delivers: REQ-9
  Touches: templates/article.html, templates/list.html
  Depends on: T-rt-1
  Check: works
  Size: big
  Milestone: M3

### Order

- Critical path: T-rt-1 → T-rt-2

### Milestones

- M1 times computed: T-rt-1 → usable state: every article has a reading time in its build data

### Open questions

- none
