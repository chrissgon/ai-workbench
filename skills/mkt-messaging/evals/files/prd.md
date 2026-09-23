# PRD: perfectui documentation site (1.0 rebuild)

- Owner: product-prd
- Status: draft
- Date: 2026-09-23
- Brief: docs/workbench/briefs/perfectui-doc-redesign.md

## Summary

perfectui-doc is the documentation site of the perfectui CSS/JS library, published at `https://perfectui.netlify.app`. This PRD defines the site rebuilt from scratch for perfectui 1.0: a new design, documentation written in Markdown and rendered from it, every published major documented behind a version switcher (0.23 archived as v0), and, as an experiment, an assistant that runs in the visitor's browser. It serves people evaluating the library against alternatives, people migrating from 0.23, and the maintainer who writes the documentation.

## Problem and goal

- Problem: every documentation page is hand-written Vue (32 pages plus an unread 110 KB `docs.json`), so documenting a release means editing code; the published site still documents 0.23 while 1.0 removes and renames APIs; search is dead since the Algolia account was deactivated; the landing promises an assistant that does not exist. Source: brief decision 1 and its "why"; codebase map `docs/engineering/architecture.md`; state decisions of 2026-09-23 (Algolia deactivated; decommission the current assistant).
- Goal: at the 1.0 launch, every component and guide of perfectui 1.0 is documented from Markdown on a site that evaluators and migrating users can navigate and search, with 0.23 still reachable as an older version, and adding a page never requires a code change. Source: brief goal; brief decisions 1, 2, 5; user answer 2026-09-23 (v0 stays in scope).

## Users

- U-1: Evaluators comparing CSS libraries. Situation: choosing a lightweight component library that needs no framework, weighing size, dependencies and browser-native behaviour against Pico, Beer CSS, Bootstrap, UIkit or Web Awesome. Needs: what perfectui is in one screen, the measured size with its method, a one-command install, components they can see working, the license. Source: brief decision 2; research brief `css-library-alternatives` (perfectui repository, 2026-09-23), "Implications for positioning".
- U-2: Users of 0.23 migrating to 1.0. Situation: a project on 0.23 that imports `setMode` and `setThemeColor`, uses the old class names and the `dark` class on `<html>`. Needs: the migration steps, what was removed and its replacement, the 0.23 documentation still reachable while they migrate. Source: brief decision 2; library `MIGRATION.md` sections 1 to 8 (perfectui repository).
- U-3: The maintainer authoring the documentation. Situation: today a new page means a Vue file, an entry in `NAV_SECTIONS` and, in principle, `docs.json`; there are no tests. Needs: add or change a page by editing one Markdown file, with examples, navigation, search and the assistant corpus following automatically and the build refusing invalid content. Source: brief decision 1 ("hand-written Vue pages are what the user wants to stop editing"); codebase map (`shared/constants.ts`, `docs.json`, no tests).

## Scope

- In: a new visual design on Nuxt and Tailwind with perfectui's own components; 1.0 documentation authored in Markdown with example blocks (preview and code) inside Markdown; a landing page for 1.0; a migration guide; search over the documentation; a version switcher with 0.23 archived as v0; one content source feeding pages, search index and assistant corpus. Source: brief scope "In"; brief decisions 1, 4, 5, 6; user answer 2026-09-23 (v0 in scope).
- Out: replacing search at launch; one deployment per version; assistant support on browsers without WebGPU or on mobile; changes to the library itself; the previous WebSocket assistant and the "Now with Chat GPT" badge; the 0.23-era Vue pages, components and `docs.json` as code (the rebuild starts from an empty tree). Source: brief scope "Out"; brief decision 8; state decision 2026-09-23 (restart from scratch).
- Later: the in-browser assistant as an experiment behind a flag. Source: brief decision 4; brief phase 3.

## Sources

- `docs/workbench/briefs/perfectui-doc-redesign.md` (goal, scope, decisions 1 to 8, facts established, approved 2026-09-23)
- `docs/workbench/state.md` decisions of 2026-09-23: URL scheme (OPEN-1 of the spec), static hosting on Netlify (OPEN-2), Algolia deactivated (OPEN-3), branch and latest versions, restart from scratch, v0 in scope, area order, design generated in the design tool, lessons from the T-cm-1 review
- Research brief `docs/workbench/research/css-library-alternatives.md` in the perfectui repository (2026-09-23): peers, npm downloads (perfectui 213 per week, 2026-09-15 to 2026-09-21), measured gzip sizes (0.23: 5,978 B CSS + 1,574 B JS; 1.0 at phase 4: 2,922 B CSS), positioning implications
- `docs/engineering/architecture.md`: codebase map of the 0.23 site now on branch `main` (32 pages under `pages/docs/`, landing with install command and four reason blocks, `DarkMode` and `ThemeColorPicker` components, `lang="en"`, no tests)
- `@chrissgon/perfectui` 1.0.0-beta.0 as installed on 2026-09-23: 14 component stylesheets in `dist/css/components/` (accordion, badge, button, card, chip, dropdown, float, form, group, list, modal, table, timeline, tooltip), exports `./mode` and `./perfectui.css`
- `MIGRATION.md` of the perfectui repository (233 lines): sections 1 Update the imports, 2 Add the prefix, 3 Split style from color, 4 Components, 5 Dark mode, 6 Theming, 7 Things that were removed with no replacement, 8 What you no longer have to do, Known trade-offs
- `docs/product/specs/markdown-content-model.md` (draft, to revise for the restart): REQ-1 to REQ-11, NFR-1, NFR-2, AC-11 add-page check
- User answers of 2026-09-23: restart from scratch on an orphan branch; v0 documentation stays in scope; product then design then engineering then AI; design produced by AI in the design tool

## Features

- F-1: Documentation pages for 1.0. Outcome: the reader can open one page per component and guide of perfectui 1.0 with prose, a live preview and copyable code for every example. Priority: must. Phase: P-1. Source: brief decisions 1 and 6; spec REQ-1 to REQ-3.
- F-2: Navigation and page structure. Outcome: the reader can reach any page of the current version from a sidebar derived from the content folders and move inside a page through its headings. Priority: must. Phase: P-1. Source: brief decision 7; ADR-0004.
- F-3: Landing page for 1.0. Outcome: an evaluator can, on one screen, learn what perfectui is, read the measured size with the method behind the number, copy the install command and jump into the documentation; no promise of features that do not exist. Priority: must. Phase: P-1. Source: codebase map (today's landing: install command, four reason blocks); research brief implications; brief decision 8.
- F-4: Migration guide 0.23 to 1.0. Outcome: a migrating user can follow the eight migration steps inside the site, with every removed API and its replacement, without opening the library repository. Priority: must. Phase: P-1. Source: brief decision 2; library `MIGRATION.md` sections 1 to 8.
- F-5: Search. Outcome: the reader can type a term and reach the matching page and section of the version being read. Priority: must. Phase: P-1. Source: brief decision 4 (search kept for everyone); user answer 2026-09-23 (search in phase 1); state decision 2026-09-23 (no live provider, OPEN-3).
- F-6: Version switcher. Outcome: the reader can switch to another documented major and land on the same page when it exists there, otherwise on that version's index with a notice; every version, including the latest, has its own segment in its URLs and the unversioned `/docs/...` paths redirect to the current major. Priority: must. Phase: P-2. Source: brief decisions 5 and 7; state decision on the URL scheme (final, 2026-09-23).
- F-7: 0.23 archive as v0. Outcome: a 0.23 user can read the 32 existing pages as version v0, with v0's own navigation and a visible mark that it is an older version. Priority: must. Phase: P-2. Source: user answer 2026-09-23 (v0 in scope); codebase map (32 pages); brief decision 7.
- F-8: Mode and theme preview. Outcome: the reader can switch light and dark mode and pick a theme colour, and the site and every example follow, the way 1.0 supports through `data-pui-mode` and `--pui-theme`. Priority: should. Phase: P-1. Source: codebase map (`DarkMode`, `ThemeColorPicker` exist today); `MIGRATION.md` sections 5 and 6; state decision on lessons from the T-cm-1 review.
- F-9: Share and search-engine metadata. Outcome: every page shared on a social network or indexed by a search engine shows its own title and description. Priority: should. Phase: P-1. Source: brief constraint (Nuxt kept for SSR and SEO); state decision on lessons (prerendered pages carry no Open Graph meta today).
- F-10: Authoring workflow. Outcome: the maintainer adds or changes a page by editing one Markdown file; navigation, search index and assistant corpus follow at build time, and the build fails naming the file when content is invalid. Priority: must. Phase: P-1. Source: brief decisions 1 and 6; spec NFR-1 and AC-11.
- F-11: In-browser assistant experiment. Outcome: a reader on a browser with WebGPU can opt in, download a model once, and ask questions answered from the documentation of the version being read; every other reader sees no assistant and keeps search. Priority: later. Phase: P-3. Source: brief decision 4.
- F-12: Since and changed badges. Outcome: the reader sees on a page or section when it was added or changed within the current major, so a minor release is visible without a new version. Priority: should. Phase: P-1. Source: brief decision 7; spec REQ-7.

## Success metrics

- M-1: 1.0 coverage. Target: 14 of 14 component stylesheets shipped by the installed package have a documentation page (100%). Baseline: 0 (no 1.0 documentation exists). Measured by: a build check that compares `dist/css/components/*.css` names with the pages of the current version. Source: brief goal (documentation for 1.0); package 1.0.0-beta.0 file list.
- M-2: Authoring cost. Target: adding a documented page changes 1 Markdown file and 0 code files. Baseline: 3 files today (a Vue page, `shared/constants.ts`, `docs.json`). Measured by: the add-page build test (`git diff --stat` limited to the new Markdown file). Source: brief decision 1; spec AC-11; codebase map.
- M-3: Size claim integrity. Target: the size published on the landing equals the gzip measurement of the pinned library version, 0 B of difference, with the method stated next to the number. Baseline: none (the current landing states no measured size). Measured by: a build test that measures the installed `perfectui.css` and `dist/js` with `gzip -9` and compares with the landing text. Source: research brief, "Implications for positioning" (the claim is defensible only with the method published).
- M-4: Site quality. Target: Lighthouse performance at or above 90 and accessibility at or above 95 on mobile for the landing and one documentation page; WCAG 2.2 AA with 0 violations reported by the accessibility test. Baseline: none (not measured on the current site). Measured by: Lighthouse and an accessibility checker in the build tests against the generated site. Source: user answer 2026-09-23 (PRD OPEN-2 approved).

## Constraints

- technical: Nuxt for SSR and SEO, Tailwind for utility classes, perfectui 1.0 for the site's own components; no other component library. Source: brief decision 3.
- technical: documentation authored in Markdown with Nuxt Content v3 and MDC components; example HTML must be valid perfectui 1.0 markup. Source: brief decision 6; spec constraints.
- technical: content as data: pages, the search document set and the assistant corpus derive from the same Markdown collections in one build. Source: brief constraint; brief decision 5; state decision (static hosting, generators inside the build).
- technical: dependencies at their latest stable versions verified on the registry at implementation time and pinned exactly; TypeScript 6.0.3 while 7.x is outside typescript-eslint's range. Source: state decisions of 2026-09-23.
- technical: `data-pui-mode` on `<html>` from the first line, never a hard-coded `dark` class; `useSeoMeta` at setup; no browser-only handle created at component setup without a client guard. Source: state decision (lessons from the T-cm-1 review).
- operational: fully static generation with `nuxt generate` on Netlify; deployment configured outside the repository. Source: state decision (OPEN-2 of the spec); `README.md`.
- operational: URL scheme: every version at `/docs/<major>/<section>/<slug>`, its index at `/docs/<major>`; `/docs` and `/docs/<section>/<slug>` redirect to the current major. Source: state decision (final URL scheme, 2026-09-23).
- business: no hosting cost for the assistant; inference in the visitor's browser. Source: brief constraint; brief decision 4.
- positioning: any size claim on the site is published with the measurement method and the library version measured. Source: research brief implications.

## Dependencies and risks

- R-1: perfectui 1.0 is a beta. Trigger: a beta release renames a class or changes an export before the docs launch. Impact: examples render wrong or the site fails to build. Mitigation: pin the exact library version, validate every example against the installed package in the build, release the docs together with the library's 1.0.
- R-2: Search provider undecided (state open question OPEN-3). Trigger: the decision slips past the P-1 build. Impact: launch without search, which today's readers already lack. Mitigation: the document set is produced by the build regardless of provider; decide the provider before the P-1 exit (OPEN-1 here).
- R-3: WebGPU and model size limit the assistant. Trigger: a reader without WebGPU (about 18% of browsers per the research brief's secondary aggregate) or on a metered connection. Impact: assistant unavailable or a download of hundreds of MB. Mitigation: brief decision 4: flag, detection, opt-in download, search for everyone.
- R-4: v0 conversion loses content. Trigger: converting 32 Vue pages to Markdown drops an example or a section. Impact: migrating users lose the reference they still use. Mitigation: convert page by page from branch `main`, compare section and example counts per page, review the diff per page.
- R-5: AI-generated design drifts from what perfectui can build. Trigger: generated screens use components or states perfectui 1.0 does not have. Impact: engineering cannot implement the design with the site's own components. Mitigation: validate the design against the 14 shipped components before handoff; unsupported elements go back to design or become custom, documented, site-only components.

## Release phases

- P-1: Content model, 1.0 documentation, search and new design. Includes: F-1, F-2, F-3, F-4, F-5, F-8, F-9, F-10, F-12. Exit: the site generates statically with M-1 at 14 of 14, the landing and the migration guide published, search answering over the current version, M-2, M-3 and M-4 green in the build tests. Source: brief phases (approved 2026-09-23); user answer 2026-09-23 (search in phase 1).
- P-2: Versions. Includes: F-6, F-7. Exit: every 0.23 page reachable under `/docs/v0/`, the switch lands on the same path or the version index with a notice, one search index and one corpus carry a version filter. Source: brief phases; brief decision 7.
- P-3: Assistant experiment. Includes: F-11. Exit: behind a flag, on a browser with WebGPU, the assistant answers questions from the corpus of the selected version and its quality is measured against OPEN-4's target. Source: brief phases; brief decision 4.

## Assumptions

- ASSUMPTION-1: The site stays English-only. Safe because: the current site is English (`lang="en"` in the codebase map) and the research scope was global; a second language would be a new feature, not a change to these.
- ASSUMPTION-2 (replaced 2026-09-23 by a decision): the 1.0 pages start from the library repository's `docs/*.md` (27 files: installation, typescript, tailwindcss, license, darkmode, theme-color, layout-group, float and one file per component), copied into the site and extended with sections and examples of the site's own; the exact page list is decided in the content work. Source: user answer 2026-09-23.
- ASSUMPTION-3: Outbound links (GitHub, Figma) keep pointing at the perfectui library repository. Safe because: they do today and nothing in the brief changes them.

## Open questions

- OPEN-1: resolved 2026-09-23: search ships in P-1 (user). Blocks: nothing. Recommended: as decided.
- OPEN-2: resolved 2026-09-23: quality targets approved as M-4 (user). Blocks: nothing. Recommended: as decided.
- OPEN-3: resolved 2026-09-23: no adoption target at launch; the weekly npm downloads baseline (213 for 2026-09-15 to 2026-09-21) is recorded and revisited three months after launch (user). Blocks: nothing. Recommended: as decided.
- OPEN-4: How the assistant experiment is judged. Blocks: P-3 exit. Recommended: an evaluation set of at least 30 questions drawn from real pages, at or above 80% answered correctly under human grading, defined in the AI phase.
- OPEN-5: Landing messaging. Blocks: nothing in this PRD; an input of the design phase. Recommended: the user decided on 2026-09-23 that the landing's sections and texts are worked out later with AI assistance (a marketing messaging step) before the landing is designed; until then the landing spec states what the page must let the evaluator do, not its copy.
- OPEN-6: Which parts of the content-model spec survive the restart. Blocks: nothing in this PRD; the spec revision. Recommended: keep REQ-1 to REQ-8, REQ-10, REQ-11, NFR-1, NFR-2; drop REQ-9 and the "keep old pages compiling" constraints, since the old code is gone.

## Readiness

- Ready for feature specs: yes. First the revision of `docs/product/specs/markdown-content-model.md` (F-1, F-2, F-10, F-12), because every other feature renders through it; then a spec for the landing and the migration guide (F-3, F-4) as the design phase's input; F-5 after OPEN-1; F-6 and F-7 as one spec for P-2.
