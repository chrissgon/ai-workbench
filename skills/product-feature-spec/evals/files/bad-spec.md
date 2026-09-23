# Feature specification: search

- Owner: product-feature-spec
- Status: draft
- Date: 2026-09-23
- Feature of: test

## Summary
Search.
## Goal and users
- Problem: x
## Scope
- In: search
## Sources
- none
## Functional requirements
- REQ-1: User can search the docs and results appear fast.
- REQ-2: Search supports filters. Source: brief decision 5
## Non-functional requirements
- NFR-1: Search is scalable. Source: brief
## Constraints
- none
## Edge cases
- EDGE-1: empty query
## Acceptance criteria
- AC-1:
  Given the docs are indexed
  When the user types "button"
  Then results include the Button page
  Covers: REQ-2
## Assumptions
- ASSUMPTION-1: index exists. Safe because: built at deploy
## Open questions
- OPEN-1: which index? Recommended: local
## Readiness
- Ready for architecture: no
