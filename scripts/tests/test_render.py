"""Tests of skills/brand-identity/scripts/render.py: the PNG header reader, the refusal of remote
references, browser discovery, fill escaping, and the size check (with a fake browser). One test renders
with a real Chrome or Chromium and is skipped when none is installed."""
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[2] / "skills/brand-identity"
RENDER = SKILL / "scripts/render.py"
CARD = SKILL / "assets/post-card-template.html"
PIECE = SKILL / "assets/piece-template.html"

spec = importlib.util.spec_from_file_location("render", RENDER)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def tiny_png(width, height):
    """A valid black RGB PNG built with zlib and struct only."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def run(*args, env=None):
    r = subprocess.run([sys.executable, str(RENDER), *args], capture_output=True, text=True, timeout=120,
                       env={**os.environ, **(env or {})})
    return r.returncode, r.stdout, r.stderr


def page(tmp_path, body, head=""):
    p = tmp_path / "piece.html"
    p.write_text(f"<!doctype html><html><head><meta charset='utf-8'>{head}</head><body>{body}</body></html>")
    return p


def fake_browser(tmp_path, width, height, hang=False):
    """An executable that writes a width x height PNG to --screenshot=<path>, then optionally never exits."""
    png = tmp_path / "fake.png"
    png.write_bytes(tiny_png(width, height))
    exe = tmp_path / "fake-browser"
    exe.write_text(f"#!{sys.executable}\nimport shutil, sys, time\n"
                   "shot = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--screenshot=')][0]\n"
                   f"shutil.copyfile({str(png)!r}, shot)\n" + ("time.sleep(600)\n" if hang else ""))
    exe.chmod(0o755)
    return exe


# PNG header

def test_png_size_reads_the_ihdr_header(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(tiny_png(7, 3))
    assert render.png_size(p) == (7, 3)
    assert render.png_complete(p)


def test_png_size_refuses_a_file_that_is_not_a_png(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"GIF89a" + b"\x00" * 30)
    with pytest.raises(ValueError):
        render.png_size(p)


def test_a_truncated_png_is_not_complete(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(tiny_png(40, 40)[:-12])
    assert not render.png_complete(p)
    assert not render.png_complete(tmp_path / "missing.png")


# Remote references

@pytest.mark.parametrize("head,body", [
    ("<link href='https://fonts.googleapis.com/css2?family=Inter' rel='stylesheet'>", ""),
    ("<style>@import url('https://example.org/a.css');</style>", ""),
    ("<style>body { background: url(http://example.org/bg.png) }</style>", ""),
    ("", "<img src='//cdn.example.org/a.png'>"),
    ("", "<div style=\"background-image:url('https://example.org/a.png')\"></div>"),
    ("", "<script>fetch('https://example.org/track')</script>"),
    ("", "<svg xmlns='http://www.w3.org/2000/svg'><image href='https://example.org/a.png'/></svg>"),
])
def test_remote_references_are_refused(tmp_path, head, body):
    code, out, err = run("--html", str(page(tmp_path, body, head)), "--width", "100", "--height", "100",
                         "--out", str(tmp_path / "o.png"), "--browser", "/nonexistent/browser")
    assert code == 2 and "remote" in err and out == ""


def test_self_contained_html_has_no_remote_reference():
    text = ("<html><head><style>@font-face{src:url(data:font/woff2;base64,AAAA)}</style></head><body>"
            "<img src='logo.png'><svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
            "<rect/></svg><p>Read it at https://example.org</p></body></html>")
    assert render.remote_references(text) == []


def test_both_templates_are_self_contained():
    assert render.remote_references(PIECE.read_text()) == []
    filled = render.fill(CARD.read_text(), {"title": "t", "subtitle": "s"})
    assert render.remote_references(filled) == []


# Browser discovery

def test_a_missing_browser_exits_3(tmp_path):
    code, _, err = run("--html", str(page(tmp_path, "x")), "--width", "100", "--height", "100",
                       "--out", str(tmp_path / "o.png"), "--browser", str(tmp_path / "no-such-browser"))
    assert code == 3 and "not an executable file" in err
    assert not (tmp_path / "o.png").exists()


def test_a_missing_render_browser_variable_exits_3_without_guessing(tmp_path):
    code, _, err = run("--html", str(page(tmp_path, "x")), "--width", "100", "--height", "100",
                       "--out", str(tmp_path / "o.png"), env={"RENDER_BROWSER": str(tmp_path / "nothing")})
    assert code == 3 and "RENDER_BROWSER" in err


# Fill

def test_fill_escapes_html():
    out = render.fill("<h1>{{title}}</h1><p>{{ subtitle }}</p>",
                      {"title": "<script>alert(1)</script> & \"q\"", "subtitle": "a'b"})
    assert out == "<h1>&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;q&quot;</h1><p>a&#x27;b</p>"


def test_fill_refuses_unknown_and_unfilled_placeholders():
    with pytest.raises(render.InputError, match="no {{other}}"):
        render.fill("{{title}}", {"title": "a", "other": "b"})
    with pytest.raises(render.InputError, match="unfilled: subtitle"):
        render.fill("{{title}} {{subtitle}}", {"title": "a"})


def test_fill_respects_the_template_maximum():
    text = '<meta name="fill-max" content="title=5,subtitle=3">{{title}}{{subtitle}}'
    assert render.fill(text, {"title": "12345", "subtitle": "abc"}).endswith("12345abc")
    with pytest.raises(render.InputError, match="6 characters, the template allows 5"):
        render.fill(text, {"title": "123456", "subtitle": "abc"})


def test_the_card_needs_both_fills(tmp_path):
    code, _, err = run("--html", str(CARD), "--width", "1080", "--height", "1350", "--out", str(tmp_path / "o.png"),
                       "--fill", "title=Only a title", "--browser", "/nonexistent/browser")
    assert code == 2 and "subtitle" in err


# Size check, with a fake browser

def test_the_right_size_is_written_with_its_hash(tmp_path):
    exe = fake_browser(tmp_path, 120, 80)
    out = tmp_path / "out/o.png"
    code, stdout, err = run("--html", str(page(tmp_path, "x")), "--width", "120", "--height", "80",
                            "--out", str(out), "--browser", str(exe))
    assert code == 0, err
    data = json.loads(stdout)
    assert (data["width"], data["height"], data["browser"]) == (120, 80, str(exe))
    assert data["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()


def test_a_wrong_size_exits_1_and_writes_nothing(tmp_path):
    exe = fake_browser(tmp_path, 120, 79)
    out = tmp_path / "o.png"
    code, _, err = run("--html", str(page(tmp_path, "x")), "--width", "120", "--height", "80",
                       "--out", str(out), "--browser", str(exe))
    assert code == 1 and "120x79, expected 120x80" in err
    assert not out.exists()


def test_a_browser_that_stays_alive_after_the_screenshot_is_stopped(tmp_path):
    exe = fake_browser(tmp_path, 50, 50, hang=True)
    code, stdout, err = run("--html", str(page(tmp_path, "x")), "--width", "50", "--height", "50",
                            "--out", str(tmp_path / "o.png"), "--browser", str(exe), "--timeout", "30")
    assert code == 0, err
    assert json.loads(stdout)["width"] == 50


# Real render

REAL_BROWSER, _ = render.find_browser(None)


@pytest.mark.skipif(REAL_BROWSER is None, reason="no Chrome or Chromium installed")
def test_real_render_of_the_post_card(tmp_path):
    out = tmp_path / "card.png"
    code, stdout, err = run("--html", str(CARD), "--width", "1080", "--height", "1350", "--out", str(out),
                            "--fill", "title=A <real> render & check", "--fill", "subtitle=Weekly vote, round 1")
    assert code == 0, err
    assert render.png_size(out) == (1080, 1350)
    assert json.loads(stdout)["browser"] == REAL_BROWSER


def test_the_browser_never_touches_the_os_keychain():
    """With a throwaway home (an eval run) the browser finds no keychain and the system asks the person to
    create one: the command line turns the keychain off."""
    cmd = render.browser_command("browser", "page.html", "shot.png", "profile", 1080, 1350)
    assert "--use-mock-keychain" in cmd and "--password-store=basic" in cmd
