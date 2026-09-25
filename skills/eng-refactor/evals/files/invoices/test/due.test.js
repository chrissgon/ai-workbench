import assert from "node:assert/strict";
import { test } from "node:test";
import { daysLeft, dueLabel } from "../src/index.js";

test("the label is the due date", () => {
  assert.equal(dueLabel("2026-09-25"), "2026-09-25");
});

test("an invalid date is rejected", () => {
  assert.throws(() => dueLabel("not a date"), RangeError);
  assert.throws(() => daysLeft("not a date"), RangeError);
});

test("one day left the day before at noon", () => {
  assert.equal(daysLeft("2026-09-25", new Date("2026-09-24T12:00:00Z")), 1);
});
