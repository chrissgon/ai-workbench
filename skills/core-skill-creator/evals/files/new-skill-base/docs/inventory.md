# Inventory: capabilities, flows and agents

What the workbench should contain, per area. This is a plan, not a promise: a skill exists only after it has been written from the template, validated, and refined against at least one real task.

**State legend.** `rewrite`: same purpose as an earlier skill, new content. `create`: no prior content; must be written alongside a real task, never from generic knowledge. `planned`: not built until a real project demands it.

**Wave** is the build order.

## Flows (`flow-`)

| Flow | Area | Phases | State | Wave |
|------|------|--------|-------|------|
| flow-fix-bug | engineering | root-cause → unit-tests → implement → code-review → pull-request | rewrite | 1 |
| flow-build-feature | engineering | feature-spec → architecture → unit-tests → implement → code-review → pull-request | rewrite | 1 |
| flow-improve-code | engineering | codebase-map or impact-analysis → tradeoffs → refactor → code-review → pull-request | rewrite | 1 |
| flow-implement-ticket | engineering | read ticket → clarify → route to fix-bug, build-feature or improve-code → update ticket | create; requires `integration:issue-tracker` | 1 |

## Evaluation status

A skill is done only when its status is `evaluated`. The status is computed, never written by hand: `evals/eval_status.py status` reads each skill's record, `skills/<name>/evals/result.json`, and compares the record's content hash with the skill folder.

The table below is generated. Do not edit it: run `python3 evals/eval_status.py inventory --write` after an eval run or a change to a skill; `scripts/validate.py` fails while it is out of date.

<!-- eval-status:begin -->
| Skill | Status | Strong with | Strong without | Floor with | Date | Iteration |
|-------|--------|-------------|----------------|------------|------|-----------|

Counts: 0 evaluated, 0 stale, 0 draft, 0 skills.
<!-- eval-status:end -->

## Progress

A tick means the skill is built. Whether it passed its evals is in the status table above, not in the tick.

Wave 1:
- [ ] flow-fix-bug
- [ ] flow-build-feature
- [ ] flow-improve-code
- [ ] flow-implement-ticket
