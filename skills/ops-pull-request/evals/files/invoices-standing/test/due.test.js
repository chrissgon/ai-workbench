import { test } from "node:test";
import assert from "node:assert/strict";
import { dueLabel } from "../src/due.js";

test("dueLabel prints the ISO date", () => {
  assert.equal(dueLabel("2026-09-25"), "2026-09-25");
});
