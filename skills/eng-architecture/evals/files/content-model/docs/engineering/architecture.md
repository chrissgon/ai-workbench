# Codebase map: plinthui-docs

- Owner: eng-codebase-map
- Status: approved
- Date: 2026-03-09
- Scope: repository root; 5 source files; measured with `scripts/map_codebase.py` (static imports only; framework auto-imports, dynamic imports and runtime injection are not counted)

## Summary

The documentation site of the Plinth UI component library. It is a static site built with Astro: every
page is a hand-written `.astro` file under `src/pages/`, wrapped by one layout that also holds the
sidebar as a hard-coded list. There is no content folder, no content collection and no generated file
yet. The build writes plain HTML to `dist/`, which a static host serves. The site talks to no service
at run time and ships no client JavaScript of its own.

## Structure

```
astro.config.mjs        site address, static output, no trailing slash
package.json            dependencies and scripts
src/
  layouts/Docs.astro    page shell: head, hand-written sidebar, main slot
  pages/index.astro     landing
  pages/guide/          one .astro file per guide page (1 today)
  pages/components/     one .astro file per component page (1 today)
```

## Stack

| Layer | Technology | Evidence |
|-------|------------|----------|
| framework | Astro 5.13.2, static output | `package.json` dependencies.astro; `astro.config.mjs` output |
| UI | @plinthkit/plinthui 1.0.0 (CSS classes) | `package.json`; import in `src/layouts/Docs.astro` |
| build | `astro build` | `package.json` scripts.build |
| type check | `astro check` with @astrojs/check 0.9.4 | `package.json` scripts.check |
| tests | Vitest 3.2.4, no test file yet | `package.json` scripts.test |
| deploy | static files from `dist/` | `astro.config.mjs` output: "static" |

## Entry points and routes

| Entry | Path | What it starts |
|-------|------|----------------|
| `/` | `src/pages/index.astro` | landing |
| `/guide/getting-started` | `src/pages/guide/getting-started.astro` | guide page |
| `/components/button` | `src/pages/components/button.astro` | component page |

## Components

| Component | Files | Location | Imported by (afferent) | Imports (efferent) | Responsibility |
|-----------|-------|----------|------------------------|--------------------|----------------|
| Docs layout | 1 | `src/layouts/Docs.astro` | 2 (both documentation pages) | 1 (the library stylesheet) | Page shell and the hand-written sidebar list |
| Pages | 3 | `src/pages/` | 0 | 1 (the layout) | One file per route, content written as HTML |

## Main paths

### Build of a documentation page
1. `src/pages/guide/getting-started.astro` — passes `title` and `description` to the layout and its HTML to the slot
2. `src/layouts/Docs.astro` — renders head, the `nav` constant as the sidebar, and the slot
3. `astro build` — writes `dist/guide/getting-started.html`

## Integration points

| System | Where | Purpose | Configured by |
|--------|-------|---------|---------------|
| none | | | |

## Security boundaries

- Untrusted input enters at: none (no forms, no query handling)
- Secrets are read at: none found in code
- Runs on the server: nothing at run time; runs in the browser: static HTML and the library stylesheet
- Public surface: the three routes above

## Observations

- The sidebar is a constant in `src/layouts/Docs.astro` (lines 10 to 14); adding a page means editing the layout.
- No `src/content.config.ts` and no `content/` folder exist.
- `trailingSlash: "never"` in `astro.config.mjs`: routes have no trailing slash.
- No test file exists; `npm test` runs Vitest with zero tests.

## Files read

- package.json — dependencies, versions, scripts
- astro.config.mjs — output mode, site address
- src/layouts/Docs.astro — shell and sidebar
- src/pages/index.astro — landing
- src/pages/guide/getting-started.astro — guide page
- src/pages/components/button.astro — component page
