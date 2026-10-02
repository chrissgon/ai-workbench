"""Tests for skills/design-execute/scripts/screenshot.mjs. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/design-execute/scripts/tests
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


# ---------- design-execute/screenshot.mjs (L13) ----------

SHOT = ROOT / "skills/design-execute/scripts/screenshot.mjs"


def test_screenshot_checks_out_and_never_installs(tmp_path):
    import shutil
    import pytest
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    work = tmp_path / "work"
    work.mkdir()
    (work / "a.html").write_text("<p>x</p>\n", encoding="utf-8")
    (work / "link.png").symlink_to(tmp_path / "elsewhere.png")
    shot = lambda out: subprocess.run([node, str(SHOT), "--html", "a.html", "--out", out, "--width", "10",
                                       "--height", "10"], cwd=work, capture_output=True, text=True, timeout=60,
                                      env={"PATH": str(Path(node).parent), "HOME": str(tmp_path)})
    for out in ("../x.png", str(tmp_path / "x.png"), "a.jpg", "missing/a.png", "link.png"):
        r = shot(out)
        assert r.returncode == 2 and "--out" in r.stderr, (out, r.stderr)
    r = shot("ok.png")
    assert r.returncode in (0, 2)
    if r.returncode == 2:
        assert "npm install --no-save playwright@1.63.0" in r.stderr
    assert not (work / "node_modules").exists()
