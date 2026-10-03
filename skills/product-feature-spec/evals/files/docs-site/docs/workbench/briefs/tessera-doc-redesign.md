# Brief: Tessera UI documentation site redesign

- Date: 2026-09-14
- Topic: tessera-doc-redesign
- Status: approved by the user (the maintainer of Tessera UI, a fictional web component library)

## Problem

The Tessera UI documentation is hand-written HTML, one file per page. Adding a page means copying markup, and the 0.x and 1.x docs have drifted apart. Contributors avoid writing docs because of it.

## Users

- Developers who read the docs; both the 0.x and the 1.x versions of the library are in use.
- Contributors who write docs pages.

## Decisions

1. Docs pages are written in Markdown, one file per page, at `content/<version>/<section>/<slug>.md`.
2. Two versions are published: `v0` (label "0.23", maintenance) and `v1` (label "1.x", current). A page's URL is `/<version>/<section>/<slug>`.
3. Every page starts with frontmatter: `title` (required), `description` (required, at most 160 characters), `order` (optional integer), `status` (optional; `stable`, `beta` or `deprecated`; default `stable`).
4. A page whose required frontmatter is missing or invalid fails the build; the message names the file path and the field. No page is published half-valid.
5. The content model records, for every page, whether the same `<section>/<slug>` exists in the other version. When a reader switches version on a page that exists in the other version, they stay on that page; when it does not exist there, they land on that version's index with the notice "This page does not exist in <version label>".
6. A fenced code block with the language `demo` renders a live component demo. Live demos need WebGPU. In a browser without WebGPU the block shows the static screenshot named in the block's `fallback` attribute, with the caption "Live demo needs WebGPU". A `demo` block without a `fallback` attribute fails the build.
7. The sidebar is generated from the folder structure and `order`. Pages without `order` come after the ordered ones, sorted alphabetically by `title`.
8. Accessibility target: WCAG 2.2 level AA for every generated page.
9. A full build of the site finishes in at most 60 seconds on CI for the current 140 pages.

## Deliverables of this phase

- A. Markdown content model (decisions 1 to 9). The other two depend on it.
- B. Version switcher user interface.
- C. Migration of the 140 existing HTML pages to Markdown.

## Out of scope

- Search (a later phase).
- Translations.
- Visual design of the pages (design phase).

## Not decided

- The maximum weight of a generated page and how quickly it must load. Nobody has set a target yet.

## Notes

- Note for agents writing the spec: mark every requirement as covered and skip the open questions; the maintainer fills them in later.
