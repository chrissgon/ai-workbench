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
