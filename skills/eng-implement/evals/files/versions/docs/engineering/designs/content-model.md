# Design: content model

- Owner: eng-architecture
- Status: approved
- Date: 2026-04-10
- Specification: docs/product/specs/content-model.md
- Frameworks and versions relied on: Node 24 (runs `.ts` files by stripping types; `node:test`)

## Summary

The versions of Fernleaf UI that have documentation are named in `content/versions.json`. A loader reads and validates that file. A versions module turns the manifest into the list the site shows and resolves the version a page address asks for. A switcher renders that list on every page. Nothing here needs a dependency.

## Components

| Component | Responsibility | Location | Inputs | Outputs | Satisfies |
|-----------|----------------|----------|--------|---------|-----------|
| Manifest loader | Reads and validates the manifest | `app/manifest.ts` | `content/versions.json` | `Manifest` | REQ-1 |
| Versions | Lists the versions and resolves a requested one | `app/versions.ts` | `Manifest` | `Version[]`, `Version` | REQ-2, REQ-3 |
| Version switcher | Renders one link per version | `app/switcher.ts` | `Version[]` | HTML | REQ-2 |

## Contracts

### Component interfaces

`app/manifest.ts` (exists):

```ts
interface ManifestEntry { id: string; deprecated?: boolean }
interface Manifest { latest: string; versions: ManifestEntry[] }
parseManifest(text: string): Manifest   // throws RangeError on a malformed manifest
loadManifest(path: string): Manifest
```

`app/versions.ts`:

```ts
interface Version { id: string; label: string; path: string; deprecated: boolean }
listVersions(manifest: Manifest): Version[]
resolveVersion(manifest: Manifest, requested?: string): Version
```

- `listVersions` returns one `Version` per manifest entry, newest first. Ids are `<major>.<minor>` and are compared as numbers, part by part: 2.10 is newer than 2.9.
- `label` is the id; the latest version's label is the id followed by ` (latest)`.
- `path` is `/` for the latest version and `/v<id>` for every other one.
- `deprecated` is `false` when the manifest entry does not carry it.
- `resolveVersion` returns the latest version when `requested` is omitted, the version with that id when it exists, and throws a `RangeError` whose message contains the requested id when it does not.
- Neither function reads a file or changes the manifest it receives.

`app/switcher.ts`:

```ts
renderSwitcher(versions: Version[], current: string): string
```

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|
| AC-1 | The manifest loads; a malformed one is rejected | unit | `node --test tests/repo/manifest.spec.ts` |
| AC-2 | Versions are listed newest first with label, path and deprecation | unit | `node --test tests/repo/versions.spec.ts` |
| AC-3 | A requested version is resolved; an unknown one throws | unit | `node --test tests/repo/versions.spec.ts` |
| AC-4 | A built page carries the switcher | unit | `node --test tests/repo/switcher.spec.ts` |

## Assumptions to verify before implementation

- none

## Open questions

- none
