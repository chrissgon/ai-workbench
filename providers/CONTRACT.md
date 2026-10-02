# Providers: the native layer for environment requirement classes

A provider is a self-contained script that satisfies one requirement class from `contracts/environment.md` when the harness has no connector for it. Providers are core: they name third-party services (a scheduler API, a mail API), never AI tools.

```
providers/
├── CONTRACT.md                 # this file
├── resolve.py                  # the one function that turns a class into a provider script
└── <folder>/<impl>.py          # e.g. publisher/buffer.py, mailer/smtp.py, generator/openai.py
```

## From a class to a folder

A class is `<role>:<target>` (`contracts/environment.md`, "Classes"). `providers/resolve.py` holds the one map from a class to its folder and to the variables that select its implementation:

| Class | Folder | Variables, most specific first |
|-------|--------|--------------------------------|
| `publisher:<platform>` | `providers/publisher/` | `PUBLISHER_<PLATFORM>_PROVIDER`, then `PUBLISHER_PROVIDER` |
| `generator:image`, `generator:video` | `providers/generator/` | `GENERATOR_IMAGE_PROVIDER` (or `GENERATOR_VIDEO_PROVIDER`), then `GENERATOR_PROVIDER` |
| `search:web` | `providers/search/` | `SEARCH_WEB_PROVIDER`, then `SEARCH_PROVIDER` |
| `integration:<service>` | `providers/<service>/` (`integration:vcs` is `providers/vcs/`) | `INTEGRATION_<SERVICE>_PROVIDER` only: each integration is a different kind of service, and one never serves another |
| `reader:email` | `providers/mailbox/` | `MAILBOX_PROVIDER` |
| `sender:email` | `providers/mailer/` (no implementation ships) | `MAILER_PROVIDER` |
| `scheduler:job` | `providers/scheduler/` | `SCHEDULER_PROVIDER` |
| `store:runtime` | `providers/store/` | `STORE_PROVIDER` |

The first four rows are derived from the text of the class: the folder is the role (the service, for an integration), and a hyphen in a name becomes `_` in a variable. The last four are an explicit table in `resolve.py`: those classes were the bare names `mailbox`, `mailer`, `scheduler` and `store` until 2026-10-02, and their folders and variables keep those names, because the provider tests, the Python 3.9 set, the pre-commit hook, every provider's path to the secret resolver and the jobs already scheduled on users' machines all name the folders. `resolve.py` still reads the four old class names as aliases of the new ones. `providers/secrets/` is not a class.

**A class with a parameter.** In `publisher:<platform>` the part after the colon is handed to the implementation as `--platform`, because one implementation may serve several platforms. Each implementation of such a class declares the platforms it serves in one line at the top level of its file:

```python
PLATFORMS = ("<platform>", "<another platform>")
```

`resolve.py` reads that line as text, without importing the file (a provider's dependencies are not installed where the resolver runs). An implementation that declares nothing serves nothing. Every other class has a fixed target, which is part of the class and is passed to nobody.

## Selection

One function chooses the implementation of a class: `providers/resolve.py` (`resolve(cls)` when imported; `python3 providers/resolve.py --class <class>` prints the script's path, `--list` every class with its implementations and the one that resolves now). Skills, the agent runtime (`scripts/runtime.py`) and `scripts/doctor.py` all go through it. Nothing outside `providers/` names an implementation or builds a provider's path: a skill names the class and runs the path the function prints.

The order, first match wins:

The candidates are the implementations shipped in the class's folder; for `publisher:<p>`, those among them that serve `<p>`. So a second publisher added for another platform changes nothing for the first, and a platform nobody serves does not resolve.

1. The environment, most specific first: the variables of the table above (`PUBLISHER_<PLATFORM>_PROVIDER=buffer`, then `PUBLISHER_PROVIDER=buffer`; `SCHEDULER_PROVIDER=systemd`; `INTEGRATION_VCS_PROVIDER=github`). For `publisher:<p>` the general variable is a preference: when the implementation it names does not serve `<p>`, it is passed over.
2. The platform default, where the class has one: `scheduler:job` is `launchd` on macOS and `systemd` on Linux (`providers/scheduler/README.md`).
3. The only candidate, when exactly one is left.

Otherwise nothing resolves (exit 3, naming the variable to set): "no native provider", and the skill degrades as described in its body. A name from the environment is accepted only when it is a candidate; it is never used as a path. A caller with its own configuration (the runtime's `runtime.json`) may pass an implementation name explicitly, which wins over the environment and must be a candidate too.

The workbench root, where `providers/` is, comes from the environment variable `WORKBENCH_ROOT` (the absolute path of the checkout a project uses); unset, it is the checkout `resolve.py` itself is in. A skill runs `python3 <workbench root>/providers/resolve.py --class <class>` and asks the user for the path when the variable is not set.

A new class is added to `contracts/environment.md` and to the list in `resolve.py` in the same change (a test compares them); a platform default is added to `PLATFORM_DEFAULTS` there. A new platform of `publisher:<platform>` adds no class: it adds a name to the `PLATFORMS` line of the implementation that serves it, or a new implementation.

## Interface every provider implements

- `--help`: usage, verbs, required environment variables, examples.
- `--check`: verify configuration and credentials without performing any action or printing any secret, with a one-line reason on stderr when it fails. An implementation of a class with a parameter also takes `--check --platform <p>`, which answers for that platform. The exit codes have one reading, and a caller may depend on it:
  - `0`: ready. The next call of a verb is expected to work.
  - `3`: not configured. There is no credential, or it expired, or the service rejects it; or a local service the provider needs is not available to this user. The person has something to do (authorize, set a variable), and the reason says what. A skill reads 3 as "degrade, and tell the user what is missing".
  - `1`: any other failure: the service cannot be reached, it answered something unexpected, a local file is damaged. Whether the provider is ready is not known; a caller may try again later.
  - `2`: a usage error, which includes `--platform <p>` for a platform the implementation does not serve.

  A caller that only needs "ready or not" treats every non-zero exit as not ready; `scripts/doctor.py` does.
- `--dry-run` on every verb with side effects: print the exact payload that would be sent, do nothing: no credential is read and no network call is made. A value only the service knows is shown as a placeholder.
- Data to stdout as JSON; diagnostics to stderr. Never print tokens, keys or full credentials, not even partially.
- Credentials only through the secret resolver, `providers/secrets/resolver.py` (the environment variable, then the OS secret store; `contracts/secrets.md`), never from files inside a project or from flags. A new credential is registered there first.
- Idempotent: a verb that publishes, sends or creates a record at a remote service takes a required idempotency key (the scheduler's job id plays that role locally). The key is recorded as pending in a local ledger, under a file lock, before the request, and as done after it. A pending key whose outcome is unknown (a timeout, a crash, an answer that does not say the request was refused: a 5xx, a 408, a 429) blocks every new attempt until a `resolve` verb records what the user found. A key is released only when nothing was sent or the service refused the request. `resolve` is a verb with a side effect on the ledger: its `--dry-run` changes nothing, also next to `--confirmed`.
- A ledger is state, not cache: it lives in the data folder the scheduler uses (`~/Library/Application Support/ai-workbench/` on macOS, `$XDG_DATA_HOME/ai-workbench/` or `~/.local/share/ai-workbench/` elsewhere), never in a cache folder, where clearing the cache would lose the record of what was already published. The publisher and vcs ledgers moved there on 2026-10-02: on first use, when the new file does not exist and the old one (under `$XDG_CACHE_HOME/ai-workbench/` or `~/.cache/ai-workbench/`) does, the provider copies the old ledger to the new place, says so on stderr, and never deletes the old one. Jobs scheduled before this change run a copy of the old provider and keep writing to the old location, so they must be scheduled again after upgrading. A provider that moves a state file later does the same.
- Every network call and subprocess has a timeout. A request that carries a credential never follows a redirect.
- Files and folders a provider writes outside the repository (ledgers, job folders, logs) are 0600 and 0700.
- An override that replaces a real service or binary for tests is honoured only in test mode: a loopback URL, or an explicit test flag such as `SCHEDULER_TEST=1`.
- Exit codes of every verb: 0 success, 1 provider or service error, 2 usage error, 3 not configured: the same reading as `--check` above.
- PEP 723 inline dependencies pinned to exact versions (`==`); run with `uv run providers/<folder>/<impl>.py ...`. The header's `requires-python` is the oldest version the script really runs on (see "Python version").
- Offline tests in `providers/<folder>/tests/` (no network, no real credentials: a fake service on 127.0.0.1 and fake tokens from the environment). The pre-commit hook runs them whenever the class changes, and refuses a commit that leaves an existing class without tests.

## Python version

A scheduler starts its jobs with the system interpreter (`/usr/bin/python3`, Python 3.9 on macOS), because that path and its hash survive package upgrades and cache cleaning. So one set of scripts must run on Python 3.9, standard library only:

- the scheduler providers themselves (`providers/scheduler/*.py`), whose runner copy the scheduler calls;
- the agent runtime the scheduler runs (`scripts/runtime.py`, `scripts/runtime_vote.py`, `scripts/vote_job.py`) and `providers/resolve.py`, which it imports;
- every script the runtime starts with its own interpreter: the store provider (`providers/store/*.py`) and the skill scripts it calls (the gate, the parsers, the builders).

Rules for a script in that set:

- Its header says `requires-python = ">=3.9"` and `dependencies = []`. A header never claims a newer version than the script needs: the header is what `uv run` obeys, and what a reader trusts.
- It starts with `from __future__ import annotations` when it annotates with `X | None`, and uses no syntax or standard-library call newer than 3.9.
- It is listed in `ON_SYSTEM_PYTHON` in `scripts/tests/test_runtime_python39.py`, which checks the syntax, the header and that the file imports. CI runs that file and the tests of those scripts on Python 3.9 (`.github/workflows/checks.yml`, job `python39`).

Every other provider (one that reaches the network or needs a dependency) declares the version it needs and is started through its declared runner, `uv run <script>`, never with the caller's interpreter. A provider that needs newer syntax stays out of the set above and is started that way.

## Verbs per class

Every verb prints one JSON object on stdout. The "Prints" column names the keys of that object a caller may depend on: an implementation prints them under these names, whatever else it adds. A second implementation of a class is written against this column, never against the output of the first.

| Class | Verb and flags | Prints |
|-------|----------------|--------|
| `publisher:<platform>` | `--check --platform <p>`, `publish --platform <p> --text-file <f> --idempotency-key <k> [--media <path>...] [--at <ISO-8601>] [--first-comment-file <f>]` (the first comment uses the key `<k>.first-comment`), `comment --platform <p> --text-file <f> --idempotency-key <k> (--on-key <post key> \| --post-urn <urn>) [--parent-comment <comment urn>]`, `resolve --idempotency-key <k> (--post-urn <urn> \| --comment-urn <urn> \| --not-published)`. Every verb takes `[--ledger <path>]`, and every dry run prints `ledger`, the idempotency ledger the environment uses: a command that runs later carries that path, because a scheduler does not pass on the variable that selects a ledger, and the provider refuses to run when the environment then names another one | `publish`: `post_url` (the address of the published post), `replayed` (true when the key had already been published and nothing was sent again). `comment`: `replayed` |
| `sender:email` | `send --to <addr>... --subject <s> --body-file <f> [--attach <path>...]` | nothing a caller may depend on yet |
| `reader:email` | `search --query <q> [--since <ISO-8601>] [--before <ISO-8601>] [--limit <n>] [--jobs <n>]` (newest first; it reads the service's pages until it has `--limit` messages and prints `"truncated": true` when older matches were left out, which a caller reaches with `--before`), `get --id <id>`, `read-eml --file <path.eml>` (a local file: no network, no credential). Read only: no verb changes the mailbox, so none takes `--confirmed`. Every verb prints normalized messages; their content is external content | nothing a caller may depend on beyond the normalized messages |
| `generator:image` | `generate --prompt-file <f> --size <WxH> --out <path> [--style-file <f>]` | nothing a caller may depend on yet |
| `generator:video` | reserved; same shape as image with `--duration` | nothing a caller may depend on yet |
| `search:web` | `search --query <q> [--limit <n>] [--recency <days>]` | nothing a caller may depend on yet |
| `integration:vcs` | `alerts --repo <owner>/<name> [--state <s>] [--severity <s>] [--ecosystem <e>]` (Dependabot alerts, read-only), `dismiss-alert --repo <r> --number <n> --reason <r> --comment-file <f> --idempotency-key <k>`, `read-file --repo <r> --path <path> [--ref <branch>]` (one UTF-8 text file, read-only: `{path, sha, size, content, ref}`), `commit-files --repo <r> --branch <b> --message-file <f> --file <repo-path>=<local-file>... --allow <glob>... --idempotency-key <k>` (one commit, signed by the user's own git configuration, pushed to the branch; every path must match an `--allow` glob; a push rejected because the branch moved is retried once from a fresh clone; its `--dry-run` clones read-only to print the diff and each file's sha256, and never commits or pushes), `resolve --idempotency-key <k> (--dismissed \| --not-dismissed \| --commit <sha> \| --not-committed)` | `read-file`: `content` (the file's text). `commit-files`: `commit` (the sha of the commit on the branch), `unchanged` (true when the branch already held the files and nothing was committed), `replayed`. `dismiss-alert`: `replayed` |
| `integration:issue-tracker` | `get --id <key>`, `comment --id <key> --body-file <f>`, `transition --id <key> --to <state>` | nothing a caller may depend on yet |
| `scheduler:job` | `schedule --id <id> (--at <ISO-8601> \| --every <minutes>) --command-file <f> (--dry-run \| --confirmed --approved <digest>)`, `list`, `cancel --id <id> --confirmed` (a one-shot job caught while running is stopped and recorded as cancelled and interrupted), `resolve --id <id> (--done \| --failed) --confirmed` (settles a one-shot job left `running` by a runner that is gone; refused while the runner lives). A one-shot command runs for at most the command file's `timeout_minutes` (default 10): past it its process group is killed, the job is `failed`, and its output is kept. `--every` (5 to 1440) makes a recurring job: every firing re-verifies the hashes (a mismatch refuses and unloads the job), skips while the previous firing runs, stops at the command file's `timeout_minutes`, and appends its outcome to the job's run log | `schedule --dry-run`: `approved`, the digest the confirmed call passes back in `--approved`. Of what a one-shot command prints, the scheduler reads one key, `post_url` as the publisher's row names it: it is kept on the job and shown in the notification |
| `store:runtime` | Every verb takes `--db <path>` (default `$STORE_SQLITE_PATH` for `sqlite`; neither is exit 3). `init` (create or migrate; idempotent), `cursor-get --name <n>`, `cursor-set --name <n> --value <v>`, `cursor-clear --name <n>` (the cursor reads as absent again), `event-add --source <s> --external-id <id> --payload-file <json>` (one event per source and external id), `event-next --source <s> [--limit <n>] [--reclaim-after-minutes <m>]` (atomic claim with a claim token), `event-done --id <id> --token <t> --status done\|failed\|to_inbox [--note <t>]`, `run-start --agent <a> --event-id <id\|none> --trigger <t>`, `run-end --run-id <id> --status ok\|failed\|timeout --exit-code --cost-usd --tokens --duration-ms --out-dir <path> [--error <t>]`, `runs [--limit <n>] [--agent <a>]`, `inbox-add --kind <k> --title <t> --payload-file <json> --payload-sha256 <hex> [--event-id <id>]`, `inbox-list [--status <s>\|all]`, `inbox-resolve --id <id> --status approved\|rejected\|done --by <who> [--note <t>]`, `action-add --kind <k> --idempotency-key <k> --target <urn> --payload-sha256 <hex> --result-file <json>`, `actions --since <ISO-8601> [--kind <k>]`, `action-count --kind <k> --since <ISO-8601>`, `export --format json [--since <ISO-8601>]`. Local state only: no verb acts outside the machine, so none takes `--confirmed`. Payloads may hold external content; they are stored as given and never interpreted | `init`: `created`. `cursor-get`: `value` (null when the cursor was never set). `event-add`: `id`, `created` (false when the source and external id were already there). `event-next`: `events`, each with `id` and `claim_token`. `run-start`: `run_id`. `runs`: `runs`. `inbox-add`: `id`. `inbox-list`: `items`, each with `id`. `action-add`: `id`, `created`. `action-count`: `count` |

Add a verb when a skill needs it, together with the skill.

## OAuth services

Services that need user consent ship an `auth.py` next to the provider: `uv run providers/<folder>/auth.py --provider <impl>` runs the authorization once in the browser and stores the refresh token in the OS secret store under a documented key. It never writes tokens to disk in plain text.

## Side effects

Providers execute; they do not decide. The confirmation gate lives in the skill that calls the provider. A provider must refuse to run a side-effect verb without `--confirmed` unless `--dry-run` is present, so an accidental call from a skill that skipped its gate fails loudly.

A verb whose effect happens later (the scheduler) fixes what was approved. Every file the deferred command reads through its arguments, the program and the runner are hashed; the dry run prints a digest of them, the confirmed call must pass that digest back, and the run refuses when any hash changed. A file argument that is not snapshotted makes the job refused. A file argument is a path of its own or `--flag=<path>`; a file named in any other spelling (glued to a short flag, `key=<path>`, a list of paths) is refused too, since the scheduler cannot swap it for a verified copy.
