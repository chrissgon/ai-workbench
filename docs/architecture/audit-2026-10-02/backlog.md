# Backlog audit, 2026-10-02

Read-only audit of `docs/backlog.md` on `main`. The audit started at `b363f1b` (#43) with pull request #44 (`refactor/providers-by-class`) still open; **#44 was merged while the audit ran (`3cbc7f2`)**, and the verdicts below were checked again on that commit. Nothing was changed, no eval was run, no model was called. Read-only commands used: `git`, `grep`, `python3 evals/eval_status.py status`, `python3 scripts/validate.py`, and three read-only `gh` calls (open pull requests, the ruleset list, the repository's merge and security settings).

How to read the evidence: `file:line` refers to `main`. Backlog line numbers are those of `docs/backlog.md` at `b363f1b`; #44 added one line after line 184 and a three-line status note after line 216, so later lines sit 1 and then 4 lines further down on `3cbc7f2`.

State of the repository that every verdict rests on:

- `python3 evals/eval_status.py status` on `3cbc7f2`: **33 evaluated, 15 stale, 0 draft** (48 skills). Stale: core-orchestrator, core-skill-creator, design-brief, design-execute, design-ux-flows, eng-architecture, eng-root-cause, eng-tradeoffs, mkt-messaging, ops-pull-request, product-backlog, product-roadmap (from #41 to #43) and eng-security-review, mkt-engage, mkt-publish (from #44); all "the skill folder changed since the recorded run".
- **CI on `main` is red after #44**: job `python39` fails (`validate` and `container` pass). It runs five test files that #42 had moved into the skills (finding 13).
- `python3 scripts/validate.py`: 0 errors, 3 warnings (two inputs no skill produces: `docs/business/idea-validation.md` for biz-market-analysis, `docs/marketing/launch-plan.md` for mkt-content-plan; and the 15 stale skills).
- Gate (`evals/eval-gate.json`): strong and grader `claude-sonnet-5-5`, floor `openrouter/deepseek/deepseek-v4.1-flash`, threshold 0.8, tolerance 0.05, measurement version 4.
- The repository has no issue (`gh issue list --state all` is empty).

## Summary

82 items were triaged: 19 security (S), 20 tooling (T), 11 runtime (R), 1 convention (C), 1 provider (P), 15 brand and social (PB; there is no PB9), 3 "Next skills" entries, 8 review decisions (D7 to D14), and 4 pieces of open work that exist only in the plan or the proof-of-concept note (called PL here).

### Question 1: has it been done?

| Verdict | Count | Items |
|---|---|---|
| DONE on `main` | 36 | S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S12 S13 S19; T2 T3 T4 T5 T6 T8 T9 T10 T12 T13 T16 T17 T20; P1; PB1 PB2 PB3 PB4 PB10 PB12 PB13; D10 D12 |
| DONE by #44, merged during the audit, each with a defect left | 2 | D9 (leftovers N2, N13), D13 (its CI job fails, N1) |
| PARTLY DONE | 18 | S11; T11 T15 T18; R1 R2 R5 R6 R7 R10; PB5 PB6 PB7 PB8 PB15; D8 D14; PL-cases |
| NOT DONE | 26 | S14 S15 S16 S17 S18; T1 T7 T14 T19; R3 R4 R8 R9 R11; C1; PB11 PB14 PB16; ops-release, mkt-launch-plan, flow-launch; D7 D11; PL-helper, PL-digest, PL-validation |

Waiting only on something external (a real run, a real account, a real week): S11, S14, S16, PB5, PB6, PB7, PB15, PB8 (the operator's decision), R10, T15 (the next CI failure).

### Question 2: does it still make sense? (the 46 items not DONE at the start of the audit; D9 and D13 stay in the list for what #44 left open)

| Verdict | Count | Items |
|---|---|---|
| KEEP | 29 | S14 S16 S17 S18; T1 T14 T15 T18 T19; R3 R4 R8 R9 R11; C1; PB6 PB11 PB14 PB16; ops-release, mkt-launch-plan, flow-launch; D7 D8 D9 D11 D13; PL-digest, PL-validation |
| KEEP BUT REWRITE | 13 | S11; T7 T11; R1 R2 R5 R6 R7 R10; PB7 PB8 PB15; PL-cases |
| MERGE INTO another item | 2 | PB5 (remainder into PB6), D14 (into T14 step 1) |
| SUPERSEDED or DROP (recommended, needs the maintainer's yes) | 2 | S15 (superseded by the durable payload folder), PL-helper (drop, or do before the round) |
| DEFERRED BY THE MAINTAINER | 0 as whole items | The local tier that is left inside T12 is deferred (backlog line 165); T12's own "Done when" holds, so T12 counts as DONE and the local tier should become its own item |

### Question 3: where does it go? (the same 46 items)

| Bucket | Count | Items |
|---|---|---|
| A. Before the round, touches skill folders | 7 | T19, C1, PB11, D7, D8, D9 (its leftovers), PL-cases |
| B. Before the round, changes what a run measures | 3 | T1, PL-digest, PL-helper |
| C. Before the round, other | 4 | T18, D13, D14, PL-validation |
| The round itself | 1 | T11 (reopened as "the final measurement round") |
| D. After the round, independent of skills | 15 | T7 T14 T15; R1 R2 R3 R4 R5 R6 R7 R8 R9 R11; PB8 PB16 |
| E. New skills or flows, or a new version of one skill, measured on its own | 6 | S17, S18, PB14, ops-release, mkt-launch-plan, flow-launch |
| F. Waiting on the maintainer or on the world | 10 | S11, S14, S15, S16, R10, PB5, PB6, PB7, PB15, D11 |

### Findings: the tick does not match the code

Ticked, and the "Done when" does not hold today:

1. **T11** (line 141, `[x]`): "the 48 skills are `evaluated` ... 0 stale, 0 draft". Today 33 evaluated and 15 stale. True at #39, undone on purpose by #41 to #44 (`docs/decisions.md`, 2026-10-02, "Phase 5 is carried out in full without measuring the skills again for now"). Its "Done when" also asks `validate.py --strict` to pass its `eval-status` check, which it does not while a skill is stale. The tick is history, not state.
2. **T13** (line 169, `[x]`): its "Done when" starts "T12 settles the floor", and T12 is unticked. Consistent only if T12 is ticked (finding 5).

Unticked, and the work is in the code:

3. **S19** (line 107, `[ ]`): "Closed by T16 when it is done". Evals run only in the container (`evals/executor.py`; `adapters/claude-code/README.md`: the adapter refuses to start without `WB_EVAL_CONTAINER=1`; CI job `container` runs `evals/tests/test_executor_docker.py`). `docs/decisions.md` 2026-10-01: "This closes backlog S19".
4. **T16** (line 203, `[ ]`): every part of its "Done when" holds (decided in `docs/decisions.md`; `eval_run.py` uses the executor for every command; a record names the environment, see `skills/ops-repo-baseline/evals/result.json` `environment`; T11 resumed and closed in it, #38 and #39).
5. **T12** (line 159, `[ ]`): its "Done when" holds (floor and threshold in `docs/decisions.md` and `evals/eval-gate.json`; `eval_run.py --skill <name>` uses them; all 48 skills have a record on that floor). What is left, the local tier, was deferred by the maintainer (line 165) and is a different deliverable.
6. **T2** (line 118, `[ ]`): every skill that commits carries the rule: `skills/ops-branch-sync/SKILL.md:76`, `skills/ops-ci-pipeline/SKILL.md:61`, `skills/ops-pull-request/SKILL.md:61` ("stage it by name after reading `git status` (never `git add -A` or `.`)"), `skills/ops-repo-baseline/SKILL.md:65`, `skills/core-skill-creator/SKILL.md:31`, `agents/implementer.md:38`, and item 4 of `shared/references/security.md:33`, which step 7 of `core-skill-creator` applies to every new skill. `eng-implement` proposes a commit and never makes one (`SKILL.md:58`); `flow-fix-bug` delivers through `ops-pull-request`. No skill says `git add -A` as an instruction.
7. **P1** (line 244, `[ ]`): `providers/publisher/linkedin.py` has `publish --first-comment-file` and a `comment` verb with its own idempotency key (help text lines 102 to 121), with offline tests (`providers/publisher/tests/test_linkedin.py:643` to `809`); `mkt-publish` shows post and first comment under one approval. The real run its "Done when" asks for is recorded under PB7 (line 276: "scheduled posts go out ... from one `plan` approval each, with first comments") and PB4, ticked, says the same (line 270).
8. **S11** (line 76, `[ ]`): the skill is built and reads `evaluated` (strong 0.98 with, 0.55 without; floor 1.00; record of 2026-10-01, measurement version 4). The text still says "draft with the floor at 0.796" (lines 79 to 80), which is the previous floor model. Only the real run on a project is left.
9. **PB6** (line 273, `[ ]`): `mkt-engage` reads `evaluated` (0.98 and 0.92), while the text says "is a draft ... Waiting on a real e-mail for ... the evals" (line 274). What is really open is the e-mail parser (`skills/mkt-engage/scripts/parse_notification.py:113`, "Unverified layout").
10. **R1, R2, R5, R6, R7** (lines 219 to 225, `[ ]`): built for one agent and left unticked on purpose (status note, line 215). Not a defect of the ticks, but no line says what "generic" means, so nothing can ever tick them (see D11).

Other places where a record and the code disagree:

11. `docs/architecture/plan-2026-10.md` phase 5 item 1 says "the scripts that had no test have one". Four scripts have no test of their own: `skills/mkt-engage/scripts/parse_notification.py`, `skills/mkt-social-copy/scripts/check_post.py` (no `scripts/tests/` folder at all), `skills/core-research/scripts/check-brief.py` (same), `skills/design-system/scripts/contrast.py` (only the `brand-identity` copy is tested, and the two copies differ).
12. `docs/inventory.md`: the Agents table lists `explorer` (line 170) and the Counts table says 5 agents built, but `agents/` holds four files; the Progress list has it unticked (line 313). Counts say "Capabilities 62 build, Flows 11 build": 47 capabilities and 1 flow exist. Several State cells quote scores of the previous gate (line 31 "floor DeepSeek V3.2 0.917"; line 102 "draft 0.1 ... floor 0.796"; line 20 "strong delta +0.125, floor 0.875").
13. **#44 merged with a failing job.** It was branched from #41, before #42 moved the skills' tests: its CI job `python39` (`.github/workflows/checks.yml`) runs `scripts/tests/test_policy_gate.py`, `test_payload.py`, `test_render.py`, `test_vote_round.py` and `test_skill_scripts.py`, none of which exists on `main`, and the job fails on `3cbc7f2` (read from the run of that commit). The merge went through because only `validate` and `tests` are required. So decision D13's proof ("CI runs them on that version") does not hold yet, and the backlog's new T15 note ("`test_concurrent_init` runs twice per push") is not true until the job is repaired.

## Items

Columns: **done?** answers question 1 with the evidence; **still makes sense?** answers question 2 (blank when the item is done); **bucket** answers question 3; size S is under an hour, M a few hours, L a day or more.

### Security (S)

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| S1 | Deterministic scan | DONE. `scripts/security_scan.py` (rules table at line 91), run by `scripts/validate.py:321,470`; tests `scripts/tests/test_security_scan.py` | | | | | |
| S2 | Pre-commit hook | DONE. `.githooks/pre-commit` runs `validate.py` and the tests of the touched `providers/`, `scripts/`, `evals/`, adapter and skill-script folders; `scripts/install-hooks.sh` | | | | | |
| S3 | Security checklist and step 7 | DONE. `shared/references/security.md` (10 items); `skills/core-skill-creator/SKILL.md:53` (step 7). The item's text still names the old path `references/security-checklist.md` (line 17) | | | | | |
| S4 | Untrusted-content rule | DONE. `scripts/security_scan.py:91,275,279` | | | | | |
| S5 | Least privilege, agents and evals | DONE. `adapters/claude-code/overrides/{reviewer,researcher,implementer,social-manager}.yaml`. The eval half (`allow_commands`, `--allowedTools`) was removed on 2026-10-01 and replaced by the container; the text (line 26) describes a mechanism that no longer exists | | | | | |
| S6 | Repository settings | DONE. Read from the host: ruleset `main` active; squash only; branches deleted on merge; secret scanning and push protection enabled. `.github/workflows/checks.yml`, `CODEOWNERS`, `dependabot.yml`, `SECURITY.md` | | | | | |
| S7 | `core-security-audit` | DONE. Skill exists and reads `evaluated` | | | | | |
| S8 | `eng-security-review` 0.1 | DONE. Skill exists (`version: "0.1"`, dependency alerts), reads `evaluated` on `main`. Text cites `scripts/tests/test_skill_scripts.py`, moved by #42 | | | | | |
| S9 | Prompt-injection evals | DONE. `eval_run.py --ablate` (`evals/eval_run.py:9,44`); core-research has 5 cases, ops-pull-request 4, eng-root-cause 4 | | | | | |
| S10 | Fix the 2026-09-27 audit | DONE. Fix log in `docs/security/audit-2026-09-27.md:126` to `162` | | | | | |
| S11 | `ops-repo-baseline` | PARTLY. Built and `evaluated` (0.98 / 0.55 / 1.00). Missing: the real run on a project that handles many credentials. Unticked: finding 8 | KEEP BUT REWRITE: tick the skill; keep one line "a real run on a project, its lessons written here without the project's name (principle 8)"; delete the old-floor numbers | F | a project of the maintainer's | M (the run) | no |
| S12 | Approvals bind the payload | DONE. `contracts/state.md:36,54`; `contracts/environment.md:56,58`; `templates/capability.SKILL.md:74,77`; in 8 actuators; `mkt-engage` binds the policy file's hash instead | | | | | |
| S13 | Secrets behind one interface | DONE. `providers/secrets/resolver.py` (registry at line 60); `contracts/secrets.md`; `scripts/doctor.py:130`; `evals/eval_run.py:321` | | | | | |
| S14 | `eng-security-review` beyond alerts | NOT DONE. The skill's description and title are dependency alerts only | KEEP. Rewrite one phrase: "an eval case built from a real finding" becomes "from a finding met on a real project, rewritten with fictional names" (principle 8) | F, then E (one skill's new version, measured alone) | a real project with a finding of each kind | L | no |
| S15 | Optional copy of the approved payload | NOT DONE (no `KeepPayload` anywhere) | SUPERSEDED, recommended DROP: since #25 a payload executed later is kept on disk in `.workbench-local/payloads/<date>/` (`contracts/environment.md:56`), which is what a diff needs; a copy under `docs/` would break "the table stores the hash, never the payload" (`contracts/state.md:54`), needs a personal-data rule first, and would change the 8 actuators | F (decision); A if kept | | M if kept | Q9 |
| S16 | Password manager as a secrets backend | NOT DONE. The seam exists (`providers/secrets/resolver.py:13`, `contracts/secrets.md:12`) | KEEP as written | F | the maintainer's manager, a real case | M | no |
| S17 | `ops-repo-baseline` applies host settings | NOT DONE. `providers/vcs/github.py` has `alerts`, `dismiss-alert`, `resolve`, `read-file`, `commit-files`, `check`; no settings verb. The skill "never changes host settings itself" (`SKILL.md:28`) | KEEP | E (provider verb in D, then one skill's new version measured alone) | S11's real run, an admin-scoped secret in `contracts/secrets.md` | L | no |
| S18 | External secret scanners as an option | NOT DONE (no mention in the skill) | KEEP, low priority; build with S17 so `ops-repo-baseline` is measured once for both | E | S17, a project that asks for one | M | no |
| S19 | Confine the floor model's runs | DONE, unticked (finding 3) | | C (tick only) | | S | no |

### Tooling (T)

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| T1 | `eval_run.py` reports whether the skill was invoked | NOT DONE. No `invoked` field in `evals/eval_run.py` or in either `run-prompt.sh` | KEEP. The 2026-10-01 budget defect (the skill listed without its description, "answered on its own in 5 of 6 runs", `adapters/claude-code/README.md`) is exactly what this field would have shown. Rewrite the path: `benchmark.json` and the record, written by `evals/eval_run.py`; each adapter reports it in `timing.json` | B | none | M | Q4 |
| T2 | Add files by name | DONE, unticked (finding 6) | | C (tick only) | | S | no |
| T3 | Eval regression on changed skills | DONE. `evals/eval_status.py`, `skills/*/evals/result.json`, `validate.py` `eval-status` check | | | | | |
| T4 | `eval_run.py` names a harness folder | DONE. No harness path in `evals/eval_run.py`; `--extra-skill-dir` at line 855. Moot since the runner left the core | | | | | |
| T5 | Tighter eval isolation | DONE (`--runs 3`, `--timeout 900`, `--max-cost-usd`: `evals/eval_run.py:224,249`). Its last sentence, "the same containment becomes the sandbox for runtime agents", was never done and is no item (see "Not covered") | | | | | |
| T6 | Optional container runner | Closed as superseded by T16 (ticked) | | | | | |
| T7 | Trigger tests for descriptions | NOT DONE | KEEP BUT REWRITE: a routing measurement per pack, run in the eval container, that writes no record and gates nothing; state that a description it changes makes that skill `stale` and measured alone | D | T18, T1 (the `invoked` signal is the measurement) | L | no |
| T8 | Parallel eval runs | DONE. `--jobs 4` default (`evals/eval_run.py:224`) | | | | | |
| T9 | The grader reads whole artifacts | DONE. `FILE_LIMIT = 60000` (`evals/eval_run.py:1030`) | | | | | |
| T10 | `lint_brief.py` separators | DONE. `skills/design-brief/scripts/lint_brief.py:66`. Text cites `scripts/tests/test_skill_scripts.py`, moved | | | | | |
| T11 | Every skill passes the gate on record | PARTLY: done at #39, 15 stale today (finding 1) | KEEP BUT REWRITE: leave T11 as the closed first round; open one new item, "final measurement round", whose "Done when" is 48 `evaluated` and `validate.py --strict` green | the round | every A and B item | L (days: account limits; two web skills run alone) | Q1 |
| T12 | The floor model on a person's machine | DONE by its "Done when", unticked (finding 5). `adapters/agents-dir/run-prompt.sh:99` still takes `ollama/<name>`, unreachable from the container (`adapters/agents-dir/README.md:50`) | Split: tick T12; the local tier becomes a new item (see "Not covered" N14), DEFERRED BY THE MAINTAINER (line 165) | C (tick, split) | | S | no |
| T13 | The floor provider is watched | DONE. Early ends retried and counted (`evals/eval_run.py:99`); `DEEPSEEK_API_KEY` registered | | | | | |
| T14 | Open items move to the issue tracker | NOT DONE. No `docs/backlog-archive.md`, no `scripts/backlog_index.py`, no issue in the repository | KEEP, with changes: see "T14" below | D (its step 1 is D14, bucket C) | hygiene (C), principle 8 cleanup, the round | M without the index script, L with it | Q7 |
| T15 | Concurrent `init` of the store | PARTLY. The hypothesis fix is in (`providers/store/sqlite.py:382` to `389`); the cause is not confirmed; no Linux reproduction | KEEP. #44 means to run the store tests twice per push (3.9 and 3.11), which doubles the chance of evidence, once its job is repaired | D (any time, in parallel with everything) | N1 | M | no |
| T16 | Evals in one fixed environment | DONE, unticked (finding 4) | | C (tick only) | | S | no |
| T17 | Evals can allow web search | DONE. `allow_web` in core-research (3 cases), biz-market-analysis, biz-icp-positioning, brand-name | | | | | |
| T18 | An installed skill keeps its description | PARTLY. The eval adapter raises the budget (`adapters/claude-code/run-prompt.sh:19,91`); nothing in either `install.sh`, nothing in `scripts/doctor.py` | KEEP. Order matters: one of its three possible answers ("shorter descriptions with the detail in the body") changes every `SKILL.md`, so the measurement and the decision must come before the round | C (measure and decide), then A only if descriptions change | none | M | Q5 |
| T19 | Assertions that pass in every run | NOT DONE (deferred on 2026-10-02 to the next round that stales the skills, which is now) | KEEP. Note: the list is rebuilt from `evals-workspace/`, which is git-ignored; this checkout holds 28 of the 48 skill folders, so 20 lists must come from wherever the T11 round was run, or from the round's pull requests | A | Q2; the T11 round's workspaces | M | Q2 |
| T20 | Flows named as planned; drift | DONE (#41, #43). Its "Remains" list is open work with no id: see N6, N7 and PL-validation | | | | | |

### Agent runtime (R)

All of R waits on D11 (generic runtime or one agent's script). Nothing in R touches a skill folder except where noted, so all of it is after the round.

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| R1 | Runtime contract | PARTLY. `contracts/runtime.md` exists and names no AI tool; it names one agent's gate (`mkt-engage/scripts/policy_gate.py`, Pieces table) and `scripts/runtime.py:135,136,199` hardcodes that skill's scripts and task text | KEEP BUT REWRITE: "Done when: the contract and `runtime.py` name no skill; the per-agent parts sit behind a handler" | D | D11 | M | Q6 |
| R2 | Storage interface | PARTLY. `providers/store/sqlite.py` (841 lines, offline tests) holds events, cursors, runs, inbox, actions; no tasks, messages, artifacts index, decisions or agent memory; selection by class since #44 | KEEP BUT REWRITE: list the tables that exist, name the ones a second agent needs, add them when R3 or R4 needs them | D | D11, T15 | M | no |
| R3 | Department agents | NOT DONE. Only `agents/social-manager.md` | KEEP. Rewrite "refined against a real company's case": the case and its decisions live in that company's project | D (agents are not measured) | D11, R1 | L | no |
| R4 | Messages between agents | NOT DONE | KEEP | D | R2, R3 | L | no |
| R5 | Approval inbox | PARTLY. Inbox table with the payload's hash, `runtime.py approve`; a daily spend cap in `contracts/runtime.md`; one agent | KEEP BUT REWRITE (generic "Done when") | D | D11, R2 | M | no |
| R6 | Scheduler and triggers | PARTLY. `providers/scheduler/launchd.py --every`, `systemd.py` (never run on a real host: `providers/scheduler/README.md:144`); schedule triggers only, none on a message or an approval | KEEP BUT REWRITE | D | D11, N12 | M | no |
| R7 | Observability | PARTLY. `runs` and `actions` tables | KEEP BUT REWRITE | D | D11 | M | no |
| R8 | Local web app | NOT DONE | KEEP | D | R2, R5, R7 | L | no |
| R9 | Scenario evals | NOT DONE | KEEP. Rewrite: lives in `evals/`, runs in the container, writes no skill record | D | R3, R4 | L | no |
| R10 | Integrations the first case needs | PARTLY. `providers/mailbox/gmail.py` built; no mailer, no CRM | KEEP BUT REWRITE: generic ("a provider class is added when an agent's first task needs it, asked, not assumed"); the case's list of services lives in the project | F | R3, the first case | M each | no |
| R11 | Chat interface | NOT DONE. `adapters/api/` exists (one model call, no tools, `run-agent.sh` only, "Not yet verified with a real key", `README.md:69`): a building block, not the interface | KEEP. Fold the screen into R8 as the item itself suggests; R11 keeps the adapter (`run-prompt.sh` so evals can run through it) and the model provider class. Its "how a run is contained (T5)" should read "the eval container's executor" | D | D11, R2, R5, R8, N11 | L | no |

### Project conventions (C)

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| C1 | Ask whether `docs/` is versioned | NOT DONE. Nothing in `core-project-init`, `contracts/state.md`, `contracts/project-layout.md` or the committing skills | KEEP. It changes `core-project-init`, `ops-pull-request`, `ops-branch-sync`, probably `flow-fix-bug`, and two contracts; three of those skills are `evaluated` today, so it belongs in the pre-round batch or it costs a second measurement of each | A | Q3 | M | Q3 |

### Providers and platforms (P)

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| P1 | First comment on published posts | DONE, unticked (finding 7). Option 1 is built; option 2 became `mkt-engage` (PB6) | | C (tick only) | | S | no |

### Brand skills and the social agent (PB)

There is no PB9 (the ids go PB8, PB10); nothing in the repository cites it.

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| PB1 | `brand-profile` | DONE, `evaluated` | | | | | |
| PB2 | `brand-strategy` | DONE, `evaluated` | | | | | |
| PB3 | `brand-voice` | DONE, `evaluated` | | | | | |
| PB4 | `mkt-content-plan`, `mkt-social-copy`, `mkt-publish` | DONE, all three `evaluated` on `main` | | | | | |
| PB5 | Mailbox provider class | PARTLY. `providers/mailbox/gmail.py`, `auth.py`, offline tests. Missing: a real notification e-mail (`providers/mailbox/README.md:91`) | MERGE INTO PB6: the provider is finished; the open part is the parser's input. Tick PB5 | F | a real e-mail | S | no |
| PB6 | `mkt-engage` | PARTLY. Skill `evaluated`; `parse_notification.py:113` returns `parsed: false` for an e-mail; that script has no test (finding 11) | KEEP. When the e-mail arrives the parser changes, `mkt-engage` goes `stale` and is measured alone. If it arrives before the round, put it in the batch | F, then A or E | a real e-mail | M | no |
| PB7 | Agent `social-manager` and its runtime slice | PARTLY. `agents/social-manager.md`, `scripts/runtime.py`, store, `run-agent.sh`. Missing: the e-mail parser, and seven days running alone | KEEP BUT REWRITE: "seven days of real use" is a record of one project; the item keeps "the e-mail trigger works on a real mailbox" and the run log lives in the project | F | PB6 | S here | no |
| PB8 | Always-on, low-cost architecture | PARTLY. The comparison asked for is written (`docs/architecture/always-on-runtime.md`); `adapters/api/` and `providers/scheduler/systemd.py` were built from it and neither has run for real | KEEP BUT REWRITE: close "compare"; what is left is three things: the operator's choice of host (F), the API adapter checked with a real key (N11), the Linux scheduler rehearsed on a real host (N12) | D | D11 | M | no |
| PB10 | `brand-identity` | DONE, `evaluated` | | | | | |
| PB11 | Linters with translated headings | NOT DONE. `product-feature-spec/scripts/lint_spec.py` takes `--file` and `--json` only (line 39 to 42); `product-backlog/scripts/lint_backlog.py:140` to `143` has no heading option; `biz-icp-positioning/scripts/lint_icp.py:6` to `9` shows the pattern | KEEP | A (product-backlog is already stale; product-feature-spec becomes stale) | none | M | no |
| PB12 | `brand-name` | DONE, `evaluated` | | | | | |
| PB13 | `brand-guidelines` | DONE, `evaluated` | | | | | |
| PB14 | Flow `flow-brand` | NOT DONE (no folder; inventory line 331 unticked) | KEEP. All six phases exist and are evaluated, so it is the cheapest flow to build | E | the round (so its phases are settled) | M to L | no |
| PB15 | Weekly vote to a published post | PARTLY. Built: `skills/mkt-vote-round` (`evaluated`), `scripts/runtime_vote.py`, `scripts/vote_job.py`, `read-file` and `commit-files` in `providers/vcs/github.py`. Missing: one real week end to end | KEEP BUT REWRITE: the text describes one profile repository's layout and wording (see "Principle 8"); keep the generic contract here, move the layout to the project or to the skill's reference | F | a real week | S here | no |
| PB16 | Weekly "latest posts" routine | NOT DONE. `mkt-vote-round/scripts/vote_update.py --record-post` adds only the vote's winner | KEEP, after D11: it would be a third use case written into `scripts/runtime*.py`, which is what D11 is meant to stop | D (if it changes `vote_update.py`, `mkt-vote-round` is measured alone) | D11, PB15's real week | M | no |

### Next skills

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| NS1 | `ops-release` | NOT DONE (no folder) | KEEP. `eng-docs/SKILL.md:42` already names it as the owner of release notes | E | a real release to write it against | L | no |
| NS2 | `mkt-launch-plan` | NOT DONE. It is the missing producer of `docs/marketing/launch-plan.md`, one of the two `validate.py` warnings | KEEP. Rewrite "at a launch's one-week results reading" (a real project's milestone) as "when a project reaches a launch" | E | a real launch; Q8 decides what the dangling input does until then | L | Q8 |
| NS3 | `flow-launch` | NOT DONE | KEEP, last: two of its five phases (`mkt-landing-page`, `mkt-analytics`) are not built either | E | NS2, two unbuilt skills | L | no |

Line 305 ("PB1 to PB7 in order") is out of date: PB1 to PB4 are done and PB5 to PB7 wait on the world, so the list gives no next skill to build. See the action plan for an order.

### Decisions D7 to D14 of the review

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| D7 | The artifact contract | NOT DONE (approved 2026-10-02). `scripts/validate.py:281` still warns on a dangling input; no `updates` key; no placeholder syntax | KEEP. It changes frontmatter in many skills (the review counts 16 that read and write the same path and 7 outputs with several producers), so it is the largest pre-round change | A (skills) and C (`validate.py`, `contracts/project-layout.md`) | PL-validation in the same change; Q8 | L | Q8 |
| D8 | Code shared by several skills | PARTLY. Pairwise identity tests exist (`scripts/tests/test_script_copies.py:29,57,66` for `redact.py`, `rank.py`, `check_refs.py`). Missing: the one source and sync script, the generic test, and the diverged pair: `contrast.py` differs between `brand-identity` and `design-system` and only the first is tested | KEEP. Regenerated identical copies do not change a hash; reconciling `contrast.py` does, for one of the two skills | A (one skill) and C (script, test) | none | M | no |
| D9 | How a skill reaches a provider | DONE by #44 (`3cbc7f2`): `providers/resolve.py`, used by `scripts/runtime.py`, `runtime_vote.py`, `doctor.py`; three skills say `resolve.py --class <class>`. Left out: `skills/mkt-publish/scripts/payload.py:6,171,363` still takes `--workbench` and `--platform` and builds the publisher's command (the backlog's status note calls it "part of D11"); the installers copy neither `shared/` nor `providers/` in `--copy` mode (plan phase 5 item 3; `adapters/agents-dir/README.md` "Limitations") | KEEP for the leftovers: move the `payload.py` change before the round, since it is inside a skill folder (N2); installers after (N13) | A | none | S to M | no |
| D10 | Tests of skill scripts in the skill | DONE (#42). `scripts/test_dirs.py`; hash and adapters skip `scripts/tests/` | | | | | |
| D11 | What the runtime is | NOT DONE: not decided (`docs/decisions.md` has D7 to D10 and D12 approved, D9 and D13 built by #44, nothing on D11). No `runtime/` folder. Meanwhile a second use case was added to the one-agent script (`scripts/runtime_vote.py`, 471 lines) | KEEP: decide before R3, PB16 and R11 | F (decision), then D | none | L after the decision | Q6 |
| D12 | Flows cited and not built | DONE (#41, #43) | | | | | |
| D13 | Python versions | DONE by #44 as a rule (`providers/CONTRACT.md` "Python version"); its CI job `python39` fails on `main` (finding 13) | KEEP: repair the job's file list (N1) | C | none | S | Q10 |
| D14 | Backlog hygiene before T14 | PARTLY. Done: the duplicate id (T17), T6 folded into T16. Not done: "tick what is built" (findings 3 to 9), "cut done items down to one line" (S9, S11, T11 and PB7 are 10 to 20 lines each) | MERGE INTO T14 step 1 (the archive), done early | C | none | S to M | no |

### Open work recorded only in the plan or the proof-of-concept note (PL)

| id | title | done? | still makes sense? | bucket | depends on | size | decision needed |
|---|---|---|---|---|---|---|---|
| PL-helper | The adapters' shared parts move to one helper (plan phase 4 item 1; note "Left for phase 4") | NOT DONE. `adapters/agents-dir/run-prompt.sh` and `adapters/claude-code/run-prompt.sh` share no file | DROP recommended: a refactor of what every run executes, with no behaviour to gain. If wanted, it goes before the round, never between the round and the next change | B | none | M | Q4 |
| PL-digest | Pin the image base by digest (note, last line) | NOT DONE. `evals/container/Dockerfile:4` `FROM node:24.10.0-bookworm-slim`; `proxy/Dockerfile:2` `FROM alpine:3.22` | KEEP. A tag can move under the round; a digest cannot. It changes the definition's hash, which every record names, so it is settled before the round | B | none | S | no |
| PL-cases | Cases adapted (plan phase 4 item 3; T11 "known case defects") | PARTLY. Done: core-research sets `allow_web`. Open: core-project-init's two always-pass assertions (now part of T19); the script that builds design-handoff's fixtures is not in the repository (`skills/design-handoff/evals/files/landing` only). Not verified: whether any case still depends on one operating system | KEEP BUT REWRITE: only the fixture builder is left; either add it under `skills/design-handoff/evals/` (the skill goes `stale`) or record that the fixture is edited by hand | A | none | S | no |
| PL-validation | Validation rules (plan phase 5 item 5; review B2; T20 "Remains" 3) | NOT DONE. `scripts/validate.py` has no check of required metadata keys, `requires` against the known classes, the `side_effects` vocabulary, the token guide, the two-case minimum, skill names cited by agents and flows, pack patterns, or a capability that invokes a skill; `packs/` is not scanned as core; the YAML loader still differs by machine (`validate.py:167` to `172`) | KEEP, and do it first: it costs no skill change by itself and it tells which skills the batch must touch | C | none | M | no |

## Not covered by any item

Work the code or the documents show is needed and no backlog item owns. Bucket in brackets.

- **N1. Repair the `python39` job, red on `main` since #44** [C, S, first thing]. Replace the five missing paths by the skills' own test folders (`skills/mkt-engage/scripts/tests`, `skills/mkt-publish/scripts/tests`, `skills/brand-identity/scripts/tests`, `skills/mkt-vote-round/scripts/tests`, or a list from `scripts/test_dirs.py` limited to the scripts in `ON_SYSTEM_PYTHON`), and add a wiring test so that a path the workflow names must exist (`scripts/tests/test_checks_wiring.py` is the place).
- **N2. `payload.py` builds a provider path** [A, S]. `skills/mkt-publish/scripts/payload.py` (`--workbench`, `--platform`). #44 left it for D11; done after the round it makes `mkt-publish` `stale` again.
- **N3. Revisit the tolerance** [B, S]. `docs/decisions.md` 2026-10-01: "`strong_tolerance` is 0.05 ... to be revisited when the 48 skills are measured". They were measured; nothing revisited it. The spread of 48 skills is in the T11 round's benchmarks. A change of the gate's rule raises the measurement version, so it is settled before the round.
- **N4. The grader grades its own model's runs** [B, decision Q4]. Review finding A5 and D4 ("a grader different from the model under test is weighed in the proof of concept"); the proof-of-concept note does not mention it. Changing the grader makes every record `stale`, so it is decided before the round or dropped on record.
- **N5. `core-skill-creator/SKILL.md` is above the size guide** [A, M]. 24,085 bytes, about 5,900 tokens (backlog line 155: "to be trimmed into `references/` and measured again"). Already `stale`. T19 also holds three of its assertions.
- **N6. The routing table lacks seven built skills** [A, S]. `brand-name`, `brand-profile`, `core-security-audit`, `eng-security-review`, `mkt-engage`, `mkt-vote-round`, `ops-repo-baseline` appear nowhere in `skills/core-orchestrator/` (T20 "Remains" 4). `core-orchestrator` is already `stale`.
- **N7. Two references that could name a skill as an artifact's writer** [A, S, optional]. `core-clarify/references/decision-tree.md`, `ops-repo-baseline/references/host-settings.md` (T20 "Remains" 1). Both skills are `evaluated`; do it in the batch or never.
- **N8. Inventory drift** [C, S]. The Counts table, the `explorer` row, State cells quoting old-gate scores, the "Tooling" sentence (finding 12).
- **N9. Scripts with no test** [C, S each; tests are outside the hash]. `parse_notification.py`, `check_post.py`, `check-brief.py`, `design-system/scripts/contrast.py` (finding 11).
- **N10. CI jobs that are not required checks** [C, S, decision Q10]. The backlog (S6) records `validate` and `tests` as the required checks; `container` and `python39` exist and are not required, which is how #44 merged with `python39` failing. Not verified: the ruleset's current list was not read.
- **N11. The API adapter is unfinished as an adapter** [D, M]. `adapters/api/` has `adapter.json`, `run-agent.sh` and tests, no `install.sh` and no `run-prompt.sh`, and has never called a real endpoint; `AGENTS.md` "Adding an adapter" asks for `install.sh` and does not mention `run-agent.sh`, the runtime's entry point that `contracts/runtime.md` defines.
- **N12. The Linux scheduler has never run on a real host** [F then D, M]. `providers/scheduler/README.md:144`; since #44 it is the default on Linux.
- **N13. Installers do not carry what a skill needs** [D, M]. `adapters/agents-dir/install.sh --copy` copies neither `shared/` nor `providers/` (its README, "Limitations"); the Claude Code adapter's install was never confirmed on a real install (its README, "Limitations"). Since #44 an installed skill also needs `WORKBENCH_ROOT`; nothing tells the installer to set or print it.
- **N14. The local tier** [F: deferred by the maintainer]. What is left of T12: a route from the container to a model on the person's machine, then one model, the evaluated skills, a threshold of its own, published and not gating.
- **N15. Containment of runtime agents** [D, with D11]. T5 promised the eval containment for them; today a runtime agent is limited by its tool list only (`run-agent.sh --tools Read,Glob,Grep`).
- **N16. Planned flows, agents and skills with no backlog id** [E]. `flow-build-feature`, `flow-improve-code`, `flow-new-project`, `flow-implement-ticket`, `flow-business-plan`, `flow-design`, `flow-social-post`, `flow-new-product`; the `explorer` agent; `design-system` 0.3 (inventory line 322); `biz-validate-idea`, the producer of the other dangling input. D12's recommendation was "mark each as planned with a backlog id"; they were marked planned without one.
- **N17. Jobs scheduled before the ledger move** [F, in the project]. #44: "those jobs are scheduled again after upgrading". It is an action in the project that uses the workbench, to be said in the pull request, not tracked here.
- **N18. Entries of `docs/decisions.md` that a later entry reversed are not marked** [C, S]. See "Overlaps and contradictions".
- **N19. Principle 8 cleanup of the documents** [C, M]. See "Principle 8".

## Cross-checks

### Ids

- **Duplicates:** none today (the second T8 became T17 on 2026-10-01).
- **Gaps:** PB9 does not exist. S and T are complete (S1 to S19, T1 to T20) and out of numeric order in the file (S14 after S8; T8 before T6; T17 after T7; T20, T19, T18, T16 at the end).
- **Cited elsewhere and missing here:** none. Every backlog id cited in `contracts/`, `providers/`, `adapters/`, `docs/inventory.md` and the skills exists (`S6`, `S13`, `S14`, `S16`, `T12`, `R2`, `R5`, `R7`, `PB1`, `PB5`, `PB6`, `PB7`, `PB10`, `PB12` to `PB15`). The `[S19]` to `[S47]` marks in `docs/architecture/research/` are source numbers, not backlog ids.
- **Ids cited from inside a skill folder** (changing the citation would make the skill `stale`): `skills/mkt-engage/scripts/parse_notification.py:23` (PB6), `skills/ops-repo-baseline/references/host-settings.md:3` (S6). T14 must keep both ids resolvable.
- **Backlog text that names things that no longer exist:** line 17, `skills/core-skill-creator/references/security-checklist.md` (now `shared/references/security.md`); lines 43 and 139, `scripts/tests/test_skill_scripts.py` (split into the skills by #42); line 26, `allow_commands` and `--allowedTools` (removed 2026-10-01); lines 11 and 74, "Tests: ... `scripts/tests`" for things now tested elsewhere; line 179, "`core-skill-creator` step 12 where they point here" (`core-skill-creator/SKILL.md` does not mention the backlog); line 232, "how a run is contained (T5)". T14's own text asks for a script "through the `integration:issue-tracker` class": no provider of that class exists (`providers/` holds mailbox, publisher, scheduler, secrets, store, vcs).

### Overlaps and contradictions

- **T11 against the inventory:** "48 evaluated" against 36 (finding 1).
- **T12, T13, T14 chain:** T13 is ticked on "T12 settles the floor"; T14 waits for "T12 closes"; T12 is unticked and, as written (three layers: "in progress", "decided", "deferred"), can never close.
- **S19, T6, T16:** one piece of work under three ids (review finding A9); T6 is ticked as superseded, S19 and T16 are unticked, all three are done.
- **T7 and T18:** both are about descriptions reaching and routing the model. Keep both, T18 first; T7 uses T1's signal.
- **S15 against `contracts/state.md:54`** ("stores the hash, never the payload") and against the durable payload folder of #25.
- **P1's "open question"** is answered twice in the file (PB4: option 1 built; PB6: option 2 became a skill) and still reads as open.
- **Runtime status note (line 215)** says D11 is "to be taken before R3", while PB15 was built into the one-agent runtime after the review and PB16 would add a third use case.
- **"Next skills"** names an order from 2026-09-26 that the PB section finished or blocked; `docs/inventory.md` waves give another order; neither says what is next.
- **`docs/decisions.md`, entries reversed by later entries and not marked:** 2026-09-28 "Claude models run on the maintainer's account" (signed-in CLI; now a token in a container); 2026-10-01 "The strong model is Claude Sonnet 5.5": "records made with the previous strong model stay valid" (reversed the same day: a different strong model is `stale`); 2026-10-01 "The strong model's eval commands are confined by a sandbox" (removed by "Adapters run only in the container"); 2026-10-01 "An eval run leaves nothing running and shows no dialog" (the keychain code was removed); 2026-10-01 "Eval runs happen outside the repository", "Not closed by this" (closed by the container). Three entries name `scripts/eval-gate.json` and the old runner path; one later entry says so.
- **The plan against the decisions:** `plan-2026-10.md` phase 6 says T14 comes "after phase 2.5 and when T12 closes"; phase 5's header was corrected for the changed order, its risk table (last row but one) still describes the old order.
- **`AGENTS.md` against the adapters:** "Adding an adapter" requires `install.sh`; `adapters/api/` has none (N11).

### T14: is it still worth doing, and when?

Worth doing, later, and smaller.

- **Why still:** the repository is public and meant for other people; after this triage about 40 items are open, 10 of them waiting on the world. An issue per item gives each a place for the evidence that arrives (a CI failure for T15, a real e-mail for PB6).
- **Why not now:** (1) seven ticks are wrong, so the open list is wrong; (2) 11 open items (bucket A and B and the round) close together in the next days, and migrating them means creating and closing 11 issues for nothing; (3) issues are public and `validate.py` does not read them, and the PB and R texts still carry one real case's decisions and run log (below); a public issue cannot be un-published the way a file line can be rewritten; (4) its precondition "after T12 closes" needs T12 ticked.
- **When:** step 1 (the archive of done items, which is D14) before the round, since it is documents only and makes the batch readable. The migration itself is the first step after the round.
- **Smaller:** drop `scripts/backlog_index.py` from the first version. It needs a provider class that does not exist, a scheduled CI job and a token. With about 30 open items an index line added in the pull request that opens the issue is enough; build the generator only if the index is found out of date twice. Keep the private-term check on each body before creating it.

### Principle 8: a real project's names, dates, numbers or decisions in the backlog

Names were removed by #21; what remains is one real case's decisions, dates, run log and repository layout, written without the name. Lines of `docs/backlog.md`:

| Lines | What it carries | Proposal |
|---|---|---|
| 257 to 264 (PB section header) | The case's decisions: LinkedIn first; "a Mac first"; "Model: Claude through the claude-code adapter"; notification e-mails as the trigger; the check made "on 2026-09-29 with a member token" and its 403 | Keep the platform fact, with its sources, in `providers/publisher/README.md` and `providers/mailbox/README.md` (where most of it already is). Replace the header by two generic lines: a project's brand artifacts live in the project; autonomy is within approved bounds. Move the case's choices (network, host, model) to that project's `docs/` |
| 272 (PB5) | "The Google project is published 'In production' as a personal-use app" (the state of one person's cloud project) | Keep the generic rule already in `providers/mailbox/README.md:17`; delete the sentence here |
| 276 (PB7) | A run log: "2026-09-30: a rehearsal passed ... about 95 s"; "first replies sent: one approved one by one and one sent ... on its own"; "scheduled posts go out ..."; "7 days running on its own" | Move to the project. Here: "built; verified by a rehearsal on a real machine; open: the e-mail trigger" |
| 278 (PB10) | One person's cover image: size, the empty area for the photo, "three variants (dark, light, blue) for the person to choose" | Delete; the lesson (leave the photo area empty) belongs in the skill if it is not there |
| 284 to 291 (PB15) | One profile repository's layout and wording: `data/pick.json`, "3 topics", "one pick per account", the profile "shows 'I wrote it'"; "Done when: one real week runs end to end on a profile repository" | The contract the feature expects is already in `docs/architecture/weekly-vote.md` and `skills/mkt-vote-round`; reduce the item to "built; open: one real week, recorded in the project". Decide whether `weekly-vote.md` itself is a generic contract (keep) or one repository's design (move): see Q11 |
| 292 to 299 (PB16) | The same repository's "Latest posts" section, `data/posts.json`, WebP thumbnails, "3 most recent entries" | Rewrite as a generic routine: "after a period, list what the publisher's ledger says was published and hand it to a project-defined target through the vcs provider"; the target's layout is the project's |
| 305 to 306 (Next skills) | "The order agreed on 2026-09-26"; "at a launch's one-week results reading ... checked against real numbers" | Rewrite as the generic rule (a marketing skill is written alongside a real launch) |
| 217 (runtime intro) | "Each item is refined against a real company's case" and, in `docs/decisions.md` 2026-09-28, "a real one-person company with no clients yet, starting with marketing agents that look for clients" | Keep the rule, drop the description of the company |
| 93, 96 (S13) | "`LINKEDIN_ACCESS_TOKEN` in the secret store ... the token's expiry (57 days)"; a cloud session's token shadowing "the maintainer's token" | The first is the state of one person's account: delete. The second is the workbench's own lesson: keep |
| 237 (C1), 119 (T2), 244 (P1) | "In one public project, launch posts and their approval records were committed ..."; "during a real project's launch"; "during a product launch" | Acceptable as written: the lesson without the project |
| 29 (S6) | `<owner>/ai-workbench` | The workbench's own repository, not a project that uses it: acceptable; "this repository" would avoid the handle |

Outside the backlog, the same kind of content: `docs/architecture/always-on-runtime.md` ("where the social agent runs once it leaves the Mac", the rehearsal's timings), `docs/architecture/weekly-vote.md`, `docs/decisions.md` 2026-09-30 ("a comparison of models on real comments (2026-09-30, 8 comments, 2 runs each)"), `docs/inventory.md` lines 31, 32, 59 and 61 ("a real company's run of 2026-09-28", "a LinkedIn cover for a real personal brand"). Not audited in full: `docs/architecture/research/` and `docs/security/`.

## Proposed action plan

The constraint: one final measurement round of the 48 skills. So everything that changes a skill folder (A) or what a run measures (B) lands first, in as few pull requests as the single working tree allows, and nothing in A or B is touched between the round and the next deliberate change.

### Step 0. Decide (maintainer, one sitting)

Q1 to Q6 block steps 2 to 4. Q7 to Q11 can wait until their step.

### Step 1. Bucket C first: no skill changes, and it tells the batch what to touch (parallel: four independent lanes)

0. **Repair the `python39` job** (N1): `main` is red. S, before anything else.
1. **Hygiene of the backlog** (D14, T14 step 1): tick S19, T16, T12, T2, P1; rewrite S11, PB5, PB6 to what is really open; reopen the round as a new item (Q1); move done items to `docs/backlog-archive.md`; give ids to N1 to N19 that survive; fix the stale paths listed under "Ids". S to M.
2. **Principle 8 cleanup** (N19) of the backlog, and the marks on reversed decisions (N18), inventory drift (N8). M. Same lane as 1 (same files).
3. **Validation rules** (PL-validation), written to warn first: required keys, class and side-effect vocabularies, cited skill names, packs scanned, one YAML loader, the token guide, "a capability does not invoke a skill". Its output is the list of skills step 2 must fix. M.
4. **T18, measurement only**: how many descriptions of the default pack reach the model on each harness, and the decision (Q5). M. If the answer is "shorter descriptions", that edit joins step 2.
5. **Missing script tests** (N9) and **required checks** (N10). S each. Tests are outside the hash, so this lane never interferes.

### Step 2. Bucket A: every change inside skill folders, batched (one working tree: these are sequential pull requests, smallest first; each ends with `eval_status.py inventory --write` and no measurement)

1. **`payload.py` asks the resolver** (N2, the leftover of D9). mkt-publish is already stale from #44.
2. **D8**: the one source and sync script, the generic identity test, `contrast.py` reconciled (one of brand-identity, design-system).
3. **D7 with PL-validation switched to errors**: placeholder syntax, `updates` beside `outputs`, the two dangling inputs (Q8), `contracts/project-layout.md` checked against the declarations. The widest change: do it once, after 1 and 2 so that it reads the final frontmatter.
4. **C1** (Q3): core-project-init, ops-pull-request, ops-branch-sync, the contracts.
5. **Small skill edits, one pull request**: PB11 (two linters), N5 (trim core-skill-creator), N6 (seven routing rows), N7 (two references, optional), PL-cases (design-handoff's fixture builder), T18's description changes if Q5 says so, PB6's parser if a real e-mail has arrived.
6. **T19 last** (Q2): remove the assertions decided, each change listed before and after. Last because every earlier step may add or change cases.

After step 2 expect most of the 48 to read `stale`; that is the intended state before the round.

### Step 3. Bucket B: what a run measures (parallel with step 2: different files, `evals/` and `adapters/`)

1. **T1**: the `invoked` field (Q4 for what it does to a score).
2. **PL-digest**: base images by digest.
3. **N3 and N4**: the tolerance from the measured spread; the grader question closed on record (Q4).
4. **PL-helper**: only if Q4 says yes; otherwise dropped on record.
5. One commit raises `measurement_version` (4 to 5) if any of 1 to 4 changes what a clean run measures (the image definition does; a new rule or grader does; a report-only field does not). After it, nothing in `evals/` or the eval adapters changes until the round is committed.

### Step 4. The final measurement round (T11 reopened)

- Precondition: steps 2 and 3 merged, `validate.py` with zero errors, `eval_run.py --check-cases` clean, the container job green.
- 48 skills, full runs, several skills at a time (`--jobs`), the two skills whose cases search the web alone and two runs at a time (the rate limit recorded in `docs/decisions.md`). Days, not hours: the strong model's account limit.
- Repairs follow the rules already agreed (the skill is fixed when the output is not good; an assertion changes only for the two recorded reasons; every change listed).
- Freeze: while the round runs, no pull request touches `skills/`, `evals/`, `adapters/*/run-prompt.sh` or `shared/`. Buckets C leftovers, D and the documents can go on in parallel, in another worktree.
- Done when: 48 `evaluated`, `validate.py --strict` green. Then make `--strict` the CI default, so the state cannot drift silently again.

### Step 5. Bucket D, after the round (independent of skills; lanes in parallel)

- **Lane 1, backlog:** T14 (issues, without the index script; Q7).
- **Lane 2, runtime, in this order:** D11 decided (Q6) → R1 (the runtime names no skill; per-agent handler; N15 containment) → R2 and R5 to R7 made generic → N12 (Linux scheduler on a real host) and PB8's leftovers (N11, the API adapter with a real key and a `run-prompt.sh`) → PB16 → R3 → R4 → R8 with R11's screen → R9.
- **Lane 3, tooling:** T15 (any time; evidence from CI, after N1), N13 (installers), T7 (after T18 and T1; a description it changes sends that one skill back to be measured alone).

### Step 6. Bucket E, new skills and flows, each measured alone when built

Order by what already exists and by what unblocks a check:

1. `flow-brand` (PB14): six phases built and evaluated.
2. `flow-build-feature`, then `flow-improve-code` and `flow-new-project` (N16): their engineering phases are all built; they turn the orchestrator's `pending` routes into real ones.
3. `ops-release` (NS1), with a real release.
4. `mkt-launch-plan` (NS2), with a real launch; it removes one dangling input. Then `flow-launch` (NS3), after `mkt-landing-page` and `mkt-analytics`.
5. `ops-repo-baseline` next version: S17 with S18, after S11's real run.
6. `eng-security-review` next version (S14), as real findings arrive.
7. The rest of N16 as projects ask.

### Bucket F, waiting (no action in the repository until the event)

S11 (a real run), S14 (real findings), S16 (a password manager in use), PB5 and PB6 and PB7 (a real notification e-mail, then days of use), PB15 (a real week), R10 (the first case's needs), PB8 (the operator's choice of host), N12, N14 (the local tier, deferred), S15 and D11 (decisions Q9 and Q6).

## Decisions for the maintainer

1. **Q1. Reopen the measurement as one new item?** T11 is ticked and 15 skills are stale. Options: (a) leave T11 ticked as the first round and open a new item, "final measurement round", with the "Done when" of step 4; (b) untick T11. Recommendation: (a); the tick then stays true to what happened and the open list shows the round.
2. **Q2. T19, which always-passing assertions go?** Options per kind: the 20 language assertions; the about 46 guards; the about 134 content ones. Recommendation: remove the 20 language assertions; keep every guard; for content, remove only those that passed in all 12 runs and do not depend on a fixture detail (decided skill by skill from the round's `grading.json`), and accept that the list for 20 skills must be rebuilt from the T11 round's data, which this checkout does not hold.
3. **Q3. C1, what does "is `docs/` versioned" mean?** Options: (a) all of `docs/` versioned or all local; (b) per kind: code-related documents versioned, work data (marketing material, approvals, state, payloads) local; (c) a list the project edits. Recommendation: (b) with two named groups and the answer recorded in the state file and the project's `AGENTS.md`; a project created before the question is asked once, on the first commit a skill would make under `docs/`.
4. **Q4. What changes in the measurement before the round?** Four yes or no answers: (a) T1 `invoked`: a with-skill run that never loaded the skill stays a score (recommended: yes, it is the description's failure, and the field only reports it; no version change); (b) the tolerance stays 0.05 unless the 48-skill spread says otherwise (recommended: compute it, change only if the pooled spread differs clearly); (c) the grader stays the strong model (recommended: yes, recorded as a decision with the bias named; a second grader doubles the cost of grading); (d) the adapters' shared helper (recommended: drop).
5. **Q5. T18, what does the installer do about the listing budget?** Options: (a) the installer writes the budget into the settings it creates; (b) smaller packs; (c) shorter descriptions with the detail in the body. Recommendation: measure first (step 1); then (a) where the harness allows it and (b) otherwise; (c) only if the measurement shows nothing else works, because it changes all 48 skills and must then land in step 2.
6. **Q6. D11, what is the runtime?** Options: (a) generic, in a top-level `runtime/` folder, per-agent parts behind a handler (the review's recommendation); (b) it stays one agent's script and the R section is cut down to what that agent needs. Recommendation: (a), decided now and built after the round; until then no new use case is added to `scripts/runtime*.py` (PB16 waits).
7. **Q7. T14, with or without the generated index?** Options: (a) as written (script, issue-tracker provider, scheduled check); (b) issues plus an index line edited in the pull request that opens or closes an issue. Recommendation: (b) right after the round; (a) only if the index is found wrong twice.
8. **Q8. D7, the two inputs no skill produces** (`idea-validation.md`, `launch-plan.md`). Options: (a) remove them from `inputs` until their producers exist; (b) add a way to declare an input as optional or planned and keep them; (c) build `biz-validate-idea` and `mkt-launch-plan` first. Recommendation: (b): both skills already treat the file as "read if present", the declaration then says so, and a dangling required input becomes an error.
9. **Q9. S15, the optional copy of an approved payload.** Options: (a) drop: the durable payload folder already keeps what was approved for anything executed later; (b) keep as written. Recommendation: (a).
10. **Q10. Required checks.** Options: (a) add `container` and `python39` to the ruleset's required checks; (b) leave `validate` and `tests`. Recommendation: (a) once `python39` is repaired and both have been green twice; a required `python39` would have stopped #44; the container job is what proves the round's environment.
11. **Q11. Principle 8, where do the case's design documents go?** `docs/architecture/weekly-vote.md` and `docs/architecture/always-on-runtime.md` describe one project's repository layout and one agent's hosting. Options: (a) keep them as the generic contract of a feature, rewritten without the case's choices; (b) move them to the project and leave a short generic contract here. Recommendation: (b) for `always-on-runtime.md` (it is a hosting decision for one operator); (a) for `weekly-vote.md`, since `mkt-vote-round` and `runtime_vote.py` implement exactly that layout and need it documented.
