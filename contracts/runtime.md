# Runtime contract

## What the runtime is

The runtime runs work without a person at the keyboard and keeps the person in charge of what matters. A person writes a request; code plans it as tasks from a flow file; each task runs as one skill, once, in the same container and through the same entry in which the skill was proven in the lab; what the run leaves comes back to the project by one rule of paths; and the task then waits for the person on a pending decision: a question to answer, or a delivery to release or send back. Releasing is not approving: a released delivery stays a draft in the project's state file. The runtime names no AI tool: the model and its adapter come from the gate file, `evals/eval-gate.json`, and adapters do the rest.

Two runtimes exist today. The first runtime (`scripts/runtime.py`) runs one agent on social comments and stays as it is until that agent moves to the container (stage 7 of the platform plan, `docs/architecture/platform-plan-2026-10-05.md`). The task runtime (`runtime/`) is stage 1 of that plan: an end-to-end skeleton, accepted on 2026-10-05 (`docs/architecture/skeleton-findings-2026-10-05.md`), which stage 2 hardens. Both keep their records in one store, `providers/store/sqlite.py`.

## The first runtime (until stage 7)

The runtime starts agents without a person at the keyboard: a scheduler fires, the runtime finds new work, runs an agent on it through an adapter, and executes the agent's proposal only when a deterministic gate allows it. It names no AI tool; adapters do. Decided on 2026-09-28 (`docs/decisions.md`, "An agent runtime as a new, tool-free layer"); first built for one agent, `social-manager` (backlog PB7), on a Mac with the launchd scheduler.

### Pieces

| Piece | Where | What it does |
|-------|-------|--------------|
| Trigger | `scheduler:job` class, a recurring job | runs `scripts/runtime.py tick` every N minutes |
| Runtime | `scripts/runtime.py` | finds new work, records it, runs the agent, applies the gate, executes, logs |
| Store | `store:runtime` class (`providers/store/`) | events, cursors, runs, inbox, actions; many writers at once |
| Agent run | `adapters/<harness>/run-agent.sh` | runs one agent on one task, read-only, and returns its answer |
| Gate | the skill's own script (`mkt-engage/scripts/policy_gate.py`) | decides whether a proposal is inside the person's approval |
| Actuator | a provider (`publisher:<platform>`) | executes, with an idempotency key |
| Configuration | `docs/workbench/runtime.json` in the project | paths, model, budgets, and optionally the implementation of a class; no secret. Its keys `mailbox`, `store`, `scheduler` and `publisher` are configuration keys, not class names: the runtime maps them to `reader:email`, `store:runtime`, `scheduler:job` and `publisher:<platform>` |
| Provider resolution | `providers/resolve.py` | turns a requirement class into the provider script; the runtime builds no provider path itself |

### An agent run

- **Input:** the agent definition (`agents/<name>.md`), a task file the runtime writes (what to do, and the trigger's data marked as external content), the skills the agent lists, and the project folder, which the runtime passes to the adapter as `--project`. The runtime itself confines nothing: what the model can read, inside the project and outside it, is what the adapter and its harness allow (each adapter's README says how far that goes; containing a runtime agent beyond its tool list is backlog N15).
- **Tools:** read only. The model reads files and answers; it cannot write files, run commands or call a network service. Everything it proposes comes back as a fenced JSON block in its answer, whose shape the task names.
- **Budget:** a spend limit per run (`max_cost_usd`) and a time limit (`timeout_seconds`); a daily spend cap across runs (`daily_cost_cap_usd`), checked before each run from the store. A run whose cost is unknown (the adapter has no price for the model, the run timed out, or it never ended) counts as `max_cost_usd_per_run`, and the tick's output says how many such runs the day has (`runs_without_cost_today`).
- **Output:** `<out>/response.md`, `<out>/timing.json` (`total_tokens`, `duration_ms`, `cost_usd`, `exit_code`), `<out>/raw.json` and `<out>/stderr.log`. The runtime keeps `<out>` under the run's folder and records the run in the store.

Adapter entry point:

```text
run-agent.sh --agent-file <agents/name.md> --task-file <f> --project <dir> --model <id> --out <dir>
             [--skill-dir <dir>]... [--max-cost-usd <amount>] [--timeout-seconds <n>]
```

It copies the skills (never links them) into a fresh working folder for the run, names `--project` to the harness as a folder to read, allows only reading tools (how far they reach outside `--project` is the harness's doing, and the adapter's README says it), loads no connectors and no user-level settings, and writes the files above. It exits 0 when the model answered, 1 otherwise.

### Why the model never acts

The trigger's data is written by strangers (comments, e-mails). A model that could run the publisher could be talked into publishing. So the model proposes; code decides and executes:

1. The model returns a proposal (a category, a language, a reply text).
2. The runtime writes the proposal's text to a file and runs the gate script with the approved policy. The policy file is bound by hash to what the person approved (its `policy:<sha256>` in the state file's standing approval); the gate script is bound only for a scheduled tick that carries `--pin` (below).
3. Only a gate result of `auto` makes the runtime call the actuator, with the file the gate checked and an idempotency key. Anything else goes to the inbox with the gate's reasons.

### What the approval of a recurring tick covers

The person approves the tick once, when it is scheduled (`scheduler:job`, `--every`), and it then runs unattended with the publishing credential. That approval covers:

- what the scheduler hashes: the command's arguments, the program, the scheduler's runner, and the files in the command file's snapshot (`runtime.py`, `runtime_vote.py`, `redact.py`, `providers/resolve.py`, the pin file). The job runs its own copies of them, and a firing whose hashes differ is refused;
- with `--pin <file>`: `docs/workbench/runtime.json` and the gate script (`mkt-engage/scripts/policy_gate.py` of the workbench `runtime.json` names), by the sha256 that `runtime.py pin` recorded in the pin file. Before anything else, every firing hashes both again and refuses (exit 3, nothing runs) when either differs. A tick without `--pin`, run by hand, checks nothing.

It does not cover the rest of what a firing loads from the workbench checkout that `runtime.json` names: the notification parser, the platform's data file (`shared/references/platforms/<publisher>.json`, from which the tick reads the platform's limits and which it passes to the skills' scripts), the adapter's `run-agent.sh`, the agent file and its skills, the providers (the publisher included), the vote step's scripts, and the folders of `path`. A vote job, once approved, runs its own verified copy of the data file. A change to them (a pull in that checkout) takes effect at the next firing, without a new approval. Keep that checkout on a reviewed revision; to bind one of those files, add it to the pin first.

A change to `runtime.json` or to the gate script stops the tick until the person reviews it, runs `runtime.py pin` again and schedules the tick again with the new pin file: that is the new approval.

### Records

- Every trigger item is an event (deduplicated by source and external id), claimed atomically, and ends `done`, `failed` or `to_inbox`.
- Every run: agent, event, start and end, status, exit code, cost, tokens, output folder.
- Every outward action: kind, idempotency key, target, payload hash, provider result.
- Every item for the person: the inbox, with the payload and its hash; the person approves or rejects it, and an approved item runs only if its hash still matches.

### The weekly vote step

When `runtime.json` has a `vote` section (`repo`, `branch`, `pillars`, optional `pillar_aliases`, `image`, `card_html`), each tick also runs the weekly vote step (`scripts/runtime_vote.py`; design in `docs/architecture/weekly-vote.md`):

1. Code reads the vote files from the repository (the `integration:vcs` provider's `read-file`, read only) and runs `mkt-vote-round`'s `vote_state.py`. Nothing pending, or a round already handled (cursor `vote:<round>`), ends the step. The cursor is written only once the round has an inbox item, so a failure before that leaves the round for the next tick; `reject` on a vote item clears it (the store's `cursor-clear`), and the next tick redoes the round.
2. The agent runs read-only with `mkt-vote-round` and returns one `vote-proposal` block. The runtime checks it against the state (the winner's text or one of the three options with a reason, the slot's language, the next pillar, three non-empty options) and never repairs it.
3. Code builds everything the approval covers: the content file, `check_post.py`, the post image (`render.py`; without a browser the post goes text-only and the item says so), the next round's queue file (`vote_update.py --queue-round`, which refuses used topics), the publish job (which carries the publisher's idempotency ledger, as the publisher's dry run names it, so that the job at its slot uses the ledger it was approved with), and one bundle file. The bundle's sha256 is the inbox item's hash. A failed check leaves the item not ready: it cannot be approved.
4. `approve --id <n> --confirmed --sha256 <hash>` on a `vote` item re-hashes every file, refuses when the queue file in the repository moved, schedules the job at the slot (the scheduler's dry run, then the confirmed call with its digest) and commits the queue file (`commit-files`, only `data/pick-queue.json`).
5. At the slot, `scripts/vote_job.py`, scheduled with the system interpreter's fixed path and carrying the folders of `runtime.json`'s `path` (the scheduler's own `PATH` is short), publishes the post (first comment, image), reads the vote files again and commits only `post_url` on the round, the post in `posts.json` and its image. The post counts as published as soon as the publisher prints its address: when only the first comment failed, the job still records the post, then exits 1 and reports the comment's error. A failure after publishing prints what to record by hand.

### Safety rules

- The runtime never publishes without a gate result of `auto` under an active approval, or an inbox item the person approved with a matching hash.
- The runtime never publishes a text in which the shared credential formats (`scripts/redact.py`) match: the model that drafted it can read files, and a comment can ask it to quote one. A reply with such a match is not sent, by the tick or by `approve`; it goes to the inbox with the value masked and no reply file, and the person answers by hand. A vote proposal with one is masked in everything built from it, and its item cannot be approved.
- A proposal block that is missing, malformed or has fields outside the task's shape sends the event to the inbox; the runtime never repairs a proposal.
- A mailbox that cannot be read (an expired authorization, the network) does not stop the tick: pasted comments and the vote step still run, the mailbox cursor stays where it was, the tick's output carries `mailbox: {status: failed, note}`, and the person is notified at most once a day.
- The mailbox cursor never moves past a message that was not read. The mailbox answers newest first and says when older messages were left out; the tick reads on until none is, and when it cannot (a later search fails, or more wait than a tick reads) it keeps what it read as events, leaves the cursor where it was and says `mailbox: {status: incomplete, note}`.
- An error the runtime did not expect, in one event or in the vote step, does not end the tick: the event ends `failed` with the error's type, a run that was open ends `failed`, the traceback goes to stderr, and the next event is handled.
- The daily cost cap stops new runs; pending events wait for the next day or for the person.
- Configuration holds paths and limits only; credentials come through `providers/secrets/resolver.py`.
- One tick at a time per project (a lock); the scheduler also refuses overlapping firings.

## Pieces

The modules of the task runtime that exist, and what each owns. A later stage adds modules; each is listed here when it is built.

| Path | What it owns |
|---|---|
| `runtime/lab.py` | The lab facade: the only file of `runtime/` that reads anything under `evals/`. Runs one skill once in the eval container; the pause on the account limit, the refusals, the early end and the stopping are the lab's own functions. Never builds the eval image: a missing one is an error |
| `runtime/ops.py` | The operations layer: request, run the next task, pending, answer, release, retry, cancel, status. Every shell calls it; no shell reaches the store, the facade or a project's files by itself |
| `runtime/cli.py` | The terminal shell: one command per operation, one JSON object printed |
| `runtime/flow_files.py` | Reads and checks a flow file, `flows/<name>.json` |
| `runtime/skill_meta.py` | What a skill declares in its frontmatter (artifact lists, requirement classes, side effects, version) |
| `runtime/path_rule.py` | The path rule: the one class of each path a run left (`state`, `machine`, `document`, `versioned`, `ignored`, `other`) |
| `runtime/state_merge.py` | The one module that decides what a run may change in `docs/workbench/state.md`. Stage 1: the whole file, only when the origin did not change; stage 2 replaces it with the real merge |
| `runtime/endings.py` | The classifier of endings: a closed list; what no rule recognises is `unclassified` |
| `runtime/project_config.py` | The project's configuration, `docs/workbench/runtime.json`, and its hash |
| `runtime/tests/` | The tests of the above, offline, with a stand-in adapter and invented skills; `corpus/` holds the classifier's corpus of archived lab runs |
| `flows/market-positioning.json` | The first flow file: a market analysis, then the customer profile and positioning |
| `providers/store/sqlite.py` | The store (class `store:runtime`): migration 2 holds the task runtime's three tables; its functions are the contract, one transaction each |
| `providers/documents/notion_blocks.py` | A pure helper of the documents provider and its round-trip test; the provider itself is stage 3 |

The configuration of a project names three absolute paths: `workbench` (the checkout the runtime runs from, a reviewed revision), `data_dir` (a folder outside every repository, for run folders and the run lock) and `store_db`. Every operation refuses a project whose configuration names another checkout than the one it runs from. The hash of the file is computed and shown; stage 2 enforces it.

## A task run

`run-next` takes the oldest `ready` task of the project, one task at a time per project (a lock in `data_dir`), and runs its skill once:

- **What enters the copy:** the artifacts the skill declares (its `inputs`, `outputs` and `updates`) that exist under `docs/` of the project, as regular files. Never the runtime's configuration, a link, a file whose real path leaves the project, or anything outside `docs/`. The project's `AGENTS.md` is left out in stage 1 and listed in `left_out`; stage 2 brings it in when the skill declares it (L5).
- **The text:** the request in the person's words, then "For this task:" and the task's text from the flow file; on a run made after an answer, every earlier reply of the task with the person's answer, oldest first, each answer stated as the person's decision. The text names no skill: the one skill staged for the run loads by its description, as in a lab run.
- **How the skill is staged:** as in a lab run (`scripts/stage_skills.py`): the skill's folder, without its `evals/` and `scripts/tests/`, with the shared references it cites, where the adapter's tool discovers skills. Only that skill is staged.
- **Where it runs:** in the eval container of `evals/executor.py`, on the image the lab evidence is bound to, through the adapter's `run-prompt.sh`, on the reference model of the gate file. A copy that carries a tool's settings is refused before any model call.
- **The network:** a skill that requires `search:web` runs on the open network and may search and fetch pages; any other run reaches only the model provider, through the egress proxy.
- **The credential:** never enters the container. The model's credential is read from the secret store on the machine and held by a key proxy outside the run container, which adds it to each call. Every value passed to a run is replaced by its marker in everything the run leaves, before anything is read or stored.
- **Limits of time:** the gate file's `timeout_seconds` (1,800) per attempt, and its retries for a timeout, a failure of the adapter, a refusal or an early end. A refused credential is never retried. On the account limit the run pauses and starts again afterwards, without counting as a failure.
- **What comes back:** each file the run created or changed is given one class by the path rule. `document` (Markdown under `docs/`), `machine` (any other file under `docs/`, and `.workbench-local/`) and `state` come back; `state` through `runtime/state_merge.py`. Only a regular file with its real path inside the copy comes back, and a file that changed in the project while the run was in progress is never overwritten. What does not come back is listed in `kept` with its class and reason. Nothing in the project is deleted.
- **Where it is kept:** the run folder `<data_dir>/task-runs/<run id>/`: `prompt.md`, `cwd/` (the copy as the run left it) and `outputs/` (`response.md`, `timing.json`, `raw.json`, `stderr.log`, `stream.jsonl`); an attempt made again is set aside beside them. The run's row in the store records the rest.

## Records

**Three tables** of migration 2 of the store: `tasks` (a request, with no parent and no skill, and the tasks of its plan), `task_runs` (one row per run: skill, version and content hash, model and adapter, web, status, failure kind, ending, attempts, cost, tokens, duration, whether the skill was reported loaded, image digest, run folder, error) and `pending_decisions` (what a task waits for the person to decide: kind, title, the reply as the body, a payload, status, resolution and answer).

**Nine task states:** `requested`, `planned`, `ready`, `running`, `waiting`, `blocked`, `done`, `failed`, `cancelled`. A `waiting` task always has exactly one open pending decision; one task is `running` at a time per database.

**Six endings** of a run that did not fail: `done`, `question`, `draft_with_questions`, `gate`, `blocked`, `unclassified`. Stage 1 recognises `done`, `question` and `draft_with_questions`, and calls anything else `unclassified`; stage 2 recognises `gate` and `blocked` and makes the classifier total against its corpus. A run that failed has a failure kind instead: `timeout`, `refused`, `auth`, `adapter`, `early_end`, `settings`, `stopped` or `internal`.

**Six kinds of pending decision:** `plan` (stage 3), `question`, `review`, `effect` (stage 4), `acceptance` (stages 3 and 6) and `your_document` (stage 10). Stage 1 opens two:

| Kind | Opened when | Resolutions |
|---|---|---|
| `question` | A run ended `question`: it wrote nothing and asks | `answered`: the task is `ready`, and its next run gets the answer |
| `review` | A run ended `done`, `draft_with_questions` or `unclassified`: the body is the whole reply, so a draft's open questions are in it | `released`: the task is `done`, the tasks that depended on it become `ready`, and the document stays a draft with its open questions; `answered`: the task is `ready` again, and its next run gets the person's text |

## The limits

The twenty limits that live in code (section B.2 of the platform plan). Each gets a test named after it in the stage that builds it; stage 1 built a first form of four of them.

| # | Limit | Built by | Test |
|---|---|---|---|
| L1 | Every run starts from a new copy, with the skills installed again from the fixed checkout | stage 2 | stage 2 |
| L2 | What enters: versioned files, the project's documents, the machine files the skills use, and what the person handed over through the file drop. No other file outside git. The store and the runtime's configuration never | stage 2 | stage 2 |
| L3 | A task with the web receives only the artifacts its skill declares | stage 2 | stage 2 |
| L4 | A tool's configuration files are removed at any depth | stage 2 | stage 2 |
| L5 | The project's `AGENTS.md` enters when the skill declares it | stage 2 | stage 2 |
| L6 | No credential enters the container | stage 2 (first form in stage 1) | first form: `runtime/tests/test_lab_facade.py`, `test_the_value_of_a_passed_variable_is_replaced_in_everything_a_run_leaves` |
| L7 | The destination of each returned file comes from the path rule | stage 2 (first form in stage 1) | first form: `runtime/tests/test_return_rules.py`, `test_every_path_gets_exactly_one_class` |
| L8 | Only a regular file, with its real path inside the copy, comes back | stage 2 (first form in stage 1) | first form: in `runtime/ops.py` (`bring_back`); its test is stage 2 |
| L9 | Code comes back as a change set; the commit is one, made by the code provider with the person's own git and signature | stage 4 | stage 4 |
| L10 | The state file comes back through a merge made by one module | stage 2 | stage 2 |
| L11 | A working document never enters a commit | stage 4 | stage 4 |
| L12 | What comes back never overwrites what changed at the origin | stage 2 (first form in stage 1) | first form: `runtime/tests/test_task_ops.py`, `test_a_file_that_changed_in_the_project_during_the_run_is_never_overwritten`; `runtime/tests/test_return_rules.py`, `test_the_state_file_comes_back_whole_only_when_the_origin_did_not_change` |
| L13 | A record only grows | stage 4 (approvals) | stage 4 |
| L14 | Everything passes the credential scan before it leaves | stage 2 | stage 2 |
| L15 | An external effect is executed by code, with the exact content approved or inside an approved policy | stage 4 | stage 4 |
| L16 | A skill with a confirmation gate runs up to the gate; what it shows there is what the person approves | stage 4 | stage 4 |
| L17 | The approval lives in the approvals table; the rows in the state file are generated copies | stage 4 | stage 4 |
| L18 | A document bound to an approval by hash is a machine file | stage 6 | stage 6 |
| L19 | The planning agent creates no task: it returns the route, and code builds the plan | stage 3 | stage 3 |
| L20 | The measurement files are not changed | stage 4 (for the change set) | stage 4 |

## What the proof covers

The battery measured one skill, in one run, with an input in the form of its cases. That holds for the runtime because the container and the entry are the same. What the runtime adds was not measured: resuming a task with the person's answers in the request, and running a skill on a document another model wrote. For those the only check is field evidence, recorded from the first task. The runtime uses a band only after checking that the measurement files of its checkout are the recorded ones and that the image is the evidence's; when either fails, the skill runs on the reference model and without autonomy. A skill runs in the condition it was measured in.
