# Workbench state

- Project: invoices
- Current flow: flow-fix-bug on "the due date comes out one day early for customers in Brazil" (user, 2026-09-25)
- Current phase: 2 failing tests: approved (user, 2026-09-26)
- Updated: 2026-09-26

## Autonomy

- Checkpoints: every-phase

## Artifacts

| Artifact | Owner skill | Status | Updated |
|----------|-------------|--------|---------|
| docs/engineering/plans/due-date-one-day-early.md (Root cause) | eng-root-cause | approved | 2026-09-25 |
| docs/engineering/plans/due-date-one-day-early.md (Failing tests) | eng-unit-tests | approved | 2026-09-26 |

## Decisions

- 2026-09-25: Phase 1 root cause approved: "yes, the cause is right, go on to the tests". (user)
- 2026-09-26: Phase 2 failing tests approved: "tests are good". (user)
- 2026-09-26: The fix reads a date-only string as a local date inside toDate; no other approach to compare. (user, at the phase 2 checkpoint)

## Approvals

| Scope | What | Payload hash | Approved | Expires | Status |
|-------|------|--------------|----------|---------|--------|

## Open questions
