"""The corpus of archived lab runs (runtime/tests/corpus/endings.jsonl) is well formed, and the classifier of
endings never guesses on it. Offline: the corpus is a file; no model is called.

The corpus is built by runtime/tests/corpus/build_corpus.py from an archive of lab runs. This file checks its
form and the two things the first classifier must already hold on every line; which ending each line must
get is tested when the classifier is made total (stage 2 of the platform plan).

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_endings_corpus.py
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "runtime"))
endings = importlib.import_module("endings")
CORPUS = REPO / "runtime" / "tests" / "corpus" / "endings.jsonl"
KEYS = {"id", "skill", "case", "tier", "response", "created", "modified", "deleted", "stopped", "outputs_written",
        "stop_reason", "guards", "pass_rate"}


def lines():
    return [json.loads(line) for line in CORPUS.read_text(encoding="ascii").splitlines()]


def test_the_corpus_is_sorted_has_closed_keys_and_holds_runs_of_both_tiers():
    rows = lines()
    assert len(rows) >= 400 and [r["id"] for r in rows] == sorted({r["id"] for r in rows})
    for r in rows:
        assert set(r) == KEYS, r["id"]
        assert r["tier"] in ("strong", "floor") and isinstance(r["response"], str)
        assert r["stopped"] == (not (r["created"] or r["modified"] or r["deleted"])), r["id"]
        assert set(r["outputs_written"]) <= set(r["created"] + r["modified"]), r["id"]
        assert r["guards"] is None or all(set(g) == {"position", "passed"} for g in r["guards"]), r["id"]
    assert {r["tier"] for r in rows} == {"strong", "floor"} and len({r["skill"] for r in rows}) >= 40
    assert (REPO / "skills" / rows[0]["skill"]).is_dir()


def test_the_classifier_answers_within_its_closed_list_and_never_calls_a_run_that_wrote_nothing_done():
    counts = {}
    for r in lines():
        changes = {"created": r["created"], "modified": r["modified"], "deleted": r["deleted"], "unchanged": []}
        ending, why = endings.classify(r["response"], changes, r["outputs_written"], [], [])
        assert ending in endings.ENDINGS and why, r["id"]
        if r["stopped"]:
            assert ending in ("question", "unclassified"), r["id"]
        else:
            assert ending != "question", r["id"]
        if not r["outputs_written"]:
            assert ending not in ("done", "draft_with_questions"), r["id"]
        counts[ending] = counts.get(ending, 0) + 1
    assert counts.get("question", 0) > 0 and counts.get("done", 0) > 0 and counts.get("unclassified", 0) > 0
