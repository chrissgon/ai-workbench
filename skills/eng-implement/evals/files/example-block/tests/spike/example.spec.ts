// Check of T-cm-4 (design assumption 1, ADR-0002): generate one page and look at its example block.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { generatePage } from "../../app/generate.ts";

const FILE = "content/components/button.md";
const html = generatePage(FILE);

// The lines between "::example" and "::" in the page's Markdown file, as the author wrote them.
function authoredExample(): string {
  const lines = readFileSync(FILE, "utf8").split("\n");
  const start = lines.indexOf("::example");
  return lines.slice(start + 1, lines.indexOf("::", start)).join("\n");
}

function codePanel(): string {
  const panel = html.match(/<pre class="example-code"><code>([\s\S]*?)<\/code><\/pre>/);
  assert.ok(panel, 'the page has no <pre class="example-code"><code> panel');
  return panel[1];
}

// The text a reader sees and copies: highlight spans removed, entities decoded.
function visibleText(code: string): string {
  return code
    .replace(/<\/?span[^>]*>/g, "")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&amp;", "&");
}

test("the page shows the rendered preview of the example", () => {
  assert.ok(
    html.includes(
      '<div class="example-preview"><button class="fl-button fl-button--primary">Save</button>' +
        '<button class="fl-button fl-button--ghost">Cancel</button></div>',
    ),
  );
});

test("the code panel is highlighted", () => {
  assert.match(codePanel(), /<span class="hl-tag">/);
});

test("the code panel shows the example exactly as the author wrote it", () => {
  assert.equal(visibleText(codePanel()), authoredExample());
});
