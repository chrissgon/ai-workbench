# Design: content model

- Owner: eng-architecture
- Status: approved
- Date: 2026-05-27
- Specification: docs/product/specs/content-model.md
- Frameworks and versions relied on: Node 24 (runs `.ts` files by stripping types; `node:test`)

## Summary

Before the site is built, every page's front matter is checked by one pure function, `validateDocs`. It receives the pages already read from disk and returns the messages of every broken rule. The build command reads the files, calls it, and stops when the list is not empty. Nothing here needs a dependency.

## Components

| Component | Responsibility | Location | Inputs | Outputs | Satisfies |
|-----------|----------------|----------|--------|---------|-----------|
| Validator | Checks pages against EDGE-1 to EDGE-4 | `app/validate.ts` | `DocPage[]` | `string[]` | REQ-1, REQ-2 |
| Build check | Reads `content/`, calls the validator, stops the build | `scripts/check-content.ts` | files | exit code, messages | REQ-3 |

## Contracts

### Component interfaces

```ts
interface DocPage { file: string; section: string; slug: string; title?: string; description?: string }
validateDocs(pages: DocPage[]): string[]
```

- Every message starts with the page's `file` and a colon.
- An empty list means every page is valid. The function never throws on a broken page and never reads a file.

### Failure paths

| EDGE | Where it is caught | What happens | Message names |
|------|--------------------|--------------|---------------|
| EDGE-1 | `validateDocs` | `title` undefined or blank | the file |
| EDGE-2 | `validateDocs` | `slug` does not match lowercase letters and digits in groups separated by single hyphens | the file and the slug |
| EDGE-3 | `validateDocs` | `description` present and longer than 160 characters; exactly 160 is valid | the file |
| EDGE-4 | `validateDocs` | the same `section/slug` seen before | the file, the address and the first file |

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|
| AC-1 | Each EDGE has a test at its boundary | unit | `node --test tests/unit/validate.spec.ts` |
| AC-2 | The build stops on a broken page | unit | `node --test tests/unit/check-content.spec.ts` |

## Assumptions to verify before implementation

- none

## Open questions

- none
