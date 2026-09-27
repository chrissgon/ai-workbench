#!/usr/bin/env node
// Render an HTML file to PNG with a headless browser.
//
// Usage: node screenshot.mjs --html <file.html> --out <file.png> --width <w> --height <h>
//                            [--full-page] [--scale <n>] [--dark] [--reduced-motion] [--wait <ms>]
//
// Needs the `playwright` package resolvable from the working directory or NODE_PATH, pinned to
// PLAYWRIGHT_VERSION below (latest on https://registry.npmjs.org/playwright/latest, read 2026-09-27).
// This script never installs anything: when the package is missing it prints the pinned install
// commands for the user to approve and run. --out must be a .png inside the working directory.
// Prints JSON {ok, out, width, height, bytes}. Exit codes: 0 ok, 1 render error, 2 usage error.
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { dirname, extname, relative, resolve, isAbsolute } from "node:path";
import { lstatSync, realpathSync, statSync } from "node:fs";

const PLAYWRIGHT_VERSION = "1.63.0";

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
// --out stays inside the working directory: a relative or absolute path whose real parent folder
// is under it, a .png name, and not an existing symlink.
const outError = (() => {
  const cwd = realpathSync(process.cwd());
  const target = resolve(cwd, out);
  if (extname(target).toLowerCase() !== ".png") return "must end in .png";
  let parent;
  try {
    parent = realpathSync(dirname(target));
  } catch {
    return "must be in an existing folder";
  }
  const rel = relative(cwd, parent);
  if (rel.startsWith("..") || isAbsolute(rel)) return "must be inside the working directory";
  try {
    if (lstatSync(target).isSymbolicLink()) return "must not be a symlink";
  } catch {
    // does not exist yet: fine
  }
  return null;
})();
if (outError) {
  console.error(`Error: --out ${JSON.stringify(out)} ${outError}. See --help.`);
  process.exit(2);
}
let chromium;
let version;
const require = createRequire(resolve(process.cwd(), "package.json"));
try {
  ({ chromium } = require("playwright"));
  version = require("playwright/package.json").version;
} catch {
  try {
    ({ chromium } = await import("playwright"));
  } catch {
    console.error(
      "Error: the playwright package is not resolvable. Ask the user before installing; the pinned commands are: " +
        `npm install --no-save playwright@${PLAYWRIGHT_VERSION} && npx playwright@${PLAYWRIGHT_VERSION} install chromium`,
    );
    process.exit(2);
  }
}
if (version && version !== PLAYWRIGHT_VERSION) {
  console.error(`Warning: playwright ${version} found; this script is pinned to ${PLAYWRIGHT_VERSION}.`);
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
