# Design system: perfectui documentation site

- Owner: design-system
- Status: draft
- Date: 2026-09-23
- Flows: docs/design/flows.md

## Summary

The library's own token specification governs every colour, size and component the site shows; the site adds only what a documentation site needs (type roles, layout, code block, navigation, search). 59 tokens and 10 text styles are mirrored in the design tool; 17 library components and 10 site-only components are inventoried for the six screens of the flows.

## Sources

- `DESIGN-SYSTEM.md` of the perfectui repository (generated from the shipped 1.0 stylesheet, read 2026-09-23): §1 foundations, §2 colour roles, §3 styles, §4 components 4.1 to 4.17, §5 interaction states, §6 building this in Figma, §7 trade-offs
- `node_modules/@chrissgon/perfectui/dist/perfectui.css` 1.0.0-beta.0: `:root` custom properties `--pui-bg`, `--pui-bg-muted`, `--pui-bg-emphasis`, `--pui-text`, `--pui-text-muted`, `--pui-border`, `--pui-theme`, `--pui-success`, `--pui-warn`, `--pui-error`, `--pui-muted`, `--pui-radius` (0.375rem), `--pui-space` (0.25rem), `--pui-font-size` (0.875rem), `--pui-border-width` (1px); colour contract `--pui-color`, `--pui-on-color`, `--pui-edge`, `--pui-ink`
- `MIGRATION.md` of the perfectui repository, "Known trade-offs" (solid theme, success and warn labels between 3.2:1 and 3.5:1 in light mode)
- `docs/design/flows.md`: SCREEN-1 to SCREEN-6 and their regions and states
- `docs/product/prd.md`: M-4 quality targets; `docs/product/specs/landing-and-site-shell.md`: REQ-7 to REQ-9
- `docs/workbench/state.md` decisions of 2026-09-23: no brand phase, logo and default theme colour kept; typography Inter and Fira Code (user); design in the design-tool draft "PerfectUI-Doc"
- Contrast ratios computed with `scripts/contrast.py` of the design-system skill (WCAG 2.x relative luminance), 2026-09-23
- Tailwind CSS default breakpoints (the site's utility layer): sm 640, md 768, lg 1024, xl 1280 (tailwindcss.com, known defaults of v4; the site's utility layer per brief decision 3)

## Ownership

- Colour roles, styles, spacing, radii, border, component anatomy and states: the perfectui library (`DESIGN-SYSTEM.md`), mirrored verbatim; the site never edits a mirrored value. When the library changes, the mirror is regenerated, not patched.
- Type roles, layout, site-only components and the rules for using library tokens on the site: this document.

## Colour

| Token | Light | Dark | Role | Source |
|-------|-------|------|------|--------|
| `--pui-bg` (page/bg) | #FFFFFF | #000000 | page background, label on a solid fill | DESIGN-SYSTEM §1.1 |
| `--pui-bg-muted` (page/bg-muted) | #F3F4F6 | #111827 | card headers, table footers, addons, stripes, hover rows | DESIGN-SYSTEM §1.1 |
| `--pui-bg-emphasis` (page/bg-emphasis) | #E5E7EB | #1F2937 | third level; the site uses it for the code block background | DESIGN-SYSTEM §1.1; site rule below |
| `--pui-text` (page/text) | #000000 | #FFFFFF | body text | DESIGN-SYSTEM §1.1 |
| `--pui-text-muted` (page/text-muted) | #6B7280 | #9CA3AF | secondary text | DESIGN-SYSTEM §1.1 |
| `--pui-border` (page/border) | #D1D5DB | #374151 | every border without a role colour | DESIGN-SYSTEM §1.1 |
| `--pui-theme` (theme/fill) | #0092CD | #07B6F0 | brand colour; also the site's link and focus-ring colour | DESIGN-SYSTEM §1.1; state decision (theme colour kept) |
| theme/on-fill | #FFFFFF | #000000 | label on a solid theme fill | DESIGN-SYSTEM §6.1 |
| theme/fill-hover | #007AAD | #48BFF2 | solid theme fill under the pointer | DESIGN-SYSTEM §6.1 |
| theme/edge | #0092CD | #07B6F0 | theme border | DESIGN-SYSTEM §6.1 |
| theme/ink | #00628B | #6BC9F5 | theme text for soft, outline and link | DESIGN-SYSTEM §6.1 |
| `--pui-success` (success/fill) | #16A34A | #22C55E | positive state | DESIGN-SYSTEM §1.1 |
| success/on-fill | #FFFFFF | #000000 | label on success | DESIGN-SYSTEM §6.1 |
| success/fill-hover | #11893D | #50CD73 | hover | DESIGN-SYSTEM §6.1 |
| success/edge | #16A34A | #22C55E | border | DESIGN-SYSTEM §6.1 |
| success/ink | #0B6E2F | #71D588 | text | DESIGN-SYSTEM §6.1 |
| `--pui-error` (error/fill) | #DC2626 | #EF4444 | destructive state, invalid fields | DESIGN-SYSTEM §1.1 |
| error/on-fill | #FFFFFF | #000000 | label on error | DESIGN-SYSTEM §6.1 |
| error/fill-hover | #B91E1E | #F5615B | hover | DESIGN-SYSTEM §6.1 |
| error/edge | #DC2626 | #EF4444 | border | DESIGN-SYSTEM §6.1 |
| error/ink | #951616 | #FA7B73 | text | DESIGN-SYSTEM §6.1 |
| `--pui-warn` (warn/fill) | #D97706 | #F59E0B | caution state | DESIGN-SYSTEM §1.1 |
| warn/on-fill | #FFFFFF | #000000 | label on warn | DESIGN-SYSTEM §6.1 |
| warn/fill-hover | #B76304 | #F7AA45 | hover | DESIGN-SYSTEM §6.1 |
| warn/edge | #D97706 | #F59E0B | border | DESIGN-SYSTEM §6.1 |
| warn/ink | #934F03 | #F9B867 | text | DESIGN-SYSTEM §6.1 |
| `--pui-muted` (muted/fill) | #6B7280 | #9CA3AF | neutral state | DESIGN-SYSTEM §1.1 |
| muted/on-fill | #FFFFFF | #000000 | label on muted | DESIGN-SYSTEM §6.1 |
| muted/fill-hover | #595F6B | #A7AEB8 | hover | DESIGN-SYSTEM §6.1 |
| muted/edge | #6B7280 | #9CA3AF | border | DESIGN-SYSTEM §6.1 |
| muted/ink | #464B55 | #B4B9C3 | text | DESIGN-SYSTEM §6.1 |
| surface/fill | #FFFFFF | #000000 | follows the page background (the usual secondary button) | DESIGN-SYSTEM §2, §6.1 |
| surface/on-fill | #000000 | #FFFFFF | label on surface | DESIGN-SYSTEM §6.1 |
| surface/fill-hover | #D7D7D7 | #060606 | hover | DESIGN-SYSTEM §6.1 |
| surface/edge | #D1D5DB | #374151 | border | DESIGN-SYSTEM §6.1 |
| surface/ink | #000000 | #FFFFFF | text | DESIGN-SYSTEM §6.1 |
| inverse/fill | #000000 | #FFFFFF | opposite of the page background | DESIGN-SYSTEM §2, §6.1 |
| inverse/on-fill | #FFFFFF | #000000 | label on inverse | DESIGN-SYSTEM §6.1 |
| inverse/fill-hover | #060606 | #D7D7D7 | hover | DESIGN-SYSTEM §6.1 |
| inverse/edge | #000000 | #FFFFFF | border | DESIGN-SYSTEM §6.1 |
| inverse/ink | #000000 | #FFFFFF | text | DESIGN-SYSTEM §6.1 |

Soft tints are opacities of the role fill (15%, 22% on hover) and outline hover is the fill at 10%, never separate tokens (DESIGN-SYSTEM §6.2). The stylesheet's `--pui-shade` is the internal hover shift (a solid fill moved 12% toward `--pui-text`, DESIGN-SYSTEM §3) and `--pui-color`, `--pui-on-color`, `--pui-edge`, `--pui-ink` are the per-element colour contract set by the colour classes; none of them is a token to set.

Site rules for using these tokens (this document): body prose uses `page/text` on `page/bg`; secondary prose uses `page/text-muted` on `page/bg` only, never on `page/bg-muted` (4.39:1, below AA); links and the focus ring use `theme/ink` for text and `theme/fill` for the ring; site-only components never use a solid `theme`, `success` or `warn` fill under text smaller than 19 px bold or 24 px regular, because those labels sit at 3.2 to 3.5:1 in light mode (library trade-off); the code block uses `page/bg-emphasis` as background with `page/text` as foreground; the token colours of highlighted code are OPEN-1.

## Contrast

| Text token | On background | Light ratio | Dark ratio | AA |
|------------|---------------|-------------|------------|----|
| page/text | page/bg | 21.00:1 | 21.00:1 | pass |
| page/text-muted | page/bg | 4.83:1 | 8.27:1 | pass |
| page/text | page/bg-muted | 19.08:1 | 17.74:1 | pass |
| page/text-muted | page/bg-muted | 4.39:1 | 6.99:1 | fail in light (site rule: not used for text) |
| theme/on-fill | theme/fill (solid button label) | 3.50:1 | 8.96:1 | fail in light for text under 24 px (library trade-off, MIGRATION.md); pass as interface colour (3:1) |
| success/on-fill | success/fill | 3.30:1 | 9.22:1 | fail in light for text (library trade-off); pass as interface colour |
| error/on-fill | error/fill | 4.83:1 | 5.58:1 | pass |
| warn/on-fill | warn/fill | 3.19:1 | 9.78:1 | fail in light for text (library trade-off); pass as interface colour |
| muted/on-fill | muted/fill | 4.83:1 | 8.27:1 | pass |
| theme/ink | page/bg | 6.73:1 | 11.30:1 | pass |
| theme/ink | theme soft tint (#D9EFF8 / #011B24) | 5.66:1 | 9.55:1 | pass |
| success/ink | page/bg | 6.39:1 | 11.58:1 | pass |
| error/ink | page/bg | 8.73:1 | 8.15:1 | pass |
| warn/ink | page/bg | 6.25:1 | 12.08:1 | pass |
| muted/ink | page/bg | 8.76:1 | 10.67:1 | pass |
| page/border (interface, 3:1) | page/bg | 1.47:1 | 2.04:1 | fail (decorative borders; site-only controls that need a visible boundary add `page/text-muted` at the boundary or a fill, see Components) |
| theme/fill as focus ring (interface, 3:1) | page/bg | 3.50:1 | 8.96:1 | pass |

## Type

- Typeface: Inter for text and interface, Fira Code for code; fallback `system-ui, sans-serif` and `ui-monospace, monospace`; both self-hosted with `font-display: swap`. Source: user answer 2026-09-23.
- Reading width: 72ch of `site/body` (about 720 px at 16 px), content column; the page frame is 1280 px wide at the `xl` breakpoint. Source: this document (recommended; OPEN-2).

| Role | Size | Line height | Weight | Source |
|------|------|-------------|--------|--------|
| text/body (component text) | 14 px | 17.5 px | inherited (Regular) | DESIGN-SYSTEM §1.4 |
| text/small (badges, tooltips, field labels) | 12 px | 15 px | inherited (Regular) | DESIGN-SYSTEM §1.4 |
| text/strong (table header) | 14 px | normal | 600 (Semi Bold) | DESIGN-SYSTEM §1.4 |
| site/display (landing value proposition) | 44 px | 52 px | 700 | this document: base 14 px × 1.25 per step, rounded to the 4 px grid (OPEN-2) |
| site/h1 (page title) | 36 px | 44 px | 600 | this document (OPEN-2) |
| site/h2 (section) | 28 px | 36 px | 600 | this document (OPEN-2) |
| site/h3 (subsection) | 22 px | 28 px | 600 | this document (OPEN-2) |
| site/lead (landing paragraph) | 18 px | 28 px | 400 | this document (OPEN-2) |
| site/body (prose) | 16 px | 24 px | 400 | this document (OPEN-2) |
| site/code (code blocks and inline code) | 14 px | 20 px | 400, Fira Code | this document; 0.23 site used Fira Code at 14 px (codebase map) |

## Space, radii, borders, elevation

| Token | Value | Role | Source |
|-------|-------|------|--------|
| space/2 | 2 px | badge vertical padding | DESIGN-SYSTEM §1.3 |
| space/4 (`--pui-space`) | 4 px | unit; gap inside a button, dropdown padding | DESIGN-SYSTEM §1.2, §1.3 |
| space/5 | 5 px | tooltip vertical padding | DESIGN-SYSTEM §1.3 |
| space/6 | 6 px | input vertical padding | DESIGN-SYSTEM §1.3 |
| space/7 | 7 px | badge horizontal padding | DESIGN-SYSTEM §1.3 |
| space/8 | 8 px | button, list item, table cell, card header vertical padding | DESIGN-SYSTEM §1.3 |
| space/10 | 10 px | tooltip horizontal padding | DESIGN-SYSTEM §1.3 |
| space/12 | 12 px | chip and input horizontal padding, addon padding, card content gap | DESIGN-SYSTEM §1.3 |
| space/16 | 16 px | button, list item, table cell, card header horizontal padding; card content padding | DESIGN-SYSTEM §1.3 |
| space/24 | 24 px | floating element distance from the viewport edge; site section gap on narrow screens | DESIGN-SYSTEM §1.3; this document |
| space/28 | 28 px | end padding of a select | DESIGN-SYSTEM §1.3 |
| space/32 | 32 px | modal margin from the viewport edge | DESIGN-SYSTEM §1.3 |
| radius/6 (`--pui-radius`) | 6 px | buttons, chips, badges, inputs, list items, accordion items, dropdowns, tooltips | DESIGN-SYSTEM §1.5 |
| radius/5 | 5 px | inner concentric corner inside a bordered container | DESIGN-SYSTEM §1.5 |
| radius/9 | 9 px | cards; site: code block and example block | DESIGN-SYSTEM §1.5; this document |
| radius/3 | 3 px | checkboxes | DESIGN-SYSTEM §1.5 |
| radius/full | 9999 px | pills, radios, switches, timeline icons | DESIGN-SYSTEM §1.5 |
| border/1 (`--pui-border-width`) | 1 px | every border and group overlap | DESIGN-SYSTEM §1.2 |
| elevation | none | the library uses no shadows; the site uses none either (dialogs use a backdrop, dropdowns a border) | DESIGN-SYSTEM §4.8, §4.9 (no shadow listed); this document |

## Layout

| Token | Value | Role | Source |
|-------|-------|------|--------|
| breakpoint/sm | 640 px | single column below; two columns above | Tailwind defaults (the site's utility layer) |
| breakpoint/md | 768 px | sidebar becomes a toggleable panel below | flows SCREEN-2 Breakpoints; Tailwind defaults |
| breakpoint/lg | 1024 px | on-page headings list shown beside content above | flows SCREEN-2; Tailwind defaults |
| breakpoint/xl | 1280 px | page frame max width | this document (OPEN-2) |
| layout/header-height | 56 px | site header | this document (OPEN-2) |
| layout/sidebar-width | 272 px | documentation navigation column (17 × 16 px) | this document (OPEN-2) |
| layout/toc-width | 208 px | on-page headings column | this document (OPEN-2) |
| layout/gutter | 16 px narrow, 32 px from md | page horizontal padding | this document (OPEN-2) |
| layout/content-width | 72ch of site/body | reading column | Type section |
| target/min | 24 × 24 px | minimum interactive target; 40 × 40 for header controls | WCAG 2.2 AA 2.5.8; skill reference |
| focus/ring | 2 px, `theme/fill`, 2 px outside, follows the radius | keyboard focus | DESIGN-SYSTEM §5 |
| motion | 150 ms on colour, border and text; none under reduced motion | transitions | DESIGN-SYSTEM §5 |

## Components

| Component | Owner | Variants | States | Screens | Source |
|-----------|-------|----------|--------|---------|--------|
| Button (`pui-btn`) | library | style × colour (4 × 7), rounded | default, hover, focus, disabled | SCREEN-1, SCREEN-3, SCREEN-4 | DESIGN-SYSTEM §4.1, §5 |
| Chip (`pui-chip`) | library | style × colour | default, hover, focus, disabled | SCREEN-2 (examples), SCREEN-3 (version label) | DESIGN-SYSTEM §4.2 |
| Badge (`pui-badge`) | library | style × colour | default | SCREEN-2 (since and changed badges) | DESIGN-SYSTEM §4.3; content-model spec REQ-7 |
| Card (`pui-card`, header, content) | library | none | default | SCREEN-1 (showcase), SCREEN-2 (examples) | DESIGN-SYSTEM §4.4 |
| List (`pui-list`, item) | library | striped, hoverable | default, hover | SCREEN-4 (results), SCREEN-5 (index) | DESIGN-SYSTEM §4.5 |
| Table (`pui-table`) | library | striped, hoverable | default | SCREEN-6 (mapping tables), SCREEN-2 | DESIGN-SYSTEM §4.6 |
| Accordion (`pui-accordion`) | library | none | open, closed, focus | SCREEN-2 (examples), SCREEN-3 (narrow navigation sections) | DESIGN-SYSTEM §4.7 |
| Modal (`pui-modal`) | library | none | open, closed | SCREEN-4 (search dialog container) | DESIGN-SYSTEM §4.8 |
| Dropdown (`pui-dropdown`) | library | none | open, closed | SCREEN-3 (version switch) | DESIGN-SYSTEM §4.9 |
| Tooltip (`pui-tooltip`) | library | none | shown, hidden | SCREEN-3 (icon-only controls) | DESIGN-SYSTEM §4.10 |
| Field group (`pui-field-group`) | library | none | default, invalid | SCREEN-2 (examples) | DESIGN-SYSTEM §4.11 |
| Input (`pui-input`) | library | none | default, focus, disabled, invalid | SCREEN-4 (search input) | DESIGN-SYSTEM §4.12 |
| Input group (`pui-input-group`, addon) | library | none | default, focus | SCREEN-1 (install command with copy control) | DESIGN-SYSTEM §4.13 |
| Checkbox, radio, switch | library | none | unchecked, checked, focus, disabled | SCREEN-3 (mode toggle as switch), SCREEN-2 | DESIGN-SYSTEM §4.14 |
| Timeline (`pui-timeline`) | library | none | default | SCREEN-2 (examples) | DESIGN-SYSTEM §4.15 |
| Group (`pui-group-row`, col, responsive) | library | row, column, responsive | default | SCREEN-1, SCREEN-2 | DESIGN-SYSTEM §4.16 |
| Float (`pui-float`) | library | none | default | SCREEN-2 (examples) | DESIGN-SYSTEM §4.17 |
| Navigation item | site | level 1 section, level 2 page | default, hover, current, focus | SCREEN-2, SCREEN-5 | flows SCREEN-2 regions |
| On-page heading link | site | level 2, level 3 | default, current, focus | SCREEN-2, SCREEN-6 | flows SCREEN-2 regions |
| Code block | site | with language label, with copy control, diff | default, copied, focus | SCREEN-2, SCREEN-6 | content-model spec REQ-10; migration-guide spec REQ-4 |
| Example block | site | preview tab, code tab | default, copied | SCREEN-1, SCREEN-2 | content-model spec REQ-3; landing spec REQ-5 |
| Search result | site | page match, section match | default, selected, focus | SCREEN-4 | search spec REQ-3, REQ-7 |
| Version switch item | site | latest, older | default, current, focus | SCREEN-3 | content-model spec REQ-5; flows IA-11 |
| Version notice | site | none | shown | SCREEN-5 | content-model spec REQ-6 |
| Callout | site | note, warning | default | SCREEN-2, SCREEN-6 | migration-guide spec (trade-offs), this document |
| Copy control | site | icon-only, with label | default, copied, focus, unavailable | SCREEN-1, SCREEN-2 | landing spec REQ-3, EDGE-9 |
| Keyboard hint | site | none | default | SCREEN-4 | search spec REQ-7 |

Site-only controls that need a visible boundary (input in the search dialog, copy control) use `page/text-muted` for the boundary or a `page/bg-muted` fill, because `page/border` sits below 3:1 (Contrast).

## Design tool

- File: the perfectui project file (key szD991W25tQxPuqhfRektk), page "Site" for the website screens. An earlier build in the draft 0aZSp3JcotPUKeduf8BCzi (collection, text styles, foundations page) is superseded and not reused.
- Collections: `pui` already exists in the file with modes `light` and `dark` and 66 variables: the 59 of DESIGN-SYSTEM §6 plus one `<role>/soft-fill` per role (the 15% tint flattened, DESIGN-SYSTEM §3.1 and §3.2); values verified against the document on 2026-09-23.
- Styles: the library's `text/body`, `text/small`, `text/strong` exist; the seven `site/*` text styles (Inter and Fira Code) are added to the file for the screens; the ten legacy `PerfectUI/doc/*` paint styles (glows, glass, tags) belong to the UI kit's own documentation and are not used by the site.
- Components: the file already holds the library's Button (28 variants, style × colour, Label), Badge (28), Card (6, Type), Accordion Item (12) and Dropdown (8); screens use them as instances. Library components the file lacks (chip, list, table, modal, input, checkbox and switch, tooltip, timeline, group, float) are drawn as frames bound to the variables when a screen needs them, because documenting the library in the design tool is out of scope (user, 2026-09-23). Site-only components (Components table, owner `site`) are built as components on the "Site" page as the screens need them.
- Validation: per screen, structural evidence returned by the writes and one screenshot; recorded by design-ui.

## Assumptions

- ASSUMPTION-1: The library's `light-dark()` values are the light and dark mode values of the Figma variables; the site sets `data-pui-mode` so both modes exist. Safe because: `perfectui.css` `:root` declares every colour with `light-dark()` and `color-scheme: light dark`.
- ASSUMPTION-2: No elevation tokens are needed because neither the library nor the six screens use shadows; dialogs rely on a backdrop. Safe because: DESIGN-SYSTEM lists no shadow, and the flows' screens have no floating card over content besides the dropdown and the dialog.

## Open questions

- OPEN-1: Colour theme for highlighted code (the token colours inside code blocks) in light and dark modes. Blocks: the code block component's final look, not the layout. Recommended: derive from the role inks (`theme/ink` keywords, `success/ink` strings, `warn/ink` numbers, `muted/ink` comments, `page/text` plain) so code uses the same seven roles as everything else and both modes are covered without a third palette.
- OPEN-2: The site-owned values marked "this document (OPEN-2)": type scale (base 14 × 1.25), reading width 72ch, page frame 1280, header 56, sidebar 272, headings column 208, gutters 16/32. Blocks: nothing; design-ui uses them as defaults. Recommended: approve as proposed; each derives from the library's 4 px unit and Tailwind's default breakpoints.

## Readiness

- Ready for design-ui: yes for tokens and type; the component build in the design tool (phase 3) runs next, and OPEN-1 and OPEN-2 block no screen.
