# Backlog: fernleaf-docs

- Owner: product-backlog
- Status: approved
- Updated: 2026-06-02

## Feature: content model (`T-cm`)

- Specification: docs/product/specs/content-model.md
- Design: docs/engineering/designs/content-model.md
- Sources: the design's contracts, failure paths and verification plan

### Tasks

- T-cm-1: Validator: validateDocs
  Does: creates `app/validate.ts` with `validateDocs` and its spec, one test per EDGE at its boundary.
  Delivers: REQ-1, REQ-2, EDGE-1, EDGE-2, EDGE-3, EDGE-4, AC-1
  Touches: Validator, `app/validate.ts`, `tests/unit/validate.spec.ts`
  Depends on: none
  Check: `node --test tests/unit/validate.spec.ts`; every test passes (verification plan: AC-1)
  Size: S, because one file with a clear contract
  Milestone: M1
  Status: done (2026-06-02) node --test tests/unit/validate.spec.ts: 6 passed, 0 failed
- T-cm-2: Build check over content/
  Does: creates `scripts/check-content.ts`, which reads the front matter of every file under `content/`, calls `validateDocs` and exits with an error when it returns messages.
  Delivers: REQ-3, AC-2
  Touches: Build check, `scripts/check-content.ts`, `tests/unit/check-content.spec.ts`
  Depends on: T-cm-1
  Check: `node --test tests/unit/check-content.spec.ts`; every test passes (verification plan: AC-2)
  Size: M, because it reads files and sets the exit code
  Milestone: M2

### Order

- Spikes: none
- Critical path: T-cm-1 → T-cm-2
- Parallel tracks: none

### Milestones

- M1 pages are checked: T-cm-1 → usable state: a list of pages is validated against every rule
- M2 the build is guarded: T-cm-2 → usable state: the build stops on a broken page

### Coverage

| Id | Delivered by |
|----|--------------|
| REQ-1 | T-cm-1 |
| REQ-2 | T-cm-1 |
| REQ-3 | T-cm-2 |
| AC-1 | T-cm-1 |
| AC-2 | T-cm-2 |

### Open questions

- none
