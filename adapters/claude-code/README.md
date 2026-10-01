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

`eval_run.py` creates the case folder (`--cwd`) in a temporary folder outside the repository and moves it into `evals-workspace/` afterwards, so a model that walks up from it finds no workbench; the adapter only needs to locate itself by its own path, which it does. `run-prompt.sh` implements the eval contract used by `core-skill-creator`: it runs one prompt with `claude -p`, makes the skill discoverable at project scope and limits settings to the project so user-level skills do not leak into a without-skill run. Commands are confined, not listed: see "Commands in an eval run" below. A prefix containing `(`, `)`, `,` or `*` is refused, since it would add rules. The skill under test and a case's dependencies (`--extra-skill-dir`) are copied into `.claude/skills/`, never linked into the workbench; a case folder that already holds `.claude/` or `.mcp.json` (from a fixture or a setup) is refused, because `--setting-sources project,local` would apply its rules, hooks or servers. No MCP servers or claude.ai connectors load: `--strict-mcp-config` and `ENABLE_CLAUDEAI_MCP_SERVERS=false` (https://code.claude.com/docs/en/mcp, read 2026-09-27), so an eval cannot write to a design tool or any other connected account. `eval_run.py` passes only an allowlisted environment: when the CLI authenticates through variables rather than its login, name them with `--pass-env` (for example `--pass-env ANTHROPIC_API_KEY`), and likewise `CLAUDE_EVAL_ARGS` for extra flags and `ANTHROPIC_BASE_URL` plus `ANTHROPIC_AUTH_TOKEN` to route a floor model through a proxy. Confirm isolation on the first run by searching the without-skill transcript for the skill's name.


## Commands in an eval run

Until 2026-10-01 a model could run only what matched a rule: each `--allow-command <prefix>` and each script of the skill was a `Bash(<prefix> *)` rule in `--allowedTools`, and print mode denied the rest. Rules match the text of a command, so harmless forms were denied: the skill's own script fed by a heredoc or called in a loop, a pipe into `tail`, a variable, `mktemp -d`. The strong model's runs kept on the maintainer's machine carry 809 denied commands; the skills where the strong model scored below the floor model are the ones with the most (22 in 6 runs of one skill, 17 of them its own script; 45 in 9 runs of another), while the floor model's adapter approved everything. The strong model was measured with fewer tools than the floor model.

Now every command runs, and the CLI's sandbox confines it (`--settings` with `sandbox.enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`, and a bare `Bash` rule; https://code.claude.com/docs/en/sandboxing, read 2026-10-01):

- It writes only inside the case folder, `/tmp` and the per-user temporary folder (bare `mktemp -d` on macOS ignores `TMPDIR`). Hooks and config inside `.git` and the installed skills stay read-only, so `git commit` works and `git init` does not: a case that needs a repository creates it in its setup.
- It reaches no network host; a local port can be opened and called. `--allow-web` adds the WebSearch and WebFetch tools and nothing for commands.
- It reads the machine except the workbench the adapter belongs to and `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.netrc`, `~/.config/gh`, `~/.docker`, `~/.kube`.
- If the sandbox cannot start (on Linux it needs bubblewrap and socat), the CLI exits with an error; it never falls back to running unconfined.

The case's `allow_commands` prefixes and the skill's own scripts are the exception (`sandbox.excludedCommands`): a call made only of them, in plain form, runs as the person, outside the sandbox, as it did under the rules. A script that starts a browser needs this (a browser's own sandbox does not start inside another), and so does one that calls a service. The CLI keeps a call sandboxed when it has a loop, a command substitution, a redirection other than `2>&1` or a `cd`, so a script that needs the browser fails in those forms and works when called plainly.

Checked on 2026-10-01 with real runs (CLI 2.1.283, Haiku): a loop over the skill's scripts, a heredoc, `mktemp -d`, `git commit`, `npm test` and a local HTTP server ran; `curl` to a public host, a write in the home folder, a read of the workbench, a write to `.git/hooks` and an edit of the installed skill were refused by the system; a render script of a skill produced its image through the browser; `permission_denials` was empty in every run.

`CLAUDE_EVAL_SANDBOX=off` (named with `eval_run.py --pass-env CLAUDE_EVAL_SANDBOX`) goes back to the rules alone, for a machine where the sandbox cannot run. Scores measured that way are lower than the model deserves and are not comparable with the others.

Not closed by this: the two tiers are still not confined alike. The floor model's adapter approves every command with no sandbox (backlog S19).

## Stopping a run

`run-prompt.sh` starts the runner in a session of its own, so the runner and everything it starts (model sessions, browsers, servers) form one process group. The group is ended, with TERM and then KILL after two seconds, when the runner returns and when the script itself gets TERM, INT or HUP (it then exits with 143). `eval_run.py` does the same one level up for every adapter call and setup command, on a timeout, on a signal and on any way out, so stopping an evaluation leaves no model session working. Before this, killing `eval_run.py` or passing a timeout left the sessions alive for many minutes. A process that moves itself into yet another session escapes this.

## Home and keychain on macOS

`run-prompt.sh` does not change `HOME`: the CLI's login belongs to the person's home, and on macOS their login keychain is found through it. So no throwaway keychain is created here (the agents-dir adapter needs one because it runs in a throwaway home), no `security` command is run, and a browser a model starts finds the person's own default keychain. An adapter that replaces `HOME` on macOS must provide a keychain there.
