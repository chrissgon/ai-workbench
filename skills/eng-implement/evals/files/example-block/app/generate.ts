import { readFileSync } from "node:fs";
import { components } from "./components/index.ts";
import { escapeHtml } from "./highlight.ts";
import { renderPage } from "./markdown.ts";

export function generatePage(file: string): string {
  const page = renderPage(readFileSync(file, "utf8"), components);
  return [
    "<!doctype html>",
    '<html lang="en">',
    `<head><title>${escapeHtml(page.title)} | Fernleaf UI</title></head>`,
    "<body>",
    "<main>",
    page.html,
    "</main>",
    "</body>",
    "</html>",
    "",
  ].join("\n");
}
