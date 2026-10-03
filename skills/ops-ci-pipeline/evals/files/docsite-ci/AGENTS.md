# docsite

Documentation site (Nuxt, static generation), hosted on Netlify at https://docs.docsite.example (site name `docsite-docs`). Repository: code.example/docsite-team/docsite.

- Install: `npm ci`
- Runtime: Node 22.19.0 (`.nvmrc`).
- Deploy tool: netlify-cli 27.10.0, run with `npx --yes netlify-cli@27.10.0`; it is not a dependency of the project.
- Checks: `npm run lint`, `npm run typecheck`, `npm run test` (unit tests, then Playwright over the generated site; run `npm run generate` first)
- One maintainer.
