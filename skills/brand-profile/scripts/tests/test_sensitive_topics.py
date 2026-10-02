"""Tests for skills/brand-profile/scripts/sensitive_topics.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-profile/scripts/tests
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


SENSITIVE = "skills/brand-profile/scripts/sensitive_topics.py"
LOCK = ('# P\n\n```sensitive-topics\n{"action": "never_reply_escalate_to_user", "topics": {'
        '"family": {"keywords": ["family", "mother"], "exclude": ["font-family"]}, '
        '"politics": {"keywords": ["election"], "exclude": []}}}\n```\n')


def test_sensitive_topics_locks_on_whole_words_and_skips_excluded_phrases(tmp_path):
    prof = tmp_path / "profile.md"
    prof.write_text(LOCK, encoding="utf-8")
    locked = run(SENSITIVE, "--profile", str(prof), stdin="How is your Family? and the Election?")
    assert locked.returncode == 1
    assert json.loads(locked.stdout)["topics"] == {"family": ["family"], "politics": ["election"]}
    for text in ("which font-family do you use?", "familiar with @layer?", "a motherboard question"):
        r = run(SENSITIVE, "--profile", str(prof), stdin=text)
        assert r.returncode == 0, (text, r.stdout)


def test_sensitive_topics_refuses_a_profile_without_a_valid_block(tmp_path):
    prof = tmp_path / "profile.md"
    prof.write_text("# P\nno block\n", encoding="utf-8")
    assert run(SENSITIVE, "--profile", str(prof), "--validate").returncode == 2
    prof.write_text('```sensitive-topics\n{"topics": {"x": {"keywords": []}}}\n```\n', encoding="utf-8")
    assert run(SENSITIVE, "--profile", str(prof), "--validate").returncode == 2
