"""Tests for shared/scripts/check_post.py, which had none. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest shared/scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys

import pytest

from shared_helpers import SOURCES, clean_usage_error, run

CHECK_POST = "check_post.py"
spec = importlib.util.spec_from_file_location("check_post_under_test", SOURCES / CHECK_POST)
check_post = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_post)

VOICE = '# Voice\n\n```voice-rules\n{"max_emojis": 0, "max_hashtags": 2, "end_with_question": true}\n```\n'
PROFILE = ('# Profile\n\n```sensitive-topics\n{"action": "never_reply_escalate_to_user", '
           '"topics": {"salary": {"keywords": ["salary"], "exclude": []}}}\n```\n')
POST = "One index made deletes 200 times faster.\nWhich one do you run?\n#databases"


def content(post=POST, comment="Write-up: tinykv.example/deletes", extra=""):
    text = f"# Post: deletes\n\n- Owner: mkt-social-copy\n\n## Post\n\n```post\n{post}\n```\n"
    if comment is not None:
        text += f"\n## First comment\n\n```first-comment\n{comment}\n```\n"
    return text + extra


@pytest.fixture()
def project(tmp_path):
    (tmp_path / "docs/brand").mkdir(parents=True)
    (tmp_path / "docs/marketing/content").mkdir(parents=True)
    (tmp_path / "docs/brand/voice.md").write_text(VOICE, encoding="utf-8")
    (tmp_path / "docs/brand/profile.md").write_text(PROFILE, encoding="utf-8")

    def check(text, *args):
        path = tmp_path / "docs/marketing/content/2026-10-05-deletes.md"
        path.write_text(text, encoding="utf-8")
        return run(CHECK_POST, "--content", str(path.relative_to(tmp_path)), *args, cwd=tmp_path)
    check.root = tmp_path
    return check


def test_a_good_post_passes_every_check(project):
    r = project(content())
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] is True and out["unchecked"] == [] and out["problems"] == []
    assert out["post"]["chars"] == len(POST) and out["post"]["lines"] == 3 and out["post"]["links"] == []
    assert out["post"]["voice"]["ok"] is True and out["post"]["sensitive"]["locked"] is False
    assert out["first_comment"]["links"] == ["tinykv.example/deletes"]


def test_a_content_file_without_one_closed_post_block_is_a_bad_file(project):
    for text, message in (("# Post\n\nno block here\n", "no ```post block"),
                          (content() + "\n```post\nagain\n```\n", "more than one ```post block"),
                          ("```post\nnever closed\n", "is not closed"),
                          ("```post\n```\n", "no ```post block")):
        r = project(text)
        assert clean_usage_error(r) and message in r.stderr, text
    assert clean_usage_error(run(CHECK_POST, "--content", str(project.root / "absent.md")))
    (project.root / "bytes.md").write_bytes(b"\xff\xfe```post\nx\n```\n")
    assert clean_usage_error(run(CHECK_POST, "--content", str(project.root / "bytes.md")))


def test_a_failed_check_is_a_problem_and_exit_1(project):
    r = project(content(post="We doubled every salary this year!\n#a #b #c"))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["ok"] is False and out["unchecked"] == []
    assert any("voice" in p and "3 hashtags, limit 2" in p for p in out["problems"])
    assert any("sensitive topics" in p and "salary" in p for p in out["problems"])
    r = project(content(comment="Ask me about my salary: tinykv.example"))
    assert r.returncode == 1 and json.loads(r.stdout)["problems"] == ["first comment: sensitive topics {'salary': ['salary']}"]


def test_a_check_that_cannot_run_is_unchecked_and_never_a_pass(project):
    (project.root / "docs/brand/voice.md").unlink()
    r = project(content(comment=None))
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["ok"] is False and out["problems"] == [] and out["first_comment"] is None
    assert out["unchecked"] == ["post: docs/brand/voice.md not found"]
    r = project(content(), "--voice", "docs/brand/voice.md", "--profile", "docs/brand/absent.md")
    assert sorted(json.loads(r.stdout)["unchecked"]) == [
        "first comment: docs/brand/absent.md not found", "post: docs/brand/absent.md not found",
        "post: docs/brand/voice.md not found"]


def test_the_two_scripts_are_found_next_to_this_one_first_then_in_a_skills_folder(tmp_path, project):
    """A skill carries generated copies of the scripts it calls, in its own scripts folder."""
    alone = tmp_path / "skill" / "scripts"
    alone.mkdir(parents=True)
    shutil.copy(SOURCES / CHECK_POST, alone / CHECK_POST)
    path = project.root / "docs/marketing/content/2026-10-05-deletes.md"
    path.write_text(content(), encoding="utf-8")

    def check(*args):
        r = subprocess.run([sys.executable, str(alone / CHECK_POST), "--content", str(path), *args],
                           capture_output=True, text=True, cwd=project.root, timeout=60)
        return r.returncode, json.loads(r.stdout)
    code, out = check()
    assert code == 1 and sorted(out["unchecked"]) == [
        "first comment: sensitive_topics.py not installed", "post: sensitive_topics.py not installed",
        "post: voice_stats.py not installed"]
    # The older layout: each script in the skill that owns it, under a skills folder.
    skills = tmp_path / "installed"
    for skill, script in (("brand-voice", "voice_stats.py"), ("brand-profile", "sensitive_topics.py")):
        (skills / skill / "scripts").mkdir(parents=True)
        shutil.copy(SOURCES / script, skills / skill / "scripts" / script)
    assert check("--skills-dir", str(skills)) == (0, check("--skills-dir", str(skills))[1])
    # Copies beside the script win over the skills folder: a broken one beside it is the one that runs.
    (alone / "voice_stats.py").write_text("import sys\nsys.exit(7)\n", encoding="utf-8")
    shutil.copy(SOURCES / "sensitive_topics.py", alone / "sensitive_topics.py")
    code, out = check("--skills-dir", str(skills))
    assert code == 1 and [u.strip() for u in out["unchecked"]] == ["post: voice_stats.py exited 7:"]
    shutil.copy(SOURCES / "voice_stats.py", alone / "voice_stats.py")
    assert check()[0] == 0


@pytest.mark.parametrize("text, found", [
    ("see short.example/x today", ["short.example/x"]),
    ("the course is at bit.ly/priya-course.", ["bit.ly/priya-course"]),
    ("read https://tinykv.example/docs, then reply", ["https://tinykv.example/docs"]),
    ("www.tinykv.example has it", ["www.tinykv.example"]),
    ("tinykv.dev is live, and so is tinykv.com.br", ["tinykv.dev", "tinykv.com.br"]),
    ("docs.tinykv.io/guide (new)", ["docs.tinykv.io/guide"]),
    ("open notes.md and run payload.py with node.js", []),
    ("version 1.2 costs 3.50/month, e.g. for a team", []),
    ("write to dana@tinykv.dev", []),
    ("no link at all", []),
])
def test_one_link_pattern(text, found):
    """The pattern knew seven endings and no host with a path, so a shortened address was not a link here
    while the reply gate of another skill counted it."""
    assert check_post.links(text) == found


def test_no_body_links_makes_a_link_in_the_post_a_problem_and_never_one_in_the_first_comment(project):
    with_link = content(post="The write-up is at tinykv.example/deletes\nWhich index do you run?")
    r = project(with_link)
    assert r.returncode == 0 and json.loads(r.stdout)["post"]["links"] == ["tinykv.example/deletes"]
    r = project(with_link, "--no-body-links")
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["ok"] is False
    assert out["problems"] == ["post: links in the body ['tinykv.example/deletes']; they go in the first comment"]
    assert project(content(), "--no-body-links").returncode == 0  # the link is in the first comment


def test_help_and_usage_errors():
    r = run(CHECK_POST, "--help")
    assert r.returncode == 0 and "--no-body-links" in r.stdout
    assert clean_usage_error(run(CHECK_POST))
    assert clean_usage_error(run(CHECK_POST, "--content"))
    assert clean_usage_error(run(CHECK_POST, "--content", "x.md", "--nope"))
