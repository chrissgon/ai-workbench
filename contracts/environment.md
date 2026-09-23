# Environment contract: requirement classes

Skills declare what they need from the environment as *classes*, never as products. The environment (a harness connector, an MCP server, or a provider script) satisfies a class. This keeps the core harness-agnostic and lets the orchestrator degrade gracefully when something is missing.

## Classes

| Class | Examples of concrete providers | Used by |
|-------|-------------------------------|---------|
| `integration:issue-tracker` | Jira, Linear, GitHub Issues | engineering flows |
| `integration:vcs` | GitHub, GitLab | delivery |
| `integration:design-tool` | Figma | design, validation |
| `search:web` | any web search tool | research, business, marketing |
| `generator:image` | any image model behind an API | design assets, marketing |
| `generator:video` | any video model behind an API | marketing (slot reserved, not implemented) |
| `publisher:<platform>` | LinkedIn via a scheduler API, X, blog CMS | marketing |
| `mailer` | SMTP, a mail API | marketing, notifications |
| `scheduler` | native scheduling in the publisher, or a harness routine | marketing, operations |

Add a class when a second skill needs it; do not add classes speculatively.

## Resolution order

1. **Harness connector** (MCP server or built-in integration). Authentication is handled by the harness and consented by the user in its UI. Preferred: the model never touches credentials.
2. **Provider script** shipped with a skill or shared in the repository, reading credentials from environment variables or the OS secret store. Used when the harness has no connector for the class, or for harnesses without connectors at all.
3. **Degrade.** The skill produces the deliverable up to the point where the tool is needed, tells the user exactly what is missing, and stops. It never fakes the effect.

A skill's body must describe its behaviour at step 3 for every class it requires.

## Credentials

- Never in this repository. `.env` files are ignored by git.
- Provider scripts read `<CLASS>_PROVIDER` to pick the implementation and provider-specific variables for credentials (documented in the script's `--help`).
- OAuth-based services need a one-time interactive authorization performed by the user with a dedicated script, which stores the refresh token in the OS secret store, never in a file inside a project.
- Service-side access approval (for example, platform APIs that require an approved developer application) is outside this repository's control. Skills say so when relevant.

## Side effects

Any skill that publishes, sends, deploys, schedules or creates something outside the repository declares it in `metadata.side_effects` and implements a `## Confirmation gate` section: show the exact payload (text, media, recipients, time, target), ask for explicit confirmation, execute only after it, then record the action in `docs/workbench/state.md`.
