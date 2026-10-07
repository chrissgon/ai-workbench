# Runtime contract

## What the runtime is

The runtime runs work without a person at the keyboard and keeps the person in charge of what matters. A person writes a request; code plans it as tasks from a flow file; each task runs as one skill, once, in the same container and through the same entry in which the skill was proven in the lab; what the run leaves comes back to the project by one rule of paths; and the task then waits for the person on a pending decision: a question to answer, or a delivery to release or send back. Releasing is not approving: a released delivery stays a draft in the project's state file. The runtime names no AI tool: the model and its adapter come from the gate file, `evals/eval-gate.json`, and adapters do the rest.

Two runtimes exist today. The first runtime (`scripts/runtime.py`) runs one agent on social comments and stays as it is until that agent moves to the container (stage 7 of the platform plan, `docs/architecture/platform-plan-2026-10-05.md`). The task runtime (`runtime/`) began as stage 1 of that plan, an end-to-end skeleton accepted on 2026-10-05 (`docs/architecture/skeleton-findings-2026-10-05.md`), and holds the stages built since ("Pieces" below). Both keep their records in one store, `providers/store/sqlite.py`.

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
| `runtime/ops.py` | The operations layer: every operation a shell can perform (request, route, approve, reject, run the next task, pending, answer, release, retry, cancel, status, the configuration, the mirrors, the file drop, the dependencies, the standing approvals, the proof, the verdict, progress, the dispatcher's jobs, the conversation). Every shell calls it; no shell reaches the store, the facade or a project's files by itself |
| `runtime/cli.py` | The terminal shell: one command per operation, one JSON object printed |
| `runtime/flow_files.py` | Reads and checks a flow file, `flows/<name>.json` |
| `runtime/skill_meta.py` | What a skill declares in its frontmatter (artifact lists, requirement classes, side effects, version) |
| `runtime/path_rule.py` | The path rule: the one class of each path a run left (`state`, `machine`, `document`, `versioned`, `ignored`, `other`) |
| `runtime/state_merge.py` | The one module that decides what a run may change in `docs/workbench/state.md` (L10): of a run's text it takes a draft row of the skill that ran, a decision attributed to that skill and a new open question (read in any list form, written as a checkbox `- [ ] <text>`, refused when attributed to the person or to another skill), line by line, on top of what the project has now; the rest stays as the project has it, and each refused line is reported with its reason. `with_answer` writes the person's answer to a question as a decision of the user; only code writes it |
| `runtime/endings.py` | The classifier of endings: a closed list; what no rule recognises is `unclassified` |
| `runtime/project_config.py` | The project's configuration, `docs/workbench/runtime.json`, and its hash |
| `runtime/workcopy.py` | What enters a run copy, limits L1 to L6, each left-out file listed with its reason (`entering`), and what comes back, limits L7, L8, L12 and L14 (`returning`, `masked_reply`); the project's `AGENTS.md` enters only when the skill declares it, without the two lines the container cannot serve, and only its workbench section when a protected path covers it and the skill is not of a code area |
| `runtime/manifest.py` | A skill's runtime manifest, `skills/<name>/evals/runtime-manifest.json`, read and checked; a task whose skill has none does not run. The skills of the packs in use (`PACKS_IN_USE`: `packs/business.txt`, `packs/brand.txt`, `packs/planning.txt` and `packs/code.txt`) have one |
| `runtime/proof.py` | The proof of a skill and the choice of a model by it: a copy of what the status script computes, kept in `<data_dir>/proof.json` and rebuilt when its inputs change; a run goes to the floor model only where the skill is `reliable` there, the measurement files are the recorded ones, the eval image is the evidence's and a key for the floor model is found: the runtime's own (`WB_RUNTIME_FLOOR_KEY`, store username `runtime-floor`), which wins when stored, else the lab's (the variables `floor_pass_env` of the gate file names); otherwise to the reference model. The routing names the key by its source (`runtime` or `lab`), never by its value |
| `runtime/router.py` | The router step: what code reads of one run of the router skill asked only for the route (the route line, or the question lines); anything else is unclassified and reaches the person whole |
| `runtime/plan.py` | The plan of a request (L19): the tasks code builds from a flow file or a route, the skills in scope, the hash the person approves, an estimate; several deliveries of one request, a brief routed again, the sub-tasks a backlog proposes |
| `runtime/board.py` | The mirror of tasks with the project's task board (`integration:issue-tracker`): only code talks to the board |
| `runtime/documents.py` | The mirror of documents with the project's documents platform (`integration:documents`): the documents a runtime manifest lists; a page that changed is never written over, and an edit is imported only on the rules of the module |
| `runtime/drop.py` | The file drop: a file the person hands to one task, in `.workbench-local/drop/<task id>/`, enters that task's runs only |
| `runtime/deps.py` | A project's dependencies, installed by code in the eval image with no model, cached, and copied into the run copies that need them |
| `runtime/changeset.py` | The change set of a code task (L9, L11): what a run did to versioned files, taken by git in the run's container and checked by the host |
| `runtime/effects.py` | A skill with a confirmation gate runs up to it (L16); the payload it showed is recovered, and code executes the effect through the code provider once the person approves its hash (L15, L17) |
| `runtime/autonomy.py` | The five autonomy modes of an area agent, what each releases, the daily caps, and whether a standing approval covers an effect |
| `runtime/progress.py` | Progress and the summary of a period, computed from the store's records |
| `runtime/dispatcher.py` | The dispatcher's decision (`decide`, pure) and the scheduler's entry for the two jobs ("The dispatcher's two jobs" below) |
| `runtime/chat.py` | The conversation with the planning agent in the terminal, one more shell of `ops.py` |
| `runtime/handlers/` | The handlers a round of the dispatcher ticks; the first is `published_posts.py` |
| `runtime/tests/` | The tests of the above, offline, with a stand-in adapter and invented skills; `corpus/` holds the classifier's corpus of archived lab runs |
| `flows/*.json` | The flow files: `market-positioning.json` (a market analysis, then the customer profile and positioning), `brand.json` (the brand flow) and `code-change.json` (the code-change flow) |
| `providers/store/sqlite.py` | The store (class `store:runtime`): migration 2 holds the task runtime's three tables, migration 3 adds `task_runs.redactions`, migration 4 a task's item on the task board, the document records and the saved platform comments, migration 5 the approvals table, and migration 6 the conversation's messages; its functions are the contract, one transaction each |
| `providers/documents/` | The documents provider (`integration:documents`): `notion.py`, with its pure converter `notion_blocks.py`, and the stand-in `local.py` |

The configuration of a project names three absolute paths: `workbench` (the checkout the runtime runs from, a reviewed revision), `data_dir` (a folder outside every repository, for run folders and the run lock) and `store_db`. Every operation refuses a project whose configuration names another checkout than the one it runs from, and a configuration whose hash is not the one the person accepted last (`accept-config --sha256 <hash>`, kept in the store).

## A task run

`run-next` takes the oldest `ready` task of the project, one task at a time per project (a lock in `data_dir`), and runs its skill once:

- **What enters the copy** (`runtime/workcopy.py`, limits L1 to L6): for a skill that requires the web, only the artifacts it declares (its `inputs`, `outputs` and `updates`) found under `docs/` and `.workbench-local/`; for any other skill, the files the project's git tracks, the documents and the state file under `docs/`, and the machine files the skill declares. Never the runtime's configuration, the store or the runtime's data folder, a link or a file whose real path leaves the project, a path with a part that carries a tool's settings, work data the skill does not declare, a credential file by its name, a file too large to scan, or a file whose text looks like it holds a credential. The project's `AGENTS.md` enters only when the skill declares it, without the two lines of the workbench section the container cannot serve (recording a use and the skill check); when a glob of `protected_paths` covers it and the skill is not of a code area, only its workbench section enters. Every file left out is listed in `left_out` with its reason.
- **The text:** the request in the person's words, then "For this task:" and the task's text from the flow file; on a run made after an answer, every earlier reply of the task with the person's answer, oldest first, each answer stated as the person's decision. Right before the answers, one line per document the documents mirror imported from the platform since the task's last run, when the skill lists it among its inputs and the project's file is still what was imported: "The person edited <path> on the platform since the last run; its content is theirs." Only code writes that line, from the record of imports, never from a run's text, and a run is given it once. The text names no skill: the one skill staged for the run loads by its description, as in a lab run.
- **How the skill is staged:** as in a lab run (`scripts/stage_skills.py`): the skill's folder, without its `evals/` and `scripts/tests/`, with the shared references it cites, where the adapter's tool discovers skills. Only that skill is staged. A skill that cites the platforms' folder (`shared/references/platforms/`) is also given the reference of every platform, with its data file, as a lab case is given the platforms it names: the runtime does not know in advance which platform a run will be told. They are read-only inputs: like the skill, they never come back (the path rule's `staged`).
- **Where it runs:** in the eval container of `evals/executor.py`, on the image the lab evidence is bound to, through the adapter's `run-prompt.sh`, on the model the skill's proof gives (`runtime/proof.py`): the floor model of the gate file only where the skill is `reliable` there, the proof holds on this checkout and machine and a key for it is found; the reference model otherwise, or when the person asks for it (`run-next --tier strong`). A copy that carries a tool's settings is refused before any model call.
- **The network:** a skill that requires `search:web` runs on the open network and may search and fetch pages; any other run reaches only the model provider, through the egress proxy.
- **The credential:** never enters the container. The model's credential is read from the secret store on the machine and held by a key proxy outside the run container, which adds it to each call. Every value passed to a run is replaced by its marker in everything the run leaves, before anything is read or stored.
- **Limits of time:** the gate file's `timeout_seconds` (1,800) per attempt, and its retries for a timeout, a failure of the adapter, a refusal or an early end. A refused credential is never retried. On the account limit the run pauses and starts again afterwards, without counting as a failure.
- **What comes back:** each file the run created or changed is given one class by the path rule. `document` (Markdown under `docs/`), `machine` (any other file under `docs/`, and `.workbench-local/`) and `state` come back; `state` through the merge of `runtime/state_merge.py`, line by line on top of what the project has now (L10), so a state file that changed at the origin during the run is merged, not kept whole. A document bound to an approval, and a machine file a skill's runtime manifest names, come back as `machine` (`runtime/workcopy.py`, `returning`). Only a regular file with its real path inside the copy comes back, a file that changed in the project while the run was in progress is never overwritten, and a file whose text looks like it holds a credential, or that is too large to scan, stays in the run folder. The reply the person reads in a pending decision has every line that looks like it holds a credential replaced by a marker (`body_masked` in the payload counts them); the run folder's `response.md` is left as it is. What does not come back is listed in `kept` with its class and reason. Nothing in the project is deleted. A versioned file comes back only from a code task (a skill of a code area), as a change set made against a commit, and such a run is refused while the project's tracked files other than the state file carry uncommitted changes; any other task is not held to that, and a versioned file outside `docs/` it changed is listed in `kept`.
- **Where it is kept:** the run folder `<data_dir>/task-runs/<run id>/`: `prompt.md`, `cwd/` (the copy as the run left it) and `outputs/` (`response.md`, `timing.json`, `raw.json`, `stderr.log`, `stream.jsonl`); an attempt made again is set aside beside them. The run's row in the store records the rest.

## Records

**Three tables** of migration 2 of the store: `tasks` (a request, with no parent and no skill, and the tasks of its plan), `task_runs` (one row per run: skill, version and content hash, model and adapter, web, status, failure kind, ending, attempts, cost, tokens, duration, whether the skill was reported loaded, image digest, run folder, error) and `pending_decisions` (what a task waits for the person to decide: kind, title, the reply as the body, a payload, status, resolution and answer).

**Nine task states:** `requested`, `planned`, `ready`, `running`, `waiting`, `blocked`, `done`, `failed`, `cancelled`. A `waiting` task always has exactly one open pending decision; one task is `running` at a time per database.

**Six endings** of a run that did not fail: `done`, `question`, `draft_with_questions`, `gate`, `blocked`, `unclassified`. Every ending is recognised by a rule that reads only the run's facts, what the skill declares (its frontmatter and runtime manifest) and sentences of the skills' own text; what no rule recognises is `unclassified` and reaches the person whole. The rules are tested against a corpus of archived lab runs, with labels a person read (`runtime/tests/corpus/`). `blocked` (the reply names a missing input and the skill that writes it) opens nothing: the task is `blocked` until the person retries it. `gate` (the run wrote the file the manifest names for its confirmation gate and asks) opens an `effect` when its payload was recovered and parsed, agrees with the configuration and its change set is not blocked; otherwise a `review` whose body starts with the reason (`runtime/ops.py`, `_effect_or_review`). A run that changed no file, asks nothing and finds the task's declared output already in the project is `done`. A run that failed has a failure kind instead: `timeout`, `refused`, `auth`, `adapter`, `early_end`, `settings`, `stopped` or `internal`.

**Six kinds of pending decision:** `plan` (stage 3), `question`, `review`, `effect` (stage 4), `acceptance` (stages 3 and 6) and `your_document` (stage 10). The store accepts all six; the runtime opens five today, and `your_document` is not opened yet:

| Kind | Opened when | Resolutions |
|---|---|---|
| `plan` | The router's run on a request gave a route, or the person named a flow (`route --flow`): code built the plan, with its hash | `approve --sha256 <hash>`: the plan's tasks are created and those with no dependency are `ready`; `reject`: the request is cancelled |
| `question` | A run ended `question`: it wrote nothing (a change limited to the state file counts as nothing) and asks | `answered`: the task is `ready`, and its next run gets the answer |
| `review` | A run ended `done`, `draft_with_questions` or `unclassified`, or ended `gate` without a payload that makes an `effect`: the body is the whole reply, so a draft's open questions are in it | `released`: the task is `done`, the tasks that depended on it become `ready`, and the document stays a draft with its open questions; `answered`: the task is `ready` again, and its next run gets the person's text |
| `effect` | A run ended `gate` and its payload was recovered, parsed, agrees with the configuration and its change set is not blocked; its hash is that of the effect document | `approve --sha256 <hash>`: the approval is recorded (L17), code checks that nothing moved and executes the effect (L15), and the task is `done`; `answered`: the task runs again with the answer; `rejected`: the task is cancelled and nothing is sent. Answering or rejecting revokes the approval in the same transaction |
| `acceptance` | An item a person wrote on the task board became a request; a backlog proposed sub-tasks outside the approved plan's limits (`subtasks`); a delivery was routed again after its brief, or a request an autonomy mode completed waits for the person's acceptance of its deliveries (`deliveries`) | `accepted` or `rejected`: a board request accepted is routed next, rejected is cancelled; accepted sub-tasks are added to the request; for deliveries the resolution and its note are recorded |

## The limits

The twenty limits that live in code (section B.2 of the platform plan). Each gets a test named after it in the stage that builds it; stage 1 built a first form of four of them.

| # | Limit | Built by | Test |
|---|---|---|---|
| L1 | Every run starts from a new copy, with the skills installed again from the fixed checkout | stage 2 | `runtime/tests/test_run_limits.py`, `test_limit_01_every_run_starts_from_a_new_copy_with_the_skill_staged_again`; and `test_the_platform_references_a_skill_cites_are_staged_with_it_read_only_as_in_a_lab_run` |
| L2 | What enters: versioned files, the project's documents, the machine files the skills use, and what the person handed over through the file drop. No other file outside git. The store and the runtime's configuration never | stage 2 (the file drop: stage 3) | `runtime/tests/test_run_limits.py`, `test_limit_02_only_versioned_files_documents_and_declared_machine_files_enter_and_never_the_store_or_the_configuration` |
| L3 | A task with the web receives only the artifacts its skill declares | stage 2 (strict form: no allowance for web and code together) | `runtime/tests/test_run_limits.py`, `test_limit_03_a_run_with_the_web_receives_only_the_artifacts_its_skill_declares` |
| L4 | A tool's configuration files are removed at any depth | stage 2 | `runtime/tests/test_run_limits.py`, `test_limit_04_a_tools_configuration_files_are_removed_at_any_depth` |
| L5 | The project's `AGENTS.md` enters when the skill declares it | stage 2 | `runtime/tests/test_run_limits.py`, `test_limit_05_agents_md_enters_only_when_the_skill_declares_it_and_without_the_two_lines_the_container_cannot_serve` |
| L6 | No credential enters the container | stage 2 (first form in stage 1) | `runtime/tests/test_run_limits.py`, `test_limit_06_no_credential_enters_the_container`; and `runtime/tests/test_lab_facade.py`, `test_the_value_of_a_passed_variable_is_replaced_in_everything_a_run_leaves` |
| L7 | The destination of each returned file comes from the path rule | stage 2 (first form in stage 1) | `runtime/tests/test_run_limits.py`, `test_limit_07_the_destination_of_each_returned_file_comes_from_the_path_rule`; and `runtime/tests/test_return_rules.py`, `test_every_path_gets_exactly_one_class` |
| L8 | Only a regular file, with its real path inside the copy, comes back | stage 2 (first form in stage 1) | `runtime/tests/test_run_limits.py`, `test_limit_08_only_a_regular_file_with_its_real_path_inside_the_copy_comes_back` |
| L9 | Code comes back as a change set; the commit is one, made by the code provider with the person's own git and signature | stage 4 | `runtime/tests/test_changeset.py`, `test_limit_09_code_comes_back_as_a_change_set_with_created_changed_and_removed_paths_and_the_executable_bit`; the one commit: `runtime/tests/test_effects.py`, `test_the_commit_is_one_made_by_the_code_provider_and_no_module_of_the_runtime_pushes` |
| L10 | The state file comes back through a merge made by one module | stage 2 | `runtime/tests/test_run_limits.py`, `test_limit_10_the_state_file_comes_back_through_the_merge_and_only_code_writes_what_is_the_persons`; the merge's rules in `runtime/tests/test_state_merge.py` |
| L11 | A working document never enters a commit | stage 4 | `runtime/tests/test_changeset.py`, `test_limit_11_a_working_document_never_enters_a_commit` |
| L12 | What comes back never overwrites what changed at the origin | stage 2 (first form in stage 1) | `runtime/tests/test_run_limits.py`, `test_limit_12_what_comes_back_never_overwrites_what_changed_at_the_origin`; and `runtime/tests/test_task_ops.py`, `test_a_file_that_changed_in_the_project_during_the_run_is_never_overwritten` (the state file is merged line by line instead: L10) |
| L13 | A record only grows | stage 4 (approvals) | `providers/store/tests/test_sqlite_approvals.py`, `test_limit_13_an_approval_is_never_deleted_and_its_status_only_moves_forward` |
| L14 | Everything passes the credential scan before it leaves | stage 2 | `runtime/tests/test_run_limits.py`, `test_limit_14_everything_passes_the_credential_scan_before_it_leaves`; the number of values the lab replaced is kept on the run's row (`task_runs.redactions`) |
| L15 | An external effect is executed by code, with the exact content approved or inside an approved policy | stage 4 (the exact content; a policy: stage 6) | `runtime/tests/test_effects.py`, `test_limit_15_the_effect_is_executed_by_code_with_exactly_the_approved_content` |
| L16 | A skill with a confirmation gate runs up to the gate; what it shows there is what the person approves | stage 4 | `runtime/tests/test_effects.py`, `test_limit_16_a_skill_with_a_gate_runs_up_to_the_gate_and_what_it_showed_is_what_the_person_approves`; the recovery of what it showed in `runtime/tests/test_gate_payload.py` |
| L17 | The approval lives in the approvals table; the rows in the state file are generated copies | stage 4 | `runtime/tests/test_effects.py`, `test_limit_17_the_approval_lives_in_the_table_and_the_state_file_row_is_a_generated_copy` |
| L18 | A document bound to an approval by hash is a machine file | stage 6 | stage 6 |
| L19 | The planning agent creates no task: it returns the route, and code builds the plan | stage 3 | stage 3 |
| L20 | The measurement files are not changed | stage 4 (for the change set: the project lists them in its protected_paths) | `runtime/tests/test_protected_paths.py`, `test_a_change_to_a_protected_path_blocks_the_change_set_and_names_the_path` and `test_a_created_or_removed_protected_path_blocks_it_too` |

## The dispatcher's two jobs

From stage 6 the task runtime runs unattended through two recurring jobs of the scheduler (`scheduler:job`, `--every 5`), both started with the system interpreter, `/usr/bin/python3`, on a copy of `runtime/dispatcher.py` kept in the job folder:

- **The poller** (`dispatcher.py poll`, `timeout_minutes` 5) calls `ops.poll`: it mirrors the task board and the documents when the project has them, expires the standing approvals past their expiry, rewrites the state file's generated lines (the `Checkpoints` line, the standing rows) when they changed, and releases the reviews each area agent's mode releases. It calls no model and starts no task.
- **The worker** (`dispatcher.py work`, `timeout_minutes` 240, the provider's maximum) calls `ops.dispatch`: the ticks of the handlers whose `dispatch` is true, the releases a mode makes, then the ready tasks one at a time, while the task's agent may start (its mode, its runs per day on the reference model, its dollars per day on the floor model). No new run starts once the round's budget (2700 seconds) is spent, or after a failure the next run would repeat. A firing that finds the last one still running is skipped by the scheduler (`skipped-overlap`).

`python3 runtime/cli.py pin --project <dir>` writes the pin, `<data_dir>/dispatch-pin.json` (mode 0600): the path and the sha256 of the accepted `docs/workbench/runtime.json`. `dispatcher.py command-file --job poll|work --project <dir> --pin <pin>` prints each job's command file: `argv` starts with the literal `/usr/bin/python3`, and the snapshot is the entry and the pin.

**What the approval of the two jobs covers.** The scheduler's digest covers the entry's copy, the pin and the arguments. The pin covers `runtime.json`: before it loads anything from the checkout, every firing hashes `runtime.json` and refuses (exit 3, nothing runs) when it is not the pinned file. Neither covers the rest of the checkout (the operations layer, the lab facade, the skills, the providers, the handlers): it stays on a revision the person reviewed. A change to `runtime.json` (a mode, a cap, a handler) stops both jobs until the person accepts it (`accept-config`), runs `pin` and schedules both jobs again with the new command files: that is the new approval. Whether the checkout's revision should also be in the pin is a question for the maintainer (open point O11 of the platform plan).

**The interpreter and the credentials** (open point O1 of the platform plan). The system interpreter has no secret-store library, so from a scheduled job the lab's lookup finds a credential only when it is set in the job's environment, which a command file cannot carry. Three answers:

1. Install the library for the system interpreter, in the user's own site folder (`/usr/bin/python3 -m pip install --user keyring==<the version the lab pins>`); a user agent runs in the login session and reads the login keychain. The job's command and its approval do not change. **Recommended**, if that version supports Python 3.9.
2. Start the jobs through `uv run --with keyring==<version>` instead of `/usr/bin/python3`: the scheduler then hashes a managed interpreter, and an upgrade of it refuses the jobs. It changes the entry's command file.
3. Put the credential in the job's environment: refused, a credential is never written into a file.

`dispatcher.py check --project <dir>` reports `"secret_store"` (whether this interpreter can import the library) and `"credential"` (whether the reference model's credential is set or found in the store), and exits 0 only when both, every module of `runtime/` and `runtime/handlers/`, the lab, docker and uv are found. Run it as the rehearsal's one-shot job, so the answer comes from the scheduler rather than a terminal. At every firing of the worker whose interpreter cannot read the store, the entry says so on standard error, and a round whose next run would go to the reference model without its credential starts nothing and says why in `"stopped"`, so no task fails for it.

## What the proof covers

The battery measured one skill, in one run, with an input in the form of its cases. That holds for the runtime because the container and the entry are the same. What the runtime adds was not measured: resuming a task with the person's answers in the request, and running a skill on a document another model wrote. For those the only check is field evidence, recorded from the first task. The runtime uses a band only after checking that the measurement files of its checkout are the recorded ones and that the image is the evidence's; when either fails, the skill runs on the reference model and without autonomy. A skill runs in the condition it was measured in.
