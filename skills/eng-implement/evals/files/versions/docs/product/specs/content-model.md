# Specification: content model

- Owner: product-feature-spec
- Status: approved
- Date: 2026-04-08
- Ready for architecture: yes

## Requirements

- REQ-1: The documented versions of Fernleaf UI are listed in one file, `content/versions.json`, with the latest one named.
- REQ-2: The site lists the versions newest first and marks the latest and the deprecated ones.
- REQ-3: A page address is resolved to a version; an address naming a version that does not exist fails the build and names that version.

## Acceptance criteria

- AC-1: Given `content/versions.json`, when it is loaded, then its versions and its latest version are available, and a malformed file is rejected.
- AC-2: Given versions 2.9, 1.4 and 2.10 with 2.10 as latest, when they are listed, then the order is 2.10, 2.9, 1.4, the first is labelled `2.10 (latest)` and served at `/`, and the others are served at `/v2.9` and `/v1.4`.
- AC-3: Given the same versions, when no version is requested, then 2.10 is resolved; when 1.4 is requested, then 1.4 is resolved; when 3.0 is requested, then an error names 3.0.
- AC-4: Given the list of versions, when a page is built, then it carries a version switcher with one link per version.
