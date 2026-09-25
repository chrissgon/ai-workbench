import assert from "node:assert/strict";
import { test } from "node:test";
import { dueLabel } from "../src/due.js";

test("the label is the due date", () => {
  assert.equal(dueLabel("2026-09-25"), "2026-09-25");
});
