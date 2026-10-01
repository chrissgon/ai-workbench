# Feature specification: markdown-content-model

- Owner: product-feature-spec
- Status: approved
- Date: 2026-09-21
- Feature of: docs/product/prd.md, phase P-1 (Plinth UI documentation site, plinthui.example)

## Summary

The documentation pages of the Plinth UI site are written as Markdown files with front matter instead of hand-written HTML pages, so a maintainer adds or edits a page by editing one file.

## Goal and users

- Problem: every documentation page is a hand-written HTML file that repeats the layout; a new component page takes a copy of another page and edits in four places. Source: brief decision 2
- Users: the maintainers of Plinth UI. Source: brief
- Success: a new page is published by adding one Markdown file, and the build fails when a page is malformed.

## Scope

- In: the content folder, the front matter schema, rendering Markdown to pages, the navigation built from front matter, removal of the hand-written pages.
- Out: search, versioned documentation, translations. Source: brief decision 5

## Sources

- docs/workbench/briefs/docs-site.md (decisions 2, 3 and 5)
- User answers of 2026-09-20

## Functional requirements

- REQ-1: The build reads every `.md` file under `content/docs/` and publishes one page per file at `/docs/<slug>/`. Source: brief decision 2
- REQ-2: Every page declares `title`, `section` and `order` in its front matter; the build validates them against a schema. Source: brief decision 3
- REQ-3: The sidebar navigation is generated from the front matter: pages grouped by `section`, sorted by `order`. Source: brief decision 3
- REQ-4: Fenced code blocks marked `html preview` render both the highlighted source and a live preview of the component. Source: user answer 2026-09-20
- REQ-5: Every existing hand-written page under `site/docs/*.html` is migrated to Markdown and the hand-written file is removed; its URL keeps answering. Source: brief decision 2

## Non-functional requirements

- NFR-1: A full build of the documentation completes in under 10 seconds for 60 pages on the CI runner. Source: user answer 2026-09-20
- NFR-2: The published pages load 0 bytes of JavaScript for Markdown rendering; rendering happens at build time. Source: brief decision 3

## Constraints

- technical: the site is built by the repository's own Node build scripts; no framework is added. Source: brief decision 3

## Edge cases

- EDGE-1: A page lacks a required front matter key or has one of the wrong type → the build fails and the message names the file and the key.
- EDGE-2: Two pages resolve to the same slug → the build fails and the message names both files.
- Categories skipped: permissions and concurrency, because the site is static.

## Acceptance criteria

- AC-1:
  Given a file `content/docs/button.md` with valid front matter
  When the build runs
  Then `/docs/button/` exists and shows the title and the rendered body
  Covers: REQ-1, REQ-2
- AC-2:
  Given a page without `title`
  When the build runs
  Then the build exits non-zero and the message names the file and `title`
  Covers: REQ-2
- AC-3:
  Given three pages in the section "Components" with orders 2, 1 and 3
  When the build runs
  Then the sidebar lists them under "Components" in the order 1, 2, 3
  Covers: REQ-3
- AC-4:
  Given a fenced block marked `html preview`
  When the page is built
  Then the page contains the highlighted source and the live preview, and no script tag for Markdown rendering
  Covers: REQ-4, NFR-2
- AC-5:
  Given the list of URLs published before the migration
  When the build runs after the hand-written pages are removed
  Then every URL of the list answers with a page built from Markdown
  Covers: REQ-5
- AC-6:
  Given 60 fixture pages
  When the build runs on the CI runner
  Then it completes in under 10 seconds
  Covers: NFR-1

## Assumptions

- ASSUMPTION-1: The 14 existing pages have no content that Markdown cannot express. Safe because: they contain headings, paragraphs, tables and code samples only.

## Open questions

- none

## Readiness

- Ready for architecture: yes
