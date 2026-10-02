# PRD: Lintel UI documentation site (1.0)

- Owner: product-prd
- Status: draft
- Date: 2026-09-23

## Summary

The documentation site of the Lintel UI CSS and JavaScript library, at https://lintel.example, rebuilt for Lintel UI 1.0. It serves people evaluating the library against alternatives and people migrating from 0.19.

## Users

- U-1: Evaluators comparing CSS libraries. Situation: choosing a lightweight component library that needs no framework, weighing size, dependencies and browser-native behaviour against the libraries of the research brief. Needs: what Lintel UI is in one screen, the measured size with its method, a one-command install, components they can see working, the license. Source: research brief `docs/workbench/research/css-library-alternatives.md`, "Implications for positioning".
- U-2: Users of 0.19 migrating to 1.0. Situation: a project on 0.19 that uses the old class names. Needs: the migration steps, what was removed and its replacement, the 0.19 documentation still reachable while they migrate. Source: library `MIGRATION.md`.

## Features

- F-1: Documentation pages for 1.0. Outcome: the reader can open one page per component of Lintel UI 1.0 with prose, a live preview and copyable code for every example. Priority: must.
- F-3: Landing page for 1.0. Outcome: an evaluator can, on one screen, learn what Lintel UI is, read the measured size with the method behind the number, copy the install command and jump into the documentation; no promise of features that do not exist. Priority: must.
- F-4: Migration guide 0.19 to 1.0. Outcome: a migrating user can follow the migration steps inside the site. Priority: must.

## Success metrics

- M-1: 1.0 coverage. Target: 14 of 14 component stylesheets have a documentation page. Measured by: a build check against `dist/css/components/*.css`.
- M-3: Size claim integrity. Target: the size published on the landing equals the gzip measurement of the pinned library version, 0 B of difference, with the method stated next to the number. Measured by: a build test that measures the installed `lintel.css` with `gzip -9` and compares it with the landing text. Source: research brief, "Implications for positioning".

## Constraints

- positioning: any size claim on the site is published with the measurement method and the library version measured. Source: research brief implications.

## Open questions

- OPEN-5: Landing messaging. Blocks: nothing in this PRD; an input of the design phase. Recommended: the landing's sections and texts are written in a messaging step before the landing is designed; until then the landing spec states what the page must let the evaluator do, not its copy.

## Readiness

- Ready for feature specs: yes.
