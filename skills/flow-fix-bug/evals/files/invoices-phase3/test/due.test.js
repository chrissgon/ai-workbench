import assert from "node:assert/strict";
import { test } from "node:test";
import { dueLabel, daysLeft } from "../src/due.js";

// The shop's servers run in these zones (AGENTS.md); CI runs in UTC.
const zones = ["UTC", "Europe/Lisbon", "America/Sao_Paulo"];

for (const zone of zones) {
  test(`dueLabel keeps a date-only due date in ${zone}`, () => {
    process.env.TZ = zone;
    assert.equal(dueLabel("2026-09-25"), "2026-09-25");
  });

  test(`dueLabel keeps the local date of a date-time in ${zone}`, () => {
    process.env.TZ = zone;
    assert.equal(dueLabel("2026-09-25T00:00"), "2026-09-25");
  });

  test(`daysLeft is 1 at noon the day before in ${zone}`, () => {
    process.env.TZ = zone;
    assert.equal(daysLeft("2026-09-25", new Date(2026, 8, 24, 12)), 1);
  });
}
