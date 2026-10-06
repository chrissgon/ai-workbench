# The task runtime

Code that turns a request into tasks and runs each task as one skill, once, in the container the skill was
proven in (`evals/executor.py`), on a fresh copy that holds only what may enter it (`workcopy.py`). What a run leaves
comes back to the project by one rule of paths, and the task then waits for the person. The design is the
platform plan, `docs/architecture/platform-plan-2026-10-05.md`; this folder is its stage 1, an end-to-end
skeleton, and is not hardened yet: stage 2 of that plan adds the limits, each with its test.

It is a second runtime only in its code. The first one, `scripts/runtime.py`, runs one agent on social
comments and stays as it is until that agent moves to the container (stage 7). Both keep their state in the
same store (`providers/store/sqlite.py`): the tables of this one are migrations 2 to 4 of that file.

## Modules

| File | What it owns |
|------|--------------|
| `lab.py` | The lab facade: the one file here that talks to `evals/eval_run.py`. Runs one skill once in the container; the attempts of a run (the pause on the account limit, the refusals, the early end, the retries) are made by the lab's one function, `evals/run_attempts.py`, reached through the runner, and the stopping is the lab's own: the runtime has no loop of its own |
| `ops.py` | The operations layer: every operation a shell can perform, once (request, run the next task, answer, release, retry, cancel, status) |
| `cli.py` | The terminal shell: one command per operation, nothing else |
| `flow_files.py` | Reads and checks a flow file, `flows/<name>.json`: the tasks of a flow and their written dependencies |
| `skill_meta.py` | What a skill declares in its frontmatter, read for the runtime |
| `path_rule.py` | The path rule: the class of one path a run left (state, machine, document, versioned, ignored, other) |
| `state_merge.py` | The one module that decides what a run may change in `docs/workbench/state.md` (L10): a draft row of the skill that ran, a decision attributed to it, a new open question (in any list form, written as a checkbox); only code writes what is the person's, the answer to a question included |
| `endings.py` | The classifier of endings: how a completed run ended, from a closed list, each ending by a rule that reads the run's facts and the skill's (`manifest.ending_facts`); it never guesses, and is tested against a corpus of archived lab runs (`python3 runtime/endings.py --corpus runtime/tests/corpus/endings.jsonl` prints its counts) |
| `project_config.py` | The project's configuration, `<project>/docs/workbench/runtime.json`, and its hash |
| `workcopy.py` | What enters a run copy (limits L1 to L6) and what comes back from it (L7, L8, L12, L14: the path rule with the manifest's bound documents, regular files inside the copy only, never over a change at the origin, the credential scan, the masked reply): the versioned files, the documents and the declared machine files of a run without the web, only the declared artifacts of a run with it; never the store, the configuration, a tool's settings or a credential; the project's `AGENTS.md` without the two lines the container cannot serve |
| `manifest.py` | A skill's runtime manifest, `skills/<name>/evals/runtime-manifest.json`: what the runtime knows of a skill that its frontmatter does not declare. A skill of a pack in use (`PACKS_IN_USE`) without a well-formed one does not run |
| `router.py` | The router step: what code reads of one run of the router skill (`core-orchestrator`, as it is) asked only for the route: the one route line `Route: <name> (<capability or flow>, <ready or pending>)`, or the question lines `Q<n>: ...`; anything else is unclassified and reaches the person whole. Pure: no lab, no store |
| `plan.py` | The plan of a request (limit L19: the planning agent creates no task): the tasks code builds from a flow file or from a route to one skill, the skills in scope (the packs of the enabled area agents of the configuration, else the pack `default`), the hash the person approves, and an estimate that counts runs |
| `board.py` | The mirror of tasks with the project's task board (`task_board` in `runtime.json`, class `integration:issue-tracker`): only code talks to the board; a person's title, text and comments come in (an item is read only when its version, which covers its content, changed; its own comments are listed at every pull), three state moves are taken (ready on a failed or blocked task, cancelled on a request, done on a task waiting on a review) and any other is written back; an item a person wrote waits for acceptance; a task already final (`done` or `cancelled`) when the board is configured (its first `sync`) is never mirrored, and `sync` and `status` give how many (`left_out_final`); a provider other than `local` is written to only until the `expires` the accepted configuration gives (`python3 runtime/cli.py sync`) |
| `documents.py` | The mirror of documents with the project's documents platform (`documents` in `runtime.json`, class `integration:documents`): only the documents a skill's runtime manifest lists; a page is read only when its version, which covers its content, changed (its own comments are listed at every pull, since a comment may not move the version) and written only when the project's file changed, its open comments saved first; a person's edit replaces the whole project document only when the project's file is still what was last written and the skill's checker passes on a scratch copy, else nothing changes and the record is `rejected` with the reason, and no task that declares it runs until `sync --take page|project --path <rel>` settles it; an edit of a `read_only` type is kept aside in `<data_dir>/documents/not-taken/` and the page written again. Never merges two versions |
| `drop.py` | The file drop: a file the person hands to one task (`python3 runtime/cli.py hand-over --project <dir> --task <id> --file <path>`) is copied into `<project>/.workbench-local/drop/<task id>/`, enters that task's runs and no other, is listed in their prompt, and never comes back changed; refused for a link, a large file, a bad or repeated name, a task that ended or runs, a credential, a git project that does not ignore the folder, and (until the maintainer answers) a task whose skill uses the web |
| `deps.py` | A project's dependencies, installed by code (`python3 runtime/cli.py deps --project <dir>`): each set the configuration declares (`dependencies`, a recipe of the closed table `RECIPES`) is installed in the eval image, in a step with no model that sees only the dependency files, cached in `<data_dir>/deps/<key>/` by the files and the image, cleared of every tool's settings, copied into a run whose copy holds versioned files after its base commit, and removed from the copy before anything comes back; a failed install fails the run before any model call |
| `changeset.py` | The change set (limits L9, L11): what a run did to versioned files, taken by git in the run's container as the difference between the copy's base commit and its working tree (a scratch index, the copy's ignore rules), classified by the path rule and checked by the host (a regular file, a path and a size the code provider takes, no credential format, no tool's settings), stored in `<run folder>/changeset/` with every file's bytes and hash; a refused path blocks the whole set. A versioned file never comes back as a loose file; the next code task of a request starts from the newest unblocked change set; a run is refused while the project's tracked files have uncommitted changes |
| `effects.py` | A skill with a confirmation gate runs up to it (limit L16): its copy holds the request's change set as one commit on a branch over the configuration's `code.base`, its temporary folder comes back in its run folder (`lab.run_skill(..., tmp_in_run=True)`), and the payload it wrote there is recovered only when it is the file its reply hashed (`recover_payload`), parsed in the pull-request skill's form (`parse_pull_request_payload`) and kept as `<run folder>/payload.md`; nothing else of the temporary folder is kept but its names and sizes. When the payload parsed, agrees with the configuration (`code`: repository, base; the head is `<branch_prefix>request-<id>`) and the change set is not blocked, the task waits on an `effect` whose hash is that of `<run folder>/effect.json`; `approve --sha256 <hash>` records the approval (the store's approvals table, L17), checks that nothing moved (the files' hashes, the base on the remote, the protected paths accepted now), and code makes the one commit and opens the pull request through the code provider (`commit-files`, `open-pr`, each with its idempotency key; L15); the state file gets a generated row. The runtime passes the provider no credential and runs no git commit or push itself |
| `proof.py` | The proof of a skill (what the status script computes, cached in `<data_dir>/proof.json`) and the choice of the model a run goes to: the floor model only where the skill is `reliable` there and the proof holds on this checkout and machine; the reference model otherwise, or when the person asks for it (`run-next --tier strong`) |

Rules of the folder: `lab.py` is the only importer of anything under `evals/`; no shell reaches the store, the
facade or a project's files except through `ops.py`; every module runs on Python 3.9 with the standard library
only (the scheduler starts the dispatcher with the system interpreter from stage 6 on); and no file here
names an AI tool, although the validator does not check this folder: the model and its adapter come from the
gate file, `evals/eval-gate.json`.

## Trying it

A project is configured with three absolute paths in `<project>/docs/workbench/runtime.json`:

```json
{"workbench": "<this checkout>", "data_dir": "<a folder outside every repository>", "store_db": "<data folder>/tasks.sqlite"}
```

Every command refuses a configuration whose hash is not the one the person accepted last. Read the file, then
accept it with the hash the refusal shows (and again after every change of the file):

```sh
python3 runtime/cli.py accept-config --project <dir> --sha256 <hash>
python3 runtime/cli.py request  --project <dir> --flow market-positioning --text "<what you want>"
#   or, without --flow, the router plans it: a model call, like run-next; then approve the plan it opens
python3 runtime/cli.py request  --project <dir> --text "<what you want>"
uv run --with keyring==25.7.0 python3 runtime/cli.py route --project <dir> --request <id>   # or --flow <name>: no run
python3 runtime/cli.py approve  --project <dir> --id <n> --sha256 <the plan's hash>
uv run --with keyring==25.7.0 python3 runtime/cli.py run-next --project <dir>   # needs docker and the credential
python3 runtime/cli.py pending  --project <dir>
python3 runtime/cli.py answer   --project <dir> --id <n> --text "<your answer>"
python3 runtime/cli.py release  --project <dir> --id <n>
python3 runtime/cli.py status   --project <dir>
```

Every run records a use of its skill with the existing recorder (`scripts/evidence.py record --start`, with the
model and adapter of the gate file), in the project's `.workbench-local/evidence/`; a use that cannot be recorded
never stops a run. The verdict on what a run delivered is yours, once per run:
`python3 runtime/cli.py verdict --project <dir> --run <run id> --word worked|corrected|failed`.

A run goes to the floor model only with a key for it. The runtime's own key, `WB_RUNTIME_FLOOR_KEY` (registry
`runtime/secrets.json`, store username `runtime-floor`), wins when it is stored: store it when you want the
runtime's runs on a key of their own, with a spend cap set at the provider. Without it, a floor run uses the lab's
key for the floor model: the variables `floor_pass_env` of the gate file names, set or found in the secret store
the way the lab's runner finds them. Without either, every run goes to the reference model. The routing a run
returns names the key by its source, never by its value: `"key": "runtime"` or `"key": "lab"` on a floor run.
`proof --project <dir>` shows, without a model call, where each skill in use would run and why.

`run-next` calls a model: it runs the skill on the model its proof gives (`proof --project <dir>` shows it without
calling one), in the eval container. It
writes no lab evidence and edits no file of the measurement.

After a run the task waits on one pending decision, unless the skill stopped on a missing input that another
skill writes (ending `blocked`): then the task is `blocked`, and `retry` makes it ready once the input exists.
A run that wrote nothing (or changed only the state file) and asks (ending `question`) opens a `question`, which is answered. Every other ending opens a `review`, whose body is the whole reply: a
run that wrote a declared output and still asks (ending `draft_with_questions`) included. A review is released
as it stands (the task is done; the document keeps its open questions and stays a draft) or answered (the task
runs again with the answer). A skill whose runtime manifest sets `mandatory_milestone` is a milestone whatever the
flow file says (the plan shows `yes, mandatory`); the review of its delivery says that the next task accepts it only
with your approval written in the document, and carries `"mandatory_milestone": true`.

## Tests

`uv run --with pytest==9.1.1 pytest runtime/tests`: offline. A stand-in adapter (a shell script) and two
invented skills replace the container and the model (`runtime/tests/standin_tree.py`); the parity test gives
the same adapter output to the lab's runner and to `lab.py`, expects the same classification, and checks that
both reach one function and that `runtime/` keeps no loop of its own.
