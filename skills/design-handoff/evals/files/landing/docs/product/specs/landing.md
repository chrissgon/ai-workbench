# Feature specification: landing

- Owner: product-feature-spec
- Status: approved
- Date: 2026-03-01
- Feature of: the PRD of the Plinth UI documentation site, phase P-1 (the 1.0 launch)

## Summary

The landing of the documentation site: it says what Plinth UI is, shows its measured size, gives the install command and leads to the documentation, for developers who evaluate a component library.

## Goal and users

- Problem: evaluators leave before they install, because the size claim cannot be verified and the docs are one click too far. Source: PRD, problem statement
- Users: front-end developers who evaluate a CSS component library for a new project. Source: PRD U-1
- Success: an evaluator reaches the documentation with the install command copied, in one screen. Source: PRD F-3

## Scope

- In: the landing page (`/`), its copy control, its size block and its components showcase.
- Out: the documentation pages, search and the version switch (other specs).

## Sources

- PRD of the documentation site (2026-02-24): U-1, F-3, constraint "no third-party host"
- User answer, 2026-03-01: the showcase shows at least 4 examples

## Functional requirements

- REQ-1: The landing states what Plinth UI is in one headline and one paragraph. The texts come from `content/landing.md`, never from the page template. Source: PRD F-3
- REQ-2: The size block shows the gzip size of the shipped CSS and JavaScript, the version and the method. The numbers are measured at build time from the installed package; a number typed by hand never ships. Source: PRD F-3
- REQ-3: The install command `npm install @plinthkit/plinthui` is shown with a copy control. After a copy the control reads "Copied" for at least 1 second and then returns to "Copy". Source: PRD F-3
- REQ-4: The primary call to action links to `/docs`. Source: PRD F-3
- REQ-5: The components showcase renders at least 4 live examples, each an example block reused from a documentation page under `content/v1/components/`. Source: user answer 2026-03-01
- REQ-6: With `prefers-reduced-motion: reduce` nothing animates: every element is in its final state from the first paint. Source: PRD, accessibility constraint
- REQ-7: The page makes no request to a third-party host: fonts and scripts are self-hosted. Source: PRD, constraint "no third-party host"

## Non-functional requirements

- NFR-1: Without JavaScript every text and the install command are readable; the copy control is absent, and 0 elements are hidden behind a script. Source: PRD, accessibility constraint

## Constraints

- technical: the site ships the library stylesheet of the installed package; it never copies its values. Source: PRD, constraint "one source for the library"

## Edge cases

- EDGE-1: the clipboard is refused → the command is shown selected for a manual copy.
- EDGE-2: the build cannot measure the size → the build fails; no size is typed by hand.
- Categories skipped: authentication, data entry and concurrency: the landing has none.

## Acceptance criteria

- AC-1:
  Given the built site
  When the landing loads
  Then the size block shows the numbers of the build's measurement
  Covers: REQ-2
- AC-2:
  Given the landing
  When the copy control is activated
  Then the clipboard holds the install command and the control reads "Copied" for at least 1 second
  Covers: REQ-3
- AC-3:
  Given reduced motion
  When the landing loads
  Then no element transitions
  Covers: REQ-6
- AC-4:
  Given the landing
  When it loads
  Then every request goes to the site's own host
  Covers: REQ-7
- AC-5:
  Given the landing
  When it loads
  Then the headline and the paragraph are the texts of `content/landing.md`, the primary call to action opens `/docs`, and the showcase shows at least 4 example blocks
  Covers: REQ-1, REQ-4, REQ-5
- AC-6:
  Given JavaScript is off
  When the landing loads
  Then every text and the install command are readable and the copy control is absent
  Covers: NFR-1

## Assumptions

- none

## Open questions

- none

## Readiness

- Ready for architecture: yes
