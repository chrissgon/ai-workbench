# Design system: plinthui documentation site

- Owner: design-system
- Status: approved
- Date: 2026-09-23
- Flows: docs/design/flows.md

## Summary

The library's own token specification governs every colour, size and component the site shows; the site adds only what a documentation site needs (type roles, layout, code block, navigation). The tokens and text styles are mirrored in the design tool; the library components and the site-only components below are inventoried for the three screens of the flows.

## Sources

- `DESIGN-SYSTEM.md` of the plinthui repository (generated from the shipped 1.0 stylesheet, read 2026-09-23): §1 foundations, §2 colour roles, §3 styles, §4 components, §5 interaction states, §6 building this in the design tool
- `node_modules/@plinthkit/plinthui/dist/plinthui.css` 1.0.0-beta.0: `:root` custom properties `--plu-bg`, `--plu-bg-muted`, `--plu-bg-emphasis`, `--plu-text`, `--plu-text-muted`, `--plu-border`, `--plu-theme`, `--plu-success`, `--plu-warn`, `--plu-error`, `--plu-radius` (0.375rem), `--plu-space` (0.25rem), `--plu-border-width` (1px)
- `docs/design/flows.md`: SCREEN-1 to SCREEN-3 and their regions and states
- `docs/workbench/state.md` decisions of 2026-09-23: no brand phase, logo and default theme colour kept; typography Inter and Fira Code (user)
- Contrast ratios computed with `contrast.py` of the design-system skill (WCAG 2.x relative luminance), 2026-09-23
- Tailwind CSS default breakpoints (the site's utility layer): sm 640, md 768, lg 1024, xl 1280

## Colour

| Token | Light | Dark | Role | Source |
|-------|-------|------|------|--------|
| `--plu-bg` (page/bg) | #FFFFFF | #000000 | page background, label on a solid fill | DESIGN-SYSTEM §1.1 |
| `--plu-bg-muted` (page/bg-muted) | #F3F4F6 | #111827 | card headers, table footers, addons, stripes, hover rows | DESIGN-SYSTEM §1.1 |
| `--plu-bg-emphasis` (page/bg-emphasis) | #E5E7EB | #1F2937 | third level; the site uses it for the code block background | DESIGN-SYSTEM §1.1; site rule below |
| `--plu-text` (page/text) | #000000 | #FFFFFF | body text | DESIGN-SYSTEM §1.1 |
| `--plu-text-muted` (page/text-muted) | #6B7280 | #9CA3AF | secondary text | DESIGN-SYSTEM §1.1 |
| `--plu-border` (page/border) | #D1D5DB | #374151 | every border without a role colour | DESIGN-SYSTEM §1.1 |
| `--plu-theme` (theme/fill) | #0092CD | #07B6F0 | brand colour; also the site's link and focus-ring colour | DESIGN-SYSTEM §1.1; state decision (theme colour kept) |
| theme/on-fill | #FFFFFF | #000000 | label on a solid theme fill | DESIGN-SYSTEM §6.1 |
| theme/fill-hover | #007AAD | #48BFF2 | solid theme fill under the pointer | DESIGN-SYSTEM §6.1 |
| theme/ink | #00628B | #6BC9F5 | theme text for soft, outline and link | DESIGN-SYSTEM §6.1 |
| `--plu-success` (success/fill) | #16A34A | #22C55E | positive state; the "Added in" badge | DESIGN-SYSTEM §1.1 |
| success/ink | #0B6E2F | #71D588 | text | DESIGN-SYSTEM §6.1 |
| `--plu-warn` (warn/fill) | #D97706 | #F59E0B | caution state; the "Changed in" badge | DESIGN-SYSTEM §1.1 |
| warn/ink | #934F03 | #F9B867 | text | DESIGN-SYSTEM §6.1 |
| `--plu-error` (error/fill) | #DC2626 | #EF4444 | destructive state, invalid fields | DESIGN-SYSTEM §1.1 |

Site rules for using these tokens (this document): body prose uses `page/text` on `page/bg`; secondary prose uses `page/text-muted` on `page/bg` only, never on `page/bg-muted` (4.39:1, below AA); links and the focus ring use `theme/ink` for text and `theme/fill` for the ring; site-only components never use a solid `theme`, `success` or `warn` fill under text smaller than 19 px bold or 24 px regular, because those labels sit at 3.2 to 3.5:1 in light mode (library trade-off); the code block uses `page/bg-emphasis` as background with `page/text` as foreground.

## Contrast

| Text token | On background | Light ratio | Dark ratio | AA |
|------------|---------------|-------------|------------|----|
| page/text | page/bg | 21.00:1 | 21.00:1 | pass |
| page/text-muted | page/bg | 4.83:1 | 8.27:1 | pass |
| page/text | page/bg-muted | 19.08:1 | 17.74:1 | pass |
| page/text-muted | page/bg-muted | 4.39:1 | 6.99:1 | fail in light (site rule: not used for text) |
| theme/on-fill | theme/fill (solid button label) | 3.50:1 | 8.96:1 | fail in light for text under 24 px (library trade-off); pass as interface colour (3:1) |
| theme/ink | page/bg | 6.73:1 | 11.30:1 | pass |
| success/ink | page/bg | 6.39:1 | 11.58:1 | pass |
| warn/ink | page/bg | 6.25:1 | 12.08:1 | pass |
| theme/fill as focus ring (interface, 3:1) | page/bg | 3.50:1 | 8.96:1 | pass |

## Type

- Typeface: Inter for text and interface, Fira Code for code; fallback `system-ui, sans-serif` and `ui-monospace, monospace`; both self-hosted with `font-display: swap`. Source: user answer 2026-09-23.
- Reading width: 72ch of `site/body` (about 720 px at 16 px), content column; the page frame is 1280 px wide at the `xl` breakpoint. Source: this document.

| Role | Size | Line height | Weight | Source |
|------|------|-------------|--------|--------|
| text/body (component text) | 14 px | 17.5 px | inherited (Regular) | DESIGN-SYSTEM §1.4 |
| text/small (badges, tooltips, field labels) | 12 px | 15 px | inherited (Regular) | DESIGN-SYSTEM §1.4 |
| site/display (landing value proposition) | 44 px | 52 px | 700 | this document: base 14 px × 1.25 per step, rounded to the 4 px grid |
| site/h1 (page title) | 36 px | 44 px | 600 | this document |
| site/h2 (section) | 28 px | 36 px | 600 | this document |
| site/h3 (subsection) | 22 px | 28 px | 600 | this document |
| site/lead (landing paragraph) | 18 px | 28 px | 400 | this document |
| site/body (prose) | 16 px | 24 px | 400 | this document |
| site/code (code blocks and inline code) | 14 px | 20 px | 400, Fira Code | this document |

## Space, radii, borders, elevation

| Token | Value | Role | Source |
|-------|-------|------|--------|
| space/4 (`--plu-space`) | 4 px | unit; gap inside a button | DESIGN-SYSTEM §1.2, §1.3 |
| space/8 | 8 px | button, list item, table cell, card header vertical padding | DESIGN-SYSTEM §1.3 |
| space/12 | 12 px | input horizontal padding, addon padding, card content gap | DESIGN-SYSTEM §1.3 |
| space/16 | 16 px | button and card header horizontal padding; card content padding | DESIGN-SYSTEM §1.3 |
| space/24 | 24 px | site section gap on narrow screens | this document |
| radius/6 (`--plu-radius`) | 6 px | buttons, badges, inputs, list items, dropdowns, tooltips | DESIGN-SYSTEM §1.5 |
| radius/9 | 9 px | cards; site: code block and example block | DESIGN-SYSTEM §1.5; this document |
| border/1 (`--plu-border-width`) | 1 px | every border and group overlap | DESIGN-SYSTEM §1.2 |
| elevation | none | the library uses no shadows; the site uses none either | DESIGN-SYSTEM §4; this document |

## Layout

| Token | Value | Role | Source |
|-------|-------|------|--------|
| breakpoint/md | 768 px | sidebar becomes a toggleable panel below | flows SCREEN-2 Breakpoints; Tailwind defaults |
| breakpoint/lg | 1024 px | on-page headings list shown beside content above | flows SCREEN-2; Tailwind defaults |
| breakpoint/xl | 1280 px | page frame max width | this document |
| layout/header-height | 56 px | site header | this document |
| layout/sidebar-width | 272 px | documentation navigation column (17 × 16 px) | this document |
| layout/toc-width | 208 px | on-page headings column | this document |
| layout/gutter | 16 px narrow, 32 px from md | page horizontal padding | this document |
| focus/ring | 2 px, `theme/fill`, 2 px outside, follows the radius | keyboard focus | DESIGN-SYSTEM §5 |
| motion | 150 ms on colour, border and text; none under reduced motion | transitions | DESIGN-SYSTEM §5 |

## Components

| Component | Owner | Variants | States | Screens | Source |
|-----------|-------|----------|--------|---------|--------|
| Button (`plu-btn`) | library | style × colour (4 × 7), rounded | default, hover, focus, disabled | SCREEN-1, SCREEN-3 | DESIGN-SYSTEM §4.1, §5 |
| Badge (`plu-badge`) | library | style × colour | default | SCREEN-2 (since and changed badges) | DESIGN-SYSTEM §4.3; content-model spec REQ-7 |
| Card (`plu-card`, header, content) | library | none | default | SCREEN-1 (showcase), SCREEN-2 (examples) | DESIGN-SYSTEM §4.4 |
| Input group (`plu-input-group`, addon) | library | none | default, focus | SCREEN-1 (install command with copy control) | DESIGN-SYSTEM §4.13 |
| Navigation item | site | level 1 section, level 2 page | default, hover, current, focus | SCREEN-2 | flows SCREEN-2 regions |
| On-page heading link | site | level 2, level 3 | default, current, focus | SCREEN-2 | flows SCREEN-2 regions |
| Code block | site | with language label, with copy control | default, copied, focus | SCREEN-2 | content-model spec REQ-10 |
| Example block | site | preview tab, code tab | default, copied | SCREEN-1, SCREEN-2 | content-model spec REQ-3; landing spec REQ-5 |
| Copy control | site | icon-only, with label | default, copied, focus, unavailable | SCREEN-1, SCREEN-2 | landing spec REQ-3, EDGE-9 |

## Design tool

- The tokens are mirrored as the design tool's variables (collection `plu`, modes `light` and `dark`), with the library's text styles and the components Button, Badge and Card; values verified against the document on 2026-09-23.

## Assumptions

- ASSUMPTION-1: The library's `light-dark()` values are the light and dark mode values of the design tool's variables; the site sets `data-plu-mode` so both modes exist. Safe because: `plinthui.css` `:root` declares every colour with `light-dark()` and `color-scheme: light dark`.

## Open questions

- none

## Readiness

- Ready for design-brief: yes.
