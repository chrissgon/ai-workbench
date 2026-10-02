"""Tests for skills/design-handoff/scripts/unpack_export.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/design-handoff/scripts/tests
"""
from __future__ import annotations

import base64
import gzip
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


# ---------- design-handoff/unpack_export.py (H05) ----------

UNPACK = "skills/design-handoff/scripts/unpack_export.py"


def export_html(manifest: dict) -> str:
    return ('<script type="__bundler/template">' + json.dumps("<html><style>a{}</style></html>") + "</script>"
            '<script type="__bundler/manifest">' + json.dumps(manifest) + "</script>")


def res(data: bytes, compressed: bool = False) -> dict:
    payload = gzip.compress(data) if compressed else data
    return {"mime": "image/svg+xml", "data": base64.b64encode(payload).decode(), "compressed": compressed}


def test_unpack_writes_valid_resources(tmp_path):
    src = tmp_path / "export.html"
    src.write_text(export_html({"logo-1": res(b"<svg/>", compressed=True)}), encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out" / "resources" / "logo-1.svg").read_bytes() == b"<svg/>"


def test_unpack_lists_the_library_classes_of_the_given_prefix(tmp_path):
    src = tmp_path / "page.html"
    src.write_text('<a class="ui-btn ui-solid grid-2"></a><style>:root{--ui-ink:#111}</style>', encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "a"), "--class-prefix", "ui")
    assert r.returncode == 0, r.stderr
    inv = json.loads((tmp_path / "a" / "inventory.json").read_text())
    assert inv["class_prefix"] == "ui" and inv["library_classes"] == ["ui-btn", "ui-solid"]
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "b"))
    inv = json.loads((tmp_path / "b" / "inventory.json").read_text())
    assert inv["class_prefixes"][0] == ["ui", 2] and "library_classes" not in inv
    assert run(UNPACK, "--file", str(src), "--out", str(tmp_path / "c"), "--class-prefix", "../x").returncode == 2


def test_unpack_refuses_traversal_and_absolute_ids(tmp_path):
    for rid in ("../../src/index", "/tmp/x", "Logo", "a/b", ".."):
        src = tmp_path / "export.html"
        src.write_text(export_html({"ok-1": res(b"x"), rid: res(b"pwned")}), encoding="utf-8")
        out = tmp_path / "out"
        r = run(UNPACK, "--file", str(src), "--out", str(out))
        assert r.returncode == 1, rid
        assert "refused export" in r.stderr
        assert list((out / "resources").iterdir()) == [], "nothing is written when one id is refused"
    assert not (tmp_path / "src").exists()


def test_unpack_refuses_symlinked_resources_dir(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "resources").symlink_to(outside)
    src = tmp_path / "export.html"
    src.write_text(export_html({"a": res(b"x")}), encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(out))
    assert r.returncode == 1
    assert list(outside.iterdir()) == []


def test_unpack_caps_decompression(tmp_path):
    src = tmp_path / "export.html"
    src.write_text(export_html({"bomb": res(b"\0" * 200_000, compressed=True)}), encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "out"), "--max-bytes", "100000")
    assert r.returncode == 1
    assert "more than 100000 bytes" in r.stderr
    assert not (tmp_path / "out" / "resources" / "bomb.svg").exists()
