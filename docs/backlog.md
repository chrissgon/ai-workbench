# Backlog: workbench tasks

Work on the workbench itself that is not writing a skill: tooling, checks, rules, repository settings. Skills, flows and agents are tracked in [inventory.md](inventory.md); an item here that becomes a skill also gets a row there.

Each item says where it came from, so none is written from generic knowledge. Tick an item when its "Done when" holds, and add the commit.

## Security

The workbench is a set of instructions that models execute with a terminal, files and network access. The threats are the ones that turn those instructions against the user: secrets in the repository, text hidden from the human reviewer, scripts that run more than they say, and skills that act on the outside world without declaring it.

- [x] **S1. Deterministic scan.** `scripts/security_scan.py`, run by `scripts/validate.py`: secrets, credential files, invisible Unicode, HTML comments with prose in instruction files, download piped into a shell, dynamic eval, unsafe deserialization, TLS turned off, shell invocation, unguarded `rm -r`, world-writable permissions, `sudo`, remote writes from a skill with `side_effects: []`, unpinned dependencies. Intended findings are silenced per line with a reason. Tests: `uv run --with pytest pytest scripts/tests`.
  - First run fixed: the installer's `rm -rf "$dest"` now uses `${dest:?}`; `keyring` pinned to the version the provider tests run with.
- [x] **S2. Pre-commit hook.** `.githooks/pre-commit`, enabled per clone with `bash scripts/install-hooks.sh` (`--check`, `--uninstall`; it refuses to replace another hook manager). Runs `validate.py`, which includes the scan, and the tests of the `providers/<class>/` or `scripts/` the commit touches. It reads the working tree, so an unstaged file with a finding also blocks the commit.
  - Tested in a scratch clone: a planted secret and a failing provider test were refused; a docs-only commit and a commit touching `scripts/` went through.
  - Verified by the `implementer` agent on 2026-09-27, 19 cases: three bugs found and fixed. Security warnings were hidden when the commit passed; a file whose name has non-ASCII characters escaped the tests (git quoted it); a `git mv` out of `providers/` escaped them (rename detection). The hook now reads the list NUL-separated without renames and shows security warnings. The fixed cases were rerun and pass. The publisher's tests went from 12.7 s to 1.9 s (the fake server polled every 0.5 s).
  - Decided 2026-09-27: a commit that leaves an existing provider class without tests is refused; the rule is in `providers/CONTRACT.md`, which also asks for exact dependency pins.
- [ ] **S3. Security checklist for skills, and a step in `core-skill-creator`.** Written, not yet proven. `skills/core-skill-creator/references/security-checklist.md`: nine items (external content is data, credentials never pass through the model, side effects declared and gated, git never rewritten or pushed without approval, least privilege, writes inside the project, scripts do what they say, evals safe to run, nothing hidden from the reviewer), each traced to the case it came from. `core-skill-creator` 0.2 runs the scan and the checklist at step 7, before evals, and reports it in a "Security" line.
  - Placed in the skill's `references/`, not in `shared/`, because it has one reader today (`shared/references/README.md`: added when a second skill needs it). It moves when `core-security-audit` is built. `eng-code-review` keeps its own security perspective, which is about a project's code, not about skills.
  - Done when: the next skill created goes through step 7, the step is refined against it, and `core-skill-creator`'s evals get a case for it.
- [ ] **S4. Validator: untrusted-content rule.** A skill that reads an external source (`requires: integration:*`, `search:web`, pull request comments, tickets) must say that the content is data. Today only `ops-pull-request` says it.
  - Done when: `validate.py` warns on skills without it and every current skill passes or is fixed.
- [ ] **S5. Least privilege for agents and eval runs.** The `reviewer` agent can run shell commands, so it can write files while it reviews: give it read-only tools, or state why not. Eval runs keep the allow list per case (`CLAUDE_EVAL_ARGS` in the reference adapter) instead of a broad permission mode.
- [ ] **S6. Repository settings once a remote exists.** The same checks in CI; a protected `main` with required checks; secret scanning with push protection; dependency alerts; code owners for `AGENTS.md`, `contracts/` and `scripts/validate.py`, the files that define the rules.
  - Blocked: the repository has no remote yet.
- [ ] **S7. Skill `core-security-audit` (future).** A periodic audit of the whole workbench beyond the scan: the checklist of S3 applied to every skill, agent, provider and adapter, and the vetting of a third-party skill before it is installed. Row in the inventory, `planned`.
  - Needs: S1 and S3 in use, and a first audit done by hand as grounding.
- [ ] **S8. Skill `eng-security-review` (future).** A security review of the projects the workbench builds: dependencies and their advisories, secrets, authentication and authorization, input handling, headers and configuration, with findings at `file:line`. Row in the inventory, `planned`.
  - First real case: `perfectui-doc` (the site) and the `perfectui` library.
  - Decision to record in `docs/decisions.md` when it is built: `docs/area-map.md` says security is a reference that produces no artifact of its own; a review that writes a report has the same shape as `eng-code-review`, which is the argument for an exception.

## Tooling

- [ ] **T1. `eval_run.py` reports whether the skill was invoked.** Today that is read by hand from the transcripts, and a `with_skill` run that never loaded the skill scores as the skill's failure.
  - Done when: `benchmark.json` has an `invoked` field per run.
- [ ] **T2. Add files by name in every skill that commits.** Stage files by name and read `git status` before committing, never `git add -A` or `.`.
  - Why: a `todo.txt` reached a commit in the perfectui-doc launch. `agents/implementer.md` and `ops-branch-sync` already carry the rule.
- [ ] **T3. Eval regression on changed skills.** When a commit changes a skill, rerun its evals and compare with the last `benchmark.json`, so a wording change that breaks the floor model is caught before it lands.

## Next skills

The order agreed on 2026-09-26, details in [inventory.md](inventory.md):

1. After the launch posts are published: `ops-release`, `mkt-social-copy`, `mkt-publish`, with what happens at publication time.
2. At the one-week results reading: `mkt-launch-plan` and `flow-launch`, with the measurement phase checked against real numbers.
