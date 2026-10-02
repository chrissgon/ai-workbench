import test from "node:test";
import assert from "node:assert/strict";
import { generatePage } from "../../app/generate.ts";

const html = generatePage("content/components/button.md");

test("generatePage wraps the page in the layout with its title", () => {
  assert.ok(html.startsWith("<!doctype html>"));
  assert.ok(html.includes("<title>Button | Fernleaf UI</title>"));
});

test("generatePage renders the note block", () => {
  assert.ok(html.includes('<aside class="note">The default variant is primary.</aside>'));
});
