"""Tests for skills/brand-voice/scripts/voice_stats.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-voice/scripts/tests
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


VOICE_STATS = "skills/brand-voice/scripts/voice_stats.py"
ROCKET, ZWJ, VS16 = chr(0x1F680), chr(0x200D), chr(0xFE0F)


def test_voice_stats_counts_emoji_sequences_hashtags_and_the_closing_question():
    family = chr(0x1F468) + ZWJ + chr(0x1F469) + ZWJ + chr(0x1F467)
    text = f"{ROCKET} NEW POST!!! {ROCKET}{ROCKET}\nbody with #inline tag {family} {chr(0x26A1)}{VS16}\nwhat do you run?\n\n#rust #db"
    r = run(VOICE_STATS, "stats", stdin=json.dumps([{"id": "S1", "text": text}]))
    assert r.returncode == 0, r.stderr
    s = json.loads(r.stdout)["samples"][0]
    assert (s["emojis"], s["emoji_line_starts"], s["hashtags"], s["exclamations"]) == (5, 1, 3, 3)
    assert s["ends_with_question"] is True


def test_voice_stats_check_reads_the_rules_block_and_reports_violations(tmp_path):
    guide = tmp_path / "voice.md"
    guide.write_text('# Voice\n\n```voice-rules\n{"max_emojis": 0, "max_hashtags": 2, "end_with_question": true, '
                     '"banned": ["excited to announce"]}\n```\n', encoding="utf-8")
    bad = run(VOICE_STATS, "check", "--rules", str(guide),
              stdin=json.dumps({"id": "d", "text": f"Excited to announce tinykv {ROCKET}\n#a #b #c"}))
    assert bad.returncode == 1
    v = json.loads(bad.stdout)["violations"]
    assert "1 emojis, limit 0" in v and "3 hashtags, limit 2" in v and "does not end with a question" in v
    assert "banned phrase: 'excited to announce'" in v
    good = run(VOICE_STATS, "check", "--rules", str(guide), stdin=json.dumps({"id": "d", "text": "900 lines. what do you use?\n#rust"}))
    assert good.returncode == 0, good.stdout


def test_voice_stats_refuses_unknown_rules_and_bad_input(tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text('{"max_emojis": true}', encoding="utf-8")
    assert run(VOICE_STATS, "check", "--rules", str(rules), stdin='{"text": "x"}').returncode == 2
    assert run(VOICE_STATS, "stats", stdin="not json").returncode == 2
    assert run(VOICE_STATS, "stats", stdin='{"text": "not a list"}').returncode == 2
