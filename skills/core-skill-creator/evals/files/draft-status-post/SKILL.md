---
name: ops-status-post
description: >
  Post a weekly delivery status to the team's chat channel: what shipped, what is blocked, what is
  next, read from the issue tracker. Use it when someone asks for the weekly status or "post the update".
license: MIT
metadata:
  area: delivery
  kind: capability
  inputs: [docs/workbench/state.md]
  outputs: []
  requires: [integration:issue-tracker, integration:chat]
  side_effects: []
  version: "0.1"
---

# Status post

## Procedure

Progress:
- [ ] Step 1: Read the tickets closed and blocked this week from the issue tracker, with their comments.
- [ ] Step 2: Draft the post: shipped, blocked (with the blocker in the ticket's words), next.
- [ ] Step 3: Save the draft to `/tmp/<channel-name>-status.md`, where the channel name is the one the user gave.
- [ ] Step 4: Post it to the channel with the available chat integration.
- [ ] Step 5: Record the post in `docs/workbench/state.md`.
