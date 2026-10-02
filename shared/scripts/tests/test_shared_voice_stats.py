"""Tests for shared/scripts/voice_stats.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest shared/scripts/tests
"""
from __future__ import annotations

import json

from shared_helpers import clean_usage_error, run

VOICE_STATS = "voice_stats.py"
ROCKET, ZWJ, VS16 = chr(0x1F680), chr(0x200D), chr(0xFE0F)


def test_voice_stats_counts_emoji_sequences_hashtags_and_the_closing_question():
    family = chr(0x1F468) + ZWJ + chr(0x1F469) + ZWJ + chr(0x1F467)
    text = f"{ROCKET} NEW POST!!! {ROCKET}{ROCKET}\nbody with #inline tag {family} {chr(0x26A1)}{VS16}\nwhat do you run?\n\n#rust #db"
    r = run(VOICE_STATS, "stats", stdin=json.dumps([{"id": "S1", "text": text}]))
    assert r.returncode == 0, r.stderr
    s = json.loads(r.stdout)["samples"][0]
    assert (s["emojis"], s["emoji_line_starts"], s["hashtags"], s["exclamations"]) == (5, 1, 3, 3)
    assert s["ends_with_question"] is True


def guide(tmp_path, rules='{"max_emojis": 0, "max_hashtags": 2, "end_with_question": true, "banned": ["excited to announce"]}'):
    path = tmp_path / "voice.md"
    path.write_text(f"# Voice\n\n```voice-rules\n{rules}\n```\n", encoding="utf-8")
    return str(path)


def test_voice_stats_check_reads_the_rules_block_and_reports_violations(tmp_path):
    bad = run(VOICE_STATS, "check", "--rules", guide(tmp_path),
              stdin=json.dumps({"id": "d", "text": f"Excited to announce tinykv {ROCKET}\n#a #b #c"}))
    assert bad.returncode == 1
    v = json.loads(bad.stdout)["violations"]
    assert "1 emojis, limit 0" in v and "3 hashtags, limit 2" in v and "does not end with a question" in v
    assert "banned phrase: 'excited to announce'" in v
    good = run(VOICE_STATS, "check", "--rules", guide(tmp_path),
               stdin=json.dumps({"id": "d", "text": "900 lines. what do you use?\n#rust"}))
    assert good.returncode == 0, good.stdout


def test_voice_stats_refuses_unknown_rules_and_bad_input(tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text('{"max_emojis": true}', encoding="utf-8")
    assert clean_usage_error(run(VOICE_STATS, "check", "--rules", str(rules), stdin='{"text": "x"}'))
    rules.write_text('["max_emojis"]', encoding="utf-8")
    assert clean_usage_error(run(VOICE_STATS, "check", "--rules", str(rules), stdin='{"text": "x"}'))
    assert clean_usage_error(run(VOICE_STATS, "stats", stdin="not json"))
    assert clean_usage_error(run(VOICE_STATS, "stats", stdin='{"text": "not a list"}'))
    assert clean_usage_error(run(VOICE_STATS, "check", "--rules", guide(tmp_path), stdin='[{"text": "a list"}]'))


def test_the_arguments_are_checked_before_standard_input_is_read(tmp_path):
    """With no argument it printed the help and exited 0; `stats --help` and an unknown subcommand answered
    "stdin is not JSON", and blocked when standard input was a terminal."""
    valid = json.dumps([{"id": "S1", "text": "x"}])
    for args in ((), ("nope",), ("stats", "extra"), ("check",), ("check", "--rules"), ("check", "--file", "x"),
                 ("check", "--rules", guide(tmp_path), "extra")):
        r = run(VOICE_STATS, *args, stdin=valid)
        assert clean_usage_error(r), args
        assert "usage: voice_stats.py" in r.stderr and "stdin is not JSON" not in r.stderr, args
    missing = run(VOICE_STATS, "check", "--rules", str(tmp_path / "absent.md"), stdin="not json")
    assert clean_usage_error(missing) and "cannot read" in missing.stderr  # the rules file, before the input
    for args in (("--help",), ("-h",), ("stats", "--help"), ("check", "--help")):
        r = run(VOICE_STATS, *args, stdin="not json")
        assert r.returncode == 0 and "Usage:" in r.stdout, args
