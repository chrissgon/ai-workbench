"""Tests for skills/design-execute/scripts/screenshot.mjs: the system-browser engine.

Run: uv run --with pytest pytest skills/design-execute/scripts/tests -q

Offline. No real browser is started: a stand-in executable records its arguments, writes a PNG where
--screenshot points and can be told to fail with the browser's "no usable sandbox" message unless
--no-sandbox is passed. The script is copied to a temporary folder so that no `playwright` package is
resolvable from it. Needs `node` on PATH; the tests are skipped without it.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "screenshot.mjs"
NODE = shutil.which("node")
MAC_APPS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

STAND_IN = r'''#!__PYTHON__
"""Stand-in browser for the screenshot tests."""
import json, os, struct, sys, time, zlib

args = sys.argv[1:]
with open(os.environ["FAKE_BROWSER_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"name": os.path.basename(sys.argv[0]), "args": args}) + "\n")
if os.environ.get("FAKE_BROWSER_SANDBOX") and "--no-sandbox" not in args:
    sys.stderr.write("[1:1:FATAL:zygote_host_impl_linux.cc] No usable sandbox! Update your kernel or see the docs.\n")
    sys.exit(1)
if os.environ.get("FAKE_BROWSER_BROKEN"):
    sys.stderr.write("stand-in: cannot open display\n")
    sys.exit(1)


def value(prefix, default=None):
    return next((a[len(prefix):] for a in args if a.startswith(prefix)), default)


width, height = (int(n) for n in value("--window-size=").split(","))
scale = float(value("--force-device-scale-factor=", "1"))
# Some real builds ignore a scale factor below 0.5: the stand-in can be told to do the same.
scale = max(scale, float(os.environ.get("FAKE_BROWSER_MIN_SCALE", "0")))
if "--dump-dom" in args:
    page_height = os.environ.get("FAKE_PAGE_HEIGHT", str(height))
    print('<html data-screenshot-probe="%s"><head></head><body></body></html>' % page_height)
shot = value("--screenshot=")
if shot:
    w, h = round(width * scale), round(height * scale)

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = (b"\x00" + b"\xff\xff\xff" * w) * h
    with open(shot, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    sys.stderr.write("%d bytes written to file %s\n" % (os.path.getsize(shot), shot))
if os.environ.get("FAKE_BROWSER_HANG"):
    time.sleep(120)
'''


def stand_in(folder: Path, name: str = "stand-in-browser") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(STAND_IN.replace("__PYTHON__", sys.executable), encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A working directory with a page to render and a copy of the script."""
    root = tmp_path / "project"
    (root / "out").mkdir(parents=True)
    (root / "card.html").write_text(
        "<!doctype html><html><head><title>Card</title></head><body><h1>Marlow Docs</h1></body></html>",
        encoding="utf-8")
    shutil.copy(SCRIPT, tmp_path / "screenshot.mjs")
    return root


def node_only(project: Path) -> str:
    """A folder that holds node and nothing else, for PATH: no real browser can be found on it."""
    folder = project.parent / "node-only"
    if not folder.exists():
        folder.mkdir()
        (folder / "node").symlink_to(NODE)
    return str(folder)


def run(project: Path, *args: str, env: dict | None = None, path: str | None = None, timeout: int = 30):
    """Run the script in the project folder with a minimal environment. Returns (process, logged calls)."""
    log = project.parent / "calls.jsonl"
    if log.exists():
        log.unlink()
    full = {"PATH": path if path is not None else node_only(project), "HOME": str(project.parent / "home"),
            "TMPDIR": str(project.parent), "FAKE_BROWSER_LOG": str(log)}
    full.update(env or {})
    proc = subprocess.run([NODE, str(project.parent / "screenshot.mjs"), *args], cwd=project, env=full,
                          capture_output=True, text=True, timeout=timeout)
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    return proc, calls


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


BASE = ("--html", "card.html", "--out", "out/card.png", "--width", "1200", "--height", "630")


def test_chrome_bin_renders_without_playwright(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, env={"CHROME_BIN": str(browser)})
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result == {"ok": True, "out": "out/card.png", "width": 1200, "height": 630, "pixel_width": 1200,
                      "pixel_height": 630, "bytes": (project / "out/card.png").stat().st_size}
    assert png_size(project / "out/card.png") == (1200, 630)
    assert "Engine: system browser" in proc.stderr and "CHROME_BIN" in proc.stderr
    assert "install" not in proc.stderr.lower()
    assert len(calls) == 1
    args = calls[0]["args"]
    assert "--headless" in args and "--window-size=1200,630" in args and "--hide-scrollbars" in args
    # The browser never touches the OS keychain: with a throwaway home the system would ask the person to create one.
    assert "--use-mock-keychain" in args and "--password-store=basic" in args
    assert "--blink-settings=preferredColorScheme=1" in args
    assert "--force-prefers-reduced-motion" not in args and "--no-sandbox" not in args
    assert args[-1].startswith("file://") and args[-1].endswith("/card.html")
    assert any(a.startswith("--user-data-dir=") for a in args)


def test_temporary_profile_is_deleted(project):
    browser = stand_in(project.parent / "bin")
    proc, _ = run(project, *BASE, env={"CHROME_BIN": str(browser)})
    assert proc.returncode == 0, proc.stderr
    assert not [p for p in project.parent.iterdir() if p.name.startswith("screenshot-")]


def test_browser_flag_wins_over_chrome_bin(project):
    chosen = stand_in(project.parent / "bin", "chosen-browser")
    other = stand_in(project.parent / "bin", "other-browser")
    proc, calls = run(project, *BASE, "--browser", str(chosen), env={"CHROME_BIN": str(other)})
    assert proc.returncode == 0, proc.stderr
    assert {c["name"] for c in calls} == {"chosen-browser"}
    assert "from --browser" in proc.stderr


@pytest.mark.parametrize("name", ["chromium", "chromium-browser", "google-chrome"])
def test_browser_found_on_path(project, name):
    folder = project.parent / "bin"
    stand_in(folder, name)
    proc, calls = run(project, *BASE, path=os.pathsep.join([str(folder), node_only(project)]))
    assert proc.returncode == 0, proc.stderr
    assert {c["name"] for c in calls} == {name}
    assert "from PATH" in proc.stderr


def test_unusable_chrome_bin_falls_back_to_path(project):
    folder = project.parent / "bin"
    stand_in(folder, "chromium")
    proc, calls = run(project, *BASE, env={"CHROME_BIN": str(project.parent / "missing-browser")},
                      path=os.pathsep.join([str(folder), node_only(project)]))
    assert proc.returncode == 0, proc.stderr
    assert "CHROME_BIN" in proc.stderr and "cannot be run" in proc.stderr
    assert {c["name"] for c in calls} == {"chromium"}


def test_sandbox_failure_is_retried_once_with_no_sandbox(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, env={"CHROME_BIN": str(browser), "FAKE_BROWSER_SANDBOX": "1"})
    assert proc.returncode == 0, proc.stderr
    assert ["--no-sandbox" in c["args"] for c in calls] == [False, True]
    assert "retrying once with --no-sandbox" in proc.stderr
    assert png_size(project / "out/card.png") == (1200, 630)
    assert json.loads(proc.stdout)["ok"] is True


def test_no_sandbox_is_not_used_for_other_failures(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, env={"CHROME_BIN": str(browser), "FAKE_BROWSER_BROKEN": "1"})
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "render failed" in proc.stderr and "cannot open display" in proc.stderr
    assert len(calls) == 1 and "--no-sandbox" not in calls[0]["args"]
    assert not (project / "out/card.png").exists()


def test_full_page_measures_the_page_first(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, "--full-page", env={"CHROME_BIN": str(browser), "FAKE_PAGE_HEIGHT": "1500"})
    assert proc.returncode == 0, proc.stderr
    assert len(calls) == 2
    assert "--dump-dom" in calls[0]["args"] and "--window-size=1200,630" in calls[0]["args"]
    assert calls[0]["args"][-1].endswith("/measure.html")
    assert "--window-size=1200,1500" in calls[1]["args"] and calls[1]["args"][-1].endswith("/card.html")
    assert png_size(project / "out/card.png") == (1200, 1500)
    assert json.loads(proc.stdout)["height"] == 630


def test_full_page_with_sandbox_failure_retries_only_the_first_pass(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, "--full-page",
                      env={"CHROME_BIN": str(browser), "FAKE_BROWSER_SANDBOX": "1", "FAKE_PAGE_HEIGHT": "900"})
    assert proc.returncode == 0, proc.stderr
    assert ["--no-sandbox" in c["args"] for c in calls] == [False, True, True]
    assert proc.stderr.count("retrying once with --no-sandbox") == 1
    assert png_size(project / "out/card.png") == (1200, 900)


def test_dark_reduced_motion_scale_and_wait_become_browser_flags(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, "--dark", "--reduced-motion", "--scale", "2", "--wait", "1500",
                      env={"CHROME_BIN": str(browser)})
    assert proc.returncode == 0, proc.stderr
    args = calls[0]["args"]
    assert "--blink-settings=preferredColorScheme=0" in args
    assert "--force-prefers-reduced-motion" in args
    assert "--force-device-scale-factor=2" in args
    assert "--virtual-time-budget=2000" in args
    assert png_size(project / "out/card.png") == (2400, 1260)
    result = json.loads(proc.stdout)
    assert (result["width"], result["height"]) == (1200, 630)
    assert (result["pixel_width"], result["pixel_height"]) == (2400, 1260)


def test_an_image_of_another_size_than_asked_is_a_render_error(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, *BASE, "--scale", "0.25", env={"CHROME_BIN": str(browser), "FAKE_BROWSER_MIN_SCALE": "0.5"})
    assert len(calls) == 1 and "--force-device-scale-factor=0.25" in calls[0]["args"]
    assert proc.returncode == 1 and proc.stdout == ""
    assert "600 x 315 px image; 300 x 158 was asked" in proc.stderr
    assert "render at the smaller --width and --height instead" in proc.stderr
    assert not (project / "out/card.png").exists()
    proc, _ = run(project, "--html", "card.html", "--out", "out/card.png", "--width", "300", "--height", "158",
                  env={"CHROME_BIN": str(browser), "FAKE_BROWSER_MIN_SCALE": "0.5"})
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["pixel_width"] == 300 and png_size(project / "out/card.png") == (300, 158)


def test_browser_that_never_exits_is_stopped(project):
    browser = stand_in(project.parent / "bin")
    proc, _ = run(project, *BASE, env={"CHROME_BIN": str(browser), "FAKE_BROWSER_HANG": "1"}, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert png_size(project / "out/card.png") == (1200, 630)


def test_browser_flag_that_cannot_run_is_a_usage_error(project):
    proc, calls = run(project, *BASE, "--browser", str(project.parent / "missing-browser"))
    assert proc.returncode == 2
    assert "--browser" in proc.stderr and proc.stdout == "" and calls == []


@pytest.mark.skipif(any(os.path.exists(p) or os.path.exists(os.path.expanduser("~") + p) for p in MAC_APPS),
                    reason="a real browser is installed in an application folder the script looks in")
def test_no_engine_names_the_options_and_installs_nothing(project):
    proc, calls = run(project, *BASE)
    assert proc.returncode == 2
    assert proc.stdout == "" and calls == []
    assert "no engine" in proc.stderr and "--browser" in proc.stderr and "CHROME_BIN" in proc.stderr
    assert "if the user chooses to install" in proc.stderr


def test_out_outside_the_working_directory_is_refused(project):
    browser = stand_in(project.parent / "bin")
    proc, calls = run(project, "--html", "card.html", "--out", "../escape.png", "--width", "1200", "--height", "630",
                      env={"CHROME_BIN": str(browser)})
    assert proc.returncode == 2
    assert "inside the working directory" in proc.stderr and calls == []


def test_help_names_the_engines(project):
    proc, _ = run(project, "--help")
    assert proc.returncode == 0
    assert "--browser" in proc.stdout and "CHROME_BIN" in proc.stdout and "playwright" in proc.stdout
