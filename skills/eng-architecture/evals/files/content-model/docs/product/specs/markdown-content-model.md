# Feature specification: markdown-content-model

- Owner: product-feature-spec
- Status: approved
- Date: 2026-03-10
- Feature of: Plinth UI documentation site, phase P-1, F-2 "Guide" and F-3 "Component pages"

## Summary

Maintainers write every guide and component page as a Markdown file with a few metadata fields; the
site turns each file into a page, builds the sidebar from the files and publishes a list of pages for
the search dialog.

## Goal and users

- Problem: every new page is a hand-written `.astro` file plus an edit to the sidebar list in the layout, so pages are added late and the sidebar goes out of date. Source: user, 2026-03-06
- Users: the library's maintainers, who write the documentation (PRD U-3)
- Success: adding a page is one new Markdown file and no other change; observed as a pull request that touches only that file and produces the page, its sidebar entry and its entry in the page list.

## Scope

- In: Markdown files for the Guide and Components sections, their metadata, the pages built from them, the generated sidebar, the generated page list.
- Out: the landing page (stays hand-written); the search dialog itself (its own specification, it only reads the page list); versioned documentation; translations; live component examples inside Markdown.

## Sources

- docs/engineering/architecture.md (codebase map, 2026-03-09)
- docs/workbench/state.md, decisions of 2026-03-06 and 2026-03-10
- User answers, 2026-03-10 (metadata fields, limits, failure behaviour)

## Functional requirements

- REQ-1: Every Markdown file in `content/guide/` becomes a page at `/guide/<slug>` and every Markdown file in `content/components/` becomes a page at `/components/<slug>`, where `<slug>` is the file name without its extension. Source: state decision 2026-03-10
- REQ-2: Every file declares in its front matter `title` (text, 1 to 60 characters), `description` (text, 1 to 160 characters) and `order` (whole number, 1 or greater); files in `content/components/` also declare `status`, one of `stable`, `beta`, `deprecated`. Source: user answer 2026-03-10
- REQ-3: Each page renders inside the existing documentation layout with the file's `title` as the page title and `description` as the meta description; a component page shows its `status` next to the title. Source: user answer 2026-03-10
- REQ-4: The sidebar is generated from the files: two groups, "Guide" then "Components", each listing its pages by `order` ascending, with the current page marked. Source: user, 2026-03-06
- REQ-5: The build writes `/pages.json`, a list with one entry per page holding `title`, `section`, `url` and `description`, in sidebar order. Source: user answer 2026-03-10
- REQ-6: The two hand-written pages are replaced by Markdown files and the hard-coded sidebar list is removed; `/guide/getting-started` and `/components/button` keep answering with the same titles. Source: state decision 2026-03-10

## Non-functional requirements

- NFR-1: A full build with 60 Markdown pages finishes in 30 seconds or less on the CI runner. Source: user answer 2026-03-10
- NFR-2: A documentation page loads 0 bytes of client JavaScript because of this feature. Source: codebase map, Summary; state decision 2026-03-06

## Constraints

- technical: Astro 5.13.2 with static output; no server at run time. Source: state decisions 2026-03-06
- technical: no new runtime or build dependency without asking. Source: state decision 2026-03-10
- operational: addresses have no trailing slash. Source: `astro.config.mjs`

## Edge cases

- EDGE-1: A file lacks a required field or a field breaks its limit (a 61-character title) → the build fails and the message names the file and the field.
- EDGE-2: A component file has a `status` outside the three values → the build fails and the message names the file and the allowed values.
- EDGE-3: Two files of one section have the same `order` → the build succeeds, the two are sorted by `title`, and the build prints a warning naming both files.
- EDGE-4: A section folder has no file → the build succeeds, the group is left out of the sidebar and `/pages.json` has no entry for it.
- EDGE-5: A file name has characters other than lowercase letters, digits and hyphens (`My Page.md`) → the build fails and the message names the file and the rule.
- Categories skipped: concurrency and permissions (a static build has neither); very large inputs beyond 60 pages (the PRD plans fewer than 60 pages for P-1).

## Acceptance criteria

- AC-1:
  Given `content/guide/theming.md` with valid front matter
  When the site is built
  Then `/guide/theming` exists with the file's title as the page title and its description as the meta description
  Covers: REQ-1, REQ-2, REQ-3
- AC-2:
  Given guide files with `order` 2 and 1 and a component file with `status: beta`
  When the site is built
  Then the sidebar lists "Guide" before "Components", the guide pages in order 1 then 2, the current page is marked, and the component page shows "beta" next to its title
  Covers: REQ-3, REQ-4
- AC-3:
  Given 3 Markdown files across the two sections
  When the site is built
  Then `/pages.json` holds exactly 3 entries, each with `title`, `section`, `url` and `description`, in sidebar order
  Covers: REQ-5
- AC-4:
  Given the repository after the change
  When the site is built
  Then `/guide/getting-started` and `/components/button` answer with the titles "Getting started" and "Button", no `.astro` file exists under `src/pages/guide/` or `src/pages/components/` for a single page, and the layout holds no hard-coded page list
  Covers: REQ-6
- AC-5:
  Given a file with a 61-character title, a component file with `status: experimental`, and a file named `My Page.md`, one at a time
  When the site is built
  Then each build fails with a message naming the file and the field, the allowed values or the naming rule
  Covers: REQ-2
- AC-6:
  Given 60 generated Markdown pages
  When the site is built on the CI runner
  Then the build takes 30 seconds or less and no documentation page references a script file added by this feature
  Covers: NFR-1, NFR-2
- AC-7:
  Given two guide files with `order: 3` and an empty `content/components/` folder
  When the site is built
  Then the build succeeds with a warning naming both files, the two are sorted by title, and the sidebar and `/pages.json` have no "Components" group
  Covers: REQ-4, REQ-5

## Assumptions

- ASSUMPTION-1: Maintainers write standard Markdown with fenced code blocks and no embedded components. Safe because: live examples are out of scope and the two existing pages use only headings, paragraphs and code.

## Open questions

- none

## Readiness

- Ready for architecture: yes
