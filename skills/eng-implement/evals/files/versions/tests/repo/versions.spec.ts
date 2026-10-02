import test from "node:test";
import assert from "node:assert/strict";
import type { Manifest } from "../../app/manifest.ts";
import { listVersions, resolveVersion } from "../../app/versions.ts";

const manifest: Manifest = {
  latest: "2.10",
  versions: [{ id: "2.9" }, { id: "1.4", deprecated: true }, { id: "2.10" }],
};

test("listVersions orders ids numerically, newest first", () => {
  assert.deepEqual(listVersions(manifest).map((version) => version.id), ["2.10", "2.9", "1.4"]);
});

test("the latest version is served at the root and labelled as latest", () => {
  assert.deepEqual(listVersions(manifest)[0], { id: "2.10", label: "2.10 (latest)", path: "/", deprecated: false });
});

test("every other version is served under /v<id>", () => {
  const [, previous, oldest] = listVersions(manifest);
  assert.deepEqual(previous, { id: "2.9", label: "2.9", path: "/v2.9", deprecated: false });
  assert.deepEqual(oldest, { id: "1.4", label: "1.4", path: "/v1.4", deprecated: true });
});

test("resolveVersion without an id returns the latest version", () => {
  assert.equal(resolveVersion(manifest).id, "2.10");
});

test("resolveVersion returns the version of a known id", () => {
  assert.equal(resolveVersion(manifest, "1.4").path, "/v1.4");
});

test("resolveVersion throws a RangeError that names an unknown id", () => {
  assert.throws(
    () => resolveVersion(manifest, "3.0"),
    (error: unknown) => error instanceof RangeError && error.message.includes("3.0"),
  );
});
