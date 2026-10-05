# The task runtime

Code that turns a request into tasks and runs each task as one skill, once, in the container the skill was
proven in (`evals/executor.py`), on a fresh copy that holds only what the skill declares. What a run leaves
comes back to the project by one rule of paths, and the task then waits for the person. The design is the
platform plan, `docs/architecture/platform-plan-2026-10-05.md`; this folder is its stage 1, an end-to-end
skeleton, and is not hardened yet: stage 2 of that plan adds the limits, each with its test.

It is a second runtime only in its code. The first one, `scripts/runtime.py`, runs one agent on social
comments and stays as it is until that agent moves to the container (stage 7). Both keep their state in the
same store (`providers/store/sqlite.py`): the tables of this one are migration 2 of that file.

## Modules

| File | What it owns |
|------|--------------|
| `lab.py` | The lab facade: the one file here that talks to `evals/eval_run.py`. Runs one skill once in the container; the pause on the account limit, the refusals, the early end and the stopping are the lab's own functions |
| `ops.py` | The operations layer: every operation a shell can perform, once (request, run the next task, answer, release, retry, cancel, status) |
| `cli.py` | The terminal shell: one command per operation, nothing else |
| `flow_files.py` | Reads and checks a flow file, `flows/<name>.json`: the tasks of a flow and their written dependencies |
| `skill_meta.py` | What a skill declares in its frontmatter, read for the runtime |
| `path_rule.py` | The path rule: the class of one path a run left (state, machine, document, versioned, ignored, other) |
| `state_merge.py` | The one module that decides what a run may change in `docs/workbench/state.md` |
| `endings.py` | The classifier of endings: how a completed run ended, from a closed list; it never guesses |
| `project_config.py` | The project's configuration, `<project>/docs/workbench/runtime.json`, and its hash |

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

```sh
python3 runtime/cli.py request  --project <dir> --flow market-positioning --text "<what you want>"
uv run --with keyring==25.7.0 python3 runtime/cli.py run-next --project <dir>   # needs docker and the credential
python3 runtime/cli.py pending  --project <dir>
python3 runtime/cli.py answer   --project <dir> --id <n> --text "<your answer>"
python3 runtime/cli.py release  --project <dir> --id <n>
python3 runtime/cli.py status   --project <dir>
```

`run-next` calls a model: it runs the skill on the reference model of the gate file, in the eval container. It
writes no lab evidence and edits no file of the measurement.

## Tests

`uv run --with pytest==9.1.1 pytest runtime/tests`: offline. A stand-in adapter (a shell script) and two
invented skills replace the container and the model (`runtime/tests/standin_tree.py`); the parity test gives
the same adapter output to the lab's runner and to `lab.py` and expects the same classification.
