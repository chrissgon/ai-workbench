"""Tests for skills/design-execute/scripts/screenshot.mjs: where --out may point, and that nothing is installed.

Run: uv run --with pytest pytest skills/design-execute/scripts/tests

Offline. No real browser is started: CHROME_BIN points to a stand-in executable that writes a PNG where
--screenshot points, PATH holds node and nothing else, and the script runs from a copy in a temporary folder,
so no `playwright` package is resolvable from it. Every name and number below is fictional.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SHOT = Path(__file__).resolve().parents[1] / "screenshot.mjs"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

STAND_IN = r'''#!__PYTHON__
"""Stand-in browser: writes a white PNG of the window size where --screenshot points."""
import struct, sys, zlib

args = sys.argv[1:]
value = lambda prefix: next((a[len(prefix):] for a in args if a.startswith(prefix)), None)
w, h = (int(n) for n in value("--window-size=").split(","))
shot = value("--screenshot=")
if shot:
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = (b"\x00" + b"\xff\xff\xff" * w) * h
    with open(shot, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
'''


def test_screenshot_checks_out_and_never_installs(tmp_path):
    script = tmp_path / "screenshot.mjs"
    shutil.copy(SHOT, script)
    browser = tmp_path / "bin" / "stand-in-browser"
    browser.parent.mkdir()
    browser.write_text(STAND_IN.replace("__PYTHON__", sys.executable), encoding="utf-8")
    browser.chmod(0o755)
    node_only = tmp_path / "node-only"
    node_only.mkdir()
    (node_only / "node").symlink_to(NODE)
    work = tmp_path / "work"
    work.mkdir()
    (work / "a.html").write_text("<p>x</p>\n", encoding="utf-8")
    (work / "link.png").symlink_to(tmp_path / "elsewhere.png")
    env = {"PATH": str(node_only), "HOME": str(tmp_path / "home"), "TMPDIR": str(tmp_path),
           "CHROME_BIN": str(browser)}
    shot = lambda out: subprocess.run([NODE, str(script), "--html", "a.html", "--out", out, "--width", "10",
                                       "--height", "10"], cwd=work, capture_output=True, text=True, timeout=60,
                                      env=env)
    for out in ("../x.png", str(tmp_path / "x.png"), "a.jpg", "missing/a.png", "link.png"):
        r = shot(out)
        assert r.returncode == 2 and "--out" in r.stderr, (out, r.stderr)
    r = shot("ok.png")
    assert r.returncode == 0, r.stderr
    assert "from CHROME_BIN" in r.stderr and (work / "ok.png").is_file()
    assert not (work / "node_modules").exists() and not (tmp_path / "node_modules").exists()
