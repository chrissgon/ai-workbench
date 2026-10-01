# plinthui design system

The token specification the plinthui component library ships. Every value below is a CSS custom
property defined in `plinthui.css`; components read only these properties.

## 1. Foundations

### 1.1 Color tokens

| Token | Light | Dark | What it is for |
| --- | --- | --- | --- |
| `--plu-bg` | #FFFFFF | #000000 | Page background, and the label on a solid fill |
| `--plu-bg-muted` | #F3F4F6 | #111827 | Card headers, table footers, addons, stripes, hover rows |
| `--plu-bg-emphasis` | #E5E7EB | #1F2937 | A third level, for authors; no component in the library uses it |
| `--plu-text` | #000000 | #FFFFFF | Body text |
| `--plu-text-muted` | #6B7280 | #9CA3AF | Secondary text: help messages, table headers, card headers |
| `--plu-border` | #D1D5DB | #374151 | Every border that is not carrying a color |
| `--plu-theme` | #0092CD | #07B6F0 | Theme color: solid buttons, links, the focus ring |
| `--plu-success` | #16A34A | #22C55E | Positive state |
| `--plu-error` | #DC2626 | #EF4444 | Destructive state and invalid fields |
| `--plu-warn` | #D97706 | #F59E0B | Caution state |
| `--plu-muted` | #6B7280 | #9CA3AF | Neutral state |

### 1.2 The four base values

The same in light and dark.

| Token | Value | Generates |
| --- | --- | --- |
| `--plu-unit` | 4px | Every padding and gap, as multiples |
| `--plu-font-size` | 14px | Component text; small text is 12px, large text is 16px |
| `--plu-radius` | 6px | Every corner |
| `--plu-border-width` | 1px | Every border and the overlap inside groups |

### 1.3 Spacing scale

Multiples of `--plu-unit`: 4px, 8px, 12px, 16px, 24px, 32px, 48px. Nothing in the library uses a
value outside this scale.

### 1.4 Type

The library sets no font family: components inherit the family of the page. Component text is
`--plu-font-size` with line height 1.5 and weight 400; labels and buttons use weight 500.

### 1.5 Elevation

The library has one shadow, used by the dialog: `0 8px 24px rgb(0 0 0 / 0.16)`. Everything else is flat
and separated by `--plu-border`.

## 2. Components

Every component takes a style axis and a color axis. Styles: `solid`, `outline`, `ghost`. Colors:
`theme`, `success`, `error`, `warn`, `muted`.

| Component | Variants | States |
| --- | --- | --- |
| Button | style: solid, outline, ghost; color: the five colors; size: sm, md, lg | default, hover, focus-visible, active, disabled, loading |
| Input | size: sm, md, lg; with addon | default, hover, focus-visible, disabled, invalid |
| Badge | style: solid, outline; color: the five colors | default |
| Card | with header, with footer | default |
| Table | striped, hover rows | default, empty |
| Tabs | underline, pills | default, hover, focus-visible, selected, disabled |
| Dialog | size: sm, md, lg | closed, open |
| Alert | color: the five colors | default |
