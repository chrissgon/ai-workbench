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

- `plugin.json`: the manifest source, copied into every build. It names no `agents` path: the build's `agents/` folder is the default place.
- `overrides/<agent>.yaml`: model, tools, permissionMode per agent, merged into the generated agents.
- `connectors.json` (when needed): which requirement classes this harness satisfies through connectors, read by `scripts/doctor.py --harness claude-code`.
- `hooks/` (when needed): validation hooks, referenced from `plugin.json`.

## Limitations

- Symlinks are created at build time, so the filesystem running the build must support them (macOS, Linux; Windows needs developer mode). Nothing symlinked is committed.
- The linked folder under `~/.claude/skills/` is picked up as the plugin `ai-workbench@skills-dir`: confirmed on 2026-10-02 with CLI 2.1.283 in a scratch home, without a model call (`claude plugin list --json` reads `enabled: true`; `claude plugin details ai-workbench@skills-dir` lists the 48 skills and the 4 agents). The manifest must not carry an `agents` key: with `"agents": "./agents"` the same CLI refused the folder ("invalid manifest file ... agents: Invalid input") and loaded nothing; the `agents/` folder of the build is found by its default place. When a later version does not pick the link up, the fallback is `claude --plugin-dir adapters/claude-code/build/<pack>`, which `install.sh` prints with the build's path.
- The shared references are in the build, at `build/<pack>/shared/references`, so a skill's `../../shared/references/<file>` resolves by the installed path.
- One pack is installed at a time: an install removes the builds of other packs, and `--uninstall` removes the link and every build.

## Evals

`run-prompt.sh` implements the eval contract (`AGENTS.md`, "Adding an adapter"): it runs one prompt with `claude -p`, with the skill under test and a case's dependencies copied (never linked) into `.claude/skills/` of the case folder, settings limited to the project scope (`--setting-sources project,local`), and no MCP servers or claude.ai connectors (`--strict-mcp-config`, `ENABLE_CLAUDEAI_MCP_SERVERS=false`; https://code.claude.com/docs/en/mcp, read 2026-09-27). A case folder that already holds `.claude/` or `.mcp.json` is refused.

It runs only inside the eval container that `evals/eval_run.py` starts (`evals/executor.py`): the image sets `WB_EVAL_CONTAINER=1` and the script refuses to start without it. The container is the boundary, so every tool is allowed (`--dangerously-skip-permissions`); the web tools are disallowed unless the case sets `allow_web`. The CLI authenticates with `CLAUDE_CODE_OAUTH_TOKEN`, a long-lived token kept in the secret store (`contracts/secrets.md`) and named in `evals/eval-gate.json` (`strong_pass_env`).

The CLI lists the available skills to the model within a character budget, its bundled skills first. With the default budget a project skill whose description is a few hundred characters long was listed by name only: asked to quote its list, the model in the container showed `- core-clarify` with no text, while the bundled skills kept theirs. Without the description the model cannot tell when the skill applies, and in one case it answered on its own in 5 of 6 runs. `run-prompt.sh` therefore sets `SLASH_COMMAND_TOOL_CHAR_BUDGET=200000`; with it the description is listed in full and the same case used the skill in 5 of 5 runs (checked 2026-10-01, CLI 2.1.283). Whether the same happened on the host before the container is not known: those transcripts no longer exist.

How it got here, in one day (2026-10-01, `docs/decisions.md`): rules that matched the text of a command denied harmless forms and made the strong model score below the floor model (809 denied commands in the runs kept on the maintainer's machine); the CLI's own sandbox fixed that on the host; then every eval moved into a container, which made both the rules and the sandbox settings unnecessary and removed them.

## Stopping a run

`run-prompt.sh` starts the runner in a session of its own, so the runner and everything it starts (model sessions, browsers, servers) form one process group. The group is ended, with TERM and then KILL after two seconds, when the runner returns and when the script itself gets TERM, INT or HUP (it then exits with 143). `eval_run.py` does the same one level up for every adapter call and setup command, on a timeout, on a signal and on any way out, so stopping an evaluation leaves no model session working. Before this, killing `eval_run.py` or passing a timeout left the sessions alive for many minutes. A process that moves itself into yet another session escapes this.
