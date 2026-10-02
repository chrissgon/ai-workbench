# Environment contract: requirement classes

Skills declare what they need from the environment as *classes*, never as products. The environment (a harness connector, an MCP server, or a provider script) satisfies a class. This keeps the core harness-agnostic and lets the orchestrator degrade gracefully when something is missing.

## Classes

| Class | Examples of concrete providers | Used by |
|-------|-------------------------------|---------|
| `integration:issue-tracker` | Jira, Linear, GitHub Issues | engineering flows |
| `integration:vcs` | GitHub, GitLab | delivery |
| `integration:design-tool` | Figma; the design-system projects of a generative design tool | design, validation |
| `search:web` | any web search tool, including fetching the pages it returns | research, business, marketing |
| `generator:image` | any image model behind an API | design assets, marketing |
| `generator:video` | any video model behind an API | marketing (slot reserved, not implemented) |
| `publisher:<platform>` | LinkedIn via a scheduler API, X, blog CMS | marketing |
| `mailer` | SMTP, a mail API | marketing, notifications |
| `mailbox` | Gmail API, IMAP (read only: search and read messages) | marketing, engagement |
| `scheduler` | native scheduling in the publisher, or a harness routine | marketing, operations |
| `store` | SQLite (a local file); a cloud database later | the agent runtime: cursors, events, runs, approval inbox, executed actions |

Add a class when a second skill needs it; do not add classes speculatively. Class names are identifiers and are not renamed: some carry a prefix (`integration:`, `search:`, `generator:`, `publisher:`) and some are bare (`mailer`, `mailbox`, `scheduler`, `store`; the last three have a native provider under `providers/`), and a skill copies a name exactly as this table spells it.

## Resolution order

1. **Harness connector** (MCP server or built-in integration). Authentication is handled by the harness and consented by the user in its UI. Preferred: the model never touches credentials.
2. **Provider script** under `providers/<class>/`, following `providers/CONTRACT.md`, reading credentials from environment variables or the OS secret store. Used when the harness has no connector for the class, or for harnesses without connectors at all.
3. **Degrade.** The skill produces the deliverable up to the point where the tool is needed, tells the user exactly what is missing, and stops. It never fakes the effect.

A skill's body must describe its behaviour at step 3 for every class it requires.

## Credentials

- Never in this repository. `.env` files are ignored by git.
- Provider scripts read `<CLASS>_PROVIDER` to pick the implementation and provider-specific variables for credentials (documented in the script's `--help`).
- OAuth-based services need a one-time interactive authorization performed by the user with a dedicated script, which stores the refresh token in the OS secret store, never in a file inside a project.
- Service-side access approval (for example, platform APIs that require an approved developer application) is outside this repository's control. Skills say so when relevant.

## Side effects and consent

Any skill that publishes, sends, deploys, schedules or creates something outside the repository declares it in `metadata.side_effects` and implements a `## Confirmation gate` section.

**One explicit approval, then autonomy.** The user approves once; after that the skill proceeds without asking again, including later and unattended for scheduled work. The gate exists to make the user see exactly what will happen, not to interrupt them repeatedly.

Approval scopes, recorded in `docs/workbench/state.md` under "Approvals":

| Scope | What the user approves | What runs without asking again | Default for |
|-------|------------------------|--------------------------------|-------------|
| action | one exact payload (text, media, recipients, time, target) | that payload, once, now or at its scheduled time | irreversible public actions: publish, send, deploy to production |
| plan | a set of actions shown together (a week of posts, a release with its steps) | every action in the set, as long as it matches what was shown | batches and scheduled series |
| standing | a class of action within stated bounds (open PRs on `feature/*`, commit to non-protected branches), with an expiry | any action inside the bounds until expiry | reversible, low-blast-radius actions inside the project |

Rules:

- The gate shows the exact payload or plan, asks once, and proceeds on an explicit yes. Silence, a previous different approval, or an approval for a similar item is not consent.
- An approval covers exactly what was shown. Any deviation (changed content, new recipient, different time or target) needs a new approval for the changed part only.
- **The approval binds a hash of the payload.** The skill writes the payload, exactly as shown, to a file in a folder from `mktemp -d` and records `sha256sum <file>` (macOS: `shasum -a 256`) in the approval's `Payload hash`. What it executes is that file, never a payload written again (a model does not write the same text twice). Before executing under an `action` or `plan` approval, it hashes the file again and executes only when the hash equals the approval's; a missing file or a different hash means showing the payload and asking again. Only the hash is stored, never the payload. When the execution comes later than the approval (a scheduled post, a plan that runs over days), the folder is a durable one inside the project that git ignores (`.workbench-local/payloads/<date>/`, mode 0700), never a temporary folder: the system removes old temporary folders, and an approval whose payload is gone cannot be verified or executed again. The skill checks that git ignores the folder before writing to it. For such a payload the hash covers contents and paths relative to the payload folder, never absolute paths, so the same payload moved or built again from unchanged sources has the same hash and stays approved. When a skill changes how it computes the hash, approvals already recorded keep their recorded hash and the skill says how to check them; an old approval whose payload cannot be checked any more is asked again for what has not run. A `standing` approval covers a class of action within bounds, not a payload; when its bounds are written in a file (an engagement policy), its `Payload hash` is `policy:<sha256 of that file>`, and every action under it checks that hash first, so editing the bounds stops the actions until the person approves the new file.
- Approvals are recorded in state with scope, summary, date, expiry and status (`pending-execution`, `executed`, `active`, `expired`). A resumed session reads them and never re-asks for what is already approved.
- **Pre-approved execution**: when an action runs later or unattended (a scheduled post, a nightly job), the confirmation happens at scheduling time with the final payload. At execution time the skill verifies the payload still matches the approval (same `Payload hash`), executes, and updates the status to `executed` with a timestamp. If it no longer matches, it does not execute and leaves a note in "Open questions".
- Standing approvals are never granted by default for public or irreversible actions; the user must state them explicitly, with bounds and expiry.
- Providers refuse side-effect verbs without `--confirmed` (see `providers/CONTRACT.md`), so a skill that skipped its gate fails loudly.

## Checking an environment

`python3 scripts/doctor.py [--harness <adapter>]` lists every class the installed skills require and whether a connector (declared in `adapters/<harness>/connectors.json`) or a native provider satisfies it. Flows run it before a phase that needs an external tool and degrade accordingly.
