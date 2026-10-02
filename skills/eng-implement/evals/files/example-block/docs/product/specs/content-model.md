# Specification: content model

- Owner: product-feature-spec
- Status: approved
- Date: 2026-04-27
- Ready for architecture: yes

## Requirements

- REQ-1: A documentation page is one Markdown file with a title, headings, paragraphs and named blocks.
- REQ-2: Code shown on a page is escaped and highlighted.
- REQ-3: A page is generated as one static HTML document.
- REQ-4: An example block shows the live result of its content and, below it, the code of that content exactly as the author wrote it, so that a reader can copy it. The author writes the example once.

## Acceptance criteria

- AC-1: Given a Markdown file with a title, headings, paragraphs and a block, when it is rendered, then each becomes its HTML and the block's body is handed to its component.
- AC-2: Given markup, when it is highlighted, then it is escaped and its tag names are marked.
- AC-3: Given `content/components/button.md`, when the page is generated, then the document carries the title and the note block.
- AC-4: Given `content/components/button.md`, when the page is generated, then the example block shows the rendered buttons and a highlighted code panel whose text equals the lines the author wrote in the block.
- AC-5: Given a component page with several example blocks, when the page is generated, then every one of them shows its preview and its code panel.
