# Workbench state

- Project: plinthui-docs
- Current flow: none
- Current phase: Engineering
- Updated: 2026-03-10

## Autonomy

- Checkpoints: every-phase

## Artifacts

| Artifact | Owner skill | Status | Updated |
|----------|-------------|--------|---------|
| docs/engineering/architecture.md | eng-codebase-map | approved | 2026-03-09 |
| docs/product/specs/markdown-content-model.md | product-feature-spec | approved | 2026-03-10 |

## Decisions

- 2026-03-06: The site stays on Astro with static output; no server and no other framework. (user)
- 2026-03-06: Content lives as Markdown files in this repository; no CMS and no external content service. (user)
- 2026-03-06: Hosting stays a static host serving `dist/`; nothing in this feature may need a server at run time. (user)
- 2026-03-10: Addresses are `/guide/<slug>` and `/components/<slug>`, without a trailing slash; the two existing addresses must keep working. (user)
- 2026-03-10: No new runtime or build dependency for this feature without asking. (user)

## Approvals

| Scope | What | Payload hash | Approved | Expires | Status |
|-------|------|--------------|----------|---------|--------|

## Open questions

- none
