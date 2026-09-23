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
