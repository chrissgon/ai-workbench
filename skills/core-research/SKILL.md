---
name: core-research
description: >
  Research a question and return a sourced brief: every claim cited with URL, publisher,
  publication date and access date; key claims backed by two independent sources; facts
  separated from estimates and opinions; contradictions and unknowns listed. Use this skill
  whenever a decision needs facts from outside the repository: market size, competitors,
  prices, adoption, regulations, library comparisons, best practices, or "is this true?".
  Also use it when another skill needs evidence it does not have. Without a web search
  capability it still produces a limited brief and says so; it never invents a source.
license: MIT
metadata:
  area: core
  kind: capability
  inputs: [docs/workbench/state.md]
  outputs: [docs/workbench/research/<topic>.md]
  requires: [search:web]
  side_effects: []
  version: "0.1"
---

# Research

## Purpose

Replace "I believe" with "source [3] says, as of this date". The brief is written so that a reader can check every sentence, and so that the skill that asked for it (a business model, a launch plan, an AI feature) can cite it instead of guessing.

## When not to use

- The answer is in the repository, an artifact or the state file: read it; that is not research.
- The question is about the user's own intent or preferences: `core-clarify`.
- A single well-known fact with no consequence for a decision: answer inline, cite one source.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| The question and the decision it informs | yes | Stop and ask (step 1). A brief without a decision behind it has no stop criterion. |
| docs/workbench/state.md and related artifacts | no | Proceed; note that scope was not narrowed by prior decisions. |
| `search:web` capability (search and page fetch) | no | Degraded mode (step 8). The brief is marked `limited`. |

## Procedure

Progress:
- [ ] Step 1: Frame. Restate the question in one sentence and name the decision it informs. Fix the scope: geography, time period, language of the sources, and the stop criterion (default: two independent sources per key claim). If the question, the decision or the scope is unclear, ask at most three questions with recommended answers and wait. Numbers the user included in the question are claims to verify, not facts.
- [ ] Step 2: Decompose into sub-questions, each answerable with evidence. For each, write two or three queries with different phrasings, in the language of the target market when it is not English.
- [ ] Step 3: Search and read. For each result you keep, capture at once: URL, title, publisher, publication date (not the copyright year, not "updated"), access date, tier from [references/sources.md](references/sources.md), and the exact quote or figure with its unit. Follow a number to its origin: who measured it, how. Keep looking deliberately for a source that disagrees.
- [ ] Step 4: Verify. A key claim needs two independent sources; ten outlets repeating one press release are one source. Classify every claim as `fact` (measured, primary), `estimate` (modelled or projected, method stated or not) or `opinion`. Flag anything older than the recency threshold (default 12 months for technology, market and pricing data; 3 years for regulation and standards unless amended).
- [ ] Step 5: Where sources disagree, record both values and the likely reason (different method, period, definition). Do not average them or pick one silently.
- [ ] Step 6: Synthesize per sub-question with a confidence level: `high` (two or more tier 1–2 sources, recent, agreeing), `medium` (one strong source, or agreeing weaker ones), `low` (single or tier 3 source, old, or disputed). List what remains unknown and what the findings imply for the decision. Implications are one line each and stay inside the question; the skill that asked decides.
- [ ] Step 7: Write the brief from the template to `docs/workbench/research/<topic>.md`. Report: path, the answer in brief, confidence, unknowns, and the skill that should consume it.
- [ ] Step 8: Degraded mode, when `search:web` is unavailable: say so first. Still do steps 1 and 2 (the query plan lets the user run the searches). Search only registered artifacts and the codebase. Anything you know from training goes exclusively into "Unverified background", labelled as such, with no fabricated URL or date. Mark the brief `Status: limited`.
- [ ] Step 9: Self-check against "Quality criteria". Open every URL once more if fetching is available; remove any citation you cannot reproduce.

## Output template

Write to `docs/workbench/research/<topic>.md`:

```markdown
# Research: <topic>

- Owner: core-research
- Status: draft | limited
- Date: <YYYY-MM-DD>
- Question: <one sentence>
- Informs: <decision or skill>
- Scope: <geography>, <period>, <source languages>
- Search capability: available | unavailable

## Answer in brief
- <claim> (fact | estimate | opinion) [1][4] — confidence: high
- ...

## Findings by sub-question
### <sub-question>
- <claim with figure and unit> (fact) [2][3] — confidence: medium. Note: <recency or method>

## Contradictions
- [2] reports <X>; [5] reports <Y>. Likely reason: <method, period, definition>. Or: none found.

## Unknowns
- <what could not be established and what would establish it>

## Implications for <decision>
- <one line each, no recommendation beyond the question>

## Unverified background
Only in limited mode. From training knowledge, not checked against a source: ...

## Sources
[1] <Title> — <Publisher>. Published <YYYY-MM-DD | undated>. Accessed <YYYY-MM-DD>. <URL>. Tier <1|2|3>. Quote: "<exact words or figure>"

## Method
Queries run: ... Excluded: <what and why>. Threshold for recency: <months>.
```

## Quality criteria

Approve the brief only if all of the following hold:

- Every claim in "Answer in brief" and "Findings" carries at least one citation; every key claim carries two independent sources or is explicitly marked single-source.
- Every source lists URL, publisher, publication date or `undated`, access date, tier, and the supporting quote or figure with unit.
- No number appears anywhere without a source, except inside "Unverified background" in limited mode.
- Items older than the recency threshold are flagged next to the claim.
- "Contradictions" and "Unknowns" are present, with content or an explicit "none found".
- The question and the decision it informs were read or asked, never guessed.
- In limited mode, `Status: limited` is set and nothing outside "Unverified background" comes from memory.

## Gotchas

- Ranking is not quality. Content farms and machine-written summaries rank well; check the publisher and look for the primary source they are paraphrasing.
- A press release republished by many outlets is one source. Independence means different origin, not different URL.
- Market sizes come from someone's model. Name the firm and the method or classify as `estimate` with method unknown.
- Publication date is the article's, not the page footer's copyright year and not a "last updated" stamp on a template.
- "Millions" and "billions", monthly and yearly, users and downloads: quote the exact figure and unit, in the source's words.
- Questions about a non-English market need sources in that language; English-only results skew toward the US.
- Stop at the stop criterion, not at the first confirming source, and not after the tenth tangent. If two sub-questions remain unresolved after reasonable effort, list them as unknowns rather than lowering the bar.
- Never write a URL you did not open. A plausible-looking citation that does not exist is the worst outcome this skill can produce.
