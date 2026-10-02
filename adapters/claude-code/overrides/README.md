# Per-agent overrides for Claude Code

One YAML file per core agent, named `<agent-name>.yaml` after the file in `agents/` (`reviewer.yaml` for `agents/reviewer.md`). Keys are merged into the agent's frontmatter by `build.py`. Only Claude Code keys belong here; the core agent body stays untouched.

```yaml
# overrides/reviewer.yaml
tools: Read, Grep, Glob
```

The overrides that ship today set `tools`, and one of them `permissionMode`; none sets a model. Another Claude Code frontmatter key is added the same way when an agent needs it.
