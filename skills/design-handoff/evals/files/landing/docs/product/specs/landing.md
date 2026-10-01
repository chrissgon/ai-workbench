# Feature specification: landing

- Owner: product-spec
- Status: approved
- Date: 2026-03-01

## Functional requirements

- REQ-1: The landing states what Plinth UI is in one headline and one paragraph. The texts come from `content/landing.md`, never from the page template.
- REQ-2: The size block shows the gzip size of the shipped CSS and JavaScript, the version and the method. The numbers are measured at build time from the installed package; a number typed by hand never ships.
- REQ-3: The install command `npm install @plinthkit/plinthui` is shown with a copy control. After a copy the control reads "Copied" for at least 1 second and then returns to "Copy".
- REQ-4: The primary call to action links to `/docs`.
- REQ-5: The components showcase renders at least 4 live examples, each an example block reused from a documentation page under `content/v1/components/`.
- REQ-6: With `prefers-reduced-motion: reduce` nothing animates: every element is in its final state from the first paint.
- REQ-7: The page makes no request to a third-party host: fonts and scripts are self-hosted.

## Non-functional requirements

- NFR-1: Without JavaScript every text and the install command are readable; the copy control is absent.

## Acceptance criteria

- AC-1: Given the built site, when the landing loads, then the size block shows the numbers of the build's measurement. Covers: REQ-2
- AC-2: Given the landing, when the copy control is activated, then the clipboard holds the install command and the control reads "Copied" for at least 1 second. Covers: REQ-3
- AC-3: Given reduced motion, when the landing loads, then no element transitions. Covers: REQ-6
- AC-4: Given the landing, when it loads, then every request goes to the site's own host. Covers: REQ-7
