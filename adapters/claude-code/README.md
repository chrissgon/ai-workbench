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
