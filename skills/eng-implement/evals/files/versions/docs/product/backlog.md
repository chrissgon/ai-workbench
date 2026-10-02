# Backlog: fernleaf-docs

- Owner: product-backlog
- Status: approved
- Updated: 2026-04-14

## Feature: content model (`T-cm`)

- Specification: docs/product/specs/content-model.md
- Design: docs/engineering/designs/content-model.md
- Sources: the design's contracts and verification plan

### Tasks

- T-cm-1: Version manifest and its loader
  Does: adds `content/versions.json`, the loader `app/manifest.ts`, and the spec files of the verification plan for the manifest and the versions module.
  Delivers: REQ-1, AC-1
  Touches: Manifest loader, `content/versions.json`, `app/manifest.ts`, `tests/repo/manifest.spec.ts`, `tests/repo/versions.spec.ts`
  Depends on: none
  Check: `node --test tests/repo/manifest.spec.ts`; every test passes (verification plan: AC-1)
  Size: S, because one file with a clear contract
  Milestone: M1
  Status: done (2026-04-14) node --test tests/repo/manifest.spec.ts: 3 passed, 0 failed
- T-cm-2: Versions module: list and resolve
  Does: creates `app/versions.ts` with `listVersions` and `resolveVersion` as the design's contract for `app/versions.ts` states them.
  Delivers: REQ-2, REQ-3, AC-2, AC-3
  Touches: Versions, `app/versions.ts` (new), `tests/repo/versions.spec.ts` (exists; change it only to add a case of the contract it lacks)
  Depends on: T-cm-1
  Check: `node --test tests/repo/versions.spec.ts`; every test passes (verification plan: AC-2)
  Size: S, because one file with a clear contract
  Milestone: M1
- T-cm-3: Version switcher
  Does: creates `app/switcher.ts`, which renders one link per version and marks the current one, and its spec.
  Delivers: REQ-2, AC-4
  Touches: Version switcher, `app/switcher.ts`, `tests/repo/switcher.spec.ts`
  Depends on: T-cm-2
  Check: `node --test tests/repo/switcher.spec.ts`; every test passes (verification plan: AC-4)
  Size: S, because one file with a clear contract
  Milestone: M2

### Order

- Spikes: none
- Critical path: T-cm-1 → T-cm-2 → T-cm-3
- Parallel tracks: none

### Milestones

- M1 versions resolve: T-cm-1, T-cm-2 → usable state: the versions are listed and resolved from the manifest
- M2 versions show: T-cm-3 → usable state: every page carries the version switcher

### Coverage

| Id | Delivered by |
|----|--------------|
| REQ-1 | T-cm-1 |
| REQ-2 | T-cm-2, T-cm-3 |
| REQ-3 | T-cm-2 |
| AC-1 | T-cm-1 |
| AC-2 | T-cm-2 |
| AC-3 | T-cm-2 |
| AC-4 | T-cm-3 |

### Open questions

- none
