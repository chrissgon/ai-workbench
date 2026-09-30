# Secrets contract

The workbench is automation that runs anywhere: a laptop, a cloud session, CI, and later the agent runtime. Every script and provider asks for a secret by name through one resolver, `providers/secrets/resolver.py`, and never knows where the value lives. Only where the value is stored changes between environments; the code path is the same.

## Rules

- A secret is read only through the resolver. A provider, script or eval never reads a credential from its own environment variable or the OS secret store directly.
- Lookup order, the same everywhere: the environment variable named like the secret, then its aliases, then the OS secret store (keyring, service `ai-workbench`, the username in the registry). The first non-empty value wins.
- Never in the repository, a project file, a flag, a prompt or the conversation. The resolver, `scripts/doctor.py` and every provider print where a secret was found (`environment (NAME)` or `secret store`), never its value, not even partially.
- One secret per purpose, with the minimum permission listed below. A permission that writes (dismissing alerts, publishing) lives in a separate secret from the one that reads, when the service allows it.
- A new secret is added to `REGISTRY` in the resolver and to the table below in the same change; the resolver's tests fail when the two disagree.
- A new place to keep secrets (a password manager) is a new lookup function in the resolver, after the OS secret store; callers do not change.

## Where to put a secret, per environment

| Environment | Where | How |
|-------------|-------|-----|
| Cloud session | the environment's settings, as an environment variable | name it exactly like the secret (`OPENROUTER_API_KEY`) |
| CI | a repository secret, mapped to an environment variable of the same name in the workflow | `env: VCS_GITHUB_TOKEN: ${{ secrets.VCS_GITHUB_TOKEN }}` |
| Local machine | the OS secret store (preferred), or an export in the shell | `uv run --with keyring==25.7.0 keyring set ai-workbench <username>`: the value is typed at a hidden prompt, never on the command line |
| Agent runtime (future, backlog R section) | the runtime's store, through the same resolver | not built yet |

Check what is set, without printing any value: `python3 providers/secrets/resolver.py --list`, or `python3 scripts/doctor.py`, which also names the requirement classes that read each secret. `eval_run.py --pass-env <NAME>` (every run) or `--floor-pass-env <NAME>` (the floor model's runs only, the right place for a provider key) fills a registered secret that is missing from the environment from the OS secret store, so a key kept there reaches eval runs without an export. The OpenRouter key is for the floor model only; Claude models run with the maintainer's own login (decided by the user on 2026-09-28).

## Registry

| Secret | Purpose | Minimum permission | Read by | Store username |
|--------|---------|--------------------|---------|----------------|
| `VCS_GITHUB_TOKEN` (alias `GITHUB_TOKEN`, read last) | read Dependabot alerts; a separate token dismisses them | fine-grained, only the repositories concerned: "Dependabot alerts: Read-only" (the dismissing token: "Read and write") | `providers/vcs/github.py`, `.github/workflows/dependabot-alerts.yml` | `github` |
| `LINKEDIN_ACCESS_TOKEN` (expiry from `LINKEDIN_TOKEN_EXPIRES_AT` when it comes from the environment) | publish posts on LinkedIn | OAuth scopes `openid`, `profile`, `w_member_social` | `providers/publisher/linkedin.py` | `publisher-linkedin` (a JSON record written by `providers/publisher/auth.py`) |
| `LINKEDIN_CLIENT_ID` | the LinkedIn app that authorizes the publisher, once | an app with the "Share on LinkedIn" product | `providers/publisher/auth.py` | `linkedin-client-id` |
| `LINKEDIN_CLIENT_SECRET` | that app's secret, used once by the authorization | the app's primary client secret | `providers/publisher/auth.py` | `linkedin-client-secret` |
| `GMAIL_REFRESH_TOKEN` | read the user's Gmail: search and read messages, never change them | OAuth scope `https://www.googleapis.com/auth/gmail.readonly` only | `providers/mailbox/gmail.py` | `mailbox-gmail` (a JSON record written by `providers/mailbox/auth.py`; from the environment, the bare refresh token) |
| `GMAIL_CLIENT_ID` | the Google Cloud OAuth client that authorizes and refreshes the Gmail access | a Desktop app client, in a project with the Gmail API and only the `gmail.readonly` scope | `providers/mailbox/auth.py`, `providers/mailbox/gmail.py` | `gmail-client-id` |
| `GMAIL_CLIENT_SECRET` | that client's secret, used by the authorization and every token refresh | the Desktop app client's secret | `providers/mailbox/auth.py`, `providers/mailbox/gmail.py` | `gmail-client-secret` |
| `OPENROUTER_API_KEY` | the floor model's eval runs through OpenRouter; Claude models use the maintainer's own login | a key used only for evals; a credit limit on it is recommended | `skills/core-skill-creator/scripts/eval_run.py` (`--floor-pass-env`), `adapters/agents-dir/run-prompt.sh` | `openrouter` |

## Why

Decided by the user on 2026-09-28 (backlog S13): the first real calls showed each provider resolving its credential its own way, a cloud session's own `GITHUB_TOKEN` shadowing the user's token (fixed with `VCS_GITHUB_TOKEN`), and the floor model's `OPENROUTER_API_KEY` living only in one shell and lost to later sessions. The lookup order (environment, then the OS secret store) is the one the providers already used; a password manager waits for a real case (backlog S16).
