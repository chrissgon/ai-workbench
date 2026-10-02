"""Tests for skills/brand-guidelines/scripts/check_guide.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-guidelines/scripts/tests
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


CHECK_GUIDE = "skills/brand-guidelines/scripts/check_guide.py"


def test_check_guide_flags_stale_quotes_uncited_files_and_foreign_colours(tmp_path):
    brand = tmp_path / "brand"
    brand.mkdir()
    (brand / "voice.md").write_text('> hello network, today I share\n', encoding="utf-8")
    (brand / "identity.md").write_text("accent #07B6F0\n", encoding="utf-8")
    (brand / "strategy.md").write_text("label: Builder of small tools\n", encoding="utf-8")
    guide = tmp_path / "guide.md"
    guide.write_text('Label "Builder of small tools" [strategy.md]\nDon\'t: "a sentence nobody ever wrote"\n'
                     'Accent #07B6F0 and #FF0000 [identity.md] [voice.md] [ghost.md]\n', encoding="utf-8")
    r = run(CHECK_GUIDE, "--guide", str(guide), "--brand-dir", str(brand))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["stale_quotes"] == ["a sentence nobody ever wrote"]
    assert out["hex_not_in_identity"] == ["#FF0000"]
    assert out["missing_sources"] == ["ghost.md"]
    ok = tmp_path / "ok.md"
    ok.write_text('"Builder of small tools" [strategy.md] [identity.md] [voice.md] #07B6F0; not defined yet: brand-profile, brand-name\n', encoding="utf-8")
    assert run(CHECK_GUIDE, "--guide", str(ok), "--brand-dir", str(brand)).returncode == 0


def test_check_guide_requires_quoted_examples_and_names_the_skill_of_a_missing_file(tmp_path):
    brand = tmp_path / "brand"
    brand.mkdir()
    for f in ("strategy.md", "voice.md", "identity.md", "profile.md"):
        (brand / f).write_text('> "NEW BLOG POST!!!"\n', encoding="utf-8")
    guide = tmp_path / "guide.md"
    guide.write_text('[strategy.md] [voice.md] [identity.md] [profile.md]\n## 8. Do and don\'t\n| Do | Don\'t |\n|---|---|\n'
                     '| "NEW BLOG POST!!!" | Too many emojis |\n', encoding="utf-8")
    out = json.loads(run(CHECK_GUIDE, "--guide", str(guide), "--brand-dir", str(brand)).stdout)
    assert out["unquoted_examples"] == ["Too many emojis"]
    assert out["absent_not_named"] == ["name.md"]
    guide.write_text('[strategy.md] [voice.md] [identity.md] [profile.md] Name: not defined yet, run brand-name.\n'
                     '## 8. Do and don\'t\n| Do | Don\'t |\n|---|---|\n| "NEW BLOG POST!!!" | "NEW BLOG POST!!!" |\n', encoding="utf-8")
    assert run(CHECK_GUIDE, "--guide", str(guide), "--brand-dir", str(brand)).returncode == 0
