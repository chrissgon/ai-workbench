# Design: content model

- Owner: eng-architecture
- Status: approved
- Date: 2026-04-29
- Specification: docs/product/specs/content-model.md
- Frameworks and versions relied on: Node 24 (runs `.ts` files by stripping types; `node:test`)

## Summary

A page is a Markdown file under `content/`. The renderer turns it into HTML and hands the body of every named block (`::name` ... `::`) to the block component registered under that name. The highlighter escapes and marks code. The generator wraps a rendered page in the layout. The example block shows a live preview of its body and the code of that body; how it gets the code is ADR-0002. Nothing here needs a dependency.

## Decisions

| # | Decision | Chosen | Class | ADR or source |
|---|----------|--------|-------|---------------|
| 1 | Where the example block takes the code it shows | Option A, to be confirmed by a spike | engineering | ADR-0002 (proposed) |

## Components

| Component | Responsibility | Location | Inputs | Outputs | Satisfies |
|-----------|----------------|----------|--------|---------|-----------|
| Renderer | Turns a Markdown file into HTML and calls block components | `app/markdown.ts` | Markdown text, components | `Page` | REQ-1 |
| Highlighter | Escapes markup and marks tag names | `app/highlight.ts` | code text | HTML | REQ-2 |
| Generator | Wraps a rendered page in the layout | `app/generate.ts` | a file path | an HTML document | REQ-3 |
| Note block | Renders an aside | `app/components/note.ts` | slot | HTML | REQ-1 |
| Example block | Renders a preview and the code panel | `app/components/example.ts` | slot | HTML | REQ-4 |

## Contracts

### Component interfaces

| Component | Props / inputs | Slots / events | Serves |
|-----------|----------------|----------------|--------|
| Renderer | `renderPage(source: string, components: Components): Page` | calls `component(slot)` once per block | REQ-1 |
| Every block component | `(slot: string) => string`; one argument, the block's body as the renderer hands it over | returns HTML | REQ-1 |
| Example block | the same interface | returns `<div class="example"><div class="example-preview">` preview `</div><pre class="example-code"><code>` highlighted code `</code></pre></div>` | REQ-4 |
| Highlighter | `highlight(code: string): string` | none | REQ-2 |
| Generator | `generatePage(file: string): string` | none | REQ-3 |

The component interface is shared by every block. Changing it (a second argument, another shape for `slot`) changes the renderer and every component, so it is decided in an ADR, not inside a task.

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|
| AC-1 | A page renders; a block's body reaches its component | unit | `node --test tests/unit/markdown.spec.ts` |
| AC-2 | Code is escaped and highlighted | unit | `node --test tests/unit/highlight.spec.ts` |
| AC-3 | A page is generated with its title and note | unit | `node --test tests/unit/generate.spec.ts` |
| AC-4 | The generated button page shows the preview and the authored code | spike | `node --test tests/spike/example.spec.ts` |
| AC-5 | Every example block of a page shows preview and code | unit | `node --test tests/unit/example.spec.ts` |

## Assumptions to verify before implementation

- The `Example block` can take the text the author wrote from the slot it receives (ADR-0002, option A). Verify by running `node --test tests/spike/example.spec.ts`: the page generated from `content/components/button.md` shows the rendered preview and a highlighted code panel equal to the authored example.

## Open questions

- none
