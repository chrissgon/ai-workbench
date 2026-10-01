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

## 2026-10-01: Eval results are recorded per skill; status is computed

A review of the inventory found that most of the skills ticked as built had no eval result on record, and some of them scored low once measured. Five causes: "done" was a tick written by hand; results lived only in the git-ignored `evals-workspace/`; changing a skill did not force a new evaluation; `eval_run.py` let infrastructure failures (a provider out of credits, a session limit) pass as low or missing scores; and eval cases were never checked (fixtures copied to another path than the prompt named, prompts citing files the case did not ship, assertions the grader could not verify).

Decided: a complete, full run writes `skills/<name>/evals/result.json`, committed, with the scores, the gate and a sha256 of the skill folder. `scripts/eval_status.py` computes each skill's status from it: `draft` (no record, a failed gate or an incomplete run), `evaluated` (gate passed on the current content) or `stale` (gate passed, then the folder changed). The status table in `docs/inventory.md` is generated from it, and `scripts/validate.py` fails when a record is invalid or the table is out of date, so a commit that changes an evaluated skill shows it as stale in the same diff. `eval_run.py` checks every case before any model call, lists infrastructure failures apart from scores and marks the iteration incomplete, with its own exit code.

Rejected: rerunning evals in the pre-commit hook or in CI (model calls, cost and provider keys do not belong there; the check compares hashes instead and stays offline); a hash over `SKILL.md` alone (a script, a reference or a case changes behaviour or what is measured as much as the body does); making `stale` and `draft` errors by default (most skills start as `draft`; `--strict` turns them into errors once the backlog of unrecorded skills is cleared).

## 2026-10-01: A turn that ends early with no error is an infrastructure failure, retried and counted

In one day of floor-model runs, about one run in nine ended its turn early with exit 0 and no error: the model stopped mid-plan, printed a tool call as text, or looped writing reminder blocks to itself. Nothing was written, no question was asked, and the run scored zero, which is not the skill's doing.

Decided: `eval_run.py` detects an early end with a deterministic, conservative rule (no file created or changed, and a response that is empty, carries tool or control markup at the start of a line, or ends on a line that announces a next action while the response asks no question), reruns it in a fresh folder up to `--retries` times, keeps every early attempt, and counts them per model in `benchmark.json` and in the record. A run that early-ends on every attempt is an infrastructure failure and makes the iteration incomplete. A reply that asks the user a question and writes nothing is a stop-and-ask, and a run that wrote a file and then stopped before finishing is graded as it is: neither is an early end.

Retries hide the problem from the scores, so they must not hide it from the report: when a model has at least three early ends and either a rate above 15% of its attempts or all of them on one case, the runner prints a warning that says to read the transcripts and decide. Concentrated on one case, the skill or the case may trigger it; spread across cases, the provider or the model is unreliable, and another provider or another floor model is the answer. Rejected: scoring early ends as zeros (it measures the provider, not the skill) and a model as the judge of what an early end is (cost, and one more thing that can fail without an error).

## 2026-10-01: The floor model is DeepSeek V4.1 Flash; local models are a measured goal

The floor model changes from `openrouter/deepseek/deepseek-v3.2` to `openrouter/deepseek/deepseek-v4.1-flash`. All measured on 2026-10-01: it has open weights (MIT) and costs a fraction of the previous one; on the five evaluated skills it scored 1.00 with the skill in every run (0.40 to 0.57 without it), with no early end in 66 attempts, where the previous floor scored 0.81 to 1.00 and ended its turn early in 22% of the attempts of one run.

The purpose of the floor is restated: a good score on a very affordable open model is the passing criterion. Running on a person's own machine (Ollama, models of 20 to 30 billion parameters) is a goal that is measured and published, and it does not block a skill. First local results on one skill (design-system, 2 cases, 3 runs each, with the skill): gpt-oss 20B 0.26; Qwen3-Coder 30B 0.43; Devstral Small 2 24B unusable through the runner (it announces a step and ends its turn every time); Qwen3.8 27B still being measured. Other inexpensive hosted models on the same skill: DeepSeek V4 Flash 1.00, Qwen3.7 Flash 0.89, gpt-oss 120B 0.17 with early ends.

How it is enforced: the gate is a committed file, `scripts/eval-gate.json` (strong and floor model, their adapters, the floor model's key variable, the threshold). `eval_run.py` takes its defaults from it, so `eval_run.py --skill <name>` runs the gate. `scripts/eval_status.py` reads a record made on another floor model as `stale` ("evaluated on another floor model"), so changing the floor sends every skill back to be rerun, and judges recorded scores against the configured threshold. A full run on another floor model, a local one for instance, writes no record unless `--record-anyway`. The file sits outside `skills/`: it names adapters and models, which the core does not, and changing it alters no skill's content hash.

Rejected: keeping the previous records as passed (they did not pass on the current gate); a local model as the gate now (the best local score so far is 0.43); several floor models in one record (one gate, one answer).

## 2026-10-01: The strong model is Claude Sonnet 5.5; both eval models are named in one file

Decided by the maintainer. Every evaluation until this date used Claude Opus 5.5 as the strong model and as the grader; it used up the account's usage limit three times in two days, and 42 skills are still to be evaluated. The strong model of the gate is now Claude Sonnet 5.5: it is strong enough for the condition "the skill does not make a strong model worse" and for grading assertions, at a fraction of the usage. A record names the strong model it was made with; records made with the previous strong model stay valid (only a change of floor model or of the skill's content makes a record stale).

Both models, their adapters and the threshold live in `scripts/eval-gate.json`, and nowhere else. A session never passes a model to the runner: `python3 skills/core-skill-creator/scripts/eval_run.py --skill <name>` reads them from that file, so every session evaluates on the same pair. Changing a model is a change to that file, with an entry here.

## 2026-10-01: An eval run leaves nothing running and shows no dialog

Two defects found while running the gate on many skills on macOS.

A browser started inside a run showed the person a "Keychain Not Found" dialog, once per launch: the run's throwaway `HOME` has no `Library/Keychains`, and Chrome looks for its "Chrome Safe Storage" item in the default keychain, which macOS finds through `HOME`. A skill's script can start the browser with a mock keychain, but a model that starts one by itself cannot be controlled. Decided: an adapter that replaces `HOME` on macOS creates an empty keychain there and makes it the default, with every `security` call run under the throwaway `HOME` only, so the person's keychains are never touched; the keychain is deleted with that home. The adapter that keeps the person's `HOME` needs nothing.

Stopping an evaluation left its model sessions working for many minutes, and starting browsers: a timeout or a kill ended only the adapter's shell. Decided: `eval_run.py` runs every adapter call and setup command in a session of its own and ends the whole process group on a timeout, when the call returns, on TERM, INT or HUP, and on any way out; each adapter does the same for the runner it starts.

## 2026-10-01: Eval runs happen outside the repository

Case folders lived under `<repository>/evals-workspace/`, so a model could walk up from its case folder and find the workbench. Evidence from the runs of that day: a floor model's log shows `find <repository>/evals-workspace/...` and its reply to a without-skill case says it will use "the workbench's own" capability, "which lives in the skills repo"; 3 of 12 floor without-skill replies of one skill name the skill; on the strong tier, without-skill replies that mention the repository by name exist for six skills (6, 3, 3, 3, 2 and 2 response files). A harness may also load instruction files from the parents of the folder it runs in. The without-skill baseline was therefore inflated, which understates what a skill adds and can change the gate's strong condition (with the skill at least as good as without it).

Decided: `eval_run.py` runs every case and every grading in a fresh temporary folder outside the repository, whose parents hold no repository, instruction file or skills folder and whose path names neither the workbench nor the skill; the environment carries no path into the repository; the folder is moved to its place under `evals-workspace/` when the run ends, also after a timeout or a stop. As a guard, the output of every without-skill run is searched for the repository's path; a hit is recorded as `contaminated` and blocks the record unless `--allow-contaminated`. Records made before this keep their scores with the skill; `eval_run.py --only without --update-record` measures the baseline again, alone, and replaces the two without-skill scores of a record that is still current.

Not closed by this: a workbench installed globally in a harness, and a model that searches the whole disk; the guard reports the second.

## 2026-10-01: The strong model's eval commands are confined by a sandbox, not listed

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
