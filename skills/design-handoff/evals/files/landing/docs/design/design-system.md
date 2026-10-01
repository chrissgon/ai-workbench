# Design system: Plinth UI documentation site

- Owner: design-system
- Status: approved
- Date: 2026-03-02
- Flows: docs/design/flows.md

## Summary

The Plinth UI library's own tokens govern every colour, size and component the site shows; the site adds only the tokens a documentation site needs.

## Sources

- `library/plinthui.css` (Plinth UI 1.0.0, the stylesheet the site ships): every `--pui-*` custom property; component classes with the prefix `pui`
- docs/design/flows.md: SCREEN-1 and SCREEN-2

## Ownership

- Colours, spacing unit, radius, border and component anatomy: the library. The site never redefines or copies a `--pui-*` value; it loads the installed package's stylesheet.
- Type roles, layout and site-only components: this document. A token that is in neither list does not exist: it is a finding for design-system, never added in code.

## Library tokens (mirror of `library/plinthui.css`)

| Token | Light | Dark | Role |
|-------|-------|------|------|
| `--pui-bg` | #FFFFFF | #000000 | page background |
| `--pui-bg-muted` | #F3F4F6 | #111827 | card headers, addons |
| `--pui-text` | #000000 | #FFFFFF | body text |
| `--pui-text-muted` | #6B7280 | #9CA3AF | secondary text |
| `--pui-border` | #D1D5DB | #374151 | every border |
| `--pui-theme` | #0092CD | #07B6F0 | brand colour, links, focus ring, the only accent |
| `--pui-success` | #16A34A | #22C55E | positive state (the "Copied" feedback) |
| `--pui-radius` | 0.375rem | same | corner radius |
| `--pui-space` | 0.25rem | same | spacing unit; every gap is a multiple of it |
| `--pui-font-size` | 0.875rem | same | component text |

## Site tokens

| Token | Value | Role |
|-------|-------|------|
| `--site-font-text` | Inter, weights 400 and 600, self-hosted from `public/fonts/` | every text |
| `--site-font-code` | Fira Code, weight 400, self-hosted from `public/fonts/` | code and the install command |
| `--site-section-gap` | calc(var(--pui-space) * 24), 96 px | vertical gap between landing sections |
| `--site-content-width` | 72rem | maximum content width |

## Components

| Component | Kind | States | Used in |
|-----------|------|--------|---------|
| Button (`pui-btn`, `pui-solid`) | library | default, hover, focus | SCREEN-1 primary call to action |
| Card (`pui-card`, `pui-card-header`, `pui-card-content`) | library | default | SCREEN-1 showcase |
| Input group (`pui-input-group`, `pui-input-group-addon`) | library | default, focus | SCREEN-1 install command |
| Badge (`pui-badge`) | library | default | SCREEN-1 size block version |
| InstallCommand | site | default, copied, no JavaScript | SCREEN-1 |
| SizeBlock | site | default | SCREEN-1 |
| ExampleBlock | site | default | SCREEN-1 showcase, documentation pages |
| SiteHeader, SiteFooter | site | default, light, dark | SCREEN-2 |

## Motion

- Entrance animations are allowed on the landing only: at most 600 ms, opacity and transform only, and none under `prefers-reduced-motion: reduce`.

## Assets

- Logo: `library/logo.svg` (the three bars), used at 32 px in the header.
- Icons: none in this release; controls are text.
