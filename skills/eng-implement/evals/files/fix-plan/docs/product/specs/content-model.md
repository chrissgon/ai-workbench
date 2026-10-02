# Specification: content model

- Owner: product-feature-spec
- Status: approved
- Date: 2027-10-25
- Ready for architecture: yes

## Requirements

- REQ-1: Every documentation page is checked before the site is built; a broken rule stops the build, and every broken rule is listed with the file it concerns.
- REQ-2: The check is one pure function over the list of pages, so that it is tested without reading files.
- REQ-3: The build command runs the check over every file under `content/`.

## Edge cases

- EDGE-1: A page without a title, or with a title made only of spaces, is reported.
- EDGE-2: A slug is lowercase letters and digits, in groups separated by single hyphens; any other slug is reported.
- EDGE-3: A description is optional. When present it is at most 160 characters: a description of 160 characters is valid, one of 161 is reported.
- EDGE-4: Two pages with the same section and slug have the same address; the second one is reported and names the first.

## Acceptance criteria

- AC-1: Given pages that break EDGE-1 to EDGE-4, when they are validated, then each broken rule yields one message that starts with the page's file; given valid pages, then the list is empty.
- AC-2: Given a `content/` folder with a broken page, when the build command runs, then it exits with an error and prints the messages.
