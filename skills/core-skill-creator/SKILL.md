---
name: core-skill-creator
description: >
  Create a new skill for this workbench or improve an existing one, and prove it works: ground
  the content in real expertise, scaffold from the templates, write it for the weakest model
  without capping strong ones, validate the conventions, write realistic evals, run them with
  and without the skill on a strong and a floor model, review its security, grade, analyze, iterate. Use this skill
  when the user asks to add, rewrite, fix or evaluate a skill, when the orchestrator recorded a
  skill gap, or when a skill failed on a real task. It refuses to write a skill from generic
  knowledge when no real task or expertise exists, and says what is needed first.
license: MIT
metadata:
  area: core
  kind: capability
  inputs: []
  outputs: []
  requires: []
  side_effects: []
  version: "0.2"
---

# Skill creator

## Purpose

A skill is done when a floor model passes its evals and a strong model scores at least as well with it as without it, on cases refined against a real task. This skill runs that loop. It operates on the workbench repository itself: `skills/`, `docs/inventory.md`, the templates and the validator.

## When not to use

- Writing a project's instruction file: `core-agents-md`.
- A one-line fix to a skill's wording with no behavioural change: edit, run `python3 scripts/validate.py`, commit.
- Creating an adapter: follow "Adding an adapter" in the workbench `AGENTS.md`.

## Inputs

| Source | Required | If missing |
|--------|----------|------------|
| Real expertise: a conversation trace with corrections, a real artifact, a runbook, a recorded failure, or a real task to run the draft against | yes | Stop. Say that the skill would be generic knowledge, and ask for a real task or material. Do not write it. |
| `docs/inventory.md` entry for the skill (area, wave, sources) | no | Propose the entry (area by the boundary test, prefix, inputs and outputs) and ask before scaffolding. |
| An adapter with `run-prompt.sh` for the harness that will run the evals, and model ids for the strong and floor models | for step 9 | Write, validate and review the skill through step 8, then ask which harness and models to use. Never mark the skill done without the runs. |

## Procedure

Progress:
- [ ] Step 1: Ground. Collect the material listed under Inputs. Write, in a scratch note, the five to ten facts, procedures or corrections the skill must carry that a model would not know or would get wrong. If the note is empty, stop (see Inputs).
- [ ] Step 2: Place it. Confirm area and name against `docs/inventory.md` and the boundary test in `docs/area-map.md`; decide `capability` or `flow`; list `inputs`, `outputs`, `requires`, `side_effects` honestly. Ask the user when two areas fit.
- [ ] Step 3: Scaffold: `bash scripts/new-skill.sh --name <name> --kind <kind> --area <area>`. For an existing skill, skip.
- [ ] Step 4: Write `SKILL.md` from the template, then check it against the writing standard in the workbench `AGENTS.md`: one default path; every step executable without inference; a template for every output; criteria for every judgment; a stop-and-ask gate for every decision that is the user's; grounding rules; the contract constrained, not the content; under 500 lines with depth in `references/`. When you find yourself writing a rule from general knowledge, delete it or trace it to step 1's note. Read [references/authoring-guide.md](references/authoring-guide.md) §"Best Practices" and §"Patterns for Effective Instructions" when a section is hard to write.
- [ ] Step 5: Bundle scripts for anything deterministic the skill repeats (parsing, validation, measurement). Scripts take flags, never prompt, implement `--help`, print JSON to stdout.
- [ ] Step 6: `python3 scripts/validate.py` until zero errors. Warnings about inputs not produced by any skill are acceptable only while the producing skill does not exist yet; note them.
- [ ] Step 7: Security review. Read [references/security-checklist.md](references/security-checklist.md), run `python3 scripts/security_scan.py skills/<name>` (plus any agent, provider or script the change touches) until it reports zero findings, and answer every checklist item with `yes` or `n/a: <why>`. Fix every `no` before writing evals. Stop and ask the user when the skill needs a side effect, a credential or a permission the request did not mention.
- [ ] Step 8: Write `evals/evals.json`: at least two cases for a new skill, one per behaviour that matters (the happy path, the ambiguous request that must trigger a question, the degraded mode, the case the skill must refuse or hand off). Prompts read like the user writes, in their language, with realistic paths and context. Each assertion is checkable by reading the output or a produced file; no "the output is good". Add fixture files under `evals/files/` when a case needs them, and the commands the cases run under `allow_commands`. Read [references/authoring-guide.md](references/authoring-guide.md) §"Evaluation Framework" for assertion and prompt design.
- [ ] Step 9: Run. From the repository root:
  ```bash
  python3 skills/core-skill-creator/scripts/eval_run.py --skill <name> --harness <adapter> --model <strong-id> --floor-model <floor-id>
  ```
  This runs every case with and without the skill, on both models, grades each assertion with a model, and writes `evals-workspace/<name>/iteration-N/benchmark.json`. Use `--dry-run` first to see the plan; `--case <id>` to run one case.
- [ ] Step 10: Analyze `benchmark.json` and read the transcripts of every failure, not just the scores. Conditions: floor model `with_skill` pass rate at or above the threshold (default 0.8); strong model `with_skill` at or above `without_skill`. Classify each failure: the agent tried several approaches (instruction vague), followed an irrelevant instruction (too many options), reinvented logic (bundle a script), guessed instead of asking (add a gate), invented a fact (add grounding). Remove assertions that pass in both configurations for every model; investigate assertions that fail everywhere.
- [ ] Step 11: Iterate `SKILL.md` from the classification, rerun (a new `iteration-N/`), and stop when both conditions hold and the last iteration changed nothing meaningful, or after five iterations, in which case report what still fails and why. Keep the skill lean: fewer, sharper instructions beat exhaustive ones.
- [ ] Step 12: Record: tick the skill in `docs/inventory.md` "Progress", add a `docs/decisions.md` entry only if a structural rule changed, bump `metadata.version`, and summarize the iterations in the report. Commit only when the user asks.
- [ ] Step 13: Self-check against "Quality criteria".

## Output template

```markdown
## Skill <created | improved>: <name> (v<version>)

- Grounded in: <trace, artifact, task>
- Files: SKILL.md (<n> lines), references/<...>, scripts/<...>, evals/evals.json (<n> cases)
- Validator: clean | <warnings and why>
- Security: scan clean | <findings silenced and why>; checklist <n> yes, <n> n/a (<item: why>)
- Evals: iteration <N>, harness <adapter>, strong <model>, floor <model>
  | Variant | Model | Pass rate | Tokens | Time |
  |---------|-------|-----------|--------|------|
  | with_skill | strong | ... | ... | ... |
  | without_skill | strong | ... | ... | ... |
  | with_skill | floor | ... | ... | ... |
  | without_skill | floor | ... | ... | ... |
- Conditions: floor ≥ 0.8: <yes/no>; strong delta ≥ 0: <yes/no>
- What changed between iterations: <one line each>
- Still failing: <case and reason, or "nothing">
```

## Quality criteria

Approve only if all of the following hold:

- Every rule and gotcha in the skill traces to the grounding note from step 1 or to an eval failure; nothing is generic knowledge dressed as a rule.
- `python3 scripts/validate.py` reports zero errors.
- The security scan reports zero findings for the skill's folder, and every item of `references/security-checklist.md` is `yes` or `n/a` with a reason.
- At least two eval cases with checkable assertions, including one that exercises asking or degrading.
- A `benchmark.json` exists with both variants and both models for the current iteration.
- Floor `with_skill` pass rate is at or above the threshold and the strong delta is not negative; or the report states which condition fails and why.
- `SKILL.md` is under 500 lines and every reference is one level deep.

## Gotchas

- The first draft always needs refinement; a skill that has not been run against a real task is a hypothesis, and its `Status` in any report is `draft`.
- A `without_skill` run is only clean if the harness cannot see the skill. If the workbench is installed globally in that harness, the run is contaminated; check the transcript for the skill's name and use the adapter's isolation notes.
- The grader is a model. Read at least one grading per case yourself before trusting the numbers; graders give the benefit of the doubt unless told not to.
- Assertions that always pass in both configurations measure nothing and inflate the score. Remove them.
- Over-specification shows up as a negative strong-model delta. Loosen the procedure, keep the criteria.
- Eval prompts in polished English test a user who does not exist. Write them the way the real user writes, in their language, with their typos.
- A skill whose job is running commands (git, a package manager) scores zero on every variant when the harness runs non-interactively and blocks them: the first `ops-branch-sync` round only described its plan. Read `permission_denials` in the run's raw output before blaming the skill, and list the commands the cases need in `evals.json` `allow_commands` (top level, or per case): named commands and subcommands (`npm test`, `git status`, `gh pr view`), never a shell or an interpreter without a script path (`node`, `python3 -c`), bare `git` or `git -c`, `env`, `xargs`, `find`, `npx` or a wildcard, which `eval_run.py` refuses (`--help` lists the rules). The skill's own scripts are allowed by the adapter. Remotes stay local: model runs get an allowlisted environment and cannot reach a network remote, the GitHub CLI or an npm token; name any variable the harness needs with `--pass-env`.
- Do not tick a skill in the inventory because it validates. Validation checks conventions; evals check behaviour.
