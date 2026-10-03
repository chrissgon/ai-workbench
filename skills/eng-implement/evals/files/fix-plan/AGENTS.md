# fernleaf-docs

The documentation site of Fernleaf UI, a component library. Pages are Markdown files; small Node scripts turn them into static HTML.

## Commands

Node 24 runs the `.ts` files directly (it strips the types). There is no install step, no `node_modules` and no network.

- One test file: `node --test tests/unit/validate.spec.ts`
- All tests: `node --test "tests/**/*.spec.ts"`
- Lint: `node scripts/lint.ts`
- There is no type-check command: types are stripped at run time, never checked. Do not add one.

## Conventions

- No dependencies. Use only what Node ships (`node:test`, `node:assert/strict`, `node:fs`, `node:path`). Never add a package or a lockfile.
- TypeScript that can be erased: no `enum`, no `namespace`, no parameter properties.
- Relative imports name the file with its extension: `import { validateDocs } from "./validate.ts"`.
- Named exports only; no default export.
- No `console.log` under `app/`.
- Two spaces, no tabs, a final newline. The lint checks these.
- Source lives in `app/`, tests in `tests/<group>/<name>.spec.ts`.
- The rules a page must follow are the EDGE items of `docs/product/specs/content-model.md`. A test states one of them; when code and test disagree, the specification decides which one is wrong.
- Commits follow Conventional Commits: `fix(validate): ...`. The owner commits; do not commit on their behalf.
- Workbench artifacts live under `docs/`; a task's status is kept in `docs/product/backlog.md`.
