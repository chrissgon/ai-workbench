## 1. Foundations

### 1.1 Color tokens

| Token | Light | Dark | What it is for |
| --- | --- | --- | --- |
| `--pui-bg` | #FFFFFF | #000000 | Page background, and the label on a solid fill |
| `--pui-bg-muted` | #F3F4F6 | #111827 | Card headers, table footers, addons, stripes, hover rows |
| `--pui-bg-emphasis` | #E5E7EB | #1F2937 | A third level, for authors — no component in the library uses it |
| `--pui-text` | #000000 | #FFFFFF | Body text |
| `--pui-text-muted` | #6B7280 | #9CA3AF | Secondary text: help messages, table headers, card headers |
| `--pui-border` | #D1D5DB | #374151 | Every border that is not carrying a color |
| `--pui-theme` | #0092CD | #07B6F0 | Brand color |
| `--pui-success` | #16A34A | #22C55E | Positive state |
| `--pui-error` | #DC2626 | #EF4444 | Destructive state and invalid fields |
| `--pui-warn` | #D97706 | #F59E0B | Caution state |
| `--pui-muted` | #6B7280 | #9CA3AF | Neutral state, the old secondary |

### 1.2 The four base values

| Base | Value | Generates |
| --- | --- | --- |
| Spacing unit | 4px | Every padding and gap, as multiples |
| Font size | 14px | Component text, and the small sizes as ratios |
| Radius | 6px | Every corner |
| Border width | 1px | Every border and the overlap inside groups |

### 1.3 Spacing scale

Multiples of the 4px unit. Nothing in the library uses a value outside this
scale.

