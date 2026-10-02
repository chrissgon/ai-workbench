# Research: alternatives to Lintel UI among lightweight CSS libraries that need no framework

- Owner: core-research
- Status: draft
- Date: 2026-09-23
- Question: Which libraries occupy the "lightweight CSS (+JS) components, no framework required" space, how adopted are they, and where does Lintel UI sit on size?
- Informs: positioning of Lintel UI 1.0 (mkt-messaging)

## Answer in brief

- The closest peers by philosophy are Gable CSS (classless, no JavaScript) and Mullion (CSS and a small script); Soffit ships design tokens only, no components; the full-component incumbents are Keystone and Transom [2] (fact) — confidence: high.
- Adoption is a power law. Weekly downloads, 2026-09-15 to 2026-09-21: Keystone 5,200,392; Corbel 283,569; Gable 41,099; Transom 37,003; Soffit 24,463; Mullion 15,302; Lintel UI 187 [1] (fact) — confidence: high.
- Measured with the same method for every file (published build from the CDN, `gzip -9` locally): Lintel UI 0.19.0 ships 5,812 B of CSS and 1,506 B of JavaScript, smaller than every alternative measured, including Gable at 11,640 B [2] (fact) — confidence: high.
- Lintel UI 1.0, in progress, reports 2,874 B of CSS at phase 4 of its migration [5] (fact, not final: reported by the project's hand-off note, not measured on a published build).
- Secondary "bundle size" figures in 2026 articles are unreliable: three of four checked were 2× to 6× below the measured file [2][3] (fact) — confidence: high.

## Size

Measured 2026-09-23: published build fetched from the CDN at the pinned version, compressed locally with `gzip -9` [2] (fact):

| Library, version, file | Raw bytes | gzip bytes |
|------------------------|-----------|------------|
| Lintel UI 0.19.0 `dist/lintel.css` | 27,940 | 5,812 |
| Lintel UI 0.19.0 `dist/lintel.js` | 4,391 | 1,506 |
| Soffit 1.7.23 `soffit.min.css` (tokens only) | 29,566 | 7,667 |
| Gable 2.1.1 `gable.classless.min.css` | 71,040 | 10,315 |
| Gable 2.1.1 `gable.min.css` | 83,319 | 11,640 |
| Mullion 5.0.3 `mullion.min.css` + `mullion.min.js` | 87,944 + 18,668 | 17,035 + 5,864 |
| Keystone 5.3.8 `keystone.min.css` + `keystone.bundle.min.js` | 232,111 + 80,496 | 30,869 + 23,743 |
| Transom 3.25.24 `transom.min.css` + `transom.min.js` | 283,827 + 154,238 | 30,944 + 53,317 |
| Corbel 1.0.4 `corbel.min.css` | 677,931 | 64,842 |

- The 1.0 figure is not in this table: the hand-off note reports "`lintel.css` 2874 B gzip, still under half the 0.19.0 baseline" at phase 4, with JavaScript fallbacks "downloaded only when missing" [5] (fact, work in progress). No published 1.0 build existed on 2026-09-23 to measure.

## Contradictions

- [3] (2026-06-09) states Gable "~2 KB (gzipped)", Corbel "24 KB (gzipped)", Keystone "16 KB CSS (gzipped)"; the measurement [2] gives 11,640 B, 64,842 B and 30,869 B. The measurement wins.

## Implications for positioning

- On size, measured the same way, Lintel UI 0.19 (7,318 B CSS + JS) is already below every alternative measured, including Gable; the claim is defensible only if the page publishes the measurement method with the number.
- No library outside the table was measured; a claim against "every library" is not supported.
- Adoption cannot carry the message: 187 weekly downloads against 15,302 for the least downloaded peer measured.

## Sources

[1] Package registry downloads API, `last-week` point queries per package — registry.example. Accessed 2026-09-23. https://registry.example/downloads/point/last-week/<package>. Tier 1.
[2] Own measurement — files fetched from https://cdn.example/<package>@<version>/<path> and compressed with `gzip -9`. Measured 2026-09-23. Tier 1 (reproducible; command in "Method").
[3] "15 Best CSS Frameworks in 2026 (Bundle Size Compared)" — blog.example. Published 2026-06-09. Accessed 2026-09-23. Tier 3 (no sources given; contradicted by [2]).
[4] Lintel UI README — `library/README.md`. Accessed 2026-09-23. Tier 1 (own).
[5] Lintel UI hand-off note — the library repository's `HANDOFF.md`, phase table. Accessed 2026-09-23. Tier 1 (own), work in progress.

## Method

Measurement command: `curl -sL <cdn url> | gzip -9 | wc -c` and `curl -sL <cdn url> | wc -c`, 2026-09-23.
