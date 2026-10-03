---
name: product-ticket-sync
description: >
  Turn the approved items of the product backlog into tickets in the team's tracker. Use this
  skill when the user asks to sync the backlog with the tracker or to open tickets for a release.
license: MIT
metadata:
  area: product
  kind: capability
  inputs: [docs/product/backlog.md]
  outputs: []
  updates: [docs/product/backlog.md]
  requires: [integration:issue-tracker]
  side_effects: []
  version: "1.0.0"
---

# Ticket sync

## Purpose

Keep the tracker and the backlog in step, so that nobody copies items by hand.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| docs/product/backlog.md | yes | Stop and tell the user that `product-backlog` writes it and to run it first. |

## Procedure

1. Read `docs/product/backlog.md` and list the items whose status is `approved`.
2. Once the backlog is approved, use the available issue-tracker integration to open one ticket per approved item, with the item's title and its acceptance criteria.
3. Write each ticket's link into the backlog, next to its item.
4. Reply with the number of tickets opened and the link of each.
