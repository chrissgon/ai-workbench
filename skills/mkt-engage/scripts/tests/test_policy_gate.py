"""Offline tests of skills/mkt-engage/scripts/policy_gate.py: the standing approval bound to the policy hash,
limits, the reply rules and the source check for factual answers."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
GATE = REPO / "skills/mkt-engage/scripts/policy_gate.py"

POLICY = """# Policy
```engagement-policy
{"auto_reply_categories": ["thanks_or_praise", "question_answerable_from_sources"], "languages": ["EN"],
 "max_replies_per_day": 2, "max_auto_replies_per_person_per_post": 1,
 "reply_rules": {"max_sentences": 3, "max_emojis": 0, "max_hashtags": 0, "allow_links": false, "banned": ["game changer"]},
 "never_in_replies": ["first computer"]}
```
"""
PROFILE = """```sensitive-topics
{"action": "never_reply_escalate_to_user", "topics": {"salary": {"keywords": ["salary"], "exclude": []}}}
```
"""


@pytest.fixture()
def proj(tmp_path):
    (tmp_path / "docs/marketing").mkdir(parents=True)
    (tmp_path / "docs/brand").mkdir(parents=True)
    (tmp_path / "docs/workbench").mkdir(parents=True)
    (tmp_path / "docs/marketing/engagement-policy.md").write_text(POLICY)
    (tmp_path / "docs/brand/profile.md").write_text(PROFILE + "\n| tinykv | 900 lines, zero deps |\n")
    h = hashlib.sha256(POLICY.encode()).hexdigest()
    (tmp_path / "docs/workbench/state.md").write_text(
        f"| standing | engagement | policy:{h} | 2026-09-30 | 2099-01-01 | active |\n")
    (tmp_path / "comment.json").write_text(json.dumps({
        "comment_urn": "urn:li:comment:(urn:li:activity:1,2)", "post_urn": "urn:li:activity:1",
        "commenter": "Sam", "text": "How big is tinykv?"}))
    return tmp_path


def decide(proj, category="question_answerable_from_sources", reply="About 900 lines, and zero deps.",
           sources=("docs/brand/profile.md, proof table",), language="EN"):
    (proj / "reply.txt").write_text(reply)
    args = [sys.executable, str(GATE), "decide", "--policy", "docs/marketing/engagement-policy.md",
            "--comment-file", "comment.json", "--category", category, "--language", language,
            "--reply-file", "reply.txt", "--skills-dir", str(REPO / "skills")]
    if sources is not None:
        (proj / "sources.json").write_text(json.dumps(list(sources)))
        args += ["--sources-file", "sources.json"]
    r = subprocess.run(args, capture_output=True, text=True, cwd=proj, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_factual_answer_with_its_numbers_in_the_cited_file_goes_out(proj):
    assert decide(proj)["decision"] == "auto"


def test_a_number_missing_from_the_sources_goes_to_the_inbox(proj):
    out = decide(proj, reply="About 900 lines, 0.8 ms p99 on a Raspberry Pi.")
    assert out["decision"] == "inbox" and any("0.8" in r for r in out["reasons"])


def test_a_factual_answer_without_sources_goes_to_the_inbox(proj):
    assert decide(proj, sources=None)["decision"] == "inbox"
    assert decide(proj, sources=[])["decision"] == "inbox"


def test_a_source_outside_the_project_is_refused(proj):
    out = decide(proj, sources=["../../etc/hosts"])
    assert out["decision"] == "inbox" and any("names no file" in r for r in out["reasons"])


def test_a_bare_file_name_is_looked_up_in_docs_brand(proj):
    assert decide(proj, sources=["profile.md:3"])["decision"] == "auto"


def test_praise_needs_no_sources(proj):
    assert decide(proj, category="thanks_or_praise", reply="Thanks, Sam.", sources=None)["decision"] == "auto"


def test_an_edited_policy_is_not_covered_by_the_approval(proj):
    p = proj / "docs/marketing/engagement-policy.md"
    p.write_text(p.read_text().replace('"max_replies_per_day": 2', '"max_replies_per_day": 20'))
    assert decide(proj)["decision"] == "inbox"


def test_paused_approval_stops_automatic_replies(proj):
    s = proj / "docs/workbench/state.md"
    s.write_text(s.read_text().replace("| active |", "| paused |"))
    out = decide(proj)
    assert out["decision"] == "inbox" and any("paused" in r for r in out["reasons"])


def test_reply_rules_and_phrases_never_in_replies(proj):
    out = decide(proj, category="thanks_or_praise", sources=None,
                 reply="Thanks! It started with my first computer. Game changer, see tinykv.dev #rust 🙂")
    reasons = " ".join(out["reasons"])
    assert out["decision"] == "inbox"
    for word in ("emoji", "hashtag", "link", "first computer", "game changer"):
        assert word in reasons


def test_sensitive_comment_is_locked(proj):
    (proj / "comment.json").write_text(json.dumps({
        "comment_urn": "urn:li:comment:(urn:li:activity:1,3)", "post_urn": "urn:li:activity:1",
        "commenter": "Kim", "text": "Nice! What's your salary?"}))
    out = decide(proj, category="thanks_or_praise", reply="Thanks, Kim.", sources=None)
    assert out["decision"] == "inbox" and any("sensitive" in r for r in out["reasons"])


def test_other_language_goes_to_the_inbox(proj):
    assert decide(proj, category="thanks_or_praise", reply="Valeu, Sam.", sources=None, language="PT")["decision"] == "inbox"


def gate(proj, *args):
    return subprocess.run([sys.executable, str(GATE), "decide", "--policy", "docs/marketing/engagement-policy.md",
                           "--comment-file", "comment.json", "--category", "thanks_or_praise", "--language", "EN",
                           *args], capture_output=True, text=True, cwd=proj, timeout=60)


def test_a_missing_reply_file_exits_2_without_a_traceback(proj):
    r = gate(proj, "--reply-file", "missing.txt")
    assert r.returncode == 2 and "--reply-file" in r.stderr and "Traceback" not in r.stderr and r.stdout == ""


def test_the_lock_beside_the_script_runs_without_a_skills_folder(proj):
    (proj / "reply.txt").write_text("Thanks, Kim.")
    (proj / "comment.json").write_text(json.dumps({
        "comment_id": "urn:li:comment:(urn:li:activity:1,3)", "post_id": "urn:li:activity:1",
        "commenter": "Kim", "text": "Nice! What's your salary?"}))
    r = gate(proj, "--reply-file", "reply.txt")
    out = json.loads(r.stdout)
    assert r.returncode == 0 and any("sensitive topics" in x for x in out["reasons"]), r.stderr


@pytest.mark.parametrize("names", [("comment_id", "post_id"), ("comment_urn", "post_urn")])
def test_the_comment_and_the_log_are_read_under_both_names(proj, names):
    cid, pid = names
    (proj / "comment.json").write_text(json.dumps({
        cid: "urn:li:comment:(urn:li:activity:1,2)", pid: "urn:li:activity:1", "commenter": "Sam",
        "text": "How big is tinykv?"}))
    assert decide(proj)["decision"] == "auto"
    for logged in (("comment_urn", "post_urn"), ("comment_id", "post_id")):
        (proj / "docs/marketing/engagement-log.jsonl").write_text(json.dumps({
            "action": "auto_replied", logged[0]: "urn:li:comment:(urn:li:activity:1,2)", logged[1]: "urn:li:activity:1",
            "commenter": "Sam", "logged_at": "2026-09-30T10:00:00+00:00"}) + "\n")
        reasons = " ".join(decide(proj)["reasons"])
        assert "already answered" in reasons and "already got an automatic reply" in reasons


def test_a_comment_without_its_identifier_is_refused(proj):
    (proj / "comment.json").write_text(json.dumps({"commenter": "Sam", "text": "hi", "post_id": "p"}))
    (proj / "reply.txt").write_text("Thanks.")
    r = gate(proj, "--reply-file", "reply.txt")
    assert r.returncode == 2 and "comment_id" in r.stderr


@pytest.mark.parametrize("reply", ["Thanks! Slides at lnk.example/db-course", "See https://code.example/x",
                                   "www.example.org has it", "It is on tinykv.dev"])
def test_one_link_pattern_finds_every_form(proj, reply):
    out = decide(proj, category="thanks_or_praise", reply=reply, sources=None)
    assert "reply: contains a link" in out["reasons"]


def test_a_file_name_is_not_a_link(proj):
    out = decide(proj, category="thanks_or_praise", reply="Thanks, it is all in notes.md.", sources=None)
    assert "reply: contains a link" not in out["reasons"]


def test_the_link_pattern_is_the_one_of_check_post():
    gate_src = GATE.read_text()
    post_src = (REPO / "shared/scripts/check_post.py").read_text()
    pattern = lambda src: src[src.index("LINK = re.compile("):].split(", re.I)", 1)[0]
    assert pattern(gate_src) == pattern(post_src)
