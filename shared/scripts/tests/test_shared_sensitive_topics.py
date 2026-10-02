"""Tests for shared/scripts/sensitive_topics.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest shared/scripts/tests
"""
from __future__ import annotations

import json

from shared_helpers import clean_usage_error, run

SENSITIVE = "sensitive_topics.py"
LOCK = ('# P\n\n```sensitive-topics\n{"action": "never_reply_escalate_to_user", "topics": {'
        '"family": {"keywords": ["family", "mother"], "exclude": ["font-family"]}, '
        '"politics": {"keywords": ["election"], "exclude": []}}}\n```\n')


def profile(tmp_path, text=LOCK):
    path = tmp_path / "profile.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_sensitive_topics_locks_on_whole_words_and_skips_excluded_phrases(tmp_path):
    prof = profile(tmp_path)
    locked = run(SENSITIVE, "--profile", prof, stdin="How is your Family? and the Election?")
    assert locked.returncode == 1
    out = json.loads(locked.stdout)
    assert out["locked"] is True and out["action"] == "never_reply_escalate_to_user"
    assert out["topics"] == {"family": ["family"], "politics": ["election"]}
    for text in ("which font-family do you use?", "familiar with @layer?", "a motherboard question"):
        r = run(SENSITIVE, "--profile", prof, stdin=text)
        assert r.returncode == 0 and json.loads(r.stdout)["locked"] is False, (text, r.stdout)


def test_validate_checks_the_block_and_reads_no_text(tmp_path):
    r = run(SENSITIVE, "--profile", profile(tmp_path), "--validate", stdin="How is your family?")
    assert r.returncode == 0 and json.loads(r.stdout) == {"ok": True, "topics": ["family", "politics"]}


def test_sensitive_topics_refuses_a_profile_without_a_valid_block(tmp_path):
    assert clean_usage_error(run(SENSITIVE, "--profile", profile(tmp_path, "# P\nno block\n"), "--validate"))
    bad = profile(tmp_path, '```sensitive-topics\n{"topics": {"x": {"keywords": []}}}\n```\n')
    assert clean_usage_error(run(SENSITIVE, "--profile", bad, "--validate"))
    assert clean_usage_error(run(SENSITIVE, "--profile", profile(tmp_path, "```sensitive-topics\nnot json\n```\n")))
    assert clean_usage_error(run(SENSITIVE, "--profile", str(tmp_path / "absent.md")))


def test_help_and_usage_errors():
    r = run(SENSITIVE, "--help")
    assert r.returncode == 0 and "Usage:" in r.stdout
    assert clean_usage_error(run(SENSITIVE))
    assert clean_usage_error(run(SENSITIVE, "--profile"))
    assert clean_usage_error(run(SENSITIVE, "--nope"))
