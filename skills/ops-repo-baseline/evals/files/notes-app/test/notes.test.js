import { test } from "node:test";
import assert from "node:assert/strict";
import { addNote } from "../src/notes.js";

test("addNote trims and numbers", () => {
  assert.deepEqual(addNote([], "  hi "), [{ id: 1, text: "hi" }]);
});
