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

`run-prompt.sh` implements the eval contract (`AGENTS.md`, "Adding an adapter"): it runs one prompt with `claude -p` in the case folder, with settings limited to the project scope (`--setting-sources project,local`) and no MCP servers or claude.ai connectors (`--strict-mcp-config`, `ENABLE_CLAUDEAI_MCP_SERVERS=false`; https://code.claude.com/docs/en/mcp, read 2026-09-27). It installs nothing. Before it starts, the eval runner has copied the skill under test (in a run with the skill only) and a case's dependency skills into `.claude/skills/` of the case folder, through `scripts/stage_skills.py`, without their `evals/` and `scripts/tests/`, with the shared references the skill cites beside them; and the runner, not this script, has refused a case folder that carries a name of `eval.settings` in `adapter.json` (`.claude`, `.mcp.json`, `CLAUDE.md`, `CLAUDE.local.md`), from a fixture or from a setup command.

What a run leaves: `response.md`, the assistant's last message, which is the reply the grader is given; `stream.jsonl`, the CLI's whole event stream, kept beside it and never shown to the grader; `timing.json`, with the tokens, the cost and `skills_loaded`, the skills the stream shows the model loading, which the runner records as whether the skill under test was invoked (never scored). A grading call runs with `--no-tools`: the grader holds this tier's credential and reads text a model under test wrote, so it gets no tool at all. `adapter.json` holds what an exhausted account answers (`eval.account_limit`: the runner then pauses every run on the account until a probe succeeds or the operator gives a time) and the refusal markers (`eval.refusal_markers`). `run-prompt.sh` and `adapter.json` are in the measurement fingerprint: a change to either is committed as one of the three kinds of measurement change (`AGENTS.md`, "Writing standard"; `python3 evals/eval_status.py measurement`).

It runs only inside the eval container that `evals/eval_run.py` starts (`evals/executor.py`): the image sets `WB_EVAL_CONTAINER=1` and the script refuses to start without it. The container is the boundary, so every tool is allowed (`--dangerously-skip-permissions`); the web tools are disallowed unless the case sets `allow_web`. The CLI authenticates with `CLAUDE_CODE_OAUTH_TOKEN`, a long-lived token kept in the secret store (`contracts/secrets.md`) and named in `evals/eval-gate.json` (`strong_pass_env`). A run of a case on the open network (`web_cases` of the gate file) gets `CLAUDE_CODE_WEB_API_KEY` instead (`strong_web_pass_env`), an API key with a low spend limit, which reaches the CLI as its API key.

The CLI lists the available skills to the model within a character budget, its bundled skills first. With the default budget a project skill whose description is a few hundred characters long was listed by name only: asked to quote its list, the model in the container showed `- core-clarify` with no text, while the bundled skills kept theirs. Without the description the model cannot tell when the skill applies, and in one case it answered on its own in 5 of 6 runs. `run-prompt.sh` therefore sets `SLASH_COMMAND_TOOL_CHAR_BUDGET=200000`; with it the description is listed in full and the same case used the skill in 5 of 5 runs (checked 2026-10-01, CLI 2.1.283). Whether the same happened on the host before the container is not known: those transcripts no longer exist.

How it got here, in one day (2026-10-01, `docs/decisions.md`): rules that matched the text of a command denied harmless forms and made the strong model score below the floor model (809 denied commands in the runs kept on the maintainer's machine); the CLI's own sandbox fixed that on the host; then every eval moved into a container, which made both the rules and the sandbox settings unnecessary and removed them.

The home a run sees is the container's own (`/home/eval`): this adapter does not replace `HOME`, while the floor model's adapter (`adapters/agents-dir/`) gives each run an empty temporary home. The two tiers' commands therefore see different homes, both inside the container and neither the home of the person who runs the evals; a case must not depend on what a home holds.

The token the strong model's runs use inside the container is registered by this adapter, in the `secrets` list of `adapter.json` (the core's registry in `providers/secrets/resolver.py` names no adapter); the name passed into the runs has one home, `strong_pass_env` of `evals/eval-gate.json`, and `eval_run.py` fills it from the OS secret store when it is not exported. `python3 scripts/doctor.py` shows whether it is found, never its value.

Lab evidence on the reference model, the strong model of the gate file, comes from tests the maintainer runs on the maintainer's account (`evals/README.md`). A run made with a stand-in runner or grader, such as this adapter's tests and the container job, is not evidence: the runner writes its files into a scratch tree inside the run folder, never into a skill's evidence folder.

## Recording a use in a project

Field evidence, a real use of a skill in a project, is recorded with `scripts/evidence.py record --start` when the use begins (the reliability model, section 7). This adapter does not install a hook for it yet (plan item F9: the installer will write a hook with the checkout's absolute path and the model id the harness gives). Until then the block of the project's instruction file, written by `core-project-init`, asks the model to run the command; the model id is then `unknown`, since it is never taken from a model's own account of what it is.

## Runtime runs

`run-agent.sh` implements the runtime contract (`contracts/runtime.md`): one agent on one task, for `scripts/runtime.py`. The run happens in `<out>/cwd`, with the agent's skills copied (never linked) into `.claude/skills/<name>`, without their `evals/` and `scripts/tests/`. The model gets the reading tools only (`--tools Read,Glob,Grep`), so it reaches a skill by reading its file: the system prompt, after the agent's body, lists each skill's `SKILL.md` path. `--project` is added as a folder the tools may use (`--add-dir`); this adapter does not confine the reading tools to it and the run folder, and whether the CLI lets them read elsewhere is the CLI's rule, which nothing here checks (backlog N15). The CLI runs in a session of its own: at `--timeout-seconds`, and whenever it returns, its whole process group is ended (TERM, then KILL five seconds later), so nothing it started outlives the run; a timeout is `exit_code` 124 in `timing.json`. `tests/test_claude_code_run_agent.py` checks all of this with a stand-in `claude` on the `PATH` (no model is called).

## Stopping a run

`run-prompt.sh` starts the runner in a session of its own, so the runner and everything it starts (model sessions, browsers, servers) form one process group. The group is ended, with TERM and then KILL after two seconds, when the runner returns and when the script itself gets TERM, INT or HUP (it then exits with 143). `eval_run.py` does the same one level up for every adapter call and setup command, on a timeout, on a signal and on any way out, so stopping an evaluation leaves no model session working. Before this, killing `eval_run.py` or passing a timeout left the sessions alive for many minutes. A process that moves itself into yet another session escapes this.
