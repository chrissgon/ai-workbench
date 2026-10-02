"""Offline tests of skills/mkt-vote-round/scripts: vote_state.py (what is pending, the rotation, the slot, the used
topics) and vote_update.py (the new vote files, in the profile repository's exact format)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[4] / "skills/mkt-vote-round/scripts"
PILLARS = "Small tools|Database performance|AI for databases, built in public"
URL = "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000101/"


def dump(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def opts(a, b, c):
    return {"A": a, "B": b, "C": c}


def closed(rnd, pillar, options, counts, winner, url=None):
    return {"round": rnd, "pillar": pillar, "options": options, "counts": dict(zip("ABC", counts)),
            "winner": winner, "post_url": url}


CALENDAR = """# Calendario de conteudo: Dana Example

## Semana 2: 2026-10-12 (rotacao B)

| # | Quando | Pilar | Idioma | Tema | Serve | Material e fonte | Aprovacao | Conteudo | Status |
|---|--------|-------|--------|------|-------|------------------|-----------|----------|--------|
| 4 | 2026-10-12T09:00:00-03:00 | Ferramentas pequenas | PT | tinykv 0.5: TTL without a dependency | devs | notes | plan | - | scheduled |
| 5 | 2026-10-14T09:00:00-03:00 | Performance de banco | EN | Weekly vote winner | devs | vote | plan | - | topic-approved |

## Fontes

| Other | table |
|-------|-------|
| not a | topic |
"""


@pytest.fixture
def vote(tmp_path):
    """Dana's vote files: a closed Database round won by A, an older round with its post, the AI round open."""
    d = tmp_path / "data"
    d.mkdir()
    pick = {"open": True, "round": "2026-10-12", "closes": "2026-10-19", "pillar": "AI for databases, built in public",
            "options": opts("What an LLM got wrong about my indexes", "Logging every failed experiment", "No AI demo yet"),
            "picks": {"3f9a0c1e5b7d2468": "C"},
            "history": [closed("2026-10-05", "Database performance",
                               opts("Durability is a budget: what an fsync demo taught me", "Reading EXPLAIN without guessing",
                                    "The index that made deletes 200 times faster"), (5, 2, 3), "A"),
                        closed("2026-09-28", "Small tools", opts("One config flag", "Deleting code", "Zero dependencies, one year later"),
                               (1, 2, 4), "C", URL)]}
    queue = [{"pillar": "Small tools", "options": opts("tinykv's test suite runs in 1.8 seconds",
                                                        "A 40-line script replaced my monitoring agent", "Why the README is 60 lines")}]
    posts = [{"date": "2026-09-30", "lang": "EN", "title": "Zero dependencies, one year later", "url": URL,
              "image": "assets/posts/2026-09-30-zero-deps.png"}]
    files = {"pick": d / "pick.json", "queue": d / "pick-queue.json", "posts": d / "posts.json", "calendar": tmp_path / "calendar.md"}
    files["pick"].write_text(dump(pick), encoding="utf-8")
    files["queue"].write_text(dump(queue), encoding="utf-8")
    files["posts"].write_text(dump(posts), encoding="utf-8")
    files["calendar"].write_text(CALENDAR, encoding="utf-8")
    files["out"] = tmp_path / "out"
    return files


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True, timeout=60)
    return r.returncode, (json.loads(r.stdout) if r.returncode == 0 else r.stderr)


def state(v, *extra):
    return run("vote_state.py", "--pick", v["pick"], "--queue", v["queue"], "--posts", v["posts"],
               "--calendar", v["calendar"], "--today", "2026-10-12", *extra)


def update(v, *extra):
    return run("vote_update.py", "--pick", v["pick"], "--queue", v["queue"], "--posts", v["posts"], "--out", v["out"], *extra)


# ---------- vote_state.py ----------

def test_the_newest_closed_round_without_a_post_is_pending(vote):
    code, out = state(vote, "--pillars", PILLARS)
    assert code == 0 and out["pending"] is True
    assert out["round"]["round"] == "2026-10-05" and out["round"]["winner"] == "A"
    assert out["round"]["winner_topic"] == "Durability is a budget: what an fsync demo taught me"
    assert out["older_without_post"] == [] and out["open_round"]["round"] == "2026-10-12"


def test_the_next_pillar_follows_the_last_queued_round(vote):
    code, out = state(vote, "--pillars", PILLARS)
    rot = out["rotation"]
    assert rot["sequence"] == ["Small tools", "Database performance", "AI for databases, built in public", "Small tools"]
    assert rot["next_pillar"] == "Database performance" and rot["source"] == "--pillars"
    assert not any("rotation's order" in w for w in out["warnings"])


def test_data_out_of_rotation_order_is_warned(vote):
    queue = json.loads(vote["queue"].read_text())
    queue[0]["pillar"] = "Database performance"
    vote["queue"].write_text(dump(queue))
    code, out = state(vote, "--pillars", PILLARS)
    assert code == 0 and out["rotation"]["next_pillar"] == "AI for databases, built in public"
    assert any("not the rotation's order" in w for w in out["warnings"])


def test_the_rotation_continues_after_the_last_queued_pillar(tmp_path):
    """A three-pillar rotation: the second pillar's round open, the third queued; next comes the first."""
    d = {"pick": tmp_path / "pick.json", "queue": tmp_path / "q.json", "posts": tmp_path / "p.json", "calendar": tmp_path / "c.md"}
    d["pick"].write_text(dump({"open": True, "round": "2026-09-29", "closes": "2026-10-05", "pillar": "Case studies",
                               "options": opts("a one", "b two", "c three"), "picks": {}, "history": []}))
    d["queue"].write_text(dump([{"pillar": "Opinions", "options": opts("d four", "e five", "f six")}]))
    d["posts"].write_text("[]\n")
    d["calendar"].write_text("# Calendar\n")
    code, out = state(d, "--pillars", "Guides|Case studies|Opinions")
    assert code == 0 and out["pending"] is False and out["round"] is None
    assert out["rotation"]["next_pillar"] == "Guides"
    code, out = state(d)
    assert out["rotation"]["next_pillar"] is None and any("--pillars" in w for w in out["warnings"])


def test_without_pillars_the_order_is_read_from_a_full_cycle(vote):
    code, out = state(vote)
    assert out["rotation"]["source"] == "data"
    assert out["rotation"]["next_pillar"] == "Database performance"


def test_a_queued_pillar_outside_the_list_is_an_error(vote):
    code, err = state(vote, "--pillars", "Guides|Case studies|Opinions")
    assert code == 2 and "not one of the pillars" in err


def test_the_slot_is_found_through_an_alias_in_a_calendar_in_another_language(vote):
    code, out = state(vote, "--pillars", PILLARS)
    assert out["slot"] is None and any("--pillar-alias" in w for w in out["warnings"])
    code, out = state(vote, "--pillars", PILLARS, "--pillar-alias", "Database performance=Performance de banco")
    assert out["slot"]["row"] == "5" and out["slot"]["language"] == "EN" and out["slot"]["status"] == "topic-approved"


def test_a_row_that_already_carries_a_post_is_passed_over_for_the_next_free_one(vote):
    cal = vote["calendar"].read_text(encoding="utf-8")
    taken = "| 5 | 2026-10-14T09:00:00-03:00 | Performance de banco | EN | Evals | devs | notes | plan | content/x.md | scheduled (job x) |"
    free = "| 7 | 2026-10-21T09:00:00-03:00 | Performance de banco | PT | Weekly vote winner | devs | vote | plan | - | proposed |"
    lines = [l for l in cal.splitlines() if not l.startswith("| 5 |")]
    at = next(i for i, l in enumerate(lines) if l.startswith("| 4 |")) + 1
    vote["calendar"].write_text("\n".join(lines[:at] + [taken, free] + lines[at:]) + "\n", encoding="utf-8")
    code, out = state(vote, "--pillars", PILLARS, "--pillar-alias", "Database performance=Performance de banco")
    assert out["slot"]["row"] == "7" and out["slot"]["language"] == "PT"
    assert any("passed over" in w and "5 (2026-10-14" in w for w in out["warnings"])
    vote["calendar"].write_text("\n".join(lines[:at] + [taken] + lines[at:]) + "\n", encoding="utf-8")
    code, out = state(vote, "--pillars", PILLARS, "--pillar-alias", "Database performance=Performance de banco")
    assert out["slot"] is None and any("no free calendar row" in w for w in out["warnings"])


def test_used_topics_come_from_calendar_queue_history_open_round_and_posts(vote):
    code, out = state(vote)
    sources = {u["source"].split(" ")[0] for u in out["used_topics"]}
    assert sources == {"calendar", "pick-queue.json[0]", "history", "open", "posts.json"}
    topics = [u["topic"] for u in out["used_topics"]]
    assert "tinykv 0.5: TTL without a dependency" in topics and "not a" not in topics and "topic" not in topics
    assert len(out["used_topics"]) == 2 + 3 + 6 + 3 + 1


def test_check_finds_the_same_topic_in_other_punctuation_and_close_wording(vote):
    code, out = state(vote, "--check", "TINYKV 0.5 - TTL without a dependency!", "--check",
                      "tinykv 0.5 TTL without dependencies, explained", "--check", "Autovacuum and dead tuples")
    exact, close, fresh = out["checks"]
    assert exact["used"] and exact["matches"][0]["source"].startswith("calendar row 4")
    assert close["used"]
    assert not fresh["used"] and fresh["matches"] == []


def test_normalisation_drops_accents_case_apostrophes_and_punctuation():
    sys.path.insert(0, str(SCRIPTS))
    import vote_state
    assert vote_state.normalize("  LinkedIn’s API won't: Café! ") == "linkedins api wont cafe"
    assert vote_state.resembles("LinkedIn's API won't let me read comments. What I did instead.",
                                "LinkedIn's API won't let me read comments on my own posts; what I built instead")
    assert not vote_state.resembles("Evals with and without a skill", "Evals and the cost of a model")


@pytest.mark.parametrize("which,content,message", [
    ("pick", "{not json", "not valid JSON"),
    ("pick", dump({"open": True, "round": "2026-10-12", "closes": "x", "pillar": "p", "options": {"A": "a", "B": "b"},
                   "picks": {}, "history": []}), "exactly the keys A, B and C"),
    ("pick", dump({"open": False, "history": [{"round": "2026-10-05", "pillar": "p", "options": opts("a", "b", "c"),
                                               "counts": {"A": 1, "B": 0, "C": 0}, "winner": "D", "post_url": None}]}), "winner"),
    ("queue", dump({"pillar": "p"}), "must be a list"),
    ("posts", dump([{"date": "2026-10-01", "title": "t"}]), "'url'"),
])
def test_malformed_files_exit_2(vote, which, content, message):
    vote[which].write_text(content, encoding="utf-8")
    code, err = state(vote)
    assert code == 2 and message in err


def test_a_round_without_picks_is_pending_with_no_winner(vote):
    pick = json.loads(vote["pick"].read_text())
    pick["history"][0].update(counts={"A": 0, "B": 0, "C": 0}, winner=None)
    vote["pick"].write_text(dump(pick))
    code, out = state(vote)
    assert out["pending"] and out["round"]["winner"] is None and out["round"]["winner_topic"] is None


# ---------- vote_update.py ----------

def test_record_post_changes_only_post_url_and_appends_the_post(vote):
    before_pick = json.loads(vote["pick"].read_text())
    code, out = update(vote, "--record-post", "--round", "2026-10-05", "--post-url",
                       "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000202/", "--date", "2026-10-14",
                       "--lang", "EN", "--title", "Durability is a budget", "--image", "assets/posts/2026-10-14-durability.png")
    assert code == 0, out
    assert {c["path"] for c in out["changed"]} == {"data/pick.json", "data/posts.json"}
    new_pick = (vote["out"] / "data/pick.json").read_text(encoding="utf-8")
    before_pick["history"][0]["post_url"] = "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000202/"
    assert new_pick == dump(before_pick)
    posts = json.loads((vote["out"] / "data/posts.json").read_text())
    assert posts[-1] == {"date": "2026-10-14", "lang": "EN", "title": "Durability is a budget",
                         "url": "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000202/",
                         "image": "assets/posts/2026-10-14-durability.png"}
    for c in out["changed"]:
        assert c["sha256"] == hashlib.sha256(Path(c["file"]).read_bytes()).hexdigest()
    assert json.loads(vote["pick"].read_text()) != before_pick  # the input was not touched


def test_record_post_is_idempotent(vote):
    code, out = update(vote, "--record-post", "--round", "2026-09-28", "--post-url", URL, "--date", "2026-09-30",
                       "--lang", "EN", "--title", "Zero dependencies, one year later")
    assert code == 0 and out["changed"] == []


def test_record_post_without_an_image_writes_null(vote):
    url = "https://www.linkedin.com/feed/update/urn:li:activity:7000000000000000303/"
    code, out = update(vote, "--record-post", "--round", "2026-10-05", "--post-url", url, "--date", "2026-10-14",
                       "--lang", "EN/PT", "--title", "Durability is a budget")
    assert code == 0
    assert json.loads((vote["out"] / "data/posts.json").read_text())[-1]["image"] is None


@pytest.mark.parametrize("url", ["https://example.com/post/1", "http://www.linkedin.com/feed/update/urn:li:share:1/",
                                 "https://www.linkedin.com.evil.test/feed/update/urn:li:share:1/",
                                 "https://www.linkedin.com/in/dana-example/", "https://www.linkedin.com/feed/update/urn:li:share:1/?x=1"])
def test_record_post_refuses_a_url_that_is_not_a_linkedin_post(vote, url):
    code, err = update(vote, "--record-post", "--round", "2026-10-05", "--post-url", url, "--date", "2026-10-14",
                       "--lang", "EN", "--title", "t")
    assert code == 1 and "not a LinkedIn post URL" in err
    assert not (vote["out"] / "data").exists()


def test_record_post_refuses_an_unknown_round_and_a_second_url(vote):
    base = ["--record-post", "--date", "2026-10-14", "--lang", "EN", "--title", "t"]
    code, err = update(vote, *base, "--round", "2026-10-12", "--post-url", URL)
    assert code == 1 and "not in pick.json's history" in err
    code, err = update(vote, *base, "--round", "2026-09-28", "--post-url",
                       "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000999/")
    assert code == 1 and "already has the post" in err


def test_queue_round_appends_a_round_in_the_repository_format(vote):
    code, out = update(vote, "--queue-round", "--pillar", "Database performance", "--calendar", vote["calendar"],
                       "--pillars", PILLARS, "--option", "A=A smaller connection pool made my queries faster",
                       "--option", "B=Dead tuples: the autovacuum setting I changed",
                       "--option", "C=900 or 26,000 writes a second: group commit in tinykv")
    assert code == 0, out
    assert [c["path"] for c in out["changed"]] == ["data/pick-queue.json"]
    text = (vote["out"] / "data/pick-queue.json").read_text(encoding="utf-8")
    queue = json.loads(text)
    assert text == dump(queue) and len(queue) == 2
    assert queue[-1] == {"pillar": "Database performance", "options": opts(
        "A smaller connection pool made my queries faster", "Dead tuples: the autovacuum setting I changed",
        "900 or 26,000 writes a second: group commit in tinykv")}


@pytest.mark.parametrize("option,message", [
    ("tinykv 0.5 - TTL without a dependency", "calendar row 4"),
    ("Durability is a budget: what an fsync demo taught me", "history round 2026-10-05"),
    ("Why the README is 60 lines!", "pick-queue.json[0]"),
    ("No AI demo yet", "open round"),
])
def test_queue_round_refuses_a_used_topic(vote, option, message):
    code, err = update(vote, "--queue-round", "--pillar", "Database performance", "--calendar", vote["calendar"],
                       "--option", f"A={option}", "--option", "B=Dead tuples: the autovacuum setting I changed",
                       "--option", "C=A smaller connection pool made my queries faster")
    assert code == 1 and "already used" in err and message in err


@pytest.mark.parametrize("options,message", [
    (["A=one topic here", "B=another topic"], "missing or empty option(s): C"),
    (["A=one topic here", "B=another topic", "C="], "missing or empty option(s): C"),
    (["A=Autovacuum dead tuples settings", "B=autovacuum dead tuples settings!", "C=third"], "the same topic"),
    (["A=" + "x" * 81, "B=b topic", "C=c topic"], "at most 80"),
    (["D=d topic", "B=b topic", "C=c topic"], "A=<topic>"),
])
def test_queue_round_refuses_missing_duplicate_or_long_options(vote, options, message):
    args = [x for o in options for x in ("--option", o)]
    code, err = update(vote, "--queue-round", "--pillar", "Database performance", "--calendar", vote["calendar"], *args)
    assert code == 1 and message in err


def test_queue_round_refuses_a_pillar_out_of_turn_and_needs_the_calendar(vote):
    args = ["--option", "A=a topic one", "--option", "B=b topic two", "--option", "C=c topic three"]
    code, err = update(vote, "--queue-round", "--pillar", "Small tools", "--calendar", vote["calendar"], "--pillars", PILLARS, *args)
    assert code == 1 and "next pillar in the rotation is 'Database performance'" in err
    code, err = update(vote, "--queue-round", "--pillar", "Small tools", *args)
    assert code == 2 and "--calendar" in err


def test_out_may_not_overwrite_the_inputs(vote):
    vote["out"] = vote["pick"].parent.parent
    code, err = update(vote, "--queue-round", "--pillar", "x", "--calendar", vote["calendar"],
                       "--option", "A=a topic one", "--option", "B=b topic two", "--option", "C=c topic three")
    assert code == 2 and "overwrite the input" in err
