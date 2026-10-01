# Messaging: plinthui 1.0 documentation site

- Owner: mkt-messaging
- Status: approved
- Date: 2026-09-23
- Page: landing (`/`)

## Summary

The landing speaks to front-end developers who evaluate a CSS component library for a new project. It promises a complete set of components at a size they can verify.

## Sources

- `docs/product/prd.md` (2026-09-23): U-1, U-2, F-3
- Size measured with `gzip -9 -c dist/plinthui.css | wc -c` on 1.0.0-beta.0, 2026-09-23: 6,214 bytes
- Library `docs/README.md`: 17 components
- User answers of 2026-09-23 (promise wording, share-image texts)

## Audience

- U-1: evaluating a component library for a new project; fears: a heavy dependency that is hard to remove. Source: PRD U-1
- U-2: maintaining a project on 0.19; fears: a migration that breaks the interface. Source: PRD U-2

## Promise

Seventeen components in 6 KB of CSS. Source: size measurement; library README; user answer 2026-09-23.

## Voice

- Plain statements with a number; no superlatives. Source: user answer 2026-09-23
- Sentence case, no exclamation marks. Source: user answer 2026-09-23

## Proof points

- PROOF-1: The stylesheet is 6,214 bytes gzipped. Evidence: measurement. Method: `gzip -9 -c dist/plinthui.css | wc -c`. Date: 2026-09-23. Source: build output of 1.0.0-beta.0
- PROOF-2: The library ships 17 components. Evidence: count of the component sections. Method: read in library `docs/README.md`, Components and Forms. Date: 2026-09-23. Source: library README

## Sections

- SECTION-1: Value proposition. Purpose: say what plinthui is. Proof: PROOF-1. Headline: Seventeen components in 6 KB of CSS. Body: plinthui is a CSS component library with no JavaScript to load and no build step to configure. Demo: the install command with a copy control. CTA: Read the docs → /docs. Source: user answer 2026-09-23
- SECTION-2: Size. Purpose: let the evaluator verify the size. Proof: PROOF-1. Headline: Measure it yourself. Body: 6,214 bytes gzipped, measured on every release with one command. Demo: the size block with the version and the command. CTA: none. Source: size measurement
- SECTION-3: Migration. Purpose: reassure 0.19 users. Proof: PROOF-2. Headline: Coming from 0.19? Body: The migration guide maps every 0.19 class to its 1.0 name. Demo: none. CTA: Open the migration guide → /docs/v1/getting-started/migrating-from-0-19. Source: PRD U-2

## Share images

- Landing card. Title: Seventeen components in 6 KB of CSS. Label: plinthui 1.0. Source: user answer 2026-09-23
- Documentation card (one per page, generated from a template). Fields: the page title and the section name, both from the page's frontmatter; label: plinthui docs. Source: user answer 2026-09-23

## Taglines

- Seventeen components in 6 KB of CSS
- The component library you can read in one sitting
- Small enough to verify

## Words

- Use: components, classes, bytes, measured. Source: user answer 2026-09-23
- Avoid: blazing, lightweight, modern, simply

## Open questions

- none

## Readiness

- Ready for design-brief: yes
