# Backlog: {project}

- Owner: product-backlog
- Status: draft
- Updated: {YYYY-MM-DD}

## Feature: {feature} (`T-{abbr}`)

- Specification: docs/product/specs/{feature}.md
- Design: docs/engineering/designs/{feature}.md
- Sources: {decisions, verification plan, assumptions}

### Tasks

- T-{abbr}-1: Spike: {the design assumption verified}
  Does: {what is done, in one or two lines}
  Delivers: REQ-n
  Touches: {design components or files}
  Depends on: none
  Check: {the design's "Verify by ..." sentence} (design assumption)
  Size: L, because {reason}
  Milestone: M1
- T-{abbr}-2: {title}
  Does: {what is done, in one or two lines}
  Delivers: REQ-n, AC-n
  Touches: {design components or files}
  Depends on: T-{abbr}-1
  Check: `{command of the verification-plan row}`; {observable result} (verification plan: AC-n)
  Size: S, because {reason}
  Milestone: M1
- T-{abbr}-9: Remove {what is removed}
  Does: {what is deleted, after its replacement works}
  Delivers: REQ-n, AC-n
  Touches: {removed files}
  Depends on: T-{abbr}-7, T-{abbr}-8
  Check: `{the "Checked by" command of the Removals table}`; {what must keep working} (verification plan: AC-n)
  Size: S, because {reason}
  Milestone: M3

### Order

- Spikes first: T-{abbr}-1 (every other task depends on a spike)
- Critical path: T-{abbr}-1 → T-{abbr}-2 → … (the `critical_path` of the lint output)
- Parallel tracks: {T-x-2 alongside T-x-3}

### Milestones

- M1 {name}: T-…, T-… → usable state: {one line the checks prove}
- M2 {name}: … → usable state: …

### Coverage

| Id | Delivered by |
|----|--------------|
| REQ-1 | T-{abbr}-2 |

### Open questions

- {only what the user must decide; else "none"}
