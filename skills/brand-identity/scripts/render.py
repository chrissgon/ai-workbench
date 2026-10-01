#!/usr/bin/env python3
"""Render a self-contained HTML piece to a PNG of an exact size with a headless browser.

Usage:
  python3 render.py --html piece.html --width 1080 --height 1350 --out piece.png
         [--fill title=... --fill subtitle=...] [--font-face "Inter:800:fonts/Inter-ExtraBold.woff2"]
         [--query v=light] [--browser <path>] [--timeout 60]

Made for scheduled jobs with no person present: no prompts, no network, one output.

- The HTML must be self-contained. Any remote reference is refused (exit 2) before the browser starts:
  an http(s), ftp or ws(s) URL, or a scheme-relative "//host" URL, in any attribute (xmlns namespaces
  excepted), in CSS url() or @import, or in a script. Text content may mention URLs. Fonts come from
  --font-face (embedded as data: URIs) or from the system; images are data: URIs or local files. The
  browser also runs with every host name mapped to "not found", so nothing reaches the network.
- --fill name=value replaces every {{name}} in the HTML with the value, HTML-escaped. A fill name the
  HTML does not contain, or a {{name}} left unfilled, is refused (exit 2). A template may declare
  <meta name="fill-max" content="title=70,subtitle=40">; a value longer than its maximum (characters)
  is refused (exit 2), so an unattended job never renders clipped text.
- --query appends a query string to the page URL (templates that pick a variant from it, e.g. v=light).
- --font-face FAMILY:WEIGHT:PATH (repeatable) embeds a .woff2, .woff, .ttf or .otf file as an
  @font-face rule at the top of <head>.
- Browser: --browser, else the RENDER_BROWSER environment variable, else Google Chrome or Chromium at
  the usual macOS paths, else google-chrome, google-chrome-stable, chromium or chromium-browser on PATH.
  A --browser or RENDER_BROWSER that is not an executable file is not replaced by a guess.
- The browser runs in a throwaway profile folder (removed afterwards) and its own process group. Once
  the screenshot is complete (the PNG ends with its IEND chunk) it gets 2 s to exit and is then
  stopped: on some machines headless Chrome stays alive after writing the file. --timeout bounds the
  whole run.
- After rendering, the PNG's width and height are read from its IHDR header; the file is written to
  --out only when they equal --width and --height.

Prints JSON {"out", "width", "height", "sha256", "browser"} to stdout; diagnostics go to stderr.
Exit codes: 0 rendered; 1 the render failed, timed out or has the wrong size (nothing written);
2 bad input (missing file, remote reference, bad fill or font); 3 no browser found (the caller
degrades, for example to a text-only post).

Browser flags, checked on 2026-09-30:
- --headless, --screenshot[=path], --window-size=W,H: Chrome Headless mode and its command-line
  reference, https://developer.chrome.com/docs/chromium/headless and
  https://developer.chrome.com/docs/automation-and-testing/headless-cli ; the path form of
  --screenshot and the default "screenshot.png" are in Chromium's
  components/headless/command_handler/headless_command_handler.cc.
- --hide-scrollbars, --disable-gpu: content/public/common/content_switches.cc ("Prevents creating
  scrollbars for web content. Useful for taking consistent screenshots.").
- --force-device-scale-factor, --force-color-profile=srgb: ui/display/display_switches.cc.
- --user-data-dir, --window-size (headless shell): headless/public/switches.h.
- --host-resolver-rules="MAP * ^NOTFOUND": services/network/public/cpp/network_switches.cc and
  net/base/host_mapping_rules.h.
- --no-first-run, --no-default-browser-check, --disable-background-networking:
  chrome/common/chrome_switches.h; --disable-extensions: extensions/common/switches.h.
  (Chromium sources at https://chromium.googlesource.com/chromium/src/+/main/.)
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"
EXIT_GRACE_S = 2
KNOWN_BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"),
]
PATH_BROWSERS = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
FONT_TYPES = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}

REMOTE_URL = re.compile(r"(?i)\b(?:https?|ftps?|wss?)://")
CSS_REF = re.compile(r"""(?i)url\(\s*['"]?\s*([^'")\s]*)|@import\s+(?:url\(\s*)?['"]?\s*([^'")\s;]*)""")
URL_ATTRS = {"src", "href", "srcset", "poster", "data", "action", "formaction", "xlink:href", "background",
             "manifest", "ping", "cite", "longdesc"}
PLACEHOLDER = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")


class InputError(Exception):
    """Bad input: exit 2."""


def png_size(path):
    """(width, height) from a PNG's IHDR chunk; ValueError when the file is not a PNG."""
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file")
    return struct.unpack(">II", head[16:24])


def _css_remote(text):
    for m in CSS_REF.finditer(text):
        ref = (m.group(1) or m.group(2) or "").strip()
        if ref.startswith("//") or REMOTE_URL.match(ref):
            yield ref


class _RemoteFinder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found, self._in = [], None

    def _add(self, where, ref):
        self.found.append(f"line {self.getpos()[0]}, {where}: {ref[:120]}")

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            value = (value or "").strip()
            if name == "xmlns" or name.startswith("xmlns:"):
                continue
            if REMOTE_URL.search(value) or (name in URL_ATTRS and any(
                    part.strip().startswith("//") for part in value.split(","))):
                self._add(f"<{tag} {name}>", value)
            elif name == "style":
                for ref in _css_remote(value):
                    self._add(f"<{tag} style>", ref)
        self._in = tag if tag in ("style", "script") else None

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        self._in = None

    def handle_data(self, data):
        if self._in == "style":
            for ref in _css_remote(data):
                self._add("<style>", ref)
        elif self._in == "script":
            for m in REMOTE_URL.finditer(data):
                self._add("<script>", data[m.start():m.start() + 80].split()[0])


def remote_references(text):
    """Every remote reference in an HTML document, as readable strings; empty when self-contained."""
    finder = _RemoteFinder()
    finder.feed(text)
    finder.close()
    return finder.found


def fill_limits(text):
    m = re.search(r"""<meta\s+name=["']fill-max["']\s+content=["']([^"']*)["']""", text, re.I)
    limits = {}
    for item in (m.group(1).split(",") if m else []):
        name, _, value = item.partition("=")
        if name.strip() and value.strip().isdigit():
            limits[name.strip()] = int(value)
    return limits


def fill(text, values):
    """Replace {{name}} with the HTML-escaped value; InputError on an unknown, missing or too long value."""
    present = set(PLACEHOLDER.findall(text))
    limits = fill_limits(text)
    for name, value in values.items():
        if name not in present:
            raise InputError(f"--fill {name}: the HTML has no {{{{{name}}}}} placeholder")
        if name in limits and len(value) > limits[name]:
            raise InputError(f"--fill {name}: {len(value)} characters, the template allows {limits[name]}")
    text = PLACEHOLDER.sub(lambda m: html.escape(values[m.group(1)], quote=True)
                           if m.group(1) in values else m.group(0), text)
    left = sorted(set(PLACEHOLDER.findall(text)))
    if left:
        raise InputError("placeholders left unfilled: " + ", ".join(left) + " (pass --fill name=value)")
    return text


def font_faces(specs):
    rules = []
    for spec in specs:
        parts = spec.split(":", 2)
        if len(parts) != 3 or not parts[0].strip() or not parts[1].strip().isdigit():
            raise InputError(f"--font-face {spec!r}: expected FAMILY:WEIGHT:PATH, for example Inter:800:Inter.woff2")
        family, weight, path = parts[0].strip(), parts[1].strip(), Path(parts[2])
        kind = FONT_TYPES.get(path.suffix.lower())
        if kind is None or not path.is_file():
            raise InputError(f"--font-face {spec!r}: needs an existing {', '.join(FONT_TYPES)} file")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        mime = "font/" + path.suffix.lower().lstrip(".")
        rules.append(f"@font-face{{font-family:{json.dumps(family)};font-weight:{weight};font-style:normal;"
                     f"src:url(data:{mime};base64,{data}) format('{kind}')}}")
    return rules


def inject_head(text, snippet):
    m = re.search(r"<head\b[^>]*>", text, re.I)
    return text[:m.end()] + snippet + text[m.end():] if m else snippet + text


def find_browser(explicit):
    """(path, None) or (None, reason)."""
    for label, value in (("--browser", explicit), ("RENDER_BROWSER", os.environ.get("RENDER_BROWSER"))):
        if value:
            if os.path.isfile(value) and os.access(value, os.X_OK):
                return value, None
            return None, f"{label} {value!r} is not an executable file"
    for path in KNOWN_BROWSERS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path, None
    for name in PATH_BROWSERS:
        found = shutil.which(name)
        if found:
            return found, None
    return None, "no Chrome or Chromium found; pass --browser or set RENDER_BROWSER"


def png_complete(path):
    """True when the file exists and ends with a PNG IEND chunk (the browser finished writing it)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() < 57:
                return False
            f.seek(-12, os.SEEK_END)
            return f.read(12) == PNG_IEND
    except OSError:
        return False


def _stop(proc):
    """Stop the browser and every process it started (it runs in its own process group)."""
    for sig, wait in ((signal.SIGTERM, 3), (signal.SIGKILL, 3)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def run_browser(cmd, shot, log, timeout):
    """Run the browser until it exits, or until the screenshot is complete plus a grace period.

    Waits on the process, never on its output pipes: a helper process the browser starts (an updater)
    can hold inherited pipes open long after the screenshot exists, and on some machines the browser
    itself stays alive after writing it. Returns "exited", "stopped" (screenshot complete, browser
    stopped) or "timeout".
    """
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    deadline, complete_at = time.monotonic() + timeout, None
    while True:
        if proc.poll() is not None:
            return "exited"
        now = time.monotonic()
        if complete_at is None and png_complete(shot):
            complete_at = now
        if complete_at is not None and now - complete_at > EXIT_GRACE_S:
            _stop(proc)
            return "stopped"
        if now > deadline:
            _stop(proc)
            return "timeout"
        time.sleep(0.1)


def browser_command(browser, page, shot, profile, width, height):
    return [browser, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
            "--force-color-profile=srgb", f"--window-size={width},{height}", f"--user-data-dir={profile}",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            # No OS keychain: with a throwaway home (an eval run, a scheduled job) the browser finds no keychain
            # and the system asks the person to create one. A screenshot stores no secret.
            "--use-mock-keychain", "--password-store=basic",
            "--disable-background-networking", "--host-resolver-rules=MAP * ^NOTFOUND",
            f"--screenshot={shot}", page]


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--html", required=True, help="the self-contained HTML piece")
    p.add_argument("--width", required=True, type=int, help="image width in pixels")
    p.add_argument("--height", required=True, type=int, help="image height in pixels")
    p.add_argument("--out", required=True, help="the PNG to write")
    p.add_argument("--fill", action="append", default=[], metavar="NAME=VALUE", help="fill {{NAME}}, repeatable")
    p.add_argument("--font-face", action="append", default=[], metavar="FAMILY:WEIGHT:PATH",
                   help="embed a font file, repeatable")
    p.add_argument("--query", default="", metavar="K=V[&K=V]",
                   help="query string for the page, for example v=light for a template's variant")
    p.add_argument("--browser", help="path to a Chrome or Chromium executable")
    p.add_argument("--timeout", type=int, default=60, help="seconds before the browser is stopped (default 60)")
    return p.parse_args(argv)


def prepare(args):
    """The HTML text to render, after checks; InputError when it cannot be rendered."""
    src = Path(args.html)
    if not src.is_file():
        raise InputError(f"--html {src}: no such file")
    if not (16 <= args.width <= 8000 and 16 <= args.height <= 8000):
        raise InputError("--width and --height must be between 16 and 8000")
    if "#" in args.query or args.query.startswith("?"):
        raise InputError("--query takes k=v pairs joined by &, without ? or #")
    if not args.out.lower().endswith(".png"):
        raise InputError("--out must end in .png")
    text = src.read_text(encoding="utf-8")
    values = {}
    for item in args.fill:
        name, sep, value = item.partition("=")
        if not sep or not PLACEHOLDER.fullmatch("{{" + name + "}}"):
            raise InputError(f"--fill {item!r}: expected name=value with a lowercase name")
        values[name] = value
    text = fill(text, values)
    remote = remote_references(text)
    if remote:
        raise InputError("the HTML references remote resources; embed them or use local files:\n  "
                         + "\n  ".join(remote))
    faces = font_faces(args.font_face)
    base = f'<base href="{html.escape(src.resolve().parent.as_uri(), quote=True)}/">'
    return inject_head(text, base + (f"<style>{''.join(faces)}</style>" if faces else ""))


def main(argv):
    args = parse_args(argv)
    try:
        text = prepare(args)
    except (InputError, UnicodeDecodeError) as e:
        print(f"render.py: {e}", file=sys.stderr)
        return 2
    browser, reason = find_browser(args.browser)
    if browser is None:
        print(f"render.py: {reason}", file=sys.stderr)
        return 3
    tmp = Path(tempfile.mkdtemp(prefix="render-"))
    try:
        page, shot = tmp / "piece.html", tmp / "shot.png"
        page.write_text(text, encoding="utf-8")
        url = page.as_uri() + (f"?{args.query}" if args.query else "")
        cmd = browser_command(browser, url, shot, tmp / "profile", args.width, args.height)
        log_path = tmp / "browser.log"
        with open(log_path, "wb") as log:
            status = run_browser(cmd, shot, log, args.timeout)
        if not png_complete(shot):
            tail = "\n".join(log_path.read_text(errors="replace").strip().splitlines()[-5:])
            what = f"did not finish in {args.timeout} s" if status == "timeout" else "exited without a screenshot"
            print(f"render.py: the browser {what}\n{tail}", file=sys.stderr)
            return 1
        try:
            width, height = png_size(shot)
        except ValueError as e:
            print(f"render.py: {e}", file=sys.stderr)
            return 1
        if (width, height) != (args.width, args.height):
            print(f"render.py: the image is {width}x{height}, expected {args.width}x{args.height}; "
                  "nothing written", file=sys.stderr)
            return 1
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shot, out)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        print(json.dumps({"out": str(out), "width": width, "height": height, "sha256": digest,
                          "browser": browser}, indent=2))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
