# Backlog: fernleaf-docs

- Owner: product-backlog
- Status: approved
- Updated: 2026-05-06

## Feature: content model (`T-cm`)

- Specification: docs/product/specs/content-model.md
- Design: docs/engineering/designs/content-model.md
- Sources: the design's contracts, verification plan and assumption 1; docs/engineering/adr/0002-example-block-source.md

### Tasks

- T-cm-1: Markdown renderer with named blocks
  Does: creates `app/markdown.ts`, which renders a page and hands each block's body to its component.
  Delivers: REQ-1, AC-1
  Touches: Renderer, `app/markdown.ts`, `tests/unit/markdown.spec.ts`
  Depends on: none
  Check: `node --test tests/unit/markdown.spec.ts`; every test passes (verification plan: AC-1)
  Size: M, because the block contract had to be confirmed
  Milestone: M1
  Status: done (2026-05-04) node --test tests/unit/markdown.spec.ts: 3 passed, 0 failed
- T-cm-2: Highlighter
  Does: creates `app/highlight.ts`, which escapes markup and marks tag names.
  Delivers: REQ-2, AC-2
  Touches: Highlighter, `app/highlight.ts`, `tests/unit/highlight.spec.ts`
  Depends on: none
  Check: `node --test tests/unit/highlight.spec.ts`; every test passes (verification plan: AC-2)
  Size: S, because one file with a clear contract
  Milestone: M1
  Status: done (2026-05-04) node --test tests/unit/highlight.spec.ts: 2 passed, 0 failed
- T-cm-3: Page generator, note block and the component registry
  Does: creates `app/generate.ts`, `app/components/note.ts` and `app/components/index.ts`; registers an example block that renders the preview only, and adds the spike's check file.
  Delivers: REQ-3, AC-3
  Touches: Generator, Note block, `app/generate.ts`, `app/components/note.ts`, `app/components/index.ts`, `scripts/generate.ts`, `tests/unit/generate.spec.ts`, `tests/spike/example.spec.ts`
  Depends on: T-cm-1
  Check: `node --test tests/unit/generate.spec.ts`; every test passes (verification plan: AC-3)
  Size: M, because several files
  Milestone: M1
  Status: done (2026-05-06) node --test tests/unit/generate.spec.ts: 2 passed, 0 failed
- T-cm-4: Spike: the example block can take the authored code from its slot
  Does: implements the code panel of the example block as ADR-0002 option A, in `app/components/example.ts` only, runs the check, and records the result under "Spike outcome" in ADR-0002, whether the option holds or not.
  Delivers: REQ-4, AC-4
  Touches: Example block, `app/components/example.ts`, `docs/engineering/adr/0002-example-block-source.md`
  Depends on: none
  Check: `node --test tests/spike/example.spec.ts`: the page generated from `content/components/button.md` shows the rendered preview and a highlighted code panel equal to the authored example (design assumption 1)
  Size: L, because a spike
  Milestone: M2
- T-cm-5: Example blocks on every component page
  Does: covers a page with several example blocks and adds the unit spec of the example block.
  Delivers: REQ-4, AC-5
  Touches: Example block, `app/components/example.ts`, `tests/unit/example.spec.ts`
  Depends on: T-cm-4
  Check: `node --test tests/unit/example.spec.ts`; every test passes (verification plan: AC-5)
  Size: S, because one file with a clear contract
  Milestone: M2

### Order

- Spikes: T-cm-4 (assumption 1) gates T-cm-5
- Critical path: T-cm-1 → T-cm-3
- Parallel tracks: T-cm-2 alongside T-cm-1; T-cm-4 alongside T-cm-1

### Milestones

- M1 pages generate: T-cm-1, T-cm-2, T-cm-3 → usable state: a Markdown page becomes an HTML document with highlighted code and notes
- M2 examples show their code: T-cm-4, T-cm-5 → usable state: every example shows its preview and the code the author wrote

### Coverage

| Id | Delivered by |
|----|--------------|
| REQ-1 | T-cm-1 |
| REQ-2 | T-cm-2 |
| REQ-3 | T-cm-3 |
| REQ-4 | T-cm-4, T-cm-5 |
| AC-1 | T-cm-1 |
| AC-2 | T-cm-2 |
| AC-3 | T-cm-3 |
| AC-4 | T-cm-4 |
| AC-5 | T-cm-5 |

### Open questions

- none
