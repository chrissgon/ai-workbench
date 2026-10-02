"""Tests for skills/brand-identity/scripts/contrast.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-identity/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


CONTRAST = "skills/brand-identity/scripts/contrast.py"


def test_contrast_computes_wcag_ratios_and_fails_by_use():
    pairs = {"pairs": [{"name": "white on black", "fg": "#FFF", "bg": "#000000", "use": "text"},
                       {"name": "blue on white", "fg": "#0092CD", "bg": "#FFFFFF", "use": "large"},
                       {"name": "blue on white small", "fg": "#0092CD", "bg": "#FFFFFF", "use": "text"}]}
    r = run(CONTRAST, stdin=json.dumps(pairs))
    assert r.returncode == 1
    out = {p["name"]: p for p in json.loads(r.stdout)["pairs"]}
    assert out["white on black"]["ratio"] == 21.0 and out["white on black"]["pass"] is True
    assert out["blue on white"]["ratio"] == 3.5 and out["blue on white"]["pass"] is True
    assert out["blue on white small"]["pass"] is False


def test_contrast_refuses_bad_colours_and_uses():
    for pair in ({"fg": "blue", "bg": "#000"}, {"fg": "#000", "bg": "#FFF", "use": "huge"}):
        assert run(CONTRAST, stdin=json.dumps({"pairs": [pair]})).returncode == 2
    assert run(CONTRAST, stdin="[]").returncode == 2
