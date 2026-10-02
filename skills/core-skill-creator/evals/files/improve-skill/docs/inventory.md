# Inventory: capabilities, flows and agents

What the workbench should contain, per area. This is a plan, not a promise: a skill exists only after it has been written from the template, validated, and refined against at least one real task.

**State legend.** `rewrite`: same purpose as an earlier skill, new content. `create`: no prior content; must be written alongside a real task, never from generic knowledge. `planned`: not built until a real project demands it.

**Wave** is the build order.

## Delivery and operations (`ops-`)

| Skill | Produces | Reads | State | Wave |
|-------|----------|-------|-------|------|
| ops-release-notes | release notes for one version | the list of changes of that version | create | 1 |

## Evaluation status

A skill is done only when its status is `evaluated`. The status is computed, never written by hand: `evals/eval_status.py status` reads each skill's record, `skills/<name>/evals/result.json`, and compares the record's content hash with the skill folder.

The table below is generated. Do not edit it: run `python3 evals/eval_status.py inventory --write` after an eval run or a change to a skill; `scripts/validate.py` fails while it is out of date.

<!-- eval-status:begin -->
| Skill | Status | Strong with | Strong without | Floor with | Date | Iteration |
|-------|--------|-------------|----------------|------------|------|-----------|
| ops-release-notes | draft | — | — | — | — | — |

Counts: 0 evaluated, 0 stale, 1 draft, 1 skills.
<!-- eval-status:end -->

## Progress

A tick means the skill is built. Whether it passed its evals is in the status table above, not in the tick.

Wave 1:
- [x] ops-release-notes
