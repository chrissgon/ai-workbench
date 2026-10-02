# fernleaf-docs

The documentation site of Fernleaf UI, a component library. Pages are Markdown files; small Node scripts turn them into static HTML.

## Commands

Node 24 runs the `.ts` files directly (it strips the types). There is no install step, no `node_modules` and no network.

- One test file: `node --test tests/unit/markdown.spec.ts`
- All tests: `node --test "tests/**/*.spec.ts"`
- Lint: `node scripts/lint.ts`
- Generate one page and print its HTML: `node scripts/generate.ts content/components/button.md`
- There is no type-check command: types are stripped at run time, never checked. Do not add one.

## Conventions

- No dependencies. Use only what Node ships (`node:test`, `node:assert/strict`, `node:fs`, `node:path`). Never add a package or a lockfile.
- TypeScript that can be erased: no `enum`, no `namespace`, no parameter properties.
- Relative imports name the file with its extension: `import { highlight } from "./highlight.ts"`.
- Named exports only; no default export.
- No `console.log` under `app/`.
- Two spaces, no tabs, a final newline. The lint checks these.
- Source lives in `app/`, block components in `app/components/`, tests in `tests/<group>/<name>.spec.ts`.
- The renderer `app/markdown.ts` and the component interface are contracts of the design: a change to either goes through the design and its decision record first, never through a task that does not list them.
- Commits follow Conventional Commits: `feat(example): ...`. The owner commits; do not commit on their behalf.
- Workbench artifacts live under `docs/`; a task's status is kept in `docs/product/backlog.md`.
