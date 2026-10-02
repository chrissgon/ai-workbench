#!/usr/bin/env node
// Render an HTML file to PNG with a headless browser.
//
// Usage: node screenshot.mjs --html <file.html> --out <file.png> --width <w> --height <h>
//                            [--full-page] [--scale <n>] [--dark] [--reduced-motion] [--wait <ms>]
//                            [--browser <path or name>]
//
// What it renders: the local file given with --html, opened as a file:// URL, and whatever that page
// links (a remote stylesheet, a font, a script is fetched and run by the browser). Render only pages
// written in the project.
//
// Engine, in this order; the one used is named on stderr:
//   1. The `playwright` package, when it is resolvable from the working directory or NODE_PATH (pinned to
//      PLAYWRIGHT_VERSION below, latest on https://registry.npmjs.org/playwright/latest, read 2026-09-27)
//      and --browser is not given.
//   2. A browser already on the machine, driven through its own headless command line
//      (--headless --screenshot=<file> --window-size=<w>,<h>). It is looked for in --browser, then the
//      CHROME_BIN environment variable, then PATH (chromium, chromium-browser, google-chrome,
//      google-chrome-stable), then the usual macOS application paths. Nothing needs to be installed.
// This script never installs anything. With neither engine it stops and names the options.
//
// Sandbox: the browser is always started with its sandbox first. Only when that start fails and the
// browser's own output says it has no usable sandbox (a container, a root user) is the same command
// retried once with --no-sandbox, and a warning on stderr says so. Without the sandbox the page's scripts
// run in an unconfined browser process, which is one more reason to render only the project's own pages.
//
// System-browser details: the colour scheme and reduced motion are forced by flags, so the result does
// not follow the machine's settings; --wait is given as virtual time, on top of 500 ms for the page to
// load and settle; with --full-page a first pass loads a temporary copy of the page that reports its
// height, and the screenshot is taken in a window that tall. The browser runs with a temporary profile
// that is deleted afterwards, and is stopped as soon as the image is written (some builds never exit on
// their own). A page script that reads the viewport height while loading may see a smaller value than
// --height in some builds; the layout that is captured uses the full --width x --height.
//
// --out must be a .png inside the working directory.
// Prints JSON {ok, out, width, height, bytes} on stdout; diagnostics go to stderr.
// Exit codes: 0 ok, 1 render error, 2 usage error or no engine.
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { delimiter, dirname, extname, join, relative, resolve, isAbsolute, sep } from "node:path";
import {
  accessSync, constants, lstatSync, mkdtempSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { spawn } from "node:child_process";
import { homedir, tmpdir } from "node:os";

const PLAYWRIGHT_VERSION = "1.63.0";
const INSTALL_HINT =
  `npm install --no-save playwright@${PLAYWRIGHT_VERSION} && npx playwright@${PLAYWRIGHT_VERSION} install chromium`;
const BROWSER_NAMES = ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"];
const MAC_APPS = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
];
const SANDBOX_RE = /no usable sandbox|without --no-sandbox|SUID sandbox helper/i;
const PROBE_ATTR = "data-screenshot-probe";
const PROBE_SCRIPT =
  `<script>addEventListener("load",function(){var d=document.documentElement,b=document.body;` +
  `d.setAttribute("${PROBE_ATTR}",Math.max(d.scrollHeight,b?b.scrollHeight:0))})</script>`;
const USAGE =
  "Usage: node screenshot.mjs --html <file.html> --out <file.png> --width <w> --height <h> " +
  "[--full-page] [--scale <n>] [--dark] [--reduced-motion] [--wait <ms>] [--browser <path or name>]\n" +
  "Renders the local HTML file to a PNG inside the working directory. Uses the playwright package when it\n" +
  "is resolvable; otherwise a browser already on the machine (--browser, then CHROME_BIN, then PATH:\n" +
  `${BROWSER_NAMES.join(", ")}, then the macOS application paths) through its headless command line.\n` +
  "--browser forces that browser. Installs nothing. Prints JSON {ok, out, width, height, bytes}; the engine\n" +
  "used and warnings go to stderr. Exit codes: 0 ok, 1 render error, 2 usage error or no engine.";

const argv = process.argv.slice(2);
if (argv.includes("--help") || argv.length === 0) {
  console.log(USAGE);
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
const scale = Number(get("--scale", "1"));
const wait = Number(get("--wait", "0"));
if (!(scale > 0) || !(wait >= 0)) {
  console.error("Error: --scale must be a positive number and --wait a number of milliseconds. See --help.");
  process.exit(2);
}
const fullPage = argv.includes("--full-page");
const dark = argv.includes("--dark");
const reducedMotion = argv.includes("--reduced-motion");
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
const pageUrl = pathToFileURL(resolve(html)).href;

// ---------- engine 1: the playwright package ----------

async function loadPlaywright() {
  const require = createRequire(resolve(process.cwd(), "package.json"));
  try {
    const { chromium } = require("playwright");
    return { chromium, version: require("playwright/package.json").version };
  } catch {
    try {
      const { chromium } = await import("playwright");
      return chromium ? { chromium } : null;
    } catch {
      return null;
    }
  }
}

async function renderWithPlaywright(browser) {
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: scale,
    colorScheme: dark ? "dark" : "light",
    reducedMotion: reducedMotion ? "reduce" : "no-preference",
  });
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(wait);
  await page.screenshot({ path: out, fullPage });
  await browser.close();
}

// ---------- engine 2: a browser on the machine, through its headless command line ----------

function executable(p) {
  try {
    accessSync(p, constants.X_OK);
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

function onPath(name) {
  for (const dir of (process.env.PATH || "").split(delimiter)) {
    if (dir && executable(join(dir, name))) return join(dir, name);
  }
  return null;
}

// A value with a folder in it is a path; a bare name is looked up on PATH.
function runnable(value) {
  if (!value) return null;
  if (value.includes("/") || value.includes(sep)) return executable(value) ? value : null;
  return onPath(value);
}

// Returns {path, source}, or null when there is none. A --browser that cannot be run is a usage error.
function findBrowser() {
  if (argv.includes("--browser")) {
    const flag = get("--browser");
    const found = runnable(flag);
    if (!found) {
      console.error(`Error: --browser ${JSON.stringify(flag ?? "")} is not an executable file or a command on PATH.`);
      process.exit(2);
    }
    return { path: found, source: "--browser" };
  }
  const env = process.env.CHROME_BIN;
  if (env) {
    const found = runnable(env);
    if (found) return { path: found, source: "CHROME_BIN" };
    console.error(`Warning: CHROME_BIN is set to ${JSON.stringify(env)}, which cannot be run; looking on PATH.`);
  }
  for (const name of BROWSER_NAMES) {
    const found = onPath(name);
    if (found) return { path: found, source: "PATH" };
  }
  for (const app of [...MAC_APPS, ...MAC_APPS.map((a) => join(homedir(), a))]) {
    if (executable(app)) return { path: app, source: "the application folder" };
  }
  return null;
}

// Start the browser, wait until ready() is true or the browser exits, then stop it and everything it started.
function launch(bin, args, ready, timeoutMs) {
  return new Promise((done) => {
    let stdout = "";
    let stderr = "";
    let settled = false;
    let poll;
    let timer;
    const child = spawn(bin, args, { stdio: ["ignore", "pipe", "pipe"], detached: process.platform !== "win32" });
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      clearTimeout(timer);
      try {
        process.kill(-child.pid, "SIGKILL");
      } catch {
        try {
          child.kill("SIGKILL");
        } catch {
          // already gone
        }
      }
      done({ stdout, stderr, ...result });
    };
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", (e) => finish({ ok: false, why: e.message }));
    // Output may still be in the pipe when the process exits: read it for a moment before judging.
    child.on("exit", (code) =>
      setTimeout(() => finish({ ok: ready(true, stdout), why: `the browser exited with code ${code}` }), 150));
    poll = setInterval(() => ready(false, stdout) && finish({ ok: true }), 100);
    timer = setTimeout(() => finish({ ok: false, why: `no result after ${timeoutMs} ms` }), timeoutMs);
  });
}

function pngSize(png) {
  if (png.length < 24 || png.toString("latin1", 12, 16) !== "IHDR") throw new Error("the browser's output is not a PNG");
  return { w: png.readUInt32BE(16), h: png.readUInt32BE(20) };
}

// A copy of the page that reports its own size, in the temporary folder; relative links keep resolving
// against the original folder through a <base> element.
function measuringCopy(dir) {
  let text = readFileSync(resolve(html), "utf8");
  if (!/<base\b/i.test(text)) {
    const base = `<base href="${pathToFileURL(dirname(resolve(html))).href}/">`;
    const anchor = /<head\b[^>]*>/i.exec(text) || /<html\b[^>]*>/i.exec(text) || /<!doctype[^>]*>/i.exec(text);
    const at = anchor ? anchor.index + anchor[0].length : 0;
    text = text.slice(0, at) + base + text.slice(at);
  }
  const file = join(dir, "measure.html");
  writeFileSync(file, text + PROBE_SCRIPT);
  return pathToFileURL(file).href;
}

async function renderWithSystemBrowser(bin) {
  const dir = mkdtempSync(join(tmpdir(), "screenshot-"));
  try {
    const shot = join(dir, "shot.png");
    const timeoutMs = 60000 + wait;
    let noSandbox = false;
    const pass = async (windowHeight, extra, url, ready) => {
      for (;;) {
        const args = [
          "--headless", `--user-data-dir=${join(dir, "profile")}`, "--no-first-run", "--no-default-browser-check",
          "--disable-extensions", "--disable-sync", "--disable-background-networking", "--disable-component-update",
          "--mute-audio", "--hide-scrollbars", "--disable-gpu", `--window-size=${width},${windowHeight}`,
          // No OS keychain: with a throwaway home (a test, an eval run, a scheduled job) the browser finds no
          // keychain and the system asks the person to create one. A screenshot stores no secret.
          "--use-mock-keychain", "--password-store=basic",
          `--force-device-scale-factor=${scale}`, `--blink-settings=preferredColorScheme=${dark ? 0 : 1}`,
          `--virtual-time-budget=${500 + wait}`,
          ...(reducedMotion ? ["--force-prefers-reduced-motion"] : []),
          ...(noSandbox ? ["--no-sandbox"] : []),
          ...extra, url,
        ];
        const result = await launch(bin, args, ready, timeoutMs);
        if (result.ok || noSandbox || !SANDBOX_RE.test(result.stderr + result.stdout)) return result;
        noSandbox = true;
        console.error("Warning: the browser reported no usable sandbox; retrying once with --no-sandbox.");
      }
    };
    const tail = (r) => (r.stderr || r.stdout).trim().split("\n").slice(-3).join(" | ");

    // --full-page only: a first pass measures the page height at this width.
    let target = height;
    if (fullPage) {
      const probeRe = new RegExp(`${PROBE_ATTR}="(\\d+)"`);
      const probe = await pass(height, ["--dump-dom"], measuringCopy(dir), (_final, stdout) => probeRe.test(stdout));
      const measured = probeRe.exec(probe.stdout);
      if (!measured) throw new Error(`could not measure the page height (${probe.why}). ${tail(probe)}`);
      target = Math.max(height, Number(measured[1]));
    }

    // The screenshot. It is ready when the file exists and has stopped growing, or when the browser exits.
    let last = -1;
    const written = (final) => {
      let size = 0;
      try {
        size = statSync(shot).size;
      } catch {
        return false;
      }
      const stable = size > 0 && (final || size === last);
      last = size;
      return stable;
    };
    const capture = await pass(target, [`--screenshot=${shot}`], pageUrl, written);
    if (!capture.ok) throw new Error(`the browser wrote no screenshot (${capture.why}). ${tail(capture)}`);
    const png = readFileSync(shot);
    const got = pngSize(png);
    const want = { w: Math.round(width * scale), h: Math.round(target * scale) };
    if (got.w !== want.w || got.h !== want.h) {
      console.error(`Warning: the image is ${got.w} x ${got.h} px; ${want.w} x ${want.h} was expected.`);
    }
    writeFileSync(resolve(out), png);
  } finally {
    try {
      rmSync(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch {
      console.error(`Warning: could not delete the temporary folder ${dir}.`);
    }
  }
}

// ---------- main ----------

try {
  let done = false;
  const pw = argv.includes("--browser") ? null : await loadPlaywright();
  if (pw) {
    if (pw.version && pw.version !== PLAYWRIGHT_VERSION) {
      console.error(`Warning: playwright ${pw.version} found; this script is pinned to ${PLAYWRIGHT_VERSION}.`);
    }
    let browser = null;
    try {
      browser = await pw.chromium.launch();
    } catch (e) {
      console.error(
        `Warning: playwright could not start its browser (${String(e.message).split("\n")[0]}); ` +
          "trying a browser on the machine.",
      );
    }
    if (browser) {
      console.error(`Engine: playwright${pw.version ? " " + pw.version : ""}`);
      await renderWithPlaywright(browser);
      done = true;
    }
  }
  if (!done) {
    const found = findBrowser();
    if (!found) {
      console.error(
        "Error: no engine. The playwright package is not resolvable and no browser was found in CHROME_BIN, on PATH (" +
          `${BROWSER_NAMES.join(", ")}) or in the macOS application folders. Options: pass --browser <path>, ` +
          "set CHROME_BIN, or, if the user chooses to install the package, the pinned commands are: " + INSTALL_HINT,
      );
      process.exit(2);
    }
    console.error(`Engine: system browser ${found.path} (from ${found.source}), headless command line`);
    await renderWithSystemBrowser(found.path);
  }
  console.log(JSON.stringify({ ok: true, out, width, height, bytes: statSync(out).size }));
} catch (e) {
  console.error(`Error: render failed: ${e.message}`);
  process.exit(1);
}
