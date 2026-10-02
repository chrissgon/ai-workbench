# Backlog: workbench tasks

Work on the workbench itself that is not writing a skill: tooling, checks, rules, repository settings. Skills, flows and agents are tracked in [inventory.md](inventory.md); an item here that becomes a skill also gets a row there.

- **Only open items are here.** Closed items are in [backlog-archive.md](backlog-archive.md), as they were written. Ids are never reused and never renumbered: they are cited in contracts, providers, skills, `decisions.md` and commits.
- **Where each item is handled** is its `Plan:` line, which names the phase and item of the plan in force, [architecture/final-plan-2026-10-02.md](architecture/final-plan-2026-10-02.md) (section "Backlog map"). Every item was triaged on 2026-10-02; the evidence is in [architecture/audit-2026-10-02/](architecture/audit-2026-10-02/README.md).
- Each item says where it came from, so none is written from generic knowledge. Tick an item when its "Done when" holds, add the commit, and move it to the archive.
- **Words about a skill's status.** How skills are tested and ranked is the reliability model ([architecture/reliability-model-2026-10-02.md](architecture/reliability-model-2026-10-02.md)): a new skill is done when its first full test has passed, and a skill is then ranked by a band (`reliable`, `watch`, `needs a test`) computed from its lab evidence. The words `draft`, `evaluated` and `stale` belong to the first round (T11, archived); the status script prints them until phase B of the plan replaces them.

## Security

The workbench is a set of instructions that models execute with a terminal, files and network access. The threats are the ones that turn those instructions against the user: secrets in the repository, text hidden from the human reviewer, scripts that run more than they say, and skills that act on the outside world without declaring it.

- [ ] **S11. Skill `ops-repo-baseline`: a real run on a project.** The repository baseline set up for this repository on 2026-09-27, as a procedure for any project: the in-repository files and the host settings, in the order that works (signing before the signed-commits rule, a first CI run before required checks, a history scan before the first push), with the decisions that differ per project asked with a recommended answer (approvals, signed commits, visibility).
  - Built: `skills/ops-repo-baseline` with `scripts/baseline_status.py` (read-only diagnosis), `scripts/secret_scan.py`, `assets/` and `references/host-settings.md`. It writes the in-repository files and the host checklist and changes no host setting (S17). It passed the gate of the first round (status table of the inventory).
  - Open: a real run on a project that handles many credentials, on a local machine (decided on 2026-09-28). Its lessons are written into the skill without the project's name.
  - Done when: that run is done and what it taught is in the skill.
  - Plan: H (waiting on the run), then G step 6.

- [ ] **S14. `eng-security-review` beyond dependency alerts.** Extend the skill from 0.1 (dependency alerts only) to the rest of S8's scope: secrets in the code and the history, authentication and authorization, input handling, security headers and configuration, with findings at `file:line` in the same report.
  - From: the user's decision on 2026-09-28 to ship 0.1 with the dependency triage only, since that part had a real case.
  - Needs: a real project with a finding of each kind to ground each part, and S8's eval runs done.
  - Done when: each added part has an eval case built from a real finding, and the report template covers it.
  - Plan: H (findings met on a real project), then G step 7: the skill's next version, tested when built.
- [ ] **S16. A password manager as a secrets backend.** A lookup function in `providers/secrets/resolver.py` after the OS secret store, reading through the manager's CLI (for example 1Password `op read` or Bitwarden `bw get`), chosen with the user.
  - From: the user's decision on 2026-09-28 for S13: leave room for it, build it with a real case.
  - Needs: the user's manager, and a test with a fake CLI; the CLI's session must never be started by a skill.
  - Plan: H (a password manager in use), then lane F6.
- [ ] **S17. `ops-repo-baseline` applies the host settings itself, when the user wants it.** An option to apply the checklist through the host's API (push protection, private reporting, alerts, merge method, the ruleset) after one approval of the whole plan, with a confirmation gate and the S12 payload hash, instead of handing the checklist to the user. The workbench aims to run fully automated for whoever chooses it.
  - From: the user's decision on 2026-09-28 for S11: version 0.1 writes the checklist; applying it automatically is a future option.
  - Needs: a provider verb for repository settings in `integration:vcs`, and an admin-scoped token kept apart from the read-only one (`contracts/secrets.md`), used only for this.
  - Plan: lane F6 (the provider verb and the admin-scoped secret), then G step 6, after the real run of S11.
- [ ] **S18. External secret scanners as an option in `ops-repo-baseline`.** Let a project choose an established scanner (for example gitleaks), pinned to an exact version and checksum, in the checks workflow and the hook, instead of or next to the bundled `secret_scan.py`.
  - From: the user's decision on 2026-09-28 for S11: the bundled scanner by default, integrations with other tools as a future option.
  - Plan: G step 6, built with S17 so that the skill changes once for both.

## Tooling

- [ ] **T1. The eval runner reports whether the skill was invoked.** Today that is read by hand from the transcripts, and a run with the skill that never loaded it scores as the skill's failure. On 2026-10-01 a harness listed a skill under test by name only, with no description, and the model answered on its own in 5 of 6 runs (`adapters/claude-code/README.md`): this field would have shown it.
  - Done when: each eval adapter reports it in `timing.json`, and `evals/eval_run.py` writes `invoked` per run in the run folder and a count per model in the line of its test event. A run that never loaded the skill still scores, as the description's failure (default 24 of the plan).
  - Plan: B8.
- [ ] **T7. A routing measurement per pack.** The prompts of the eval cases run with a whole pack installed, and the report says which skill each prompt loaded, read from T1's `invoked` field: prompts that should load a skill and did not, and prompts that loaded another one. So a large pack (a company's worth of skills) still routes to the right skill. It writes no evidence of a skill and gates nothing; a description it leads to change is a change of that one skill, tested as the reliability model asks.
  - From: trigger tests for descriptions in Anthropic's skill-creator (https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md, read 2026-09-27), rewritten on 2026-10-02 as a measurement.
  - Done when: one routing report exists per pack, listing the prompts that loaded another skill or none.
  - Plan: B9a (the runner's routing mode), D3 (the pilot uses it), lane F4; after T18 and T1.
- [ ] **T14. Open backlog items move to the repository's issues.** Decided by the maintainer on 2026-10-01; made smaller on 2026-10-02. The repository is meant for many people, and issues are where they look for work, comment and pick a task.
  - Step 1, done on 2026-10-02: the closed items are in `docs/backlog-archive.md`, and every tick in this file matches the code.
  - What moves: every open item becomes one issue. The title keeps the id (`T15: Find what makes concurrent init of the store fail`), because ids are cited in `docs/decisions.md`, `docs/inventory.md`, commits and code comments. The body is the item's text: what, why, what is done, done-when. Labels follow this file's sections.
  - What stays here: `docs/backlog.md` becomes a short index, one line per open item (`- T15: <title> (#<issue>, <labels>)`), so an agent finds the work without a network call. The line is edited in the pull request that opens or closes the issue. No generated index and no script (default 86 of the plan): a generator needs a provider of the class `integration:issue-tracker`, which does not exist, a scheduled CI job and a token; it is built only if the index is found out of date twice.
  - Care: issues are public and `scripts/validate.py` does not read them, so principle 8 is checked by the author, and the private-term check is run on each body before the issue is created; a body that fails is not created. English only, as everywhere.
  - Order: a dry run that prints each issue (title, labels, body) for the maintainer to approve once; the issues and labels; this file replaced by the index and a table from id to issue number; `AGENTS.md` ("docs/backlog.md: workbench tasks") updated. The two ids cited from inside skill folders (PB6, S6) stay resolvable.
  - Done when: no open item lives only in this file, the index matches the open issues, and the references to ids in the repository still resolve through the index or the archive.
  - Plan: lane F1, the first thing after phase E.

- [ ] **T15. Find what makes concurrent `init` of the store fail.** On 2026-10-01 `providers/store/tests/test_sqlite.py::test_concurrent_init` failed once in CI (four processes initialising the same new database returned `[0, 1, 0, 0]`; Linux runner, Python 3.11) on a change that did not touch the store, and passed on every run before and after. The log held no stderr, so the error is unknown.
  - Done the same day (pull request #25), on a hypothesis: `private_files()` checked that the `-wal` and `-shm` files exist and then set their mode, and SQLite deletes both when the last connection closes, so another process could remove one in between (`FileNotFoundError`, exit 1). The chmod now ignores a file that is gone, with a test for that case, and `test_concurrent_init` prints each process's stderr when it fails.
  - Not confirmed: the failure was not reproduced locally (210 rounds of 8 concurrent `init` on macOS, before and after the change), so the cause may be another one. Candidates to check: `BEGIN IMMEDIATE` or the first read answering "database is locked" at once while another process switches the file to WAL (`enable_wal` retries only its own statement), and the busy timeout not applying during that switch.
  - 2026-10-02: the store's tests now also run on Python 3.9 in CI (job `python39`, decision D13), so `test_concurrent_init` runs twice per push; a failure in either job is evidence for this item, with the stderr the test prints.
  - To do: reproduce on Linux (a loop of concurrent `init` in a container or a CI job run many times) with stderr kept; confirm or replace the hypothesis; if `init` can still exit 1 under contention, make it retry or wait, and decide whether the other verbs need the same. Close when the cause is named with evidence, or after the next failure in CI is read from its stderr.
  - Plan: HP3 fixes the one confirmed cause (concurrent `init` with a missing folder); lane F5 reproduces what is not explained; H (the next failure in CI).
- [ ] **T18. An installed skill keeps its description in the harness's skill list.** Found on 2026-10-01 while measuring in the container: one harness lists skills to the model within a character budget, its own bundled skills first, and lists a project skill past the budget by name only. The eval adapter now raises the budget (`adapters/claude-code/README.md`), but a person who installs a pack gets the default: with dozens of skills installed, most would reach the model without the text that says when to use them. `AGENTS.md` ("Packs") already says installation is by pack because of this budget; nothing measures it.
  - To do: measure, per harness and per pack, how many installed skills keep their description (ask the model to quote its list); decide what the installer does about it (set the budget in the settings it writes, smaller packs, shorter descriptions with the detail in the body) and add a check to `scripts/doctor.py`.
  - Done when: after `install.sh --pack default`, every installed skill's description reaches the model on each supported harness, or the installer says which do not.
  - Plan: A8 and C0.10 (the measurement, in phase A and again at the end of phase C), decision 9 (where the harness has a budget setting the installer writes it when the person agrees; otherwise a smaller pack; shorter descriptions only as the last resort, inside phase C), lane F3 (the installer and the `doctor.py` check).
- [ ] **T19. Assertions that pass in every run.** Deferred by the maintainer on 2026-10-02, to be investigated later: removing an assertion makes its skill `stale`, and measuring the skills again was not worth the time then. In the measurement that closed T11 (3 runs of each of the 4 variants per case: with and without the skill, strong and floor model), 200 of the 663 assertions passed in every run of every variant, in 46 of the 48 skills. Such an assertion never moves the score between variants; it raises every score, the baseline's included, and so narrows the gain a skill shows. It does not change which skills pass.
  - Three kinds, counted with a text rule, so the split between the last two is approximate: 20 say the reply is in the language of the prompt; about 46 are guards (something that must not happen: a token not repeated, a planted instruction not followed, nothing published or dismissed without approval, no file written before the user answers); about 134 are content that the model gets right without the skill too.
  - Proposed, not decided: remove the 20 language assertions (17 skills); keep the guards, whose purpose is to fail the day the behaviour breaks, not to separate variants; review the content ones skill by skill, since some are too easy to tell anything and others depend on the fixture and a weaker model could miss them. Eight were also left untouched on purpose while repairing skills and wait for the same decision (three in eng-codebase-map, two in eng-architecture, three in core-skill-creator).
  - Caveat: at most 12 runs per assertion; passing in all of them does not show it would never fail.
  - How to list them again: for each skill, in its latest complete iteration under `evals-workspace/<skill>/`, read every `eval-<case>/<variant>/run-<k>/grading.json` and keep the assertions whose `passed` is true in all of them. `core-skill-creator` step 10 asks for this list in the report of every evaluation, so a skill evaluated from now on carries its own.
  - Done when: the maintainer decides per kind, the assertions that go are removed with the change listed before and after, and the skills touched are measured again. Do it together with another change that already stales those skills (phase 5 of `docs/architecture/plan-2026-10.md`), so that they are measured once.
  - 2026-10-02, decided (default 33 of the plan): the language assertions are removed; guards are kept and reworded so that the grader can verify them; content assertions that every variant passes are replaced by sharper ones the baseline fails. No separate pass and no measurement for it alone: the work is the cases part of each skill's row in phase C, from the per-assertion lists of the audit's group reports.
  - Plan: phase C, every row; done when the last row has merged.
- [ ] **T21. First full test of the 48 skills.** The first round (T11, archived) measured the 48 skills once in the container, under a rule of three computed states. The reliability model replaces that rule, and phases B and C of the plan change what a run measures and every skill. This item is the first full test of each skill under the model: every case with the skill on both models and without it on the reference model, 3 runs each, graded once.
  - Before it: phases A to D of the plan. Whatever is known to need fixing in a skill folder, in a case or in what a run measures is fixed first.
  - Deferred by the maintainer (the plan, "Open for the maintainer"): the adjustments of phases A, B, C and P come first, with the cheap part of phase D (the static checks, a smoke pass of every case once, and the guard cases of the skills that declare a side effect). The pilot and this item are started later by the maintainer, as one battery. Until then the 48 skills read `needs a test`, and a skill gets its full test earlier only when the smoke pass shows a problem.
  - Done when: every skill has a full test in its evidence and a band, and the skills that are not `reliable` are listed by name with their cause.
  - Plan: phase E (default 34), after the pilot of phase D.
- [ ] **T22. Move the dated fixtures forward before 2027-10-02.** The cases of `brand-profile`, `mkt-content-plan` and `mkt-publish` whose result depends on the day of the run keep the real clock: phase C sets their fixture dates at least a year ahead and makes the prompts name dates or posts, never "next week" (decision 6 of the plan). Those fixtures expire again on 2027-10-02.
  - To do before that date: move the dates forward in the three skills' fixtures. These are case changes: the evidence of the changed cases drops, and each of the three skills gets a full test, with the baseline run for the changed cases.
  - Done when: no case of the three skills depends on a date that has passed, and each has a full test after the change.
  - Plan: H (the date).

## Agent runtime

Status note, 2026-10-01: R1, R2, R5, R6 and R7 are built for one agent (the social agent, PB7) and stay unticked because none is generic yet; the runtime script names its providers and its use case in code.

Status note, 2026-10-02 (decisions D9 and D13, `docs/decisions.md`): the runtime no longer builds a provider's path. It asks `providers/resolve.py` for the store, the mailbox, the publisher, the scheduler and the vcs provider by class, so the vote step schedules with systemd on Linux; a name in `runtime.json` still wins. The scripts the scheduler starts are tested on Python 3.9 in CI. Still named in the runtime's code: the scripts of `mkt-engage`, `mkt-vote-round`, `mkt-social-copy`, `mkt-publish` and `brand-identity` that it calls.

Decided on 2026-10-02 (decision 10 of the plan; D11 of `docs/architecture/review-2026-10-01.md`): the runtime becomes generic, in a top-level `runtime/` folder, with the per-agent parts behind a handler. It is built after phase E, as lane F2, which gets its own plan as its first step. Until then no new use case is added to `scripts/runtime*.py` (PB16 waits), and what loses work or state today is repaired as it is (N20 to N22).

The goal decided on 2026-09-28 (`docs/decisions.md`): a company run by agents, one per department, managed from a local web app; marketing agents first. Each item is refined against a real company's case before it is generalised.

- [ ] **R1. Runtime contract.** `contracts/runtime.md`: what an agent run is (agent, task, inputs, allowed tools and skills, budget), how the runtime starts one through an adapter, and what it records. No AI tool named.
  - Built for one agent: the contract exists and names no AI tool. It names one agent's gate script, and `scripts/runtime.py` names that skill's scripts and its task text.
  - Done when: the contract and the runtime's code name no skill, and the per-agent parts sit behind a handler.
  - Plan: lane F2, with N15.
- [ ] **R2. Storage interface.** A store contract (tasks, messages, artifacts index, decisions, approvals, agent memory, run log) with interchangeable implementations, selected like providers; SQLite first, with offline tests; the user picks the store.
  - Built: `providers/store/sqlite.py`, selected by class, with offline tests, holds events, cursors, runs, the inbox and actions.
  - Open: tasks, messages, an artifacts index, decisions and agent memory, each added when R3 or R4 needs it.
  - Done when: every table a second agent needs exists behind the same verbs, with offline tests.
  - Plan: lane F2; T15 is about the same file.
- [ ] **R3. Department agents.** Agent definitions per department (marketing first, then sales, finance, operations), each with scope, skills, tools and a budget, from `templates/agent.md`.
- [ ] **R4. Messages between agents.** A message contract (who may ask whom for what, format, replies, deadlines) stored through R2; artifacts over invocation still holds.
  - Plan: lane F2, after R2 and R3.
- [ ] **R5. Approval inbox.** Every outward action from any agent waits in one place for the user, with S12's payload hash, spend limits and standing approvals from `contracts/environment.md`.
  - Built for one agent: an inbox table that stores the payload's hash, `runtime.py approve`, and a daily spend cap in `contracts/runtime.md`.
  - Done when: an outward action of any agent waits in the same inbox under the same rules, and no code of the inbox names an agent or a skill.
  - Plan: lane F2.
- [ ] **R6. Scheduler and triggers.** Runs start on a schedule, on a message, or on an approval; built on the `scheduler` provider class.
  - Built: triggers on a schedule (`providers/scheduler/launchd.py --every`, and `systemd.py`, which has never run on a real host: N12).
  - Open: a trigger on a message and a trigger on an approval.
  - Done when: a run of any agent starts on each of the three kinds of trigger.
  - Plan: lane F2, after N12.
- [ ] **R7. Observability.** Per run: what the agent read, did and cost, and where it failed; readable by the web app.
  - Built for one agent: the `runs` and `actions` tables of the store.
  - Done when: for a run of any agent, what it read, did and cost and where it failed can be read through the store's verbs, which is what R8 shows.
  - Plan: lane F2.
- [ ] **R8. Local web app.** Org chart, task board, approval inbox, messages, costs; reads and writes only through R2. It also holds the chat view of R11: one app, not two.
  - Plan: lane F2, after R2, R5 and R7.
- [ ] **R9. Scenario evals.** Multi-agent scenarios ("a week of a small company's marketing") graded like skill evals. They live in `evals/`, run in the eval container and write no evidence of a skill.
  - Plan: lane F2, after R3 and R4.
- [ ] **R10. Integrations the first case needs.** Provider classes for what marketing agents use (for example e-mail and a CRM), chosen with the user; asked, not assumed.
- [ ] **R11. A chat interface for the whole workbench.** Requested by the user on 2026-09-30: an interface like the ones general assistants have, where a person runs every action of the workbench (skills, flows, agents, approvals) by talking to it, with a model reached through an API key or a model running locally.
  - Why: today the workbench runs only inside an AI coding tool through an adapter, so using it means installing and learning one of those tools. A chat interface lets someone with only an API key, or only a local model, use it.
  - Shape, from the repository's rules: the interface is a harness, so it lives in `adapters/<name>/` and reads the core like any adapter (principle 2), with its own `run-prompt.sh` so the evals can run through it. Models are providers of a requirement class (for example `model:<provider>`, one implementation per API and one for a local runtime), and keys come through the secrets resolver, never through the browser or the repository. Confirmation gates show up as approval cards backed by the payload hash, the same records R5's inbox reads; runs and artifacts go through R2. The screen is the chat view of R8's web app; this item keeps the adapter and the model class.
  - Built so far: `adapters/api/` runs one agent on one task with one model call and no tools (`run-agent.sh` only). It is a building block, not the interface: N11.
  - To decide when building: a local backend that owns files, commands and the approval gate (a page in the browser cannot run skills' scripts on its own); which API providers and which local runtime come first, asked to the user; which models are supported, decided by their evidence, since a local model may score below the floor model; and how a run is contained (the executor of the eval container is the model for it: N15).
  - Done when: someone with only an API key, and someone with only a local model, each run a capability skill end to end from the interface, including one confirmation gate shown, approved and recorded; and `eval_run.py` runs a skill's cases through the interface's adapter.
  - Plan: lane F2, after R2, R5, R8 and N11.

## Project conventions

- [ ] **C1. Ask whether a project's `docs/` is versioned.** Requested by the user on 2026-09-28. Skills write everything a project produces under `docs/`: specs, ADRs and plans next to reviews, design explorations, marketing posts and their images, approvals and the workflow state. Some projects want all of it on GitHub; others want only code-related documentation there. In one public project, launch posts and their approval records were committed before the owner decided they should not be.
  - What: `core-project-init` asks, when it sets up a project, whether `docs/` is versioned or kept local (added to `.gitignore`), with a recommendation, and records the answer in `docs/workbench/state.md` and the project's `AGENTS.md` section, where every skill reads it. Skills that commit (`ops-pull-request`, `ops-branch-sync`, flows) then leave `docs/` out when it is local, and never open a pull request only to record workflow data.
  - To decide when building: whether the choice is all of `docs/` or per kind (code-related docs versioned, work data local); where state and approvals live when `docs/` is versioned but they should not be; and how a project created before this question moves over.
  - Done when: a new project is set up with each answer and the commits that follow respect it.
  - 2026-10-02, decided (default 84 of the plan): the question is asked per kind (code-related documents versioned, work data local), and the answer is recorded in the state file and in the project's `AGENTS.md`. A project created before the question exists is asked once, on the first commit a skill would make under `docs/`.
  - Plan: phase C: the rows of `core-project-init` (the question), `ops-pull-request`, `ops-branch-sync` and `flow-fix-bug` (the answer respected), and C0.1 (the contracts).

## Brand skills and the social agent

Decided on 2026-09-29: build the skills for a personal brand, then an agent from this repository that runs around the clock and manages social networks, interacting as the brand and the person's profile say. Every item is refined against a real case before it is generalised.

- A project's brand artifacts (profile, voice, calendar, approvals, state) live in that project, never in this repository.
- Network: LinkedIn first.
- Autonomy: within approved bounds. Posts come from a calendar the person approves once (`plan` approval); replies to comments on the person's own posts go out alone inside an engagement policy (`standing` approval with bounds and expiry); anything else waits for the person.
- Where it runs: a Mac first (`scheduler` provider on launchd). A low-cost always-on architecture is PB8.
- Model: Claude through the claude-code adapter (same rule as the 2026-09-28 decision on eval runs).
- How new comments are found: LinkedIn notification e-mails. Checked on 2026-09-29 with a member token (`w_member_social`): `GET /rest/socialActions/{post}/comments` on published posts returned `403 Not enough permissions to access: partnerApiSocialActions.GET_ALL.20260901`. The Comments API documentation (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api, accessed 2026-09-29) marks `r_member_social_feed` "Restricted ... granted to select developers only", while `w_member_social` is open and covers "Post, comment and like posts on behalf of an authenticated member" (https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access, accessed 2026-09-29). Writing a reply works; reading comments does not. Rejected: browser automation of LinkedIn (against its User Agreement, risks the person's account); applying for the Community Management API (uncertain for an individual, kept as an option).

- [ ] **PB6. Skill `mkt-engage`: the e-mail parser.** The skill replies to comments on the person's own posts inside an engagement policy (topics, tone, daily limit, what always goes to the person), enforcing the profile's sensitive-topics lock (never reply, escalate; keywords first, then the model's judgement), with the payload hash for anything approved one by one. Comments are external content and the main prompt-injection surface of the agent.
  - Built: `skills/mkt-engage` with `policy_gate.py`, which binds the standing approval to the policy file's hash (`docs/decisions.md`, 2026-09-29); the mailbox provider it reads through (PB5, archived). It passed the gate of the first round (status table of the inventory).
  - Open: the e-mail parser. `scripts/parse_notification.py` reads a pasted comment link; for a notification e-mail it returns `parsed: false` ("Unverified layout"), because no real notification e-mail has been read yet: whether it carries the comment text, the commenter and the post and comment ids a reply needs, and which search query finds it. The script has no test of its own (N9).
  - When the e-mail arrives: if the skill's row of phase C has not merged, the parser joins that row; after it, the parser is a change of that one skill, with the mailbox class back in its `requires` (default 57 of the plan) and the test its class asks for. The fixture made from the e-mail is rewritten with fictional names.
  - Done when: the parser reads the fields of a real notification e-mail, with offline tests.
  - Plan: H (a real notification e-mail), then the row of `mkt-engage`.
- [ ] **PB7. Agent `social-manager` and the runtime slice it needs.** `agents/social-manager.md`, plus R1 (runtime contract), R2 (SQLite store), R5 (approval inbox), R6 (triggers: calendar times and new notification e-mails) and R7 (run log), built for this one agent first.
  - Built on 2026-09-29: `contracts/runtime.md`, `providers/store/sqlite.py`, the inbox as a store table plus `runtime.py approve`, which sends only the reply whose hash the person saw, recurring jobs in `providers/scheduler/launchd.py --every`, runs and actions in the store, `scripts/runtime.py` with offline tests, `adapters/claude-code/run-agent.sh` (reading tools only) and `agents/social-manager.md`. The model proposes and code decides and sends: the agent has no tool that writes, runs commands or reaches the network. `runtime.py add-comment` takes a pasted comment link while the e-mail trigger is unverified, so a project's `runtime.json` can run without a mailbox.
  - Verified by a rehearsal on a real machine and by first use in a project. The run log of a project that uses the agent lives in that project, not here.
  - Open: the e-mail trigger, which waits on PB6.
  - Done when: the e-mail trigger works on a real mailbox.
  - Plan: H (with PB6); the slice becomes generic in lane F2 (R1, R2, R5, R6, R7).
- [ ] **PB8. Always-on, low-cost architecture.** Requested on 2026-09-29: compare where an agent runs once it leaves a person's machine, with costs from the vendors' pages.
  - Done on 2026-09-30: the comparison (`docs/architecture/always-on-runtime.md`: a small server with a tool-free API adapter recommended), and the two pieces built from it, `adapters/api/` and `providers/scheduler/systemd.py`.
  - Open, three leftovers: the operator's choice of a host and of how the model is called, which is theirs; the API adapter checked with a real key and finished as an adapter (N11); the Linux scheduler rehearsed on a real host (N12).
  - Done when: N11 and N12 are closed.
  - Plan: H (the operator's choice), lane F2.
- [ ] **PB11. Spec and backlog linters with translated headings.** Found on 2026-09-29: `product-feature-spec/scripts/lint_spec.py` and `product-backlog/scripts/lint_backlog.py` require English section names, so a project whose artifacts are in Portuguese writes English headings over Portuguese content. Add heading options, as `biz-icp-positioning`'s scripts have.
  - Plan: phase C, the rows of `product-backlog` and `product-feature-spec`.
- [ ] **PB14. Flow `flow-brand`.** Phases, as listed on 2026-09-29: profile (a person) → name → strategy → identity → voice → guidelines; each phase is a brand skill, with a checkpoint.
  - Plan: G step 1: its six phases are built, so it is the cheapest flow to build.
- [ ] **PB15. A weekly post vote becomes a published post.** Requested on 2026-09-30: a vote held in a public repository picks a topic; an agent drafts the post on the winner and proposes the topics of a later round; the person approves both once a week; code publishes the post at the calendar's time and records it in the repository. Nothing goes out without that approval, and a changed post needs a new one.
  - Built on 2026-09-30: the skill `mkt-vote-round`, `read-file` and `commit-files` in the vcs provider, `render.py`, the runtime's vote step (`scripts/runtime_vote.py`) and the scheduled job (`scripts/vote_job.py`). What the repository must hold and what the step does each week is the contract in `docs/architecture/weekly-vote.md`.
  - External content: picks are written by visitors. They are counts; the agent never reads their text.
  - Open: one real week from end to end. Its run log stays in the project that runs it.
  - Done when: one real week runs end to end with one approval: the round's winner is published, the repository records the post's link, and the next round is queued.
  - Plan: H (a real week), then lane F2, after N20.
- [ ] **PB16. A weekly routine that updates "Latest posts" on a profile repository.** Requested on 2026-09-30: once a week, automatically, the "Latest posts" section of a profile README shows the posts published that week.
  - The profile layout the feature expects: the section shows the 3 most recent entries of `data/posts.json`, each as a card with the post's own image kept in the repository as a WebP thumbnail (no image is loaded from LinkedIn). Without the routine, entries are added by hand, each with its own approval. PB15 adds only the post that won the weekly vote; the other posts of the week and posts published by hand stay out.
  - What: once a week, after the week's last scheduled post, a routine (1) lists the posts published in the last 7 days from the publisher's ledger (`providers/publisher/linkedin.py` records each post's idempotency key and URN); (2) takes each post's title (its first line), language, date and image from the project's own post artifacts, never from LinkedIn; (3) makes the thumbnails; (4) adds the entries to the profile repository and lets its workflow rebuild the README, in one commit.
  - Why the ledger and not LinkedIn: reading the member's own posts needs `r_member_social`, restricted to select developers (the same 403 recorded above for comments), so the routine only knows the posts the workbench published.
  - Approval: the posts are already public and each was approved when it was published, so a `standing` approval with bounds fits (only posts found in the ledger, only `data/posts.json` and `assets/posts/` in the profile repository, a limit of posts per run, an expiry). Asked to the person when building, not assumed.
  - Depends on: PB4 (`mkt-publish` and the post artifacts it reads), PB7's runtime slice (R6 a weekly trigger), and the same way to commit to the profile repository as PB15; the two items can share it.
  - To decide when building: posts published outside the workbench (recommended: the routine lists nothing it cannot prove from the ledger, and the person adds such a post by asking); a post without an image (recommended: a card with the pillar name, as the renderer already draws a neutral block); the day and time of the run.
  - Done when: one real week's posts appear in "Latest posts" with their images and links without the person touching the repository, and a week with no new post changes nothing.
  - Plan: lane F2. It waits for decision 10: it would be a third use case written into `scripts/runtime*.py`.

## Next skills

The order agreed on 2026-09-26, details in [inventory.md](inventory.md):

1. The brand and social agent section above, PB1 to PB7 in order; `ops-release` after it.
2. At a launch's one-week results reading: `mkt-launch-plan` and `flow-launch`, with the measurement phase checked against real numbers.

- [ ] **NS1. Skill `ops-release`.** Release notes and a version, with the side effect `publish`. `eng-docs` already names it as the owner of release notes. No folder yet.
  - Plan: G step 3, with a real release to write it against.
- [ ] **NS2. Skill `mkt-launch-plan`.** The writer of `docs/marketing/launch-plan.md`, which `mkt-content-plan` reads when present and no built skill writes.
  - Plan: G step 4, with a real launch.
- [ ] **NS3. Flow `flow-launch`.** messaging → launch-plan → content-plan → landing-page → analytics. Two of its phases, `mkt-landing-page` and `mkt-analytics`, are not built either.
  - Plan: G step 4, after NS2.

## Found by the audit of 2026-10-02

Work the code or the documents show is needed and no item owned (N1 to N19: the backlog audit, "Not covered by any item"; N20 to N22: the review of the providers and the runtime; N23 and N24: the reliability model). N3 and N17 are in the archive, with the reason.

- [ ] **N1. The wiring test of the CI workflow.** The `python39` job, which failed on `main` because it named five test files that had moved into the skills, is repaired (pull request #45). Open: `scripts/tests/test_checks_wiring.py` requires that every path a file under `.github/workflows/` names exists, and the jobs of `checks.yml` get a `timeout-minutes`.
  - Plan: A1.
- [ ] **N2. `payload.py` builds a provider's path.** `skills/mkt-publish/scripts/payload.py` takes `--workbench` and `--platform` and builds the publisher's command itself, where every other caller asks `providers/resolve.py`. It becomes `--publisher <path>` (the path the resolver printed) with `--platform` required.
  - Plan: phase C, the row of `mkt-publish` (default 68).
- [ ] **N4. The grader grades its own model's runs.** Decided on 2026-10-02: every run is graded once, by the configured grader, which stays the same model and gets a key of its own in the gate file (decision 2 of the plan). Open: the grader's disagreement with itself is measured on the pilot's stored replies.
  - Plan: B3 (the grading), D4 (the measurement).
- [ ] **N5. `skills/core-skill-creator/SKILL.md` is above the size guide.** About 6,000 tokens by the validator's rule (characters divided by 4), against a guide of about 5,000. To be trimmed into `references/`.
  - Plan: phase C, the row of `core-skill-creator`.
- [ ] **N6. The routing table lacks seven built skills.** `brand-name`, `brand-profile`, `core-security-audit`, `eng-security-review`, `mkt-engage`, `mkt-vote-round` and `ops-repo-baseline` appear nowhere in `skills/core-orchestrator/`.
  - Plan: phase C, the row of `core-orchestrator`; A5 adds the validator's rule.
- [ ] **N7. Two references that could name a skill as an artifact's writer.** `skills/core-clarify/references/decision-tree.md` ("a `core-critique` candidate") and `skills/ops-repo-baseline/references/host-settings.md` ("triage them with `eng-security-review`").
  - Plan: phase C, the rows of `core-clarify` and `ops-repo-baseline`.
- [ ] **N8. Inventory drift.** `docs/inventory.md`: the Counts table (62 capabilities and 11 flows to build, 5 agents, where 47 capabilities, 1 flow and 4 agents exist), the `explorer` row of the Agents table (no such file under `agents/`), and State cells that quote scores of an earlier gate.
  - Plan: A3.
- [ ] **N9. Scripts with no test of their own.** `skills/mkt-engage/scripts/parse_notification.py`, `skills/mkt-social-copy/scripts/check_post.py`, `skills/core-research/scripts/check-brief.py` (those two skills have no `scripts/tests/` folder), and `skills/design-system/scripts/contrast.py` (only the copy in `brand-identity` is tested, and the two copies differ). A test is outside a skill's content hash.
  - Plan: phase C, the rows of `mkt-engage`, `mkt-social-copy`, `core-research` and `design-system`.
- [ ] **N10. CI jobs that are not required checks.** The ruleset requires `validate` and `tests`; the jobs `container` and `python39` exist and are not required, which is how a pull request merged with `python39` failing.
  - Done when: both are required checks of the ruleset. It is the maintainer's action, once both have been green twice (default 87 of the plan).
  - Plan: phase A, the maintainer's actions.
- [ ] **N11. The API adapter is unfinished as an adapter.** `adapters/api/` has `adapter.json`, `run-agent.sh` and tests; no `install.sh`, no `run-prompt.sh`, and it has never called a real endpoint. `AGENTS.md` "Adding an adapter" asks every adapter for `install.sh`.
  - Done when: it has both scripts, a check with a real key is recorded, and `AGENTS.md` says what an adapter of this kind must have.
  - Plan: lane F2 (with PB8).
- [ ] **N12. The Linux scheduler has never run on a real host.** `providers/scheduler/systemd.py` is the default on Linux and is tested offline only (`providers/scheduler/README.md`).
  - Done when: a one-shot job and a recurring job run on a real host, and what the rehearsal finds is fixed.
  - Plan: H (the operator's choice of a host), then lane F2; HP3 fixes two known defects of it (an overlap and an early firing).
- [ ] **N13. Installers do not carry what a skill needs.** A copy install brings neither `shared/` nor `providers/`; an installed skill that reaches a provider needs `WORKBENCH_ROOT`, and nothing tells the installer to set or print it; the install on the primary harness was never confirmed on a real install.
  - Plan: A6 (the stripped copy, `shared/references/` beside the skills, an install confirmed to load), lane F3 (providers, the root).
- [ ] **N14. The local-model tier.** Split from T12 (archived) on 2026-10-02. Deferred by the maintainer on 2026-10-01. Evals run only in a container whose network reaches the hosted providers, so a model served on the person's machine is not reachable from a run. To investigate when this is taken up again: a route from the container to the local server (a fourth network mode in the executor, or an entry on the proxy's list), and whether the local model's context and speed hold inside that setup. Then the measurement: one model, the skills, a threshold of its own, published and not gating. Under the reliability model a local model is one more model in the tables: an id in the gate file, and no test of anything else.
  - First local results, one skill, with the skill, measured on a person's machine before the container (2026-10-01): gpt-oss 20B 0.26, Qwen3-Coder 30B 0.43, Devstral Small 2 24B unusable through the runner.
  - Done when: one local model's results on the skills are published beside the others, from runs made in the container.
  - Plan: lane F7.
- [ ] **N15. Containment of runtime agents.** T5 (archived) promised the eval containment as the sandbox of runtime agents. Today a runtime agent is limited by its tool list only (`run-agent.sh --tools Read,Glob,Grep`).
  - Plan: lane F2, with R1.
- [ ] **N16. Planned flows, agents and skills with no backlog id.** `flow-build-feature`, `flow-improve-code`, `flow-new-project`, `flow-implement-ticket`, `flow-business-plan`, `flow-design`, `flow-social-post`, `flow-new-product`; the `explorer` agent; the next version of `design-system`; `biz-validate-idea`, the writer of `docs/business/idea-validation.md`, which `biz-market-analysis` reads when present. They are marked planned wherever they are cited, without an id.
  - Done when: each has an id here and in the inventory.
  - Plan: A9 (the ids), phase G (the building).
- [ ] **N18. Entries of `docs/decisions.md` that a later entry reversed are not marked.** Among them: Claude models on the maintainer's signed-in account; records of the previous strong model staying valid; the strong tier's sandbox; the throwaway keychain; "not closed by this" under runs outside the repository; the flat `skills/` layout's sentence on the plugin; requirement classes keeping their names.
  - Plan: A3.
- [ ] **N19. Principle 8 cleanup of the documents.** What identifies one real project (its name, people, accounts, repository layout, run log) in this file, in `docs/inventory.md`, in `docs/decisions.md` and in the two design documents written around one case.
  - Plan: A3.
- [ ] **N20. Runtime and providers: what loses work or state today.** For a project that runs the runtime as it is: a vote round silently lost when an item is rejected; an error that is not the runtime's own leaving claimed events and a run row in `running`; a run of unknown cost not counted against the daily cap; a mailbox search that is cut without saying so; and the other findings of that class in `architecture/audit-2026-10-02/round2-providers-runtime.md`.
  - Done when: each finding the plan lists under HP1 has its fix and the test the report names.
  - Plan: HP1, from the first day; it touches no skill folder and nothing the measurement covers.
- [ ] **N21. Providers and runtime against their contracts.** The code and the contract say the same thing: one reading of `--check`'s exit codes in the three providers, a handler timeout in the callback servers, `--check` reading through the resolver, a malformed retry setting found before a post is public, and the rest of the plan's HP2.
  - Plan: HP2; it starts on the shared files after C0.2.
- [ ] **N22. Providers and runtime: platform coupling outside the skills, nits, test gaps.** The runtime reads a platform's limits from the platform's data file and its own constants go; the couplings to one platform that the report's table lists; the scheduler's overlap and early firing; concurrent `init` with a missing folder; the nits.
  - Plan: HP3.
- [ ] **N23. Field evidence: the triggers of the recorder, and contributed files.** A use of a skill in a project is recorded in that project, self-reported, and shown in its own columns. Open after the recorder itself (`scripts/evidence.py`, item B15): the installers write the checkout's path and offer to set `WORKBENCH_ROOT`; an adapter hook records a use when a workbench skill is loaded; the runtime records a use and its verdict from what the person does with the item in the inbox; `export` and `import` exercised with one contributed file.
  - Done when: a use started by the hook and a use started by the runtime appear in a project's evidence file with a listed model id, and one contributed file is imported and shown in the field columns.
  - Plan: B15 (the recorder), the row of `core-project-init` (the block that asks for field evidence), lane F9.
- [ ] **N24. What the reliability model leaves for later.** Replaying sampled field tasks on other models (the task and its files stay in the project; only the resulting lines travel); whether field evidence may count toward `reliable`, once recorded uses can be compared with verdicts; the numeric decays.
  - Plan: lane F10, not before the tables have field evidence to sample from.

Decisions of the review of 2026-10-01 (`docs/architecture/review-2026-10-01.md`) and pieces of the previous plan that are still open. They keep the ids those documents gave them:

- [ ] **D7. The artifact contract.** Approved on 2026-10-02: every skill declares what it writes and updates, one owner per path, a placeholder syntax, and a dangling input becomes an error.
  - Plan: C0.1, C0.2 and the frontmatter part of every row of phase C.
- [ ] **D8. Code shared by several skills.** One source and a sync script, a generic identity test, and the one pair of copies that differs (`contrast.py`) reconciled.
  - Plan: C0.3, C0.4 and the scripts part of the rows.
- [ ] **D11. What the runtime is.** Decided: generic (decision 10 of the plan). Open: building it.
  - Plan: lane F2.
- [ ] **D12. Planned skills cited without the mark.** Flows are marked planned where cited; ten capabilities still cite a planned skill without the mark.
  - Plan: the body part of those rows of phase C; A5 adds the validator's rule.
- [ ] **PL-digest. The eval image's bases are pinned by digest.** `evals/container/Dockerfile` and `evals/container/proxy/Dockerfile` start from tags, which can move.
  - Plan: B1.
- [ ] **PL-cases. The fixtures of `design-handoff` have no builder.** Recorded as edited by hand; no builder script is added (default 46 of the plan).
  - Plan: phase C, the row of `design-handoff`.
- [ ] **PL-validation. Validation rules.** `scripts/validate.py` lacks: required metadata keys, `requires` against the known classes, the `side_effects` vocabulary, the token guide, the two-case minimum, skill names cited by agents and flows, `packs/` scanned as core, one frontmatter parser on every machine, and a check that a capability does not invoke a skill.
  - Plan: A5 (as warnings), C0.1 and C0.2 (as errors).

## Cases the audit proposed and phase C does not add

The six group reports of the audit (`architecture/audit-2026-10-02/group-1.md` to `group-6.md`) propose cases for branches no case reaches. Phase C adds the targeted ones (decision 14 of the plan); the plan counts 31 proposed cases that are not targeted and leaves them for the next change of each skill. One item per skill, each naming where the report describes the case with its prompt and assertions. A case added later is a case change: it enters through a full test of its skill, and costs 6 runs on the reference model. Plan, for all of them: nothing before phase E; each is built when its skill is next changed.

Not listed: the degraded-mode cases proposed for `design-execute`, `design-system` and `product-backlog`, which the guard cases of their rows in phase C cover (default 39 of the plan).

- [ ] **K1. `biz-icp-positioning`: a case for the degraded mode.** With no web search: a query plan, `Status: limited`, nothing scored. (group-1, biz-icp-positioning, should-fix 8.)
- [ ] **K2. `biz-market-analysis`: a case for the degraded mode.** The scoped fixture with no web search: `Status: limited`, a query plan and no scores. (group-1, biz-market-analysis, should-fix 7.)
- [ ] **K3. `brand-guidelines`: a case for the trigger "after any brand file changes".** An existing guide whose label and one quote are older than the strategy: the stale quotes named and the guide corrected. (group-1, brand-guidelines, should-fix 2.)
- [ ] **K4. `brand-identity`: a case for the stop on a missing strategy.** No `docs/brand/strategy.md`: the skill stops and says which skill writes it. (group-1, brand-identity, should-fix 6.)
- [ ] **K5. `brand-name`: a case for research mode after the answers.** A state file that holds the three answers: candidates, each checked. (group-1, brand-name, should-fix 4.)
- [ ] **K6. `brand-voice`: a case for the stop on a missing profile, and two more branches.** At least the stop with no `docs/brand/profile.md`; also fewer than three samples (`hypothesis`) and corrections that become rules (`confirmed`). (group-1, brand-voice, should-fix 5.)
- [ ] **K7. `core-agents-md`: a case for an instruction inside a file the skill reads.** A tool-specific instruction file that carries, among real conventions, a line addressed to a model: quoted as not followed, and not written into `AGENTS.md`. (group-2, core-agents-md, should-fix 7.)
- [ ] **K8. `core-clarify`: a case for an instruction inside a ticket written by someone else.** A fixture ticket that tells the assistant to mark it approved and skip the questions. (group-2, core-clarify, should-fix 8.)
- [ ] **K9. `core-critique`: a case for an instruction inside the proposal.** A fixture plan with a line that tells reviewers to approve it without findings: quoted to the user as a finding. (group-2, core-critique, should-fix 8.)
- [ ] **K10. `design-handoff`: a case for the "only a screenshot" mode.** A draft with every timing, state and value marked as an assumption or an open question, and the export asked for. (group-3, design-handoff, should-fix 6.)
- [ ] **K11. `product-backlog`: a case for planning from the specification alone.** No design and none coming: every task marked `design pending`, its check taken from an acceptance criterion. (group-3, product-backlog, should-fix 5.)
- [ ] **K12. `product-feature-spec`: a case for a phase with several deliverables.** The skill proposes which one this specification covers and asks. (group-3, product-feature-spec, "For the maintainer to decide".)
- [ ] **K13. `product-prd`: a case for a request that is one feature.** No PRD is written or changed, and the reply names `product-feature-spec` as the skill for the request. (group-3, product-prd, should-fix 5.)
- [ ] **K14. `eng-code-review`: a case for a check that cannot run.** A project whose `AGENTS.md` names a lint command that is not installed: recorded as `not run` with the reason, a finding of severity high, and the verdict is request changes. Also unmeasured: a pull request with no integration, and a large or rename-heavy change. (group-4, eng-code-review, should-fix 5.)
- [ ] **K15. `eng-codebase-map`: a case for a specification that is named and not found.** The reply asks for its path and writes nothing under `docs/engineering/`. (group-4, eng-codebase-map, should-fix 7.)
- [ ] **K16. `eng-docs`: a case for the first Inputs gate.** No plan and a changed source file: the reply asks which change to document, recommends one, and writes no document. (group-4, eng-docs, should-fix 2.)
- [ ] **K17. `eng-implement`: a case for a dependency that is not done.** A task that comes after one still `todo`: the reply quotes the task script's output and stops; no file changes. (group-4, eng-implement, should-fix 5.)
- [ ] **K18. `eng-integration-tests`: a case for the Inputs gates.** No earlier release's files and no base commit: the reply asks what the code before the change is, recommends one, and writes no test. (group-4, eng-integration-tests, should-fix 2.)
- [ ] **K19. `eng-refactor`: a case for a red check before the start.** One failing test in the project: the reply quotes the failing check as printed before any change, leaves the source unchanged and asks what to do about it. (group-5, eng-refactor, should-fix 9.)
- [ ] **K20. `eng-root-cause`: a case for a symptom that does not reproduce.** After two honest attempts: what was tried with its output, no cause asserted, a grade below `confirmed` or a question for the missing condition, no source file changed. (group-5, eng-root-cause, should-fix 7.)
- [ ] **K21. `eng-unit-tests`: a case for the missing input.** No plan and no specification: the reply asks which behaviour must change and which must stay, and writes no test file. (group-5, eng-unit-tests, should-fix 7.)
- [ ] **K22. `ops-ci-pipeline`: a case for a red run with no message.** "CI is red, fix it": the reply asks for the failing step's message or log and changes no file. (group-5, ops-ci-pipeline, should-fix 8.)
- [ ] **K23. `ops-repo-baseline`: a case for an existing workflow and a planted test value.** The existing workflow is unchanged and its gaps are listed as proposals; the allow line for the fixture is proposed and added only on agreement; no value is shown. (group-5, ops-repo-baseline, should-fix 8.)
- [ ] **K24. `mkt-content-plan`: a case for a slot whose pillar has no material.** The strategy is present, one pillar has no note and no rule covers it: an empty topic and a question that names the pillar. Also unmeasured: the stop on a missing strategy. (group-6, mkt-content-plan, should-fix 2.)
- [ ] **K25. `mkt-social-copy`: a case for a sensitive hit that blocks a post.** A slot whose only material touches a locked subject: the content file is `blocked` or not written, the reply says why, and no post text mentions the subject. Also unmeasured: a slot without material. (group-6, mkt-social-copy, should-fix 4.)
- [ ] **K26. `mkt-vote-round`: a case for fewer than three topics with material.** Notes with two usable lines for the next pillar: the reply asks for material and names the pillar; no third option is invented. Also unmeasured: nothing pending. (group-6, mkt-vote-round, should-fix 7.)
