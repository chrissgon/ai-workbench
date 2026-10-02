import test from "node:test";
import assert from "node:assert/strict";
import { renderPage } from "../../app/markdown.ts";

const echo = { echo: (slot: string) => `<section>${slot}</section>` };

test("renderPage reads the title and renders headings and paragraphs", () => {
  const page = renderPage("---\ntitle: Button\n---\n# Button\n\nStarts an action.\n\n## Variants", {});
  assert.equal(page.title, "Button");
  assert.equal(page.html, "<h1>Button</h1>\n<p>Starts an action.</p>\n<h2>Variants</h2>");
});

test("renderPage hands a block's body to its component", () => {
  const page = renderPage("::echo\nplain text\n::", echo);
  assert.equal(page.html, "<section>plain text</section>");
});

test("renderPage rejects an unknown block and an unclosed block", () => {
  assert.throws(() => renderPage("::chart\nx\n::", echo), /unknown block "chart"/);
  assert.throws(() => renderPage("::echo\nx", echo), /block "echo" is not closed/);
});
