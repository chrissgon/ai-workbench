# Workbench state

- Project: fernleaf-docs
- Current flow: none
- Current phase: Engineering
- Updated: 2026-05-06

## Autonomy

- Checkpoints: every-phase

## Artifacts

| Artifact | Owner skill | Status | Updated |
|----------|-------------|--------|---------|
| docs/product/specs/content-model.md | product-feature-spec | approved | 2026-04-27 |
| docs/engineering/designs/content-model.md | eng-architecture | approved | 2026-04-29 |
| docs/engineering/adr/0002-example-block-source.md | eng-architecture | draft | 2026-04-29 |
| docs/product/backlog.md | product-backlog | approved | 2026-04-30 |

## Decisions

- 2026-04-27: No dependency and no install step; the site builds with what Node ships. (user)
- 2026-04-27: An example is written once in the page; nobody keeps a second copy of it in sync. (user)
- 2026-04-29: How the example block gets the authored text is ADR-0002; it stays `proposed` until the spike T-cm-4 has run, and the choice between its options is the user's. (eng-architecture, approved by user)
- 2026-04-30: The owner commits; a task ends with a proposed commit message. (user)

## Approvals

| Scope | What | Payload hash | Approved | Expires | Status |
|-------|------|--------------|----------|---------|--------|

## Open questions

- none
