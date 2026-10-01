# Claude Code adapter

Builds a Claude Code plugin from the core for one pack and installs it. The adapter tracks no skill content and no symlinks: `build/<pack>/` is generated and ignored by git.

## Install

```bash
bash adapters/claude-code/install.sh                    # pack "default": every area except optional ones
bash adapters/claude-code/install.sh --pack all         # optional areas too
claude --plugin-dir adapters/claude-code/build/default  # one session only, after a build
```

Skills are invoked as `/ai-workbench:<skill-name>` and trigger automatically from their descriptions.

## What lives here and nowhere else

- `plugin.json`: the manifest source, copied into every build.
- `overrides/<agent>.yaml`: model, tools, permissionMode per agent, merged into the generated agents.
- `connectors.json` (when needed): which requirement classes this harness satisfies through connectors, read by `scripts/doctor.py --harness claude-code`.
- `hooks/` (when needed): validation hooks, referenced from `plugin.json`.

## Limitations

- Symlinks are created at build time, so the filesystem running the build must support them (macOS, Linux; Windows needs developer mode). Nothing symlinked is committed.
- Whether a symlinked folder under `~/.claude/skills/` is picked up as a plugin must be confirmed on the first real install; the fallback is `claude --plugin-dir`.

## Evals

`run-prompt.sh` implements the eval contract used by `core-skill-creator`: it runs one prompt with `claude -p`, makes the skill discoverable at project scope and limits settings to the project so user-level skills do not leak into a without-skill run. Each `--allow-command <prefix>` from a case's `allow_commands` becomes a `Bash(<prefix> *)` rule in `--allowedTools`, and so does every script in the skill's `scripts/` folder; any other command is denied and listed in `raw.json` `permission_denials` (checked on 2026-09-27 with a real run: an allowed `git status` ran, a denied `echo $VAR` was refused, and `touch` still ran because `acceptEdits` approves file commands inside the case folder). A prefix containing `(`, `)`, `,` or `*` is refused, since it would add rules. The skill under test and a case's dependencies (`--extra-skill-dir`) are copied into `.claude/skills/`, never linked into the workbench; a case folder that already holds `.claude/` or `.mcp.json` (from a fixture or a setup) is refused, because `--setting-sources project,local` would apply its rules, hooks or servers. No MCP servers or claude.ai connectors load: `--strict-mcp-config` and `ENABLE_CLAUDEAI_MCP_SERVERS=false` (https://code.claude.com/docs/en/mcp, read 2026-09-27), so an eval cannot write to a design tool or any other connected account. `eval_run.py` passes only an allowlisted environment: when the CLI authenticates through variables rather than its login, name them with `--pass-env` (for example `--pass-env ANTHROPIC_API_KEY`), and likewise `CLAUDE_EVAL_ARGS` for extra flags and `ANTHROPIC_BASE_URL` plus `ANTHROPIC_AUTH_TOKEN` to route a floor model through a proxy. Confirm isolation on the first run by searching the without-skill transcript for the skill's name.

## Stopping a run

`run-prompt.sh` starts the runner in a session of its own, so the runner and everything it starts (model sessions, browsers, servers) form one process group. The group is ended, with TERM and then KILL after two seconds, when the runner returns and when the script itself gets TERM, INT or HUP (it then exits with 143). `eval_run.py` does the same one level up for every adapter call and setup command, on a timeout, on a signal and on any way out, so stopping an evaluation leaves no model session working. Before this, killing `eval_run.py` or passing a timeout left the sessions alive for many minutes. A process that moves itself into yet another session escapes this.

## Home and keychain on macOS

`run-prompt.sh` does not change `HOME`: the CLI's login belongs to the person's home, and on macOS their login keychain is found through it. So no throwaway keychain is created here (the agents-dir adapter needs one because it runs in a throwaway home), no `security` command is run, and a browser a model starts finds the person's own default keychain. An adapter that replaces `HOME` on macOS must provide a keychain there.
