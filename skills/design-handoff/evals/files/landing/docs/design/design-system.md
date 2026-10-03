# Design system: Plinth UI documentation site

- Owner: design-system
- Status: approved
- Date: 2026-03-02
- Flows: docs/design/flows.md
- Lint: ok (2026-03-02)

## Summary

The Plinth UI library's own tokens govern every colour, size and component the site shows; the site adds only the tokens a documentation site needs. 11 library tokens, 4 site tokens and 8 components for the two screens of the flows.

## Sources

- `library/plinthui.css` (Plinth UI 1.0.0, the stylesheet the site ships): every `--ui-*` custom property; component classes with the prefix `ui`
- docs/design/flows.md: SCREEN-1 and SCREEN-2
- Contrast ratios computed with `contrast.py` of the design-system skill, 2026-03-02
- User answer, 2026-03-02: typography Inter and Fira Code, self-hosted

## Ownership

- Colours, spacing unit, radius, border and component anatomy: the library. The site never redefines or copies a `--ui-*` value; it loads the installed package's stylesheet.
- Type roles, layout and site-only components: this document. A token that is in neither list does not exist: it is a finding for design-system, never added in code.

## Colour

| Token | Light | Dark | Role | Source |
|-------|-------|------|------|--------|
| `--ui-bg` | #FFFFFF | #000000 | page background, label on a solid fill | library/plinthui.css |
| `--ui-bg-muted` | #F3F4F6 | #111827 | card headers, addons | library/plinthui.css |
| `--ui-text` | #000000 | #FFFFFF | body text | library/plinthui.css |
| `--ui-text-muted` | #6B7280 | #9CA3AF | secondary text | library/plinthui.css |
| `--ui-border` | #D1D5DB | #374151 | every border | library/plinthui.css |
| `--ui-theme` | #0092CD | #07B6F0 | brand colour, links, focus ring, the only accent | library/plinthui.css |
| `--ui-success` | #16A34A | #22C55E | positive state (the "Copied" feedback) | library/plinthui.css |

## Contrast

Ratios come from `contrast.py`, never from memory.

| Text token | On background | Light ratio | Dark ratio | AA |
|------------|---------------|-------------|------------|----|
| `--ui-text` | `--ui-bg` | 21.00:1 | 21.00:1 | pass (needs 4.5:1); used on SCREEN-1 value proposition |
| `--ui-text-muted` | `--ui-bg` | 4.83:1 | 8.27:1 | pass (needs 4.5:1); used on SCREEN-1 size block method |
| `--ui-text` | `--ui-bg-muted` | 19.08:1 | 17.74:1 | pass (needs 4.5:1); used on SCREEN-1 card headers |
| `--ui-bg` | `--ui-theme` | 3.50:1 | 8.96:1 | fail in light for text under 24 px (needs 4.5:1); the primary call to action is 24 px or larger |

## Type

- Typeface: Inter for text, Fira Code for code and the install command, self-hosted from `public/fonts/`. Source: user answer 2026-03-02
- Reading width: 72rem of content (`--site-content-width`). Source: this document

| Role | Size | Line height | Weight | Source |
|------|------|-------------|--------|--------|
| display (value proposition) | 48 px | 56 px | 600 | this document |
| body | 16 px | 24 px | 400 | this document |
| component text (`--ui-font-size`) | 0.875rem | 1.25 | 400 | library/plinthui.css |
| code | 14 px | 20 px | 400 | this document |

## Space, radii, borders, elevation

| Token | Value | Role | Source |
|-------|-------|------|--------|
| `--ui-space` | 0.25rem | spacing unit; every gap is a multiple of it | library/plinthui.css |
| `--ui-radius` | 0.375rem | corner radius | library/plinthui.css |
| `--ui-border-width` | 1px | every border | library/plinthui.css |
| `--site-section-gap` | calc(var(--ui-space) * 24), 96 px | vertical gap between landing sections | this document |
| elevation | none | the library uses no shadows | library/plinthui.css |

## Layout

| Token | Value | Role | Source |
|-------|-------|------|--------|
| `--site-content-width` | 72rem | maximum content width | this document |
| `--site-font-text` | Inter, weights 400 and 600, self-hosted from `public/fonts/` | every text | user answer 2026-03-02 |
| `--site-font-code` | Fira Code, weight 400, self-hosted from `public/fonts/` | code and the install command | user answer 2026-03-02 |
| breakpoints | 360 px, 768 px, 1280 px | the widths of the flows | docs/design/flows.md SCREEN-1 |
| motion | entrance animations on the landing only: at most 600 ms, opacity and transform only, none under `prefers-reduced-motion: reduce` | transitions | this document |

## Components

| Component | Owner | Variants | States | Screens | Source |
|-----------|-------|----------|--------|---------|--------|
| Button (`ui-btn`, `ui-solid`) | library | solid | default, hover, focus | SCREEN-1 (primary call to action) | library/plinthui.css |
| Card (`ui-card`, `ui-card-header`, `ui-card-content`) | library | none | default | SCREEN-1 (showcase) | library/plinthui.css |
| Input group (`ui-input-group`, `ui-input-group-addon`) | library | none | default, focus | SCREEN-1 (install command) | library/plinthui.css |
| Badge (`ui-badge`) | library | none | default | SCREEN-1 (size block version) | library/plinthui.css |
| InstallCommand | site | none | default, copied, no JavaScript | SCREEN-1 | flows SCREEN-1 regions |
| SizeBlock | site | none | default | SCREEN-1 | flows SCREEN-1 regions |
| ExampleBlock | site | none | default | SCREEN-1 (showcase) | flows SCREEN-1 regions |
| SiteHeader, SiteFooter | site | none | default, light, dark | SCREEN-2 | flows SCREEN-2 regions |

## Design tool

- File: the design system is loaded in the design tool as the project "Plinth UI site"; values verified against this document on 2026-03-02.

## Assets

- Logo: `library/logo.svg` (the three bars), used at 32 px in the header.
- Icons: none in this release; controls are text.

## Assumptions

- none

## Open questions

- none

## Readiness

- Ready for design-brief: yes
