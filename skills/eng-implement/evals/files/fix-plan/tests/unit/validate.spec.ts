import test from "node:test";
import assert from "node:assert/strict";
import { validateDocs } from "../../app/validate.ts";
import type { DocPage } from "../../app/validate.ts";

function page(overrides: Partial<DocPage> = {}): DocPage {
  return { file: "content/guide/install.md", section: "guide", slug: "install", title: "Install", ...overrides };
}

test("a complete page is valid", () => {
  assert.deepEqual(validateDocs([page({ description: "How to install Fernleaf UI." })]), []);
});

test("a missing or blank title is reported with the file (EDGE-1)", () => {
  assert.deepEqual(validateDocs([page({ title: undefined })]), ["content/guide/install.md: title is missing"]);
  assert.deepEqual(validateDocs([page({ title: "   " })]), ["content/guide/install.md: title is missing"]);
});

test("a slug with capitals, spaces or doubled hyphens is reported (EDGE-2)", () => {
  for (const slug of ["Install", "get started", "get--started", "-install"]) {
    assert.equal(validateDocs([page({ slug })]).length, 1, slug);
  }
  assert.deepEqual(validateDocs([page({ slug: "get-started-2" })]), []);
});

test("a description of exactly 160 characters is valid (EDGE-3)", () => {
  assert.deepEqual(validateDocs([page({ description: "a".repeat(160) })]), []);
});

test("a description of 161 characters is reported (EDGE-3)", () => {
  assert.deepEqual(validateDocs([page({ description: "a".repeat(161) })]), [
    "content/guide/install.md: description is longer than 160 characters",
  ]);
});

test("two pages with the same section and slug are reported once, on the second (EDGE-4)", () => {
  const errors = validateDocs([page(), page({ file: "content/guide/setup.md" }), page({ section: "components" })]);
  assert.deepEqual(errors, ["content/guide/setup.md: address /guide/install is already used by content/guide/install.md"]);
});

// docs/engineering/plans/duplicate-address-across-sections.md, "Failing tests"
test("two pages with the same slug in different sections are both valid (EDGE-4)", () => {
  const pages = [page(), page({ file: "content/components/install.md", section: "components" })];
  assert.deepEqual(validateDocs(pages), []);
});
