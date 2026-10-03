# Design brief: og-image

- Owner: design-brief
- Status: approved
- Date: 2026-03-04
- Type: image
- For: the share image (og:image) of the Plinth UI documentation site: one card for the landing and one per documentation page, from one template
- Values: inline
- Direction: open: three directions
- Lint: ok (2026-03-04)

## Summary

Explore three directions for the share card of the Plinth UI documentation site at 1200 × 630 px in light mode. The texts, the colours, the typefaces and the mark are fixed; the composition, the scale of the title and the use of the mark are open.

## Sources

- docs/design/design-system.md (colours, type, spacing, 2026-03-02)
- docs/design/flows.md (page titles and sections, 2026-03-02)
- library/logo.svg (the mark)
- User answer, 2026-03-03: the tagline on the card and the address shown

## Subject

Plinth UI is a tiny CSS and JavaScript component library that works with any framework. It ships buttons, inputs, dialogs, cards and badges as plain classes over the browser's own elements, with no runtime dependency. Its documentation site has a landing page, a guide and one page per component.

When someone pastes a link to the site in a chat or a social feed, the preview shows this card. Example: a link to the Button page shows a card with the section "Components", the title "Button", the mark and the site address.

## Audience and voice

- Front-end developers who see the card at thumbnail size in a feed and decide in a second whether the link is worth opening; they distrust heavy libraries and marketing claims.
- Voice: plain, technical, short sentences, no exclamation marks.
- Words to use: tiny, CSS, JavaScript, components, no dependencies.
- Words to avoid: revolutionary, blazing, next-generation, beautiful.

## Creative direction

No previous version.

References as attitudes: the scale of a book cover (one thing very large), the flatness of a technical drawing (borders, no shadows), no illustration of people or devices.

- Direction A, "Stacked": the three bars of the mark grow into the composition; the card is built from three stacked horizontal bands and the title sits in the widest one.
- Direction B, "Specimen": the title is set as large as the longest value allows, like a type specimen, on a plain background; the mark and the address are small and stay in one corner.
- Direction C, "Blueprint": the card looks like a component drawn on a grid: a thin border frame, a 48 px grid in the border colour, the title inside an outlined box that reads as a Plinth UI card component.

Every direction keeps the mark, the brand colour as the only accent and the text typeface. Allowed: scaling, cropping and repeating the mark's bars; a grid or borders in the border colour. Not allowed: gradients, shadows, photographs, emoji, a second accent colour, any text not listed under Content.

## Visual language

Colours, light mode only:

| Role | Value |
| --- | --- |
| Background | #FFFFFF |
| Muted background | #F3F4F6 |
| Text | #000000 |
| Muted text | #6B7280 |
| Border | #D1D5DB |
| Brand (the only accent) | #0092CD |

Type: Sans Serif for text (the generic `sans-serif` family of the system) and Monospace for code (the generic `monospace` family). Both are system typefaces: no font file is downloaded. Title weight 700, every other text weight 400 or 500.

Sizes: title between 72 px and 120 px; section label 32 px; tagline 40 px; site address 32 px, set in the code typeface. No text below 32 px, and the title and the tagline never below 40 px.

Space: multiples of 4 px; the safe area is inset 64 px from every edge. Corner radius 6 px, border width 1 px on the Blueprint grid and 2 px on frames.

The mark is three stacked bars, each wider than the one above, in the brand colour:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
  <rect x="14" y="8" width="20" height="10" rx="2" fill="#0092CD"/>
  <rect x="9" y="20" width="30" height="10" rx="2" fill="#0092CD"/>
  <rect x="4" y="32" width="40" height="10" rx="2" fill="#0092CD"/>
</svg>
```

## Content

- **Size:** 1200 × 630 px. Safe area: 64 px inset from every edge; every text and the mark stay inside it.
- **Format:** PNG, under 300 KB.
- **Text:** in order of hierarchy: 1. the title (variable field); 2. the section label (variable field, absent on the landing card); 3. the wordmark "Plinth UI" next to the mark; 4. the tagline "Tiny CSS and JavaScript components. No dependencies." (landing card only; user answer 2026-03-03); 5. the address "plinthui.example" (user answer 2026-03-03). Minimum text size 32 px; title and tagline at least 40 px.
- **Variable fields:**
  - Title: the page title from the flows. On the landing card the title is "Plinth UI components for any framework". Longest documentation title: "Theming with custom properties" (30 characters). The landing title has 38 characters and is the longest value the field must fit, on at most two lines.
  - Section label: "Guide" or "Components"; longest "Components" (10 characters).

## Constraints

- Colours, typefaces and sizes only from Visual language.
- Texts verbatim from Content; no other text on the card.
- Text on its background passes WCAG AA: at least 4.5:1. The brand colour #0092CD on #FFFFFF is 3.5:1, so it is never used for text smaller than the title; white text on a brand-colour band is allowed only at 40 px bold or larger. Muted text #6B7280 is used only on #FFFFFF (4.8:1), never on the muted background (4.4:1).
- The card is a template: the same layout holds the landing card and every documentation page.
- No network request when the card is rendered: system typefaces, the mark inline.

## Deliverables

- Round 1: one image per direction (A, B, C), the landing card, 1200 × 630 px, light mode: three images.
- Round 2: the chosen direction complete: the landing card and three documentation pages ("Getting started", "Theming with custom properties", "Button").

## Evaluation criteria

- CRIT-1: The image is exactly 1200 × 630 px, PNG, under 300 KB.
- CRIT-2: The title reads at 25% of the size (300 × 158 px).
- CRIT-3: The mark, the wordmark "Plinth UI" and the brand colour #0092CD are present, and no other accent colour is used.
- CRIT-4: Every text is verbatim from the brief and no other text appears.
- CRIT-5: The title "Plinth UI components for any framework" fits in at most two lines without overflow or clipping.
- CRIT-6: Every text and the mark stay inside the 64 px safe area.
- CRIT-7: Every text has a contrast of at least 4.5:1 with its background, or is 40 px bold or larger with at least 3:1.

## Attachments

- Send: this brief; library/logo.svg
- Do not send in round 1: any earlier share image of the site

## Prompt

```text
Design a share card (Open Graph image) for the documentation site of Plinth UI, a tiny CSS and
JavaScript component library that works with any framework and has no dependencies.

Size: exactly 1200 x 630 px, light mode, exported as PNG under 300 KB. Keep every text and the mark
inside a safe area inset 64 px from every edge.

Texts, verbatim, in order of importance:
1. Title: "Plinth UI components for any framework" (at most two lines, 72 to 120 px, weight 700)
2. Wordmark next to the mark: "Plinth UI"
3. Tagline: "Tiny CSS and JavaScript components. No dependencies." (at least 40 px)
4. Address: "plinthui.example" (32 px, monospace)
No other text.

Colours: background #FFFFFF, muted background #F3F4F6, text #000000, muted text #6B7280,
border #D1D5DB, brand #0092CD as the only accent. Never use the brand colour for text smaller than
the title. White text on a brand band only at 40 px bold or larger.

Type: the generic sans-serif family for text and the generic monospace family for code.
System typefaces only, no font download.

Mark: three stacked bars, each wider than the one above, in the brand colour; use the attached SVG.

Not allowed: gradients, shadows, photographs, emoji, a second accent colour.

The card is a template: the same layout must also hold a documentation page with a section label
("Guide" or "Components", 32 px) and a title up to 30 characters.

Direction:
```

## Open questions

- none

## Readiness

- Ready for design-execute: yes
