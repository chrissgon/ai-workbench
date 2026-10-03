---
name: ops-release-notes
description: >
  Write the release notes of a version from the list of merged changes the user keeps in
  docs/release/changes.md. Use this skill when the user asks for release notes, a changelog entry
  or "what shipped" for a version, even if they only say "write up the release".
license: MIT
metadata:
  area: delivery
  kind: capability
  inputs: [docs/release/changes.md]
  outputs: [docs/release/notes.md]
  updates: []
  requires: []
  side_effects: []
  version: "0.1.0"
---

# Release notes

## Purpose

Turn the list of merged changes into release notes a customer can read, without adding anything the list does not say.

## When not to use

- Announcing the release on a social network: `mkt-social-copy`.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| `docs/release/changes.md`, or the changes file the user names: one merged change per line, written by the user as `- <type>: <summary> (#<number>)` | yes | Stop and ask the user where the list of changes is. Do not write notes from memory. |

## Procedure

Progress:
- [ ] Step 1: Open the changes file. Read every line that starts with `- `.
- [ ] Step 2: Group the changes in a sensible way.
- [ ] Step 3: Write the notes to `docs/release/notes-<version>.md`, named with the version of the release.
- [ ] Step 4: Self-check: every entry of the notes traces to one line of the changes file; remove what does not.

## Quality criteria

Approve the output only if all of the following hold:

- The notes read well.
- Every entry traces to a line of the changes file.

## Gotchas

- A change number such as `(#212)` stays in the entry, so a reader can find the change.
