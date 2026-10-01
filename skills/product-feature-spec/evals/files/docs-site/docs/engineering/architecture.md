# Codebase map: tessera-doc

- Updated: 2026-09-12
- Repository: tessera-doc (static documentation site)

## Stack

- Static site built with Eleventy 3.0 on Node 22. No client framework.
- Hosting: static files on a CDN. No server-side code at request time.
- CI: one workflow that runs `npm run build`, then `npm test`.

## Layout

| Path | What |
|------|------|
| `site/v0/**/*.html`, `site/v1/**/*.html` | the hand-written pages today: 140 files (62 in v0, 78 in v1) |
| `site/_includes/layout.njk` | page shell: header, sidebar, slot for the version switcher |
| `site/_data/nav.json` | the sidebar, maintained by hand |
| `src/demo-runner.js` | mounts a live demo on a `<canvas>`; reads `navigator.gpu` and throws when it is undefined |
| `assets/screenshots/` | one static PNG screenshot per demo |
| `eleventy.config.js` | build configuration |
| `tests/links.test.js` | link checker, run by `npm test` |

## Facts

- No Markdown is processed today. `markdown-it` 14 ships with Eleventy and is not configured.
- `site/_data/nav.json` and the folder structure disagree in 9 entries.
- The build takes 21 seconds on CI today.
- 31 pages exist only in v1; 15 exist only in v0.
