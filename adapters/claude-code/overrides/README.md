# Per-agent overrides for Claude Code

One YAML file per core agent, named `<agent-name>.yaml`. Keys are merged into the agent's frontmatter by `build.py`. Only Claude Code keys belong here; the core agent body stays untouched.

```yaml
# overrides/code-reviewer.yaml
model: sonnet
tools: Read, Grep, Glob, Bash
permissionMode: default
```
