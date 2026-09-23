# Backlog: tiny

## Feature: tiny (`T-ti`)

### Tasks

- T-ti-1: skeleton
  Does: sets up
  Delivers: REQ-1
  Touches: app
  Depends on: T-ti-2
  Check: build passes
  Size: S, because one file
  Milestone: M1
- T-ti-2: component
  Does: builds
  Delivers: REQ-9
  Touches: comp
  Depends on: T-ti-1
  Check: works
  Size: big
  Milestone: M3

### Milestones

- M1 base: T-ti-1 → usable state: builds
