#!/usr/bin/env node
// Render an HTML file to PNG with a headless browser.
//
// Usage: node screenshot.mjs --html <file.html> --out <file.png> --width <w> --height <h>
//                            [--full-page] [--scale <n>] [--dark] [--reduced-motion] [--wait <ms>]
//
// Needs the `playwright` package resolvable from the working directory or NODE_PATH.
// Prints JSON {ok, out, width, height, bytes}. Exit codes: 0 ok, 1 render error, 2 usage error.
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { statSync } from "node:fs";

const argv = process.argv.slice(2);
if (argv.includes("--help") || argv.length === 0) {
  console.log(
    "Usage: node screenshot.mjs --html <file.html> --out <file.png> --width <w> --height <h> " +
      "[--full-page] [--scale <n>] [--dark] [--reduced-motion] [--wait <ms>]",
  );
  process.exit(argv.length === 0 ? 2 : 0);
}
const get = (flag, fallback) => {
  const i = argv.indexOf(flag);
  return i >= 0 ? argv[i + 1] : fallback;
};
const html = get("--html");
const out = get("--out");
const width = Number(get("--width"));
const height = Number(get("--height"));
if (!html || !out || !width || !height) {
  console.error("Error: --html, --out, --width and --height are required. See --help.");
  process.exit(2);
}
let chromium;
try {
  const require = createRequire(resolve(process.cwd(), "package.json"));
  ({ chromium } = require("playwright"));
} catch {
  try {
    ({ chromium } = await import("playwright"));
  } catch {
    console.error("Error: the playwright package is not resolvable; install it or set NODE_PATH.");
    process.exit(2);
  }
}
try {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: Number(get("--scale", "1")),
    colorScheme: argv.includes("--dark") ? "dark" : "light",
    reducedMotion: argv.includes("--reduced-motion") ? "reduce" : "no-preference",
  });
  await page.goto(pathToFileURL(resolve(html)).href, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(Number(get("--wait", "0")));
  await page.screenshot({ path: out, fullPage: argv.includes("--full-page") });
  await browser.close();
  console.log(JSON.stringify({ ok: true, out, width, height, bytes: statSync(out).size }));
} catch (e) {
  console.error(`Error: render failed: ${e.message}`);
  process.exit(1);
}
