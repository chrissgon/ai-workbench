# Visual identity: Dana Example

- Owner: brand-identity
- Status: approved (2026-09-27)
- Date: 2026-09-27
- Reads: docs/brand/strategy.md (approved), docs/brand/voice.md (confirmed), tinykv's design tokens
- First piece: profile cover; variant B chosen and applied on 2026-09-27

## In one sentence
The look of tinykv carried over to the person: dark first, one warm accent, no decoration [1]

## Base
tinykv's design tokens; dark mode by default [1]

## Colours
| Role | Dark | Light | Origin (token or `brand`) |
|------|------|-------|---------------------------|
| Background | #0B0B0C | #FFFFFF | --tk-bg |
| Text | #F4F4F5 | #18181B | --tk-fg |
| Accent | #FBBF24 | #F59E0B | --tk-accent |

Usage rules: the dark accent #FBBF24 on #0B0B0C is 11.79:1, fine for text; the light accent #F59E0B on white is 2.15:1, only for graphics, never for text [2].

## Typography
| Use | Typeface | Weight | Licence (URL) |
|-----|----------|--------|---------------|
| All text | System font stack; no web fonts | 400, 700 | none needed |

## Elements
- A monospaced key-value line ("key = value") as the only ornament [1]
- Never used: gradients, stock photos, emojis in images [1]

## Formats
| Piece | Size | Safe area | Source |
|-------|------|-----------|--------|
| Profile cover | 1584 x 396 | 420 px from the left kept free | piece template, secondary, unverified |

Production: HTML rendered with `render.py` (script of brand-identity); sources in docs/brand/pieces/

## Tokens
```brand-tokens
{"mode_default": "dark", "color": {"bg": {"dark": "#0B0B0C", "light": "#FFFFFF"}, "fg": {"dark": "#F4F4F5", "light": "#18181B"}, "accent": {"dark": "#FBBF24", "light": "#F59E0B"}}, "font": {"body": "system-ui"}}
```

## Assumptions
- none

## Sources
[1] Decisions in docs/workbench/state.md, 2026-09-27.
[2] contrast.py output, 2026-09-27.
