# agents-dir adapter

Installs the selected pack of skills into `~/.agents/skills/`, the directory that Codex, Cursor, Cline, OpenCode, OpenClaw and most tools following the Agent Skills standard scan. Nothing is generated; each skill folder is symlinked (or copied with `--copy`).

```bash
bash adapters/agents-dir/install.sh                # pack "default", user-level
bash adapters/agents-dir/install.sh --pack all     # optional areas too
bash adapters/agents-dir/install.sh --project .    # project-level: ./.agents/skills
```

## Limitations

- Agents (`agents/`) are not installed by this adapter: agent formats differ per tool. Add a dedicated adapter when a tool's subagent format is needed.
- References to `../../shared/` resolve only when the whole repository is present next to the symlinked skills. With `--copy`, shared references are not copied yet; use symlinks where possible.

## Evals

`run-prompt.sh` implements the eval contract with OpenCode (`opencode run`) by default, or any CLI through `RUN_PROMPT_CMD` (`{prompt_file}`, `{model}`, `{cwd}` placeholders, filled with shell-quoted values). Token counts are not reported. The skill under test and a case's dependencies (`--extra-skill-dir`) are copied into the case folder, never linked, so a run that approves every tool cannot edit the workbench; a case folder that already holds `.agents/`, `.opencode/` or `opencode.json` is refused. `--allow-command` is not enforced: the containment is the environment `eval_run.py` builds, so name the runner's provider key with `eval_run.py --pass-env`. No connectors or MCP servers load while the throwaway home is used (the default). Isolation caveat observed on the first run: the default runner also loads skills from the user-level skill directories of other tools, so a without-skill run is clean only if the workbench is not installed globally anywhere; check the transcript for the skill name.

## Floor model through OpenRouter

The floor runs recorded before 2026-09-28 used `claude-haiku-4-5-20251001` (35 runs, through the claude-code adapter) and `openrouter/deepseek/deepseek-v3.2` (6 runs, through this adapter), read from `evals-workspace/*/iteration-*/benchmark.json` on the maintainer's machine. OpenCode had no stored credentials (`opencode auth list`: 0), so the OpenRouter key came from the shell environment. Since the containment of 2026-09-27, `eval_run.py` passes only an allowlisted environment and this adapter uses a throwaway home, so the key must be named explicitly:

```bash
export OPENROUTER_API_KEY=...   # from the OS secret store or the environment settings, never a file in the repository
python3 skills/core-skill-creator/scripts/eval_run.py --skill <name> --harness claude-code --model <strong-id> \
  --floor-harness agents-dir --floor-model openrouter/deepseek/deepseek-v3.2 --pass-env OPENROUTER_API_KEY
```

Requires `opencode` on `PATH`.
