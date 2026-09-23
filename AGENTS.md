# ai-workbench: maintainer instructions

You are maintaining a repository of agents, skills and workflows that let an AI build a digital solution end to end. This file tells you how the repository is organized and what rules every file must follow. Read it before adding or editing anything.

## Principles

1. **Harness-agnostic core.** Files under `skills/`, `agents/`, `shared/`, `contracts/` and `templates/` must not mention any AI tool by name, its directories (`.claude/`, `.cursor/`, `.codex/`, `.agents/`) or its tool names. Say "create the file", "run the command", "use the available issue-tracker integration; if there is none, ask the user to paste the ticket".
2. **Open-closed adapters.** Anything specific to one AI tool lives only inside `adapters/<harness>/`. Adapters read the core; the core never reads adapters. Adding a harness never edits the core.
3. **Write for the weakest model you will run.** See "Writing standard" below.
4. **Artifacts over invocation.** Capabilities never invoke other skills. They read and write artifacts in the target project (see `contracts/`). Only flows invoke skills, and they do it by name.
5. **English only.** Every file in this repository is written in English.

## Layout

```
skills/<name>/SKILL.md      one folder per skill, flat; prefix encodes the area
agents/<name>.md            agent bodies for delegation; frontmatter has only name, description, metadata
shared/references/*.md      cross-cutting references (security, accessibility, performance, privacy, prompting)
contracts/                  project-layout.md, state.md, environment.md, templates/ for artifacts
templates/                  capability.SKILL.md, flow.SKILL.md, agent.md
adapters/<harness>/         adapter.json, install.sh, optional build.*, overrides/, README.md
scripts/                    validate.py, new-skill.sh
docs/                       area-map.md, decisions.md, skill-authoring-guide.md
```

## Areas and prefixes

| Prefix | Area | Kind of area |
|--------|------|--------------|
| `biz-` | Business | lifecycle |
| `product-` | Product | lifecycle |
| `brand-` | Brand | lifecycle |
| `design-` | Design | lifecycle |
| `eng-` | Engineering | lifecycle |
| `ops-` | Delivery and operations | lifecycle |
| `mkt-` | Marketing and growth | lifecycle |
| `ai-` | AI and machine learning inside the solution | horizontal |
| `core-` | The workbench itself: orchestration, research method, skill creation, project memory | horizontal |
| `flow-` | Workflows that orchestrate skills, inside one area or across areas | orchestration |

Lifecycle areas form a chain: Business → Product → Brand → Design → Engineering → Delivery → Marketing. Horizontal areas have no fixed position; flows insert them at defined points. Full map, sub-areas and insertion points: `docs/area-map.md`.

**Boundary test** when a capability could belong to two areas: would a senior practitioner of that area know how to do this without expertise from the other area? If yes, it belongs to that area. Writing landing-page copy is Marketing even when a model writes it; designing how to show model uncertainty to a user is AI, because a designer without AI background does not know how.

**Transversal concerns** (security, accessibility, performance, privacy, documentation) are references in `shared/`, not areas: they constrain work, they do not produce artifacts of their own.

## Skill kinds

- **Capability** (`<area>-<name>`): does one job. Self-contained. Never invokes another skill. May load its own `references/` and `../../shared/references/`.
- **Flow** (`flow-<name>`): orchestrates capabilities by name, phase by phase, with a user checkpoint at the end of each phase. Reads and updates `docs/workbench/state.md` in the target project so it can resume across sessions. Phases may be optional.

An **agent** (`agents/<name>.md`) is a delegation target: a persona with a scope and a list of skills, used when a harness can run work in isolation or in parallel (review, exploration, implementation). Agents are few. Their body is harness-neutral; model, tools and permissions come from `adapters/<harness>/overrides/`.

## Frontmatter contract

```yaml
---
name: biz-business-model            # matches the folder; lowercase, hyphens; prefix from the table
description: >                       # 1–1024 chars; what it does AND when to use it; imperative; pushy
  ...
license: MIT
metadata:
  area: business                     # business | product | brand | design | engineering | delivery | marketing | ai | core
  kind: capability                   # capability | flow
  inputs: [docs/business/icp.md]     # artifacts read if present (paths relative to target project root)
  outputs: [docs/business/business-model.md]   # artifacts written
  requires: []                       # environment requirement classes, see contracts/environment.md
  side_effects: []                   # e.g. [publish], [deploy], [send]. Non-empty => "## Confirmation gate" section required
  version: "0.1"
---
```

`inputs`/`outputs` are the artifact contract in machine-readable form. The orchestrator uses them to know what already exists; `scripts/validate.py` checks that every input is produced by some skill.

`requires` names a *class* of tool (`integration:issue-tracker`, `generator:image`, `publisher:linkedin`), never a concrete product. The environment maps classes to concrete tools. A skill must say what it does when a requirement is missing (usually: produce the deliverable up to the point where the tool is needed, then stop and tell the user).

`side_effects` marks actuators: skills that change the world outside the repository. Actuators follow preview → explicit confirmation → execute → record in state. Never skip the confirmation.

## Writing standard

Cheap models drop steps in long lists, invent structure when there is no template, misjudge ambiguity and lose their way in branches. Write so that they cannot:

- One default path. Mention alternatives in one line, do not branch.
- Every step executable without inference. Nothing implied. Say which file to open, what to look for, what to write where.
- A template for every output. Put short templates inline and long ones in `assets/`.
- Criteria for every judgment: "approve if all of the following hold: ...".
- Checklists with tracked progress for anything with more than three steps.
- Scripts for anything deterministic (parsing, validation, formatting, API calls). Scripts accept input via flags, env or stdin, never prompts; implement `--help`; print data to stdout and diagnostics to stderr.
- Explicit stop-and-ask gates: "Stop here and ask the user if X is unclear."
- Load references per step ("When you reach step 4, read references/pricing-models.md"), never all up front.
- `SKILL.md` stays under 500 lines and roughly 5,000 tokens. Depth goes into `references/`, one level deep.

Every skill is evaluated with a strong model and with a floor model; it passes only when the floor model passes. Floor models are configured in the eval tooling, not named in skills.

## Adding a skill

1. `bash scripts/new-skill.sh --name <prefix-name> --kind capability|flow --area <area>`
2. Fill `SKILL.md` from the template. Delete sections that do not apply; do not leave placeholders.
3. Declare `inputs`, `outputs`, `requires`, `side_effects` honestly.
4. Add `references/`, `assets/`, `scripts/` only when the body needs them.
5. Add `evals/evals.json` with at least two realistic cases.
6. `python3 scripts/validate.py` until it reports zero errors.
7. Ground the content in real expertise: past corrections, real artifacts, real failures. Do not generate from generic knowledge. See `docs/skill-authoring-guide.md`.

## Adding an agent

Create `agents/<name>.md` from `templates/agent.md`. Frontmatter allows only `name`, `description` and `metadata`. Anything harness-specific goes to `adapters/<harness>/overrides/<name>.yaml`.

## Adding an adapter

Create `adapters/<harness>/` with `adapter.json`, `install.sh`, `README.md`, and optionally `build.*` and `overrides/`. Build outputs stay inside the adapter folder. The adapter may symlink or copy core folders; it may not modify them. `scripts/validate.py` fails if a core file references a harness.

## Validation

`python3 scripts/validate.py` checks: folder name equals `name`; prefix and area are valid and consistent; `kind` matches the prefix; description length; line limit; no harness names or paths in the core; `side_effects` implies a `## Confirmation gate` section; every `inputs` path is some skill's `outputs`; relative links resolve; agent frontmatter keys. Run it before every commit. `--strict` turns warnings into errors.

## Never

- Never put a harness name, path or tool name in a core file.
- Never store credentials in this repository. Providers read them from the environment.
- Never let a capability invoke another skill.
- Never ship an actuator without a confirmation gate.
- Never write a skill from generic knowledge without a real task to refine it against.
- Never write repository content in a language other than English.
