---
name: biz-pricing-notes
description: >
  Write down the pricing decisions the user states in the conversation, one line each, with the
  date and the reason. Use this skill when the user says "note this price" or "record our pricing".
license: MIT
metadata:
  area: business
  kind: capability
  inputs: []
  outputs: [docs/business/pricing-notes.md]
  updates: []
  requires: []
  side_effects: []
  version: "1.0.0"
---

# Pricing notes

## Purpose

Keep the pricing decisions of a project in one file, in the user's words.

## Stop rules

1. **No decision stated.** If the user's message states no price and no reason, write nothing and ask what was decided.

## Procedure

1. Take today's date from the command `date +%F`.
2. Append one line per decision the user stated to `docs/business/pricing-notes.md`: `- <date>: <the decision, in the user's words>. Reason: <the reason they gave, or "none given">`.
3. Reply with the lines you appended.
