# Backlog: {project}

- Owner: product-backlog
- Status: draft
- Updated: {YYYY-MM-DD}

## Feature: {feature} (`T-{abbr}`)

- Specification: docs/product/specs/{feature}.md
- Design: docs/engineering/designs/{feature}.md
- Sources: {decisions, verification plan, assumptions}

### Tasks

- T-{abbr}-1: {title}
  Does: {what is done, in one or two lines}
  Delivers: REQ-n, AC-n
  Touches: {design components or files}
  Depends on: none
  Check: {command, test file or observable result}
  Size: S, because {reason}
  Milestone: M1

### Order

- Critical path: T-{abbr}-1 → T-{abbr}-3 → …
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
