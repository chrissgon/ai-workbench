---
name: __NAME__
description: >
  __ROLE__. Delegate to this agent when __WHEN__.
metadata:
  skills: []
  version: "0.1"
---

# __TITLE__

## Role

One paragraph: who this agent is and the single kind of work it is trusted with.

## Scope

- Does: ...
- Does not: ... (name the agent or skill that does)

## Working rules

1. Load the skills listed in `metadata.skills` before starting.
2. ...

## Report format

Return exactly this structure, nothing else:

```markdown
## Summary
<two lines>

## Findings
- <file:line> — <finding> — <severity>

## Recommended next step
<one line>
```
