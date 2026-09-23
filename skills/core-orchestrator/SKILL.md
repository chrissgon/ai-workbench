---
name: core-orchestrator
description: >
  Route a request to the one skill or flow that should handle it, across business, product,
  brand, design, engineering, delivery, marketing, AI and the workbench itself. Use this skill
  first whenever a request could be handled by more than one skill, spans more than one area,
  continues a previous multi-phase effort, or when it is unclear whether a skill applies at
  all. Also use it when the user asks "where are we", "what's next" or "what can you do here".
  Do not use it for a one-step request that needs no specialized knowledge; answer that directly.
license: MIT
metadata:
  area: core
  kind: capability
  inputs: [docs/workbench/state.md]
  outputs: []
  requires: []
  side_effects: []
  version: "0.3"
---

# Orchestrator

## Purpose

Decide which skill runs, say why, and hand over. The orchestrator never does the work of the skill it routes to. It exists because skills are invoked by description and a request often matches several, spans several areas, or continues work from a previous session that only the project state knows about.

## When not to use

- A one-step request with no specialized knowledge ("rename this variable", "what does this error mean"): answer directly.
- The user names a skill explicitly: invoke that skill; do not re-route.
- You are already inside a flow and the request is the answer to its checkpoint: continue the flow.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| docs/workbench/state.md | no | Treat the request as standalone. If the chosen route is a flow, tell the user the flow will create the state file through `core-project-init`. |

## Procedure

Progress:
- [ ] Step 1: Read `docs/workbench/state.md` if it exists. Note: current flow, current phase, `Autonomy.Checkpoints`, open questions, approvals. If the request continues the current flow (answers its checkpoint, says "continue", "next", or names the phase), route to that flow and skip to step 7.
- [ ] Step 2: Classify the request's shape with the table below. Pick exactly one row.

  | Shape | Signals | Route to |
  |-------|---------|----------|
  | direct | one step, no specialized knowledge, no side effects | no skill; answer directly |
  | capability | one deliverable, one area ("validate the business model", "review this diff") | one `<area>-` skill |
  | flow, one area | several steps in one area, or a deliverable that needs earlier steps ("marketing strategy for the launch", "fix this bug end to end") | one `flow-` skill |
  | flow, cross-area | outcome spanning areas ("build a product from scratch", "launch X") | `flow-new-product` or the cross-area flow that matches |
  | ambiguous | two rows fit with different deliverables, or the target is unknown (which product, which repository) | ask (step 6) inside the routing block, with Route set to the most likely skill and status `pending`; use `core-clarify` only when the request is a plan that needs a full brief |

- [ ] Step 3: Find the area. Read [references/routing.md](references/routing.md) and match the request's *intent*, not its words; requests arrive in any language. If two areas fit, apply the boundary test: would a senior practitioner of area X know how to do this without expertise from area Y? If yes, X. Keep in mind: AI *inside the product* is the `ai-` area; the workbench improving itself is `core-`.
- [ ] Step 4: Pick the skill from the routing table row. If the routed skill is not available in this environment, say so, propose one fallback (the closest available skill, or direct execution with its limits stated) as a recommendation, and wait for the user's yes before proceeding. Add `- [ ] Skill gap: <request> → <missing skill>` to "Open questions" in the state file when it exists.
- [ ] Step 5: Check what the skill needs. For each artifact in its `inputs`, note present or missing. For each class in its `requires`, check the environment (run the environment doctor if available; otherwise look for the integration or provider). Missing inputs and requirements never block routing: the skill degrades as its body describes. You only report them.
- [ ] Step 6: If the shape was ambiguous or a key fact is unknown, stop and ask. At most three questions, each with a recommended answer. Do not guess the product, the repository, the platform or the audience. Ask *inside* the routing block: Route names the most likely skill with its shape word (`capability` or `flow`) and the status `pending`; fill Why, Context and Requirements with what you know; put the questions under Next. Never replace the shape word with `ambiguous`; ambiguity is expressed by `pending`. The block is the structure the reader relies on; it is never skipped, even when the answer is a question.
- [ ] Step 7: Write the routing block (template below), then invoke the chosen skill by name. Hand over everything you learned in steps 1 and 5 so the skill does not ask again.
- [ ] Step 8: Self-check against "Quality criteria" before invoking.

## Output template

```markdown
Route: <skill-name> (<capability | flow>, <ready | pending>)
Why: <intent> → <area> → <skill>, in one line
Context: found <artifacts present, or "none">; missing <artifacts absent, or "none">
Requirements: <class → satisfied by ... | missing → the skill will ...>; or "none"
Autonomy: <Autonomy.Checkpoints value, or "not set">
Next: <the first thing the routed skill will do, or the questions you are asking>
```

For `direct`, skip the block and answer.

## Quality criteria

Approve the route only if all of the following hold:

- Exactly one skill is named with its shape word, `ready` or `pending`; or the shape is `direct`.
- The routing block is present whenever the shape is not `direct`, including when the output is a set of questions.
- "Why" names the intent and the area, not keywords from the request.
- None of the routed skill's work was done here.
- Every missing input and unsatisfied requirement is stated; none blocked the route.
- Ambiguity was resolved by asking, never by picking the most likely option silently; a missing skill was never replaced by a fallback without the user's yes.
- `direct` was chosen only for a one-step request with no specialized knowledge and no side effects.
- If a state file exists, its current flow and autonomy mode were read and respected.

## Gotchas

- "Improve our onboarding" fits product, design, engineering and marketing. It is `ambiguous`; ask what "onboarding" and "improve" mean here before routing.
- A ticket is not automatically engineering. Read it (or ask for it) before routing; design and marketing tickets exist.
- A request that names a product with no `docs/` artifacts and no state file: ask where the project lives before assuming it is the current directory.
- Never start two flows for one request. A cross-area outcome goes to one cross-area flow, which invokes the others one level deep.
- Requests with side effects ("post", "send", "deploy", "delete") are never `direct`, even when they look like one step. Route to the skill that owns the confirmation gate; if none exists, execute only after showing the exact payload and getting an explicit yes.
- The user writing in Portuguese does not change the route. Match intent; reply in the user's language; keep artifacts in English unless the project says otherwise.
