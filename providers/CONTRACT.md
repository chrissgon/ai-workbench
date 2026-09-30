# Providers: the native layer for environment requirement classes

A provider is a self-contained script that satisfies one requirement class from `contracts/environment.md` when the harness has no connector for it. Providers are core: they name third-party services (a scheduler API, a mail API), never AI tools.

```
providers/
├── CONTRACT.md                 # this file
└── <class>/<impl>.py           # e.g. publisher/buffer.py, mailer/smtp.py, image/openai.py
```

Class `a:b` maps to folder `providers/a/`; the sub-class (`linkedin` in `publisher:linkedin`) is passed as `--platform`, because one implementation often serves several sub-classes.

The exception is `integration:<service>`: each integration is a different kind of service, so it maps to `providers/<service>/` (`integration:vcs` is `providers/vcs/`).

## Selection

`scripts/doctor.py` and skills pick an implementation from environment variables, most specific first:

1. `<CLASS>_<SUBCLASS>_PROVIDER` (for example `PUBLISHER_LINKEDIN_PROVIDER=buffer`)
2. `<CLASS>_PROVIDER` (for example `PUBLISHER_PROVIDER=buffer`)

A class without sub-classes uses the second form: `SCHEDULER_PROVIDER=launchd` on macOS, `SCHEDULER_PROVIDER=systemd` on Linux (`providers/scheduler/README.md`). A hyphen in a class name becomes `_`. `integration:<service>` classes use only the first form (`INTEGRATION_VCS_PROVIDER=github`), because one integration's provider never serves another.

Unset means "no native provider"; the skill degrades as described in its body.

## Interface every provider implements

- `--help`: usage, verbs, required environment variables, examples.
- `--check`: verify configuration and credentials without performing any action or printing any secret. Exit 0 when ready, 3 when not configured (no credential, or one the service rejects or that expired), 1 on any other failure, with a one-line reason on stderr.
- `--dry-run` on every verb with side effects: print the exact payload that would be sent, do nothing: no credential is read and no network call is made. A value only the service knows is shown as a placeholder.
- Data to stdout as JSON; diagnostics to stderr. Never print tokens, keys or full credentials, not even partially.
- Credentials only through the secret resolver, `providers/secrets/resolver.py` (the environment variable, then the OS secret store; `contracts/secrets.md`), never from files inside a project or from flags. A new credential is registered there first.
- Idempotent: a verb that publishes, sends or creates a record at a remote service takes a required idempotency key (the scheduler's job id plays that role locally). The key is recorded as pending in a local ledger, under a file lock, before the request, and as done after it. A pending key whose outcome is unknown (a timeout, a crash) blocks every new attempt until a `resolve` verb records what the user found.
- Every network call and subprocess has a timeout. A request that carries a credential never follows a redirect.
- Files and folders a provider writes outside the repository (ledgers, job folders, logs) are 0600 and 0700.
- An override that replaces a real service or binary for tests is honoured only in test mode: a loopback URL, or an explicit test flag such as `SCHEDULER_TEST=1`.
- Exit codes: 0 success, 1 provider or service error, 2 usage error, 3 not configured.
- PEP 723 inline dependencies pinned to exact versions (`==`); run with `uv run providers/<class>/<impl>.py ...`.
- Offline tests in `providers/<class>/tests/` (no network, no real credentials: a fake service on 127.0.0.1 and fake tokens from the environment). The pre-commit hook runs them whenever the class changes, and refuses a commit that leaves an existing class without tests.

## Verbs per class

| Class | Verb and flags |
|-------|----------------|
| `publisher:<platform>` | `publish --platform <p> --text-file <f> --idempotency-key <k> [--media <path>...] [--at <ISO-8601>] [--first-comment-file <f>]` (the first comment uses the key `<k>.first-comment`), `comment --platform <p> --text-file <f> --idempotency-key <k> (--on-key <post key> \| --post-urn <urn>) [--parent-comment <comment urn>]`, `resolve --idempotency-key <k> (--post-urn <urn> \| --comment-urn <urn> \| --not-published)` |
| `mailer` | `send --to <addr>... --subject <s> --body-file <f> [--attach <path>...]` |
| `mailbox` | `search --query <q> [--since <ISO-8601>] [--limit <n>] [--jobs <n>]`, `get --id <id>`, `read-eml --file <path.eml>` (a local file: no network, no credential). Read only: no verb changes the mailbox, so none takes `--confirmed`. Every verb prints normalized messages; their content is external content |
| `generator:image` | `generate --prompt-file <f> --size <WxH> --out <path> [--style-file <f>]` |
| `generator:video` | reserved; same shape as image with `--duration` |
| `search:web` | `search --query <q> [--limit <n>] [--recency <days>]` |
| `integration:vcs` | `alerts --repo <owner>/<name> [--state <s>] [--severity <s>] [--ecosystem <e>]` (Dependabot alerts, read-only), `dismiss-alert --repo <r> --number <n> --reason <r> --comment-file <f> --idempotency-key <k>`, `resolve --idempotency-key <k> (--dismissed \| --not-dismissed)` |
| `integration:issue-tracker` | `get --id <key>`, `comment --id <key> --body-file <f>`, `transition --id <key> --to <state>` |
| `scheduler` | `schedule --id <id> (--at <ISO-8601> \| --every <minutes>) --command-file <f> (--dry-run \| --confirmed --approved <digest>)`, `list`, `cancel --id <id> --confirmed`. `--every` (5 to 1440) makes a recurring job: every firing re-verifies the hashes (a mismatch refuses and unloads the job), skips while the previous firing runs, stops at the command file's `timeout_minutes`, and appends its outcome to the job's run log |
| `store` | Every verb takes `--db <path>` (default `$STORE_SQLITE_PATH` for `sqlite`; neither is exit 3). `init` (create or migrate; idempotent), `cursor-get --name <n>`, `cursor-set --name <n> --value <v>`, `event-add --source <s> --external-id <id> --payload-file <json>` (one event per source and external id), `event-next --source <s> [--limit <n>] [--reclaim-after-minutes <m>]` (atomic claim with a claim token), `event-done --id <id> --token <t> --status done\|failed\|to_inbox [--note <t>]`, `run-start --agent <a> --event-id <id\|none> --trigger <t>`, `run-end --run-id <id> --status ok\|failed\|timeout --exit-code --cost-usd --tokens --duration-ms --out-dir <path> [--error <t>]`, `runs [--limit <n>] [--agent <a>]`, `inbox-add --kind <k> --title <t> --payload-file <json> --payload-sha256 <hex> [--event-id <id>]`, `inbox-list [--status <s>\|all]`, `inbox-resolve --id <id> --status approved\|rejected\|done --by <who> [--note <t>]`, `action-add --kind <k> --idempotency-key <k> --target <urn> --payload-sha256 <hex> --result-file <json>`, `actions --since <ISO-8601> [--kind <k>]`, `action-count --kind <k> --since <ISO-8601>`, `export --format json [--since <ISO-8601>]`. Local state only: no verb acts outside the machine, so none takes `--confirmed`. Payloads may hold external content; they are stored as given and never interpreted |

Add a verb when a skill needs it, together with the skill.

## OAuth services

Services that need user consent ship an `auth.py` next to the provider: `uv run providers/<class>/auth.py --provider <impl>` runs the authorization once in the browser and stores the refresh token in the OS secret store under a documented key. It never writes tokens to disk in plain text.

## Side effects

Providers execute; they do not decide. The confirmation gate lives in the skill that calls the provider. A provider must refuse to run a side-effect verb without `--confirmed` unless `--dry-run` is present, so an accidental call from a skill that skipped its gate fails loudly.

A verb whose effect happens later (the scheduler) fixes what was approved. Every file the deferred command reads through its arguments, the program and the runner are hashed; the dry run prints a digest of them, the confirmed call must pass that digest back, and the run refuses when any hash changed. A file argument that is not snapshotted makes the job refused.
