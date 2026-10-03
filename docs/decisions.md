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

**Reversed in part the same day** (entry "Packs are the unit of installation; optional areas exist"): the Claude Code adapter is no longer itself the plugin with `skills` symlinked to the core; it builds one plugin folder per pack. What stands: `skills/` is flat, the root privileges no harness, each adapter is self-contained.

Rejected: nesting skills by area (the plugin loader scans `skills/<name>/SKILL.md`; nesting would need manifest arrays for one rule more) and making the repository root a Claude Code plugin (privileges one harness at the root). The Claude Code adapter is itself the plugin, with `skills` symlinked to the core. A generic `agents-dir` adapter covers every tool that reads `~/.agents/skills/`.

## 2026-09-22: Environment requirement classes and actuator contract

Exposed by the "schedule a social post" scenario. Skills declare `requires` as classes, resolved by harness connector, then provider script, then graceful degradation. Skills with `side_effects` must implement a confirmation gate. Image generation ships first; video is a reserved slot.

## 2026-09-22: Write for the weakest model, evaluate against a floor model

**Reversed in part on 2026-10-02** (entry of 2026-10-02, "The reliability model, simplified after its independent review"): a skill no longer has to pass on the floor model. The gate is evaluated on the reference model; the floor model's results are recorded and shown, and no rule reads them. What stands: skills are written for the weakest model that will run them, and every skill is run on a floor model.

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

## 2026-09-28: An agent runtime as a new, tool-free layer; storage behind an interface; a real company's case first

Decided by the user. The end goal is a company run by agents, one per department, that take tasks, talk to each other through recorded messages and keep their data, managed from a local web app. The runtime is a new layer on top of the current core (skills, agents, contracts, providers), not a rewrite of it, and it names no AI tool: it runs agents through adapters, the way evals already run prompts through `run-prompt.sh`. Persistence is an interface with interchangeable implementations (SQLite first, a cloud store later), chosen by the user, in the same open-closed shape as providers. It is built against a real company's case, marketing agents first; what describes that company, its decisions and its data live in its own project, not here.

Rejected: building on one agent framework directly (it would tie the core to one vendor, against principle 1); keeping `docs/workbench/state.md` as the only store (a Markdown file does not take several agents writing at once); starting with a library project (not a company). Also rejected on 2026-09-28: a per-request "quick mode" without gates like Kiro's Quick Spec (https://kiro.dev/blog/faster-smarter-specs/, from a search snippet, accessed 2026-09-27). It runs every spec phase without approvals, which is what `Autonomy.Checkpoints: end` already does, while ours keeps confirmation gates for outward actions in every mode; switching it per request instead of per project adds a second switch to maintain and no safety.

## 2026-09-28: Security reviews of a project write their own artifact

`docs/area-map.md` treats security as a transversal reference that produces no artifact of its own. `eng-security-review` is the exception: triaging a project's dependency alerts ends in decisions (update, or dismiss with the host's reason and evidence) that must survive the session and back the dismissals, so it writes `docs/engineering/security-reviews/<date>.md`, the same shape as `eng-code-review`'s reports. The reference stays in `shared/references/security.md` for the rules every skill follows; the skill applies them to one project's state at one date. Version 0.1 covers dependency alerts only, by the user's decision (backlog S14 for the rest). Dismissals are an outward action with a confirmation gate; updates are proposed as tasks for `eng-implement`, never applied by the review.

## 2026-09-28: Claude models run on the maintainer's account; OpenRouter only for the floor model

**Reversed in part on 2026-10-01** (entries "The floor model is DeepSeek V4.1 Flash", "Evals run only in a container" and "The eval container, as built"): the strong runner is no longer the CLI signed in on the maintainer's machine; in the container it authenticates with a long-lived token from the secret store, passed by variable name; the floor model named here was replaced; and the options are read from `evals/eval-gate.json`, not passed by hand. What stands: the strong model and the grader run on the maintainer's account, and the floor provider's key reaches floor runs only.

Stated by the maintainer. Strong-model runs and the grader go through the claude-code adapter, signed in with the maintainer's own account; OpenRouter is used only to run the floor model (DeepSeek V3.2 through the agents-dir adapter). `eval_run.py --floor-pass-env` passes the OpenRouter key to floor runs only; before it, `--pass-env` handed the key to every run and to the grader. Rejected: running Claude models through OpenRouter (a second bill and a key the Claude runs do not need).

## 2026-09-29: Parallel by default

Stated by the user after the floor-model evals of six skills ran one after another for more than an hour: "o que puder ser rodado em paralelo deve rodar em paralelo". Added as principle 7 in `AGENTS.md`. Independent work runs at the same time; sequential execution needs a reason (a dependency, a shared resource, a rate limit) and says which. First application: `eval_run.py --jobs`, default 4, at most 8. The earlier belief that parallel agents-dir runs break the runner (backlog S9) is withdrawn: the "UnknownError" it recorded is what a missing provider key produces, and four concurrent floor-model runs with separate homes all answered (backlog T8).


## 2026-09-29: A standing approval whose bounds live in a file binds that file's hash

`contracts/environment.md` said standing approvals carry no hash, because they cover a class of action, not a payload. The first standing approval over a public action, automatic replies to comments on a person's own LinkedIn posts (backlog PB6), keeps its bounds (categories, languages, daily limit, phrases never used in replies) in `docs/marketing/engagement-policy.md`. An edit to that file would silently widen what the person approved. The approval row therefore records `policy:<sha256 of the file>`, and `mkt-engage`'s `policy_gate.py` refuses automatic replies when the file's hash, the row's status (`active`, or `paused` by the person) or its expiry does not hold. Rejected: re-reading the policy's bounds from the approval row's text (a model would have to parse prose, and a changed file would still pass).

## 2026-09-30: In the runtime, the model proposes and code decides; a factual answer needs checked sources

`contracts/runtime.md`: an agent started by a trigger gets reading tools only (`run-agent.sh --tools Read,Glob,Grep`) and returns a proposal block; `scripts/runtime.py` runs the skill's gate and only then calls the provider. Trigger data (comments, e-mails) is written by strangers, so a model that could run the publisher could be talked into publishing.

A comparison of models on real comments (2026-09-30, 8 comments, 2 runs each) showed why the gate cannot trust the model's own category: DeepSeek V3.2 once labelled a question with no source "answerable from sources" and invented the answer, and the gate would have let it out. `policy_gate.py` now requires a factual answer to cite project files that exist, and every number in the reply to appear in them. A claim without a number still passes any deterministic check; the model choice covers that (Sonnet 5.5 classified all 16 cases correctly). Rejected: a second model as a judge (cost and latency for 0 to 30 replies a day) until a real miss shows it is needed.

## 2026-10-01: Eval results are recorded per skill; status is computed

**Decided to be replaced on 2026-10-02** (entry of 2026-10-02, "The reliability model, simplified after its independent review"): one record per skill and the three states give way to evidence lines per run and to bands. Until phase B of the plan in force builds that, the record, the three states and the generated table described here are what the tools do. The paths are the ones of the day: the status script is `evals/eval_status.py` since the entry "The eval harness lives in `evals/`".

A review of the inventory found that most of the skills ticked as built had no eval result on record, and some of them scored low once measured. Five causes: "done" was a tick written by hand; results lived only in the git-ignored `evals-workspace/`; changing a skill did not force a new evaluation; `eval_run.py` let infrastructure failures (a provider out of credits, a session limit) pass as low or missing scores; and eval cases were never checked (fixtures copied to another path than the prompt named, prompts citing files the case did not ship, assertions the grader could not verify).

Decided: a complete, full run writes `skills/<name>/evals/result.json`, committed, with the scores, the gate and a sha256 of the skill folder. `scripts/eval_status.py` computes each skill's status from it: `draft` (no record, a failed gate or an incomplete run), `evaluated` (gate passed on the current content) or `stale` (gate passed, then the folder changed). The status table in `docs/inventory.md` is generated from it, and `scripts/validate.py` fails when a record is invalid or the table is out of date, so a commit that changes an evaluated skill shows it as stale in the same diff. `eval_run.py` checks every case before any model call, lists infrastructure failures apart from scores and marks the iteration incomplete, with its own exit code.

Rejected: rerunning evals in the pre-commit hook or in CI (model calls, cost and provider keys do not belong there; the check compares hashes instead and stays offline); a hash over `SKILL.md` alone (a script, a reference or a case changes behaviour or what is measured as much as the body does); making `stale` and `draft` errors by default (most skills start as `draft`; `--strict` turns them into errors once the backlog of unrecorded skills is cleared).

## 2026-10-01: A turn that ends early with no error is an infrastructure failure, retried and counted

In one day of floor-model runs, about one run in nine ended its turn early with exit 0 and no error: the model stopped mid-plan, printed a tool call as text, or looped writing reminder blocks to itself. Nothing was written, no question was asked, and the run scored zero, which is not the skill's doing.

Decided: `eval_run.py` detects an early end with a deterministic, conservative rule (no file created or changed, and a response that is empty, carries tool or control markup at the start of a line, or ends on a line that announces a next action while the response asks no question), reruns it in a fresh folder up to `--retries` times, keeps every early attempt, and counts them per model in `benchmark.json` and in the record. A run that early-ends on every attempt is an infrastructure failure and makes the iteration incomplete. A reply that asks the user a question and writes nothing is a stop-and-ask, and a run that wrote a file and then stopped before finishing is graded as it is: neither is an early end.

Retries hide the problem from the scores, so they must not hide it from the report: when a model has at least three early ends and either a rate above 15% of its attempts or all of them on one case, the runner prints a warning that says to read the transcripts and decide. Concentrated on one case, the skill or the case may trigger it; spread across cases, the provider or the model is unreliable, and another provider or another floor model is the answer. Rejected: scoring early ends as zeros (it measures the provider, not the skill) and a model as the judge of what an early end is (cost, and one more thing that can fail without an error).

## 2026-10-01: The floor model is DeepSeek V4.1 Flash; local models are a measured goal

**Reversed in part on 2026-10-02** (entry of 2026-10-02, "The reliability model, simplified after its independent review"): "a good score on a very affordable open model is the passing criterion" no longer holds; the floor model's results are information. What stands: the floor model named here, and a local model as a goal that is measured and published.

The floor model changes from `openrouter/deepseek/deepseek-v3.2` to `openrouter/deepseek/deepseek-v4.1-flash`. All measured on 2026-10-01: it has open weights (MIT) and costs a fraction of the previous one; on the five evaluated skills it scored 1.00 with the skill in every run (0.40 to 0.57 without it), with no early end in 66 attempts, where the previous floor scored 0.81 to 1.00 and ended its turn early in 22% of the attempts of one run.

The purpose of the floor is restated: a good score on a very affordable open model is the passing criterion. Running on a person's own machine (Ollama, models of 20 to 30 billion parameters) is a goal that is measured and published, and it does not block a skill. First local results on one skill (design-system, 2 cases, 3 runs each, with the skill): gpt-oss 20B 0.26; Qwen3-Coder 30B 0.43; Devstral Small 2 24B unusable through the runner (it announces a step and ends its turn every time); Qwen3.8 27B still being measured. Other inexpensive hosted models on the same skill: DeepSeek V4 Flash 1.00, Qwen3.7 Flash 0.89, gpt-oss 120B 0.17 with early ends.

How it is enforced: the gate is a committed file, `scripts/eval-gate.json` (strong and floor model, their adapters, the floor model's key variable, the threshold). `eval_run.py` takes its defaults from it, so `eval_run.py --skill <name>` runs the gate. `scripts/eval_status.py` reads a record made on another floor model as `stale` ("evaluated on another floor model"), so changing the floor sends every skill back to be rerun, and judges recorded scores against the configured threshold. A full run on another floor model, a local one for instance, writes no record unless `--record-anyway`. The file sits outside `skills/`: it names adapters and models, which the core does not, and changing it alters no skill's content hash.

Rejected: keeping the previous records as passed (they did not pass on the current gate); a local model as the gate now (the best local score so far is 0.43); several floor models in one record (one gate, one answer).

## 2026-10-01: The strong model is Claude Sonnet 5.5; both eval models are named in one file

**Reversed in part the same day** (entries "Evals run only in a container; the runner leaves the skill; a record says how it was measured" and "The record and the gate as built"): a record made with another strong model does not stay valid; it reads `stale`. The command and the file are `evals/eval_run.py` and `evals/eval-gate.json` since "The eval harness lives in `evals/`". What stands: the strong model, and both models named in one file and never passed by hand.

Decided by the maintainer. Every evaluation until this date used Claude Opus 5.5 as the strong model and as the grader; it used up the account's usage limit three times in two days, and 42 skills are still to be evaluated. The strong model of the gate is now Claude Sonnet 5.5: it is strong enough for the condition "the skill does not make a strong model worse" and for grading assertions, at a fraction of the usage. A record names the strong model it was made with; records made with the previous strong model stay valid (only a change of floor model or of the skill's content makes a record stale).

Both models, their adapters and the threshold live in `scripts/eval-gate.json`, and nowhere else. A session never passes a model to the runner: `python3 skills/core-skill-creator/scripts/eval_run.py --skill <name>` reads them from that file, so every session evaluates on the same pair. Changing a model is a change to that file, with an entry here.

## 2026-10-01: An eval run leaves nothing running and shows no dialog

**Reversed in part the same day** (entry "Adapters run only in the container; cases list no commands; tolerance 0.05"): the throwaway keychain was removed with the rest of the code for running on a person's machine. What stands: a run's processes are ended as a group, on every way out.

Two defects found while running the gate on many skills on macOS.

A browser started inside a run showed the person a "Keychain Not Found" dialog, once per launch: the run's throwaway `HOME` has no `Library/Keychains`, and Chrome looks for its "Chrome Safe Storage" item in the default keychain, which macOS finds through `HOME`. A skill's script can start the browser with a mock keychain, but a model that starts one by itself cannot be controlled. Decided: an adapter that replaces `HOME` on macOS creates an empty keychain there and makes it the default, with every `security` call run under the throwaway `HOME` only, so the person's keychains are never touched; the keychain is deleted with that home. The adapter that keeps the person's `HOME` needs nothing.

Stopping an evaluation left its model sessions working for many minutes, and starting browsers: a timeout or a kill ended only the adapter's shell. Decided: `eval_run.py` runs every adapter call and setup command in a session of its own and ends the whole process group on a timeout, when the call returns, on TERM, INT or HUP, and on any way out; each adapter does the same for the runner it starts.

## 2026-10-01: Eval runs happen outside the repository

**Superseded in part the same day** (entry "The eval container, as built"): what the last paragraph leaves open is closed by the container, which sees no home folder, no checkout and no disk to search. What stands: case folders are created outside the repository.

Case folders lived under `<repository>/evals-workspace/`, so a model could walk up from its case folder and find the workbench. Evidence from the runs of that day: a floor model's log shows `find <repository>/evals-workspace/...` and its reply to a without-skill case says it will use "the workbench's own" capability, "which lives in the skills repo"; 3 of 12 floor without-skill replies of one skill name the skill; on the strong tier, without-skill replies that mention the repository by name exist for six skills (6, 3, 3, 3, 2 and 2 response files). A harness may also load instruction files from the parents of the folder it runs in. The without-skill baseline was therefore inflated, which understates what a skill adds and can change the gate's strong condition (with the skill at least as good as without it).

Decided: `eval_run.py` runs every case and every grading in a fresh temporary folder outside the repository, whose parents hold no repository, instruction file or skills folder and whose path names neither the workbench nor the skill; the environment carries no path into the repository; the folder is moved to its place under `evals-workspace/` when the run ends, also after a timeout or a stop. As a guard, the output of every without-skill run is searched for the repository's path; a hit is recorded as `contaminated` and blocks the record unless `--allow-contaminated`. Records made before this keep their scores with the skill; `eval_run.py --only without --update-record` measures the baseline again, alone, and replaces the two without-skill scores of a record that is still current.

Not closed by this: a workbench installed globally in a harness, and a model that searches the whole disk; the guard reports the second.

## 2026-10-01: The strong model's eval commands are confined by a sandbox, not listed

**Reversed the same day** (entry "Adapters run only in the container; cases list no commands; tolerance 0.05"): the sandbox settings, the command rules and `allow_commands` were removed; the container is the boundary for both tiers. What stands: the finding that a list of allowed command texts denies harmless commands.

The strong model scored below the floor model on several skills. The cause was the eval harness, not the skills: the strong model's adapter let a command run only when its text matched a rule (the case's `allow_commands` and the skill's scripts), while the floor model's adapter approved everything. Harmless forms did not match: the skill's own script fed by a heredoc or called in a loop, a pipe, a variable, `mktemp -d`. The runs kept on the maintainer's machine carry 809 denied commands on the strong tier, most on the skills where it lost to the floor (22 in 6 runs of one, 17 of them the skill's own script; 53 in 15 runs of a research skill, 40 of them web tools its cases had not allowed).

Options weighed: a longer list of rules (still matches text, so the next harmless form is denied again); approving everything, as the floor tier does (some cases plant an instruction in a fixture on purpose, and a model that followed it would act on the maintainer's machine); a sandbox.

Decided: on the strong tier every command runs inside the harness's sandbox, enforced by the operating system: writes inside the case folder and temporary folders, no network, no read of the workbench or of credential folders, and no start at all when the sandbox is unavailable. The case's `allow_commands` prefixes and the skill's own scripts keep running unconfined when called plainly, as before, since a browser does not start inside the sandbox. `allow_web` stays a per-case decision. Details and the checks made: `adapters/claude-code/README.md`.

Consequences: a record whose strong-tier runs were made under the rules understates the strong model; the gate was still passed under the harder condition, so those records stay valid, and they are measured again as each skill is next evaluated. `eval_status.py` does not turn a record `stale` for an adapter change. The two tiers are still not confined alike: confining the floor tier is backlog S19.

## 2026-10-01: Skill evaluation pauses for an architecture review

In one day the eval harness was changed four times for causes found while measuring: runs that failed on infrastructure counted as scores, without-skill runs found the workbench by walking up, the strong tier was denied harmless commands the floor tier could run, and floor runs found the workbench by searching the disk. Each fix changed what the records mean, and 26 records were partly measured again twice. The last cause, and a shell profile on the maintainer's machine that breaks `cd` for every run, point at the same thing: results depend on the machine.

Decided by the maintainer: before a container environment is tried (backlog T16), the state is written down (backlog T11), the whole architecture is reviewed, tests included, and a plan is made from the architecture that is decided, so that the remaining skills, and the 26 already recorded, are measured once more and not again after that.

## 2026-10-01: Evals run only in a container; the runner leaves the skill; a record says how it was measured

Decided by the maintainer on the review of that day (`docs/architecture/review-2026-10-01.md`, D1, D2, D3, D5, D6):

- **One environment, no alternative.** Every eval run executes in a container built from one pinned image, one container per run, started by an executor layer between the runner and the adapters. The container is the boundary for both tiers, which get the same rights; nothing of the workbench or of the person's home is mounted. There is no host mode: one standard, so that every record is comparable. This closes backlog S19 and replaces T6.
- **The eval runner moves out of `core-skill-creator`** to a top-level `evals/` folder with its tests, the grading template and the gate configuration.
- **A record names how it was measured** (image digest, runner and CLI versions, strong model, grader, measurement version) and is `stale` when the skill folder, the floor model, the strong model, the grader or the measurement version differs. The measurement version is a number in the gate configuration, raised on purpose when a change alters what is measured; the runner's own hash is not used.
- **In the container the strong runner authenticates with a long-lived token** from the secret store, passed as an environment variable; to be confirmed by the proof of concept.
- **Network:** egress only to the model provider; a case with `allow_web` gets open egress; language dependencies and a browser come with the image.

## 2026-10-01: The gate asks the threshold of both models

**Reversed in part on 2026-10-02** (entry of 2026-10-02, "The reliability model, simplified after its independent review"): the gate is evaluated on the reference model alone; the floor model's score is information. What stands: the threshold of 0.8 and the tolerance against the baseline.

The rule in the code was: the floor model with the skill at the threshold (0.8) or above, and the strong model with the skill at least as good as without it. The strong model had no threshold of its own, so a skill passed with the strong model at 0.78; and the comparison had no tolerance, so a difference smaller than the spread between runs could fail a skill.

Decided by the maintainer (D4): a skill passes when **both models score at the threshold or above with the skill, and the strong model with the skill is not below the strong model without it by more than a tolerance**. The tolerance is a number in the gate configuration, set from the spread measured in the container's proof of concept and approved by the maintainer; until then it is 0. Changing the rule raises the measurement version, so every record made under the old rule reads `stale`.

## 2026-10-01: The eval harness lives in `evals/`

Done as decided (D2): `eval_run.py`, `eval_status.py`, `eval-gate.json`, the grading template and their tests moved to a top-level `evals/` folder. It is not part of the core: it reads `adapters/` to find a harness's runner, which a core file may not do. `core-skill-creator` keeps the procedure and names the commands; a change to the runner or to how every skill is graded no longer changes that skill's hash. Entries above this one name the old paths (`skills/core-skill-creator/scripts/eval_run.py`, `scripts/eval_status.py`, `scripts/eval-gate.json`); they are left as written.

## 2026-10-01: The record and the gate as built

Done as decided (D3, D4). `evals/eval-gate.json` gains `grader`, `strong_tolerance` (0 until the proof of concept gives it a number) and `measurement_version` (2; a record without the field is version 1, the earlier rule). A record gains `measurement_version`, `tolerance` and, when the runner supplies it, `environment`. The status is `stale` when the measurement version, the strong model, the grader or the floor model differs from the configured one, or the skill folder changed. Records of version 1 stay valid files and all read `stale`; they are not rewritten, they are replaced when each skill is measured in the container. Raising the measurement version is a deliberate act in the commit that changes what a run measures: the next raise comes with the container environment.

## 2026-10-01: The eval container, as built

The proof of concept confirmed D1, D5 and D6 (`docs/architecture/container-poc-2026-10-01.md`). Every command of an eval (model run, grading, setup, fixture commit) runs in its own container, started by `evals/executor.py` from the definition in `evals/container/`. A container sees the run folder, the adapters, the shared references and the skill; it reaches the model providers through an allowlisting proxy on an internal network, nothing at all for setup, and the open network only for a case with `allow_web`. The strong runner's token and the floor runner's key come from the secret store and travel by variable name. A record names the definition's hash and the image id. Measurement version 3.

The unit tests of the runner drive stand-in adapters on the host through a module switch; that switch is not an option of the runner and no record can be written through it by a person running the command.

## 2026-10-01: Adapters run only in the container; cases list no commands; tolerance 0.05

Following the container (entry above), decided by the maintainer and built:

- **The eval adapters refuse to start outside the eval container.** Both allow a model every tool; that is safe only where the container is the boundary. The code that existed for running on a person's machine is removed: command rules and sandbox settings in the strong adapter, the throwaway keychain in the floor adapter.
- **`allow_commands` is gone** from the runner, from the adapter contract and from the 32 case files that listed it. It named what a model could run on a person's machine; in the container every command runs. An `evals.json` that still carries it is refused, so that no case keeps a setting that does nothing.
- **A case's setup runs in the container**, also in the check made before the first model call. The static check (`--check-cases`, which `validate.py` runs) needs no container: a case with setup is listed there as unchecked.
- **`strong_tolerance` is 0.05**, approved by the maintainer from the spread measured in the proof of concept; to be revisited when the 48 skills are measured.
- A CI job builds the image on Linux and checks, without a model, that a run writes only in its folder, sees no home and no checkout, reaches nothing without a network, only the providers through the proxy, and the open network when a case asks for it.

None of this raises the measurement version: version 3 was set with the container and no record exists under it yet.

## 2026-10-01: The strong adapter raises the skill-listing budget; measurement version 4

The first skills measured in the container showed the strong model ignoring a skill it had been given. Cause: the harness lists skills to the model within a character budget, its bundled skills first, and listed the skill under test by name only, with no description (`adapters/claude-code/README.md`). The adapter now raises the budget so that the description is listed. This changes what a strong-tier run measures, so the measurement version goes from 3 to 4; the five records made under version 3 in the hours between were discarded before being committed, and those skills are measured again. What a person's own installation shows the model is a separate question: backlog T18.

## 2026-10-01: What measuring 48 skills in the container found in the harness

Found while measuring, each fixed in `evals/` or an adapter with a test; none changes what a clean run measures, so the measurement version stays 4, and the skills a defect had touched were measured again.

- **A run could read the cases of its own skill.** The skill folder is mounted read-only for the adapter to copy, and its `evals/` folder (expected output, assertions) came with it. Seven floor runs of four skills had read it. An empty folder now covers it.
- **Images went to the grader as text.** A produced PNG was pasted into the grading prompt, which told the grader nothing and made some prompts too long to pass as one argument, so gradings failed. A binary file is now described (kind, size, dimensions), and the strong adapter takes the prompt on standard input.
- **The floor runner's web search is rate limited.** With several runs searching at once the search service answers 429 and the model waits until the run times out. Skills whose cases search the web are measured alone, two runs at a time. A rate limit is one of the reasons principle 7 accepts for not running in parallel.
- **A provider refusal is not a score.** One baseline case, an audit of a deliberately malicious fixture run without the skill, is refused by the strong model's provider on every attempt. The runner counts it as an infrastructure failure, so that skill has no complete record. Whether such a case counts as zero for the baseline, or the fixture changes, is the maintainer's decision.

What the skills needed, in general terms, so that the next ones are written with it: a grader sees only the reply and the files a run leaves, so a skill's report must quote the evidence (the command and the output line of a check, before and after), and an assertion must ask for that evidence, never for "the script was run"; a fixture must be a small real project in the project's layout, not placeholders; a script that needs a browser finds it from the environment and works where a browser refuses its own sandbox; a description must name the user's words for every situation the skill handles, or the model does not use it.

## 2026-10-01: A refused baseline run scores zero; a case may bring files of the repository

Decided by the maintainer for the last two skills without a record.

- **A provider's refusal of a without-skill run is a score of zero**, listed in `benchmark.json` `baseline_refusals`. The baseline exists to show what the skill adds, and "the model alone could not do the task" is a baseline. The same refusal of a run that has the skill stays an infrastructure failure: it says nothing about the skill and is never a score. The alternative, a milder fixture, would have weakened what the case tests (an audit of a deliberately hostile skill).
- **A case may list `workbench_files`**: files and folders of this repository copied into the case folder at the same relative path. It is for a skill whose job is the workbench itself (creating, validating, evaluating skills), which needs the real tooling to act on. The alternative, a copy of that tooling kept as a fixture, would drift from the real one. Refused: paths that leave the repository, version control, eval workspaces and any skill's eval cases, which hold expected outputs. Such a case deliberately shows the model part of the repository; the contamination guard looks for the repository's path, which the copies do not carry.

## 2026-10-02: Flows that are not built are named as planned; capabilities state the artifact they need

Decision D12 of `docs/architecture/review-2026-10-01.md`, as built. Only `flow-fix-bug` exists, so every other flow name is marked planned wherever it is cited as a route (the orchestrator, its routing table, the area map, the inventory); the orchestrator keeps its rule for a missing skill, which is to name it as the route with the status `pending` and propose one fallback for the user to accept. A capability no longer tells the model to run or route to another skill: it states the artifact it needs, names the skill that writes it, and stops for the user to run it, so that only flows invoke skills (principle 4). The alternative, removing the citations, would have left the orchestrator without a name for requests that are flows, and its eval cases expect those names.

## 2026-10-02: Phase 5 decisions: D7 to D10 and D12 approved; a skill's tests live in the skill and outside its hash

Decided by the maintainer, on the decision table of `docs/architecture/review-2026-10-01.md`.

- **D7, D8, D9, D10 and D12 are approved as recommended**: the artifact contract (D7), one source for shared code (D8), providers named by class (D9), tests of skill scripts in the skill (D10), and flows that cite only what exists (D12). They are phase 5 of `docs/architecture/plan-2026-10.md`.
- **A skill's script tests do not count for its content hash and are not copied into an eval run.** They live in `skills/<name>/scripts/tests/`. `evals/eval_status.py` leaves everything under that folder out of the hash, and the eval adapters remove it from the copy of the skill a model gets, as they do with `evals/`. Reason: a test is not part of what a model uses, so a new or changed test measures nothing differently and must not cost a measurement. The alternative, tests kept in `scripts/tests/` so that the hash never sees them, left skill scripts far from their tests and the hook unable to tell which tests a changed script needs. The skills that already had tests inside their folder read `stale` once, because their recorded hash was computed with those files.
- **Phase 5 is carried out in full without measuring the skills again for now.** A skill whose folder phase 5 changes reads `stale` until a later measurement round, which is done together with backlog T19 (assertions that pass in every run). Until then `stale` on such a skill means "changed by phase 5, last measured before it", not a defect.

## 2026-10-02: The orchestrator is the one capability that hands a request over; requirement classes keep their names

**Reversed in part the same day** (decision 14a of `docs/architecture/final-plan-2026-10-02.md`): requirement classes are renamed; every class takes the form `<role>:<target>` (`mailer` becomes `sender:email`, `mailbox` `reader:email`, `scheduler` `scheduler:job`, `store` `store:runtime`), in phase C of that plan. What stands: the orchestrator is the one exception to principle 4.

Approved by the maintainer, closing what backlog item T20 left open. `core-orchestrator` is the one exception to principle 4: it is the router, so it names a skill and hands the request over to it, and does none of that skill's work; every other capability reads and writes artifacts, and `AGENTS.md` says so in the principle, in "Skill kinds" and in "Never". Requirement class names are not renamed: some carry a prefix and some are bare (`mailer`, `mailbox`, `scheduler`, `store`), a skill copies a name exactly as `contracts/environment.md` spells it; renaming would change every skill and provider that declares one.

## 2026-10-02: Providers are resolved by class; one interpreter rule; ledgers in a data folder (D9, D13)

Decisions D9 and D13 of `docs/architecture/review-2026-10-01.md`, as built.

- **One resolution function.** `providers/resolve.py` turns a requirement class into the provider script, in this order: the class's environment variable (`<CLASS>_<SUBCLASS>_PROVIDER`, then `<CLASS>_PROVIDER`; the naming that existed), the platform default where one exists (`scheduler`: launchd on macOS, systemd on Linux), the only implementation when the class ships exactly one. Nothing resolving is exit 3 with the variable to set; an unknown class is exit 2. A name is accepted only when it is a script shipped in the class's folder, never as a path.
- **Who uses it.** `scripts/runtime.py` and `scripts/runtime_vote.py` (the store was a fixed path, the scheduler was launchd on every platform), `scripts/doctor.py` (it had its own lookup, and reported a class as missing unless its variable was set; it now checks the provider the function chooses), and the skills, which run `python3 <workbench root>/providers/resolve.py --class <class>` and use the printed path. A name in `runtime.json` still wins, so existing files keep working.
- **The workbench root** is the environment variable `WORKBENCH_ROOT`; unset, the function uses its own checkout, and a skill asks the user.
- **What was weighed.** A registry file mapping classes to scripts was rejected: the folder layout already is the registry, and a second list would drift. Resolving inside each skill's own script was rejected: skills would each carry a copy of the rule. A default for every class with several implementations was rejected: only the scheduler has a choice the platform decides; any other class with two implementations is the user's choice, asked through the variable.
- **Python version (D13).** `providers/CONTRACT.md` names the scripts that run on the system interpreter the scheduler uses (Python 3.9): the scheduler providers, the runtime and what it starts with its own interpreter, and `providers/resolve.py`. Their header says `requires-python = ">=3.9"`; the store provider claimed 3.10 and needed nothing from it, so its header was corrected. `scripts/tests/test_runtime_python39.py` checks syntax, header and import for each, and a CI job runs their tests on Python 3.9. Providers that need more are started through `uv run`.
- **Ledgers.** The idempotency ledgers of the publisher and vcs providers moved from the cache folder to the data folder the scheduler uses, because clearing a cache must not lose the record of what was published. On first use the old ledger is copied to the new place and kept. Reading the old ledger on every lookup was considered, for jobs scheduled before the change, which run a copy of the old provider and keep writing to the old place; the maintainer chose the simpler rule instead: those jobs are scheduled again after upgrading.
- **Left for D11:** the runtime still names the skill scripts it calls, and `payload.py` still builds the publisher's path from the workbench path and the platform.

## 2026-10-02: A full audit before one final measurement round

**Reversed in part the same day** (entry of 2026-10-02, "The reliability model, simplified after its independent review"): there is no final round and no freeze after it. The next measurement is the first full test of the 48 skills under the model, and a later change costs a small test. The section this entry says awaits the maintainer was answered in full on 2026-10-02. What stands: the audit, its findings, and the order of the plan (what is known to need fixing is fixed before the 48 skills are tested).

The 48 skills were measured once in the container (backlog T11), and the changes merged since then left 15 of them `stale`. The maintainer decided that the skills are measured one more time and that this round is to be the last for the skills as they are: everything that has to be fixed is fixed before it, even at the cost of measuring all 48 again, and whatever changes a skill's folder or what a run measures is frozen after it.

So that the round is planned from what is true, the whole repository was audited first: nine read-only audits run in parallel (six over the 48 skills in groups, one over the eval harness, one over what crosses skills, one over every backlog item), none changing a file or calling a model. The reports are in `docs/architecture/audit-2026-10-02/`.

What the audit found, in short:

- **In the skills.** Reports that say a check was done instead of quoting its output, and assertions that ask for what a grader cannot see (a command that ran, a file that did not change); script paths that exist only in the workbench; stop gates without the words that make them hold; about 30% of the assertions passing in every variant, and several cases that score the same with and without the skill; 25 skills writing the state file without declaring it; fixtures with runtimes the image lacks, dates relative to the day of the run and, in places, the numbers and dates of one real case; nine scripts that end in a traceback on a missing flag value.
- **In the harness.** A grader that is inconsistent rather than biased, mostly for what its template does not say and what it cannot see; three runs per case, where one iteration's mean moves by about 0.045 between identical reruns; an early-end detector wrong in 7 of 12 detections; runs that can read more of the workbench than they should; an image that cannot be rebuilt and whose scratch folder the floor runner cannot write; a contamination check that cannot fire; nothing that stops a change to the measurement without raising its version.
- **In the backlog.** 82 items: 38 done, 18 partly done, 26 not done; nine ticks that do not match the code; 19 pieces of work that no item covered; one CI job failing on `main`.

The plan in force is `docs/architecture/final-plan-2026-10-02.md`. It replaces `docs/architecture/plan-2026-10.md`, whose phases 0 to 4 are done. Its order follows one rule: repairs that touch neither a skill nor the measurement, then the measurement changed once (version 5), then every skill edited once, then a dry run, then the round, and only after it the work that is independent of skills.

Its section "Decisions for the maintainer" awaits the maintainer: 14 decisions that change the plan (among them the runs per case, single or double grading, how the freeze is enforced, the image's platform, a fixed clock, the owners of the shared ledgers, what the runtime is, and what is done with fixtures that carry a real case) and 76 defaults that apply unless the maintainer objects. Until they are answered nothing in that section is decided. Rejected as an alternative: measuring the 15 stale skills now and fixing the rest later, which would have cost a second round for most skills.

## 2026-10-02: A reliability score per model, built from evidence, replaces the three eval states

**Replaced by the next entry.** What stands of this entry is its direction: evidence per model instead of three states, a full test once, small tests afterwards. Its details do not hold any more: the score is not weighted by kind and decayed, field use carries no skill, the first full test is not 1,884 runs, CI does not fail on "guard cases without lab evidence", and the model document does not win over the plan (the two say the same thing: one describes the model, the other the work).

Decided by the maintainer before the plan of 2026-10-02 started. A skill is no longer `draft`

Why: under the three states any change inside a skill folder discarded all its evidence and asked for a complete measurement on two models, so the plan had to build a freeze and one last round of 3,140 runs around that cost, and it would not scale with more skills, more changes or more models. Under the model the first full test of the 48 skills is 1,884 runs and one grading pass (about 36% of the calls on the strong model's account), and a later change costs a bump, a targeted test or nothing.

Rejected: keeping the states and making the round cheaper (the cost of every later change stays); a score with no lab requirement (the behaviours ordinary use never exercises, such as stopping before a side effect, would go unmeasured, so guard cases are always run in the container); thresholds on the score alone (a backtest on the 48 records shows they cannot separate a fresh full test from a version bump with no new evidence, so two rules stand beside the score); a decay by age (a score that moves with the calendar makes the generated table stale with no commit).

The model, its backtest, its limits and its changes to the plan are in `docs/architecture/reliability-model-2026-10-02.md`, which awaits review; where it differs from `docs/architecture/final-plan-2026-10-02.md` it wins, and the plan is amended after the review.

## 2026-10-02: The reliability model, simplified after its independent review: bands by rules from lab evidence only

The model of the entry above was reviewed the same day by an independent reviewer (4 blockers, 14 important findings, 9 minor ones; digest in `docs/architecture/audit-2026-10-02/model-review.md`). The maintainer adopted the simpler version that review recommends, with every correction it proposes. The same reviewer then read the pull request that carried the result and found ten points where a rule did not work as written (P1 to P10 in the digest); all were accepted, and this entry states the model with them applied. This entry replaces the details of the entry above; its direction (evidence per model instead of three states, a full test once, small tests afterwards) stands.

What is decided:

- **Evidence** is one line per lab run, in one file per test event. A skill's content hash leaves out all of `evals/`; each case has its own hash, over the whole case. The 48 records of the first round stay as history and nothing is converted from them.
- **Two kinds of lab test**: a full test (every case with the skill on one version on the reference model, plus the baseline) and a partial test (named cases, with the skill only). The baseline is reused while the case, the model and the measurement are unchanged. Only a full test evaluates the gate: an added case is `pending` until it has run, a changed case enters through a full test, and an abandoned full test keeps its lines.
- **Change classes**: X for security and contract, Y for everything else, Z only by an allow-list written from the positive side (the `## Purpose` section and text outside any section that instructs: a typo or formatting) with a budget in characters. The validator checks the declared class against the diff.
- **Guards**: the tag is on the assertion; every guard assertion must have run, and have no confirmed failure, in the with-skill runs of the current set (the lab lines of the current `X.Y` made since the newest epoch, measurement floor or dependency change that applies to them); a failed guard verdict is graded once more before it counts, and a confirmed failure is cleared only by a change; guard cases run again on every Y change and do not alone return a skill to `reliable`; a skill with side effects has a guard for each declared effect.
- **Bands are rules**, computed on the reference model: `needs a test` (with its cause, which says which test), `watch`, `reliable`. The score is the Wilson lower bound over lab evidence, called the pessimistic score and shown with the mean and the number of runs; inherited evidence is capped (3 runs, all of it together, and none across a major version) instead of decayed. At the third Y change since the newest full test a skill is `watch` until a full test.
- **Measurement changes** are of three kinds: grader side (lab evidence is discarded), execution side (an epoch for the skills affected), infrastructure (nothing).
- CI fails on what section 5 of the model lists (the bump, the class, the version file, the guard for a declared effect, the validity of evidence, the measurement fingerprint), the one place where that list is kept; never on a score or a band.

Two points were put to the maintainer explicitly, and both were answered yes:

1. **Field evidence never promotes a skill by itself.** It is recorded in the project from the first day and shown in its own columns per model, labelled self-reported; it can demote by a signal counted on the reference model, with a maximum weight per contributor, and after a change of behaviour a skill returns to `reliable` only with lab runs: 3 to 9, the affected cases and the guard cases.
2. **`reliable` requires a pessimistic score of 0.70 or more.** A small skill that has just passed its full test with a marginal mean therefore starts in `watch` (6 of the 48 would, on the records of the first round). "Done" for a new skill remains "its first full test passed".

Why: as first written, the bands were decided by rules with four holes. A guard had to exist and to have run, never to pass; the lowest change class could not be verified and accepted changes of behaviour; any change followed by a test of the failed cases erased their bad runs from the gate; and field evidence, selected and self-reported, entered the same sum as lab evidence and could return a skill to `reliable`. The simpler version closes the four with about half the parts.

Rejected: keeping the numeric decays (0.95, 0.6, 0.2 per change, 0.8 per measurement step), which the data of today cannot calibrate and which barely moved the score of a skill with much evidence; thresholds of 0.50 and 0.45, under which a skill at 0.54 read `reliable`; the conversion of the 48 old records into evidence, which would have weighed nothing, since phase C rewrites the cases and phase B changes what the grader sees; a baseline on the floor model in every full test, which no rule reads; a second grading pass.

What it costs: the first full test of the 48 skills is 1,437 runs and 1,437 gradings for 160 cases (159 base cases and one platform case), 2,394 calls on the strong model's account, about the size of the first round. What every later change costs is in one place, the model's table "What a change costs". A changed step costs 3 to 9 lab runs, where daily use alone would have been enough under the first version; that is the price of the first point above.

Left for later, on purpose: field evidence counting toward a band, once recorded uses can be compared with verdicts; the numeric decays.

The model is in `docs/architecture/reliability-model-2026-10-02.md` and the work in `docs/architecture/final-plan-2026-10-02.md`: the first describes the model, the second the work, and the plan already contains the model's consequences.

## 2026-10-02: Principle 8 is separation, not masking (decision 11 of the final plan, as narrowed)

Decided by the maintainer. The workbench holds no file of a project that uses it and names no such project, its people or its accounts. Real data as such is not the problem: a number, a date, a palette or a measured result that came from a real case may stay in a fixture or in a lesson.

- What identifies a project is replaced: its name, a prefix or path that carries the name, people, handles, hosts, the identifiers of its files in other tools. A name that is already a replacement and names no project that uses the workbench is not replaced again.
- Numbers, dates, schedules, palettes and the figures in a "Gotchas" section stay as they are.
- A file copied whole from a project becomes a fixture that belongs to the test: only what the case needs, under a fictional name.
- No eval case is removed for this.
- One exception to the rule on names: the maintainer's own name and handle where ownership needs them (the license, the code owners file, an adapter's manifest that names its author).

`AGENTS.md` says this in the three places that said numbers go: principle 8, step 7 of "Adding a skill" and the "Never" list.

Rejected: rewriting every such fixture as fiction, numbers and dates included (the largest of them would take a day or more, and baselines would move for no gain: a number identifies nobody); removing the affected cases (two skills would lose their main cases); leaving the fixtures as they are (the repository is public and principle 8 would stay broken).

Why: the first wording of principle 8 asked for "invented numbers", which made a lesson measured on a real case impossible to keep and turned a cleanup of names into a rewrite of whole fixtures. What the principle protects is the project and its people, and they are identified by names, never by a count.

## 2026-10-02: Requirement classes all take the form `<role>:<target>` (decision 14a)

Decided by the maintainer; it reverses the part "requirement classes keep their names" of the entry of 2026-10-02 on the orchestrator. Four classes were bare while the others carried a role: `mailer` becomes `sender:email`, `mailbox` becomes `reader:email`, `scheduler` becomes `scheduler:job`, `store` becomes `store:runtime`. `integration:*`, `search:web`, `generator:*` and `publisher:<platform>` keep their names.

- Only the class names change: in `contracts/environment.md`, in skills' `requires`, in the orchestrator's class table, in `providers/CONTRACT.md`, in the class list of `providers/resolve.py` and in the names the runtime passes to it. The provider folders, the `<CLASS>_PROVIDER` environment variables, the keys of a project's `runtime.json` and every data name stay; the resolver keeps reading the four old names as aliases, so a job scheduled before the rename keeps running. No project migrates anything.
- Two forms of a class: `<role>:<target>` with a fixed target, where the target is part of the class's identity, and `<role>:<parameter>`, where the part after the colon is handed to the provider. Only `publisher:<platform>` has the second form.
- The validator refuses a bare class in a skill's `requires`: a warning first, an error once every skill is edited.

Rejected: moving the provider folders to `providers/<role>/<target>/` (it would drop the provider tests from CI, break the hook's path mapping, each provider's lookup of the secret resolver and the jobs already scheduled, and a skill sees a class name, never a folder); renaming later (after the first full test a rename is a tested change of every skill that names a class).

Why now: every skill is being edited once anyway, so the rename costs nothing in evidence. The work is item C0.2 of `docs/architecture/final-plan-2026-10-02.md` and the rows of the skills that name a renamed class.

## 2026-10-02: Four design rules in `AGENTS.md` (decision 14b)

Decided by the maintainer. The part of the SOLID principles that holds for text a model interprets, written into `AGENTS.md` as "Design rules":

1. A skill names no harness (principle 1, already enforced).
2. A skill's procedure names no social platform: it declares the class it needs and reads what is specific to a platform from that platform's reference. What a user types in a request may name a platform.
3. Adding a platform adds a reference file, a data file where a script needs one, and a provider where something is executed; it edits no skill's procedure, and only that platform's cases are run. The rule holds for a platform whose post is text with optional media, the shape of the one platform built today. A platform of another shape is expected to edit the skills that build, write and gate a post. A parser of one platform's own format stays as code in its skill, and a table of networks inside a skill gains its rows there.
4. One skill per job: a skill is split only when the part has its own trigger, its own requirements or side effects, or its own artifact. No skill is split before the first full test of the 48.

With them, the rule on product names said once next to principle 1: a third-party product that is not an AI tool may be named where it is what a user types or what the code must recognise; AI tools and generative design tools are replaced by fictional names; a social platform's rules live in its reference and data file.

Not adopted, with the reason: a formal profile contract with declared capabilities, and a validator rule that refuses platform names, wait until a second platform is built, because a contract drawn from one example describes that example. The code host is out of scope: no second host is planned.

## 2026-10-02: Platform references, tested per platform (decision 14c)

Decided by the maintainer.

- `shared/references/platforms/<platform>.md`, one file per social platform, holds what the platform is as a medium: text limits, the media it requires, how links behave, the shape of a post's URL and of its identifiers, what can be read from outside. What belongs to one implementation (credentials, that service's errors, how to call it) stays in the provider.
- A skill's step is literal about where the platform comes from: the `Network:` field of the calendar row or post file the step works on; when there is none, the platform the request names; when neither names one, the skill asks. It then reads that platform's reference, and stops and says the platform is not supported when there is no such file.
- Scripts take `--platform`, and read simple machine data (URL patterns, host names, limits, media types) from `shared/references/platforms/<platform>.json` through a path given by flag (`--platform-file`), never from a table in the skill. A parser that is code for one platform stays in its skill behind `--platform`.
- A platform's cases live in `skills/<name>/evals/platforms/<platform>.json`, outside the skill's content hash. The gate and the score are computed on the base cases only; a platform's cases run with the skill only, as a partial test, and the status shows their mean and number of runs.
- Scope now: the first reference (the one platform built today) and the eight skills that carry its knowledge. References for other platforms are written when each has a real task, never from general knowledge.

Rejected: platform knowledge in each provider (one provider may serve several platforms, and six of the eight skills that need the knowledge declare no publisher); a table of platforms inside each skill (adding a platform would edit every skill and ask for a test of each).

The work is items C0.2 and C0.9 and the skills' rows of `docs/architecture/final-plan-2026-10-02.md`; the inventory of platform knowledge is `docs/architecture/audit-2026-10-02/platform-inventory.md`.

## 2026-10-02: Dependency alerts raised by eval fixtures: a standing rule

The code host's dependency graph reads every manifest in the repository, whatever `.github/dependabot.yml` says, so an eval fixture that names real packages raises alerts on packages nothing here ever installs. It has happened twice: 30 alerts from two fixtures of `ops-ci-pipeline`, dismissed by hand on 2026-09-28 (`docs/security/dependabot-triage-2026-09-28.md`), and 21 open on 2026-10-02, all from one manifest, `skills/eng-architecture/evals/files/content-model/package.json` (read from the host's alerts API that day). New advisories keep arriving against fixtures that do not change.

Bumping the fixture each time is not the answer. A fixture's manifest is part of its case, so a bump changes the case's hash, which drops that case's lab evidence and asks for a test of the skill, to silence an alert about code that never runs.

The rule, item A14 of `docs/architecture/final-plan-2026-10-02.md`:

1. **Invented packages wherever the case does not need the real ones.** A fixture manifest names packages that exist in no registry, under a fictional scope, as the fixture of `eng-security-review` already does: such a manifest raises no alert at all.
2. **Where the case needs real packages** (the skill must read a real framework's version, or a real tool's configuration), the versions are current on the day the skill's row is written, and **no lockfile that lists real transitive packages is committed**: a lockfile puts hundreds of packages into the dependency graph for one case. A lockfile of invented packages is fine.
3. **An alert a fixture raises later is dismissed**, with the reason "not used" and the comment "a test fixture, never installed". It is not fixed by a bump.
4. **The fixture is bumped only when its skill is next changed** for another reason, in the same pull request, so that the case changes once.

For case authors the rule is repeated in `evals/README.md`, which item C0.7 of the plan creates. The 21 open alerts are handled by the row of `eng-architecture` in phase C, which edits that fixture once; the row of `ops-ci-pipeline` follows point 2 for the lockfile it was going to add.

Whether the host can do point 3 by itself, with an alert rule that dismisses by manifest path under `skills/*/evals/files/`, was to be tried with this change. It was not settled, and this is what is known:

- The host's REST API, read with the command-line tool on 2026-10-02, has no endpoint for alert rules at the two paths tried under `dependabot/` (both answer "Not Found"), so the rule could not be created or tested from a pull request.
- Such a rule is created in the repository's settings page. That is a change of the repository's settings, which is the maintainer's to make, so it was not made here.
- Not verified: whether a custom rule of the host can match on a manifest path at all. If it can, the maintainer adds the rule and records it here; until then point 3 is done by hand, or through `eng-security-review`, whose dismissals sit behind a confirmation gate.

One setting goes with the rule: the host's automatic security-update pull requests stay off for this repository, so that none edits a fixture manifest. Read on 2026-10-02 from the repository's settings through the API: they are disabled.

Rejected: bumping fixtures as alerts arrive (each bump costs the case's evidence); removing the manifests from the fixtures (a project without a manifest is not the small real project a case needs); moving the fixtures out of the repository (the cases must ship with their skill).

## 2026-10-03: measurement version 5 closed

Phase B of the final plan is complete: what a run sees, how it is graded and scored, and the evidence it writes are settled for measurement version 5. Kind: the version and the floor were raised to 5 by the first commit of phase B (a grader-side change: the grader is shown the assistant's last message and a facts block), and every change since, to the image, the staging, the grading, the scoring and the adapters, was made while it was open. This closes it: nothing measured while it was open is evidence, and from this commit on the runner writes evidence under it.

- Measurement version 5, floor 5: every lab line below version 5 weighs nothing, and no line was converted from the 48 old records, which stay as the history of the first round (`skills/<name>/evals/result.json`). All 48 skills read `needs a test`, the intended state before their first full test.
- Fingerprint: `965d9daceaf76c445084882edab65909d6d5dea0c75bdc88853d46bf740bdbde`, over the grading template, `evals/measure.py` and `evals/measurement.json`, the executor and `evals/container/`, `scripts/stage_skills.py`, and the `run-prompt.sh` and `adapter.json` of the two eval adapters. The validator fails when it differs from the files; a later change to one of them is committed with `python3 evals/eval_status.py measurement --kind grader|execution|infrastructure --cause "<why>"`.
- The image: `wb-eval:55d46a74dd9b` (named after the hash of `evals/container/`), platform `linux/arm64`, digest `sha256:4a446f8ae551e20ccca1728602c6fa8ce510b73db4b1fdb17cf87ad21351eb28`. Kept as an archive made with `python3 evals/executor.py archive --out <file>`, sha256 `26073454f11dade40259da6410c7ad040368159db6ffd0712b181b80f46f220c`; the maintainer keeps the archive outside the repository, since two builds of one definition can differ.
- The last change inside the open version: the gate's two comparisons allow for the arithmetic of floats (`FLOAT_SLACK`, 1e-9, in `evals/measure.py`): six runs at 0.8 average 0.7999999999999999, which failed a threshold of 0.8.
- Built in phase B with it: the evidence store, one file per test event; full, partial and platform tests; the version file, the bump command and the version and class checks; guard and format tags and the second grading of a failed guard; the pessimistic score and the three bands, computed by `python3 evals/eval_status.py status`; the two snapshot tables of `docs/inventory.md`, a warning when behind and never an error; the field recorder, `scripts/evidence.py`; and the code owners of the measurement, the evidence, the version files and the old records (`.github/CODEOWNERS`).
- Written by `python3 evals/eval_status.py measurement --close`.

Not yet run, and listed in the pull request that closed the version as the proof run of phase B: the one skill run through the new harness on both tiers with a model, which the plan places before this close. Anything it finds is a change of one of the three kinds, committed with the command above.

## 2026-10-03: The proof run of phase B; the skill-listing measurement taken again; the grading's tokens

The first part of phase D ran on `main` at `cbe3321`: D1, D2, the proof run of phase B on `ops-branch-sync` (a trial of 2 runs per case, no evidence) and the listing measurement of A8 and C0.10. The full record is `docs/architecture/phase-d-proof-2026-10-03.md`. No fingerprinted file changed: measurement version 5 stands, with the same fingerprint.

- **The strong model id.** The pinned CLI accepts `claude-sonnet-5-5`, names it as the model of every run, and gives it a 200,000-token context and 32,000 output tokens. The gate file stays as it is.
- **One grading without tools: 11,622 tokens** on average over 24 gradings (11,013 to 12,032), against 29.6 thousand in the first round. A guard's second grading cost 11,987 tokens.
- **The grader's disagreement on this run:** `--regrade` of the 24 replies changed 2 of 96 verdicts (2.1%), and 1 of the 31 verdicts the first grading failed. This is one skill and one run of the instrument, not D4's measurement on the pilot.
- **The skill-listing measurement, default pack (48 skills, 37,718 characters of descriptions).** Installed by each harness's installer into a scratch home and asked once for its skill list:
  - `claude-code`: 28 of 48 descriptions reached the model, and 20 skills by name only.
  - `agents-dir` (opencode 1.18.32): 48 of 48.

  By decision 9 the harness that cuts the list has a budget setting, so the answer is the installer writing that budget when the person agrees (lane F3), and no description is shortened. Eval runs are not affected, since the strong eval adapter raises the budget (entry of 2026-10-01).
- **An operator error, resolved.** The floor tier's first attempt failed with `401 "User not found."` because the new OpenRouter key had been stored under another name than the store username the floor adapter reads (`openrouter`). Once it was stored under that name, `--resume` ran the 8 floor runs. This was no defect of the instrument. The runner did retry the 401 as an adapter failure, and that is listed with the other defects.
- **Defects found,** each with its smallest fix in the record; none in a fingerprinted file:
  - an authentication failure retried as an adapter failure (`evals/eval_run.py`);
  - `eval_status.py evidence` accepting an event whose `runs` differs from the configured number;
  - `ops-branch-sync` case 4, whose standing approval cannot be reached with `gh` signed out (a case defect, for the smoke pass);
  - `--regrade` and `--resume` resolving a relative path against the caller's folder before the repository.
