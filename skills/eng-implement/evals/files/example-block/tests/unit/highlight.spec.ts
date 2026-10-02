import test from "node:test";
import assert from "node:assert/strict";
import { highlight } from "../../app/highlight.ts";

test("highlight escapes markup and marks tag names", () => {
  assert.equal(
    highlight('<a href="/x">go</a>'),
    '&lt;<span class="hl-tag">a</span> href=&quot;/x&quot;&gt;go&lt;/<span class="hl-tag">a</span>&gt;',
  );
});

test("highlight keeps line breaks and indentation", () => {
  assert.equal(highlight("a\n  b"), "a\n  b");
});
