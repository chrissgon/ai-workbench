# plinthui-docs

The documentation site of the Plinth UI component library, built as static files.

## Commands

- Build: `npm run build` (writes `dist/`)
- Test: `npm test`

## Rules

- The site is static: nothing of ours runs on a server, and the host serves `dist/` as it is.
- Specifications live in `docs/product/specs/`; designs in `docs/engineering/designs/`.
- A new runtime or build dependency is added only after the maintainers agree to it.
