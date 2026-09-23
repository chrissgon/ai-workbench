# agents-dir adapter

Installs the core skills into `~/.agents/skills/`, the directory that Codex, Cursor, Cline, OpenCode and most tools following the Agent Skills standard scan. Nothing is generated; each skill folder is symlinked (or copied with `--copy`).

```bash
bash adapters/agents-dir/install.sh                # user-level, all tools that read ~/.agents/skills
bash adapters/agents-dir/install.sh --project .    # project-level: ./.agents/skills
```

## Limitations

- Agents (`agents/`) are not installed by this adapter: agent formats differ per tool. Add a dedicated adapter when a tool's subagent format is needed.
- References to `../../shared/` resolve only when the whole repository is present next to the symlinked skills. With `--copy`, shared references are not copied yet; use symlinks where possible.
