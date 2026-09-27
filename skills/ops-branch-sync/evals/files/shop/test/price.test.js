import { test } from "node:test";
import assert from "node:assert/strict";
import { lineTotal } from "../src/price.js";

test("a line without discount is price times quantity", () => {
  assert.equal(lineTotal(250, 3), 750);
});
