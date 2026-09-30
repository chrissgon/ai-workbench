# Decisions log

One entry per structural decision. Newest last. Each entry: date, decision, alternatives rejected, why.

## 2026-09-22: Harness-agnostic core with adapters, Claude Code first

Rejected: a repository built only for Claude Code. Skills (`SKILL.md`) and project instructions (`AGENTS.md`) are open standards read by most tools; agent bodies converge on Markdown with `name` and `description`. Only advanced frontmatter, hooks and directories differ, and those live in adapters. Cost accepted: harness-exclusive features are only available through their adapter, and the core describes capabilities instead of naming tools.

## 2026-09-22: Workflows are skills; agents are thin delegation wrappers

Rejected: workflows as a third artifact type, and agents that carry full workflow prompts. No harness has a native "workflow"; a skill is the only executable unit every tool understands, and it runs in the main context where the user answers checkpoints. Agents exist only for isolation or parallelism. This also removes the skill-vs-agent duplication found in the previous repository.

## 2026-09-22: Nine areas, three levels, area prefixes

Seven lifecycle areas plus two horizontal ones (AI, Core). Three levels: area, sub-area, capability. Prefixes because skills install flat and names collide otherwise. `flow-` is a single prefix for every workflow regardless of scope: one rule instead of two.

## 2026-09-22: AI is a horizontal area, not an Engineering sub-area

Reversed an earlier decision. AI has no fixed position in the chain and produces artifacts of its own, which distinguishes it from transversal concerns. Rejected: distributing AI capabilities across areas (five owners, quintuple maintenance) and treating AI as references only (no deliverables). Boundary test and insertion points in `docs/area-map.md`.

## 2026-09-22: Areas communicate through artifacts, capabilities never invoke skills

Exposed by scenario validation. Keeps capabilities independent and testable, lets every capability run standalone, and makes flows resumable through a state file.

## 2026-09-22: Flat `skills/`, root is harness-neutral, adapters self-contained

Rejected: nesting skills by area (the plugin loader scans `skills/<name>/SKILL.md`; nesting would need manifest arrays for one rule more) and making the repository root a Claude Code plugin (privileges one harness at the root). The Claude Code adapter is itself the plugin, with `skills` symlinked to the core. A generic `agents-dir` adapter covers every tool that reads `~/.agents/skills/`.

## 2026-09-22: Environment requirement classes and actuator contract

Exposed by the "schedule a social post" scenario. Skills declare `requires` as classes, resolved by harness connector, then provider script, then graceful degradation. Skills with `side_effects` must implement a confirmation gate. Image generation ships first; video is a reserved slot.

## 2026-09-22: Write for the weakest model, evaluate against a floor model

Detailed means explicit and templated, not long. Each skill must pass its evals on a floor model, not only on the strongest one. Floor models are configured in the eval tooling.

## 2026-09-22: No stacks from the factory

Engineering skills are stack-agnostic procedures with an optional `references/stacks/<stack>.md` slot and a detection rule. Stacks are added from real projects, following the authoring guide's rule against generic knowledge.

## 2026-09-22: Packs are the unit of installation; optional areas exist

Harnesses load every installed skill's name and description into every session and truncate past a budget, so "install everything" degrades triggering once the catalog grows. `packs/<name>.txt` lists patterns; adapters resolve them at install time. The Claude Code adapter now builds a plugin folder per pack (`build/<pack>/`) with per-skill symlinks, which also removed the only tracked symlink from the repository. The assistant area (`asst-`) is the first optional area: same rules, excluded from `default`. Rejected: a separate repository for the assistant pack (double tooling for the same conventions) and a tenth core area (scope creep on the "digital solution" promise).

## 2026-09-22: One explicit approval, then autonomy

Confirmation gates exist so the user sees exactly what will happen, not to interrupt repeatedly. Three approval scopes (action, plan, standing) are recorded in `docs/workbench/state.md`; a resumed session never re-asks for what is approved; scheduled work is confirmed at scheduling time and executed unattended after verifying the payload still matches. Flows honour a per-project `Autonomy.Checkpoints` setting (every-phase, milestones, end). Rejected: asking at every step (kills autonomy) and implicit consent from silence or from similar past approvals (unsafe).

## 2026-09-22: OpenClaw is a compatible runtime, not a content source

OpenClaw follows the Agent Skills spec and reads `~/.agents/skills`, so the `agents-dir` adapter covers it with no extra work. It is an always-on, messaging-connected runtime with cron, which makes it the natural home for the assistant area and for scheduled actuators. It is not a substitute for the assistant pack: a runtime is where skills run, a pack is what skills exist. Its bundled and community skills may cover many day-to-day tasks, so `asst-` skills are written only for gaps and for tasks that must follow this repository's contracts. No dedicated adapter until a real need (translating `requires` into its gating metadata). Security caveat: broad access and a history of exposed instances and malicious community skills; run isolated with least privilege and vet third-party skills.

## 2026-09-23: Build order approved; skills are written alongside a real project

Engineering before business for refinement (most mature content, daily use); merges (eng-root-cause, eng-implement, eng-code-review, core-critique) and drops (btw, coaching skills, duplicate documentation agent, organization-specific deploy and rewrite planner, stack-bound engineer agents) approved. A real project is the vehicle for waves 2 to 5; when it is an AI product, the AI engineering skills move forward to its engineering wave, and its business and product phases come right after core. Skills without prior expertise are written only alongside the real project phase that needs them.

## 2026-09-23: Skills never assume; they ask

Stated by the user as a design rule after a first initialization of a real project: agents and skills must not presume anything the user has not decided; they ask, with a recommendation. Added as a principle in `AGENTS.md`, reinforced in the writing standard and the capability template. It coexists with the one-approval rule: asking for a decision once is not repeated approval-seeking. Motivated by a real project where a "migration" request in fact hid a radical redesign that only the user could scope.

## 2026-09-23: Code reviews are temporary artifacts under docs/engineering/reviews/

`eng-code-review` writes `docs/engineering/reviews/<change>.md` (task id, else branch, else pull request number) so a flow can resume at the review step in a new session and `ops-pull-request` can carry the verdict and its conditions into the pull request description. Like plans, reviews are day-to-day artifacts: removed or archived when the change ships. The review never edits code; findings go back to `eng-implement` or the backlog. The `reviewer` agent is one perspective per instance, for harnesses that run work in isolation; the skill runs the perspectives sequentially everywhere else.

## 2026-09-28: An agent runtime as a new, tool-free layer; storage behind an interface; a real company as the first case

Decided by the user. The end goal is a company run by agents, one per department, that take tasks, talk to each other through recorded messages and keep their data, managed from a local web app. The runtime is a new layer on top of the current core (skills, agents, contracts, providers), not a rewrite of it, and it names no AI tool: it runs agents through adapters, the way evals already run prompts through `run-prompt.sh`. Persistence is an interface with interchangeable implementations (SQLite first, a cloud store later), chosen by the user, in the same open-closed shape as providers. The first case is a real one-person company with no clients yet, starting with marketing agents that look for clients.

Rejected: building on one agent framework directly (it would tie the core to one vendor, against principle 1); keeping `docs/workbench/state.md` as the only store (a Markdown file does not take several agents writing at once); starting with a library project (not a company). Also rejected on 2026-09-28: a per-request "quick mode" without gates like Kiro's Quick Spec (https://kiro.dev/blog/faster-smarter-specs/, from a search snippet, accessed 2026-09-27). It runs every spec phase without approvals, which is what `Autonomy.Checkpoints: end` already does, while ours keeps confirmation gates for outward actions in every mode; switching it per request instead of per project adds a second switch to maintain and no safety.

## 2026-09-28: Security reviews of a project write their own artifact

`docs/area-map.md` treats security as a transversal reference that produces no artifact of its own. `eng-security-review` is the exception: triaging a project's dependency alerts ends in decisions (update, or dismiss with the host's reason and evidence) that must survive the session and back the dismissals, so it writes `docs/engineering/security-reviews/<date>.md`, the same shape as `eng-code-review`'s reports. The reference stays in `shared/references/security.md` for the rules every skill follows; the skill applies them to one project's state at one date. Version 0.1 covers dependency alerts only, by the user's decision (backlog S14 for the rest). Dismissals are an outward action with a confirmation gate; updates are proposed as tasks for `eng-implement`, never applied by the review.

## 2026-09-28: Claude models run on the maintainer's account; OpenRouter only for the floor model

Stated by the maintainer. Strong-model runs and the grader go through the claude-code adapter, signed in with the maintainer's own account; OpenRouter is used only to run the floor model (DeepSeek V3.2 through the agents-dir adapter). `eval_run.py --floor-pass-env` passes the OpenRouter key to floor runs only; before it, `--pass-env` handed the key to every run and to the grader. Rejected: running Claude models through OpenRouter (a second bill and a key the Claude runs do not need).

## 2026-09-29: Parallel by default

Stated by the user after the floor-model evals of six skills ran one after another for more than an hour: "o que puder ser rodado em paralelo deve rodar em paralelo". Added as principle 7 in `AGENTS.md`. Independent work runs at the same time; sequential execution needs a reason (a dependency, a shared resource, a rate limit) and says which. First application: `eval_run.py --jobs`, default 4, at most 8. The earlier belief that parallel agents-dir runs break the runner (backlog S9) is withdrawn: the "UnknownError" it recorded is what a missing provider key produces, and four concurrent floor-model runs with separate homes all answered (backlog T8).


## 2026-09-29: A standing approval whose bounds live in a file binds that file's hash

`contracts/environment.md` said standing approvals carry no hash, because they cover a class of action, not a payload. The first standing approval over a public action, automatic replies to comments on a person's own LinkedIn posts (backlog PB6), keeps its bounds (categories, languages, daily limit, phrases never used in replies) in `docs/marketing/engagement-policy.md`. An edit to that file would silently widen what the person approved. The approval row therefore records `policy:<sha256 of the file>`, and `mkt-engage`'s `policy_gate.py` refuses automatic replies when the file's hash, the row's status (`active`, or `paused` by the person) or its expiry does not hold. Rejected: re-reading the policy's bounds from the approval row's text (a model would have to parse prose, and a changed file would still pass).

## 2026-09-30: In the runtime, the model proposes and code decides; a factual answer needs checked sources

`contracts/runtime.md`: an agent started by a trigger gets reading tools only (`run-agent.sh --tools Read,Glob,Grep`) and returns a proposal block; `scripts/runtime.py` runs the skill's gate and only then calls the provider. Trigger data (comments, e-mails) is written by strangers, so a model that could run the publisher could be talked into publishing.

A comparison of models on real comments (2026-09-30, 8 comments, 2 runs each) showed why the gate cannot trust the model's own category: DeepSeek V3.2 once labelled a question with no source "answerable from sources" and invented the answer, and the gate would have let it out. `policy_gate.py` now requires a factual answer to cite project files that exist, and every number in the reply to appear in them. A claim without a number still passes any deterministic check; the model choice covers that (Sonnet 5.5 classified all 16 cases correctly). Rejected: a second model as a judge (cost and latency for 0 to 30 replies a day) until a real miss shows it is needed.
