# Design system: Fernleaf

- Owner: design-system
- Status: approved
- Date: 2027-02-10
- Flows: docs/design/flows.md
- Lint: ok (2027-02-10)

## Colour

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| --fl-bg | #FBFAF5 | #14201A | page background |
| --fl-surface | #FFFFFF | #1C2B23 | cards |
| --fl-ink | #1B2A22 | #EEF3EE | text |
| --fl-muted | #55665C | #A9B8AE | secondary text |
| --fl-brand | #2F7A4F | #6FC495 | buttons, links, the leaf of the wordmark |
| --fl-border | #D9DED4 | #2E4136 | card borders |

## Type

- Text: Sans Serif (the system's generic sans-serif family); weights 400 and 600.
- Scale: hero headline 56 px / 64 px, section title 32 px / 40 px, body 18 px / 28 px, caption 14 px / 20 px.

## Space and shape

- Spacing in multiples of 8 px; content width at most 1120 px.
- Radius 12 px on cards and buttons; border 1 px.

## Components

| Component | Screens | Notes |
|-----------|---------|-------|
| Store button | SCREEN-1 | the stores' own badges, never redrawn |
| Benefit card | SCREEN-1 | icon, title, one sentence |

## Contrast

| Pair | Light | Dark | Result |
|------|-------|------|--------|
| --fl-ink on --fl-bg | 14.34:1 | 14.94:1 | pass |
| button text on --fl-brand (#FFFFFF light, #14201A dark) | 5.23:1 | 8.00:1 | pass |

## Assumptions

- none
