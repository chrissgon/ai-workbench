# ai-workbench

Harness-agnostic agents, skills and workflows that let an AI build a digital solution end to end: business, product, brand, design, engineering, delivery, marketing, and AI inside the product.

## Principles

1. **The core never depends on a specific AI tool.** Skills, agents, shared references and contracts speak in capabilities, not in harness tool names or paths.
2. **Adapters are open-closed.** Supporting a new AI tool means adding a folder under `adapters/`. It never means editing the core.
3. **Write for the weakest model you will run.** Every step explicit, every output templated, every judgment given criteria. Detailed does not mean long.
4. **Areas talk through artifacts, not calls.** A capability reads what earlier phases wrote to `docs/` in the target project; only flows invoke skills.
5. **Everything in this repository is written in English.**

## Layout

```
skills/        the core: one folder per skill, flat, prefix = area (see AGENTS.md)
agents/        harness-neutral agent bodies used for delegation (review, explore, implement)
shared/        references consumed by many skills (security, accessibility, prompting...)
contracts/     what skills read and write in a target project, and the state file schema
templates/     SKILL.md and agent templates used by scripts/new-skill.sh
adapters/      one self-contained folder per AI tool (claude-code, agents-dir, ...)
scripts/       repo tooling: validate.py, new-skill.sh
docs/          area map, decisions log, skill authoring guide
```

## Install

Each adapter documents its own install. From the factory:

- **Claude Code**: `bash adapters/claude-code/install.sh` (loads the repo as a plugin)
- **Codex, Cursor, Cline, OpenCode and any tool that reads `~/.agents/skills/`**: `bash adapters/agents-dir/install.sh`

## Validate

```bash
python3 scripts/validate.py
```

Runs on every commit-worthy change. It enforces naming, frontmatter, the 500-line limit, the no-harness-names rule, the artifact chain and confirmation gates for skills with side effects.

## Status

Structure and conventions are in place. Skills are being inventoried per area; see `docs/area-map.md`.
