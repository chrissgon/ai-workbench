# Plan: duplicate-address-across-sections

- Task: "Two pages with the same slug in different sections stop the build" (docs team)
- Date: 2027-11-09

## Root cause

- Owner: eng-root-cause
- Evidence: confirmed

### Report
Seen: `content/guide/install.md` and `content/components/install.md` are reported with "address /install is already used". Expected: both pages are valid; their addresses are `/guide/install` and `/components/install`. Reported by: docs team.
Suggested fix: none

### Reproduction
`tests/unit/validate.spec.ts` — run with `node --test tests/unit/validate.spec.ts`.
| Case | Node 24 |
|------|---------|
| `guide/install` and `components/install` | one message: `content/components/install.md: address /install is already used by content/guide/install.md` |
| `guide/install` twice | the message names `/install`, not `/guide/install` |

### Cause
app/validate.ts:25 `const address = page.slug;`
The address is built from the slug alone. EDGE-4 of `docs/product/specs/content-model.md` defines it as the section and the slug ("Two pages with the same section and slug have the same address"), and the design's failure path for EDGE-4 reads "the same `section/slug` seen before", so two sections that use one slug collide.

### Discriminating experiment
| Case | Predicted by the cause | Observed | Rules out |
|------|------------------------|----------|-----------|
| one slug in two sections | reported | reported | a check that compares files instead of addresses |
| one slug twice in one section | reported, address without the section | `address /install` | a wrong message only |

### Reach
- Triggers: two pages that share a slug in two sections.
- Same assumption elsewhere: none: searched for `page.slug` under `app/`.

### Why it escaped
- The EDGE-4 test had no case of one slug in two sections.

### What a fix must preserve
- Two pages with the same section and slug: the second is reported and names the first, with the address `/<section>/<slug>`.
- Every other test of `tests/unit/validate.spec.ts` keeps passing.

## Failing tests

- Owner: eng-unit-tests
- Command: `node --test tests/unit/validate.spec.ts`
- Files: `tests/unit/validate.spec.ts`

| Test | Source | Expected before the change | Observed before (per runtime) |
|------|--------|----------------------------|-------------------------------|
| two pages with the same slug in different sections are both valid (EDGE-4) | Root cause › Report | fails now | Node 24: one message, `address /install is already used` |
| two pages with the same section and slug are reported once, on the second (EDGE-4) | What a fix must preserve | fails now | Node 24: two messages, each naming `/install` |
| the five other tests | What a fix must preserve | passes now | passes |

- Result before the change: 2 failed, 5 passed (the failures are exactly the `fails now` rows)
- Pending decisions: none
