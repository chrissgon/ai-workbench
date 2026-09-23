---
name: core-critique
description: >
  Adversarially review a plan, proposal, artifact or proposed solution before anyone acts on
  it: find the concrete ways it fails, each with a trigger, an impact and a test or
  mitigation, and give a verdict with conditions. Use this skill when the user asks for a
  critique, a stress test, a devil's advocate, "what could go wrong", or a second opinion on a
  business model, a PRD, a design, a launch plan, an AI feature or a bug-fix approach; and as
  the review step of flows before implementation or publication. Not for reviewing code diffs
  (that is eng-code-review) or for resolving open decisions (that is core-clarify).
license: MIT
metadata:
  area: core
  kind: capability
  inputs: [docs/workbench/state.md]
  outputs: [docs/workbench/critiques/<topic>.md]
  requires: []
  side_effects: []
  version: "0.1"
---

# Critique

## Purpose

Assume the proposal will fail and find out how, before it costs anything. A critique is a list of concrete failure modes with what triggers each one, what breaks, and what would reveal or prevent it, closed by a verdict. It exists to make the proposal better; it never rewrites the proposal, which stays with the skill that owns it.

## When not to use

- A code diff: `eng-code-review`.
- Decisions still open, a plan that is not yet a plan: `core-clarify` first. A critique of a guessed intent is noise.
- The user wants alternatives compared rather than one proposal attacked: `eng-tradeoffs` for technical options; for other areas, ask which proposal to critique.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| The proposal under critique (a file path, a message, or an artifact in `docs/`) | yes | Ask for it. Never critique from memory of a conversation alone; ask the user to point at the text. |
| Its stated goal (in the proposal, a brief, a root-cause document or the state file) | yes | Stop and ask what the proposal must achieve, with your best reading as the recommendation. Do not proceed on a guessed goal. |
| docs/workbench/state.md | no | Skip the contradiction check against recorded decisions. |

## Procedure

Progress:
- [ ] Step 1: Ground. Read the proposal in full, the artifacts it builds on, the recorded decisions in the state file, and, for anything that touches code, the code it changes and the code that consumes it. Restate the proposal in at most five lines, then list every assumption it rests on as `Assumes: ...`. Unstated assumptions are the first place failures hide.
- [ ] Step 2: Pick the lenses. Open [references/lenses.md](references/lenses.md) and take the lens set for the proposal's domain (engineering, business, product, design, marketing, AI). Add the "any proposal" lens, always.
- [ ] Step 3: For each lens category, ask "how does this fail?" and write down only failures with a concrete trigger (an input, a state, an event, an actor) and an observable impact. A worry without a trigger is not a finding; drop it or turn it into a question for the user.
- [ ] Step 4: Check alignment. Does the proposal address the stated goal or root cause, or a symptom of it? Cite the goal and the part of the proposal that addresses it. Missing alignment is a blocking finding.
- [ ] Step 5: Check contradictions with recorded decisions, registered artifacts and the codebase. Each one is a finding that names both sides.
- [ ] Step 6: Rate each finding with the table below: severity and likelihood. Then give it a mitigation or a test that would reveal it, actionable by the owner skill.
- [ ] Step 7: Enforce the minimum. At least two findings. If, after all lenses, none with a real trigger exists, write two "what if" scenarios you tested and why the proposal holds under each; never write "looks good".
- [ ] Step 8: Verdict. `approved`, `approved with changes` (list them; each maps to a finding) or `needs revision` (any blocking finding). Write the artifact from the template, report the path, the verdict and the blocking findings, and name the owner skill that should act.
- [ ] Step 9: Self-check against "Quality criteria".

Severity: `blocking` (defeats the goal, loses data or money, irreversible or public harm), `high` (likely to fail for a common case), `medium` (fails for an edge case, recoverable), `low` (quality or cost issue). Likelihood: `high`, `medium`, `low`, judged from how common the trigger is.

## Output template

Write to `docs/workbench/critiques/<topic>.md`:

```markdown
# Critique: <topic>

- Owner: core-critique
- Status: draft
- Date: <YYYY-MM-DD>
- Proposal: <path or reference>
- Goal it must achieve: <quoted or cited>

## Proposal in five lines
...

## Assumptions the proposal rests on
- Assumes: ... (stated | unstated)

## Findings
| # | Failure mode | Trigger | Impact | Severity | Likelihood | Test or mitigation | Where |
|---|--------------|---------|--------|----------|------------|--------------------|-------|
| 1 | ... | ... | ... | blocking | high | ... | <section, file:line> |

## Alignment with the goal
<addresses the goal | addresses a symptom: ...>

## Contradictions
- <decision or artifact> vs <proposal part>; or "none"

## What-if scenarios tested (when fewer than two findings)
- What if ...: holds because ...

## Verdict
<approved | approved with changes | needs revision>
Conditions: <one per changed finding>, or "none"
Next: <owner skill>, because ...
```

## Quality criteria

Approve the critique only if all of the following hold:

- Every finding has a trigger, an impact, a severity, a likelihood, a test or mitigation, and a location in the proposal or code.
- There are at least two findings, or two tested what-if scenarios with the reason each holds.
- Every assumption the proposal rests on is listed, marked stated or unstated.
- The goal was read or asked, never guessed; alignment is judged against it explicitly.
- The proposal itself was not edited.
- The verdict's conditions map one to one to findings; no condition appears without a finding.

## Gotchas

- Happy-path success says nothing about edge cases; the lenses exist so you look at boundaries, timing, state, integration and scale on purpose.
- "No side effects" is an assumption. Find the consumers of what changes and check each.
- A fix that removes the symptom may leave the cause; compare against the root-cause document when one exists.
- Performance claims without a measurement are hope; ask for the number or mark the claim as an unstated assumption.
- In business proposals, "no competitors" means the search was not done; top-down market sizing without a bottom-up check is a finding, not a fact.
- In AI features, hallucination and cost at scale are normal outcomes, not edge cases; a proposal without an eval set and a cost ceiling has two findings already.
- Be adversarial with the proposal, not with the person. Every finding carries a way out.
- Fewer, sharper findings beat a long list of worries. If a finding has no trigger, it is not a finding.
