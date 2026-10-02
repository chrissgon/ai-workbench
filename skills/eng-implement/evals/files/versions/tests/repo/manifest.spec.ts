import test from "node:test";
import assert from "node:assert/strict";
import { loadManifest, parseManifest } from "../../app/manifest.ts";

test("loadManifest reads content/versions.json", () => {
  const manifest = loadManifest("content/versions.json");
  assert.equal(manifest.latest, "2.1");
  assert.deepEqual(manifest.versions.map((entry) => entry.id), ["2.1", "2.0", "1.4"]);
});

test("parseManifest rejects an id that is not <major>.<minor>", () => {
  assert.throws(() => parseManifest('{"latest":"2","versions":[{"id":"2"}]}'), RangeError);
});

test("parseManifest rejects a latest that is not listed", () => {
  assert.throws(() => parseManifest('{"latest":"3.0","versions":[{"id":"2.1"}]}'), /3\.0/);
});
