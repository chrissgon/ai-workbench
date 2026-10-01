# {name}

{one-paragraph overview from README or manifest description: what it is, for whom, current version or status}

## Architecture

See `{architecture artifact path}` for components, contracts and hard rules.

## Commands

| Task | Command | Notes |
|------|---------|-------|
| Install | `{from lockfile: bun install / npm ci / pnpm install}` | |
| Build | `{from scripts}` | |
| Test | `{from scripts}` | {what it runs: unit, e2e} |
| Lint | `{from scripts}` | |
| Type-check | `{from scripts}` | |
| Release | `{from scripts}` | {who runs it} |

## Conventions

- Code style: {formatter and linter names from configs}; run `{lint command}` before committing.
- Naming and structure: {only what a config or document states}
- Commits: {from commitlint config or hooks, e.g. Conventional Commits}
- Pull requests: {from template or documented process}

## Testing

- {frameworks from configs}; tests live in `{folders}`; {coverage or e2e notes grounded in config}

## Security

- {secrets handling from .gitignore/.env.example; auth or data rules only if documented}

## Working rules

{conventions carried over from tool-specific files, confirmed by the user, in tool-neutral words; one per line}
