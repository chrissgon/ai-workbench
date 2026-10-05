# ai-workbench

Harness-agnostic skills, agents and workflows that let an AI build a digital solution end to end: business, product, brand, design, engineering, delivery, marketing, and AI inside the product. A skill reads and writes artifacts in the target project's `docs/` folder, so later phases, other skills and other people find what earlier ones produced.

The skills, their areas and how each one stands under the reliability model are listed in [docs/inventory.md](docs/inventory.md); the areas and how they chain are in [docs/area-map.md](docs/area-map.md). The rules every file follows are in [AGENTS.md](AGENTS.md).

## Principles

The eight principles of [AGENTS.md](AGENTS.md), in one line each:

1. **Harness-agnostic core.** Skills, agents, shared files, contracts, templates and providers name no AI tool, its folders or its tool names.
2. **Open-closed adapters.** Everything specific to one AI tool lives in `adapters/<harness>/`; adding a harness never edits the core.
3. **Write for the weakest model you will run.** One default path, a template for every output, criteria for every judgment, scripts for anything deterministic, and every fact traced to a source.
4. **Artifacts over invocation.** A capability never invokes another skill; it reads and writes artifacts. Only flows invoke skills, and `core-orchestrator` routes a request without doing the routed skill's work.
5. **Never assume; ask.** A decision that belongs to the user and is not recorded is asked, with a recommended answer.
6. **English only.** Every file in this repository is written in English.
7. **Parallel by default.** Independent work (eval runs, checks, research, agents with separate scopes) runs at the same time; work runs in sequence only when one step needs another's result, a shared resource cannot be used concurrently, or a rate limit forces it.
8. **Shared core, projects outside.** The repository holds only the workbench: nothing that identifies a project that uses it, and none of its work data. Examples and fixtures use fictional names and `.example` hosts.

## Layout

```
skills/<name>/      one folder per skill, flat; the prefix is the area (biz, product, brand, design, eng, ops, mkt, ai, core, asst, flow)
agents/             four harness-neutral agents for delegated work: implementer, researcher, reviewer, social-manager
shared/references/  security.md, the one cross-cutting reference, and platforms/: one reference and one data file per social platform
shared/scripts/     the one source of every script more than one skill carries; scripts/sync_copies.py writes the copies
contracts/          what skills read and write in a target project: project-layout.md, state.md, environment.md, runtime.md, secrets.md, vote-data.md
providers/          native implementations of requirement classes, resolved by providers/resolve.py: reader:email, publisher:<platform>,
                    scheduler:job, store:runtime, integration:vcs; the interface is providers/CONTRACT.md
templates/          capability.SKILL.md, flow.SKILL.md and agent.md, used by scripts/new-skill.sh
packs/              installation subsets: default (every area but the optional ones), all, assistant
adapters/           one folder per AI tool: claude-code and agents-dir install the skills; api runs the agent runtime with one model call and no tools
evals/              the eval harness: eval_run.py (the runner), executor.py and container/ (every run executes in a container),
                    eval_status.py (status, hashes, the inventory table), eval-gate.json (models, grader, gate, measurement version), tests/
scripts/            repository tooling: validate.py, security_scan.py, sync_copies.py, owner_table.py, new-skill.sh, install-hooks.sh,
                    select_skills.py, doctor.py, and the agent runtime (runtime.py, runtime_vote.py, vote_job.py)
runtime/            the task runtime: a request becomes tasks, each task runs one skill in the eval container, a person decides
                    through pending decisions; lab.py is the one file that imports the eval runner, ops.py the operations, cli.py the shell
flows/              one data file per flow: the tasks and their written dependencies, read by the task runtime
.githooks/          the versioned pre-commit hook
docs/               area map, decisions, inventory, backlog, architecture notes and plans
```

## Install

Each adapter documents its own install in its `README.md`. Without `--pack`, the `default` pack installs every area except the optional ones (`packs/README.md`).

- **Claude Code**: `bash adapters/claude-code/install.sh [--pack <name>]` builds a plugin and links it where Claude Code loads it.
- **Codex, Cursor, Cline, OpenCode, OpenClaw and any tool that reads `~/.agents/skills/`**: `bash adapters/agents-dir/install.sh [--pack <name>] [--project <dir>]`.

Both installers put `shared/references/` beside the skills and take `--uninstall`. The `api` adapter installs nothing: it is the tool-free way for the agent runtime (`contracts/runtime.md`) to call a model.

Which requirement classes the environment satisfies: `python3 scripts/doctor.py`.

## Checks

```bash
python3 scripts/validate.py                 # conventions: names, frontmatter, the artifact contract, eval cases, harness names in the core
python3 scripts/security_scan.py --strict   # secrets, hidden text, unsafe script patterns, undeclared side effects
bash scripts/install-hooks.sh               # once per clone: enables .githooks/ (--check, --uninstall)
```

The pre-commit hook runs `validate.py`, then `security_scan.py --strict`, then the tests of every folder the commit touches: `providers/<class>/`, `scripts/`, `evals/`, `shared/`, an adapter, or a skill's `scripts/` (its `scripts/tests/`). The tests need [uv](https://docs.astral.sh/uv/). CI runs the same checks in its `validate` and `tests` jobs, beside a `python39` job and a `container` job for the eval container.

A new skill starts from `bash scripts/new-skill.sh --name <prefix-name> --kind capability|flow --area <area>`; `AGENTS.md`, "Adding a skill", has the rest.

## How a skill is judged

Every skill is tested in the lab: its eval cases (`skills/<name>/evals/evals.json`) run in a container, with the skill and without it, and a grader judges each assertion. Under the reliability model ([docs/architecture/reliability-model-2026-10-02.md](docs/architecture/reliability-model-2026-10-02.md)), a skill is ranked by the evidence of the tests it has passed rather than by a single pass: a full test (`python3 evals/eval_run.py --skill <name>`) runs every case and evaluates the gate on the reference model named in `evals/eval-gate.json` (the mean with the skill at the threshold or above, and not below the baseline without the skill by more than the tolerance); a partial test (`--cases <ids>`) carries a small change; each run leaves an evidence line, and the skill's band (`reliable`, `watch` or `needs a test`) is computed from that evidence, never ticked. `python3 evals/eval_status.py status` prints each skill's band with its cause and the command that clears it. Check a skill's cases without calling a model with `python3 evals/eval_run.py --skill <name> --check-cases`.

## Status

What is built and how each skill stands: [docs/inventory.md](docs/inventory.md). What remains: [docs/backlog.md](docs/backlog.md) and the plan in [docs/architecture/final-plan-2026-10-02.md](docs/architecture/final-plan-2026-10-02.md).
