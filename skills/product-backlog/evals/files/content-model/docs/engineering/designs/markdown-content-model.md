# Design: markdown-content-model

- Owner: eng-architecture
- Status: approved
- Date: 2026-09-23
- Specification: docs/product/specs/markdown-content-model.md
- Frameworks and versions relied on: none; Node 22 standard library and the repository's own build scripts

## Summary

Documentation pages become Markdown files under `content/docs/`. A loader reads each file and validates its front matter against a schema; a renderer turns the body into HTML at build time, with a preview block for `html preview` fences; a navigation generator writes the sidebar data from the front matter; a page template wraps each rendered body in the layout. The hand-written pages and the hand-written sidebar are removed after their Markdown replacements publish the same URLs.

## Sources

- docs/product/specs/markdown-content-model.md
- build/build.mjs, build/highlight.mjs, site/docs/*.html, site/partials/sidebar.html (read 2026-09-23)

## Decisions

| # | Decision | Chosen | Class | ADR or source |
|---|----------|--------|-------|---------------|
| 1 | Where content lives | `content/docs/<slug>.md` | decided | brief decision 2 |
| 2 | Front matter format | YAML subset: flat `key: value` lines, parsed by the loader | engineering | ADR-0003 |
| 3 | Markdown renderer | the vendored `build/vendor/markdown.mjs` already used for the changelog | engineering | ADR-0004 |

## Components

| Component | Responsibility | Location | Inputs | Outputs | Satisfies |
|-----------|----------------|----------|--------|---------|-----------|
| Content loader | Reads every `.md` file, splits front matter from body, derives the slug, detects duplicate slugs | build/content/load.mjs | content/docs/*.md | page records | REQ-1, EDGE-2 |
| Front matter schema | Validates `title` (string), `section` (string), `order` (integer) and names the file and key on failure | build/content/schema.mjs | page records | validated records or an error | REQ-2, EDGE-1 |
| Markdown renderer | Renders the body to HTML at build time | build/content/render.mjs | body | HTML | REQ-1, NFR-2 |
| Preview block | Renders an `html preview` fence as highlighted source plus the live markup | build/content/preview.mjs | fence | HTML | REQ-4, NFR-2 |
| Navigation generator | Groups records by `section`, sorts by `order`, writes the sidebar data | build/content/nav.mjs | validated records | build/.cache/nav.json | REQ-3 |
| Page template | Wraps a rendered body and the sidebar in the layout | site/templates/doc.html | HTML, nav.json | dist/docs/<slug>/index.html | REQ-1, REQ-3 |
| Migrated content | The 14 existing pages as Markdown files | content/docs/*.md | site/docs/*.html | Markdown files | REQ-5 |

## Data or content model

```
content/docs/button.md
---
title: Button
section: Components
order: 1
---
```

`title` and `section` are non-empty strings; `order` is an integer; an unknown key is an error (EDGE-1). The slug is the file name without `.md`; two files with the same slug in different folders are an error (EDGE-2).

## Contracts

### Routes
| Route | Params | Resolves to | Serves |
|-------|--------|-------------|--------|
| /docs/<slug>/ | slug | dist/docs/<slug>/index.html | REQ-1, REQ-5 |

### Files and generated artifacts
| Path | Produced by | Shape (example) | Consumed by | Serves |
|------|-------------|-----------------|-------------|--------|
| build/.cache/nav.json | Navigation generator | `[{"section":"Components","pages":[{"title":"Button","slug":"button"}]}]` | Page template | REQ-3 |
| test/fixtures/urls-before.txt | captured once from the current site | one URL per line | URL check | REQ-5 |

## Flows

### Build
1. Content loader — reads the files and derives the slugs.
2. Front matter schema — validates every record; the build stops on the first invalid one.
3. Markdown renderer and Preview block — render each body.
4. Navigation generator — writes nav.json.
5. Page template — writes one page per record.

### Failure paths
| EDGE | Where it is caught | What happens | Message names |
|------|--------------------|--------------|---------------|
| EDGE-1 | Front matter schema | build exits 1 | file and key |
| EDGE-2 | Content loader | build exits 1 | both files |

## Removals

| Removed | Replaced by | Must keep working | Checked by |
|---------|-------------|-------------------|------------|
| site/docs/*.html (14 hand-written pages) | Migrated content, Page template | every URL in test/fixtures/urls-before.txt | test/urls.test.mjs |
| site/partials/sidebar.html (hand-written sidebar) | Navigation generator | the sidebar order of the current site | test/nav.test.mjs |

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|
| AC-1 | a valid fixture page is published with its title and body | integration | `node --test test/build.test.mjs` |
| AC-2 | a fixture without `title` fails the build and the message names the file and the key | unit | `node --test test/schema.test.mjs` |
| AC-3 | three fixtures with orders 2, 1, 3 come out as 1, 2, 3 in nav.json | unit | `node --test test/nav.test.mjs` |
| AC-4 | a preview fence yields source and preview, and the page has no rendering script | unit | `node --test test/preview.test.mjs` |
| AC-5 | every URL in test/fixtures/urls-before.txt exists in dist/ | integration | `node --test test/urls.test.mjs` |
| AC-6 | 60 generated fixture pages build in under 10 seconds | performance | `node build/bench.mjs --pages 60` |

## Traceability

| Id | Where in this design |
|----|----------------------|
| REQ-1 | Content loader, Markdown renderer, Page template |
| REQ-2 | Front matter schema |
| REQ-3 | Navigation generator, Page template |
| REQ-4 | Preview block |
| REQ-5 | Migrated content, Removals |
| NFR-1 | Verification plan AC-6 |
| NFR-2 | Markdown renderer, Preview block |
| EDGE-1 | Front matter schema |
| EDGE-2 | Content loader |

## Assumptions to verify before implementation

- The vendored `build/vendor/markdown.mjs` passes the info string of a fenced block (`html preview`) to a hook, so the Preview block can intercept it. Verify by rendering one fence with a hook in a scratch script.
- Rendering 60 pages with the vendored renderer and `build/highlight.mjs` stays under 10 seconds on the CI runner. Verify by running the renderer over 60 generated pages before building the rest.

## Open questions

- none
