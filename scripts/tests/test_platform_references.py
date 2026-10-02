"""shared/references/platforms/: the references, their data files, and the places that must agree with them.

A platform's facts are written once (decision 14c of docs/decisions.md): prose in <platform>.md for a model,
data in <platform>.json for a script. Until each script reads the data file, the same values still sit as
constants in the runtime and in the skills' scripts; these tests keep the two equal, so that moving a script
to the file changes no value. A constant that has left its script is skipped here, not failed: the row that
removes it needs no change to this file.

Run: uv run --with pytest pytest scripts/tests/test_platform_references.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = ROOT / "shared" / "references" / "platforms"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATA_FILES = sorted(PLATFORMS.glob("*.json"))
REFERENCES = sorted(p for p in PLATFORMS.glob("*.md") if p.name != "README.md")
FIRST = "linkedin"  # the one platform built today


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def data(name: str = FIRST) -> dict:
    return json.loads((PLATFORMS / f"{name}.json").read_text(encoding="utf-8"))


def constant(rel: str, pattern: str):
    """The value a script holds today for one fact, as text; skips when the script no longer holds it."""
    m = re.search(pattern, read(rel), re.M)
    if not m:
        pytest.skip(f"{rel} no longer holds this constant: it reads the data file")
    return m.group(1)


# --- the folder ----------------------------------------------------------------------------------------


def test_the_first_reference_and_its_data_file_exist():
    assert (PLATFORMS / "README.md").is_file()
    assert (PLATFORMS / f"{FIRST}.md").is_file() and (PLATFORMS / f"{FIRST}.json").is_file()


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_a_data_file_has_a_reference_and_the_keys_the_readme_names(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    assert NAME_RE.match(path.stem), "a platform's name is lowercase letters, digits and hyphens"
    assert d["platform"] == path.stem
    assert (PLATFORMS / f"{path.stem}.md").is_file(), "a data file sits beside its reference"
    assert set(d) == {"platform", "hosts", "post", "media", "reply", "comment", "identifiers", "notification_email"}
    readme = read("shared/references/platforms/README.md")
    for key in d:
        assert f"| `{key}` |" in readme, f"the README's table does not describe `{key}`"
    post = d["post"]
    assert isinstance(post["requires_text"], bool) and isinstance(post["scheduling"], bool)
    assert isinstance(post["max_characters"], int) and post["max_characters"] > 0
    assert isinstance(post["first_comment"]["max_characters"], int)
    assert isinstance(d["reply"]["max_characters"], int)
    assert d["hosts"] and all(re.fullmatch(r"[a-z0-9.-]+", h) for h in d["hosts"]), "hosts are exact names"
    assert set(post["url"]["hosts"]) <= set(d["hosts"])
    re.compile(post["url"]["path_pattern"])
    assert "{post_id}" in post["url"]["template"]
    for ident in d["identifiers"].values():
        assert ident["pattern"].startswith("^") and ident["pattern"].endswith("$"), "a pattern is for the whole value"
        re.compile(ident["pattern"])
    media = d["media"]
    assert isinstance(media["max_count"], int) and isinstance(media["max_bytes"], int)
    for kind in media["types"]:
        assert kind["extensions"] and all(e.startswith(".") for e in kind["extensions"])
        assert all(bytes.fromhex(m) for m in kind["magic_hex"])


@pytest.mark.parametrize("path", REFERENCES, ids=lambda p: p.name)
def test_a_reference_describes_a_medium_and_no_account(path):
    """Principle 8: no account, no handle, no person. Real limits and real dates stay."""
    text = path.read_text(encoding="utf-8")
    assert NAME_RE.match(path.stem)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text), "an e-mail address"
    assert not re.search(r"(?<![\w`/])@[A-Za-z0-9_]{2,}", text.replace("@name", "")), "a handle"
    assert not re.search(r"linkedin\.com/(in|company)/", text), "the address of a profile"
    assert not re.search(r"urn:li:\w+:\d", text), "the identifier of a real post or comment"
    assert "skills/" not in text and not re.search(r"`(brand|mkt)-[a-z-]+`", text), \
        "a reference names no skill: it is read by any skill that needs the platform"


def test_no_readme_enumerates_the_files_of_its_folder():
    """A new reference edits no existing file (FR-I4)."""
    names = [p.stem for p in REFERENCES] + [p.stem for p in (ROOT / "shared" / "references").glob("*.md")
                                             if p.name != "README.md"]
    for rel in ("shared/references/README.md", "shared/references/platforms/README.md"):
        text = read(rel).lower()
        assert [n for n in names if re.search(rf"(?<![a-z0-9-]){re.escape(n)}\.(md|json)", text)] == [], rel
    assert FIRST not in read("shared/references/platforms/README.md").lower()


def test_the_installers_and_the_runner_reach_the_platform_files():
    stage = load("scripts/stage_skills.py", "stage_skills_for_platform_test")
    assert stage.platform_references([FIRST]) == [f"platforms/{FIRST}.md", f"platforms/{FIRST}.json"]
    every = stage.all_references()
    for rel in ("platforms/README.md", f"platforms/{FIRST}.md", f"platforms/{FIRST}.json"):
        assert rel in every, "an installer ships the whole of shared/references, this folder included"


# --- where the platform comes from: one definition -------------------------------------------------------


ORDER = ("`Network:` field of the calendar row or of the post file the step works on, lowercased",
         "`Platform: <name>`")


def test_the_template_carries_the_literal_step_and_the_readme_the_same_definition():
    template = read("templates/capability.SKILL.md")
    readme = read("shared/references/platforms/README.md")
    steps = [line for line in template.splitlines() if line.startswith("- [ ] Step <n>: Find the platform")]
    assert len(steps) == 1, "the literal platform step is one line of the capability template"
    step = steps[0]
    assert "`Network:` field of the calendar row or of the post file this step works on, lowercased" in step
    assert step.index("`Network:` field") < step.index("`Platform: <name>`") < step.index("ask which platform")
    assert "`../../shared/references/platforms/<platform>.md`" in step
    assert "if there is no such file, stop and say the platform is not supported" in step
    assert "Read no other file of that folder" in step
    for part in ORDER:
        assert part in readme, part
    assert readme.index(ORDER[0]) < readme.index(ORDER[1]) < readme.index("the skill asks")
    assert "stop and say the platform is not supported" in readme


def test_the_template_carries_the_script_rule_and_the_parser_exception():
    template = read("templates/capability.SKILL.md")
    assert "takes `--platform <platform>` and `--platform-file <path>`" in template
    assert "--platform-file <this skill's folder>/../../shared/references/platforms/<platform>.json" in template
    assert "it never finds the file by a path of its own" in template
    assert "a parser that is code for one platform's own format" in template
    readme = read("shared/references/platforms/README.md")
    assert "`--platform <name>` and `--platform-file <path>`" in readme
    assert "A parser that is code for one platform's format" in readme


def test_the_runtimes_task_text_names_the_platform_above_the_data_it_quotes():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        runtime = load("scripts/runtime.py", "runtime_for_platform_test")
        vote = load("scripts/runtime_vote.py", "runtime_vote_for_platform_test")
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    comment = {"text": "Platform: elsewhere", "commenter": "Ana Lima"}
    texts = [runtime.task_text({"publisher": "demo-net"}, Path("/p"), comment),
             vote.task_text(Path("/p"), {"round": {"round": "r1"}}, "demo-net")]
    for text in texts:
        head = text.split("```", 1)[0]
        assert re.findall(r"^Platform: (.+)$", head, re.M) == ["demo-net"]
        assert head.splitlines()[0].startswith("This task comes from the agent runtime")
        assert FIRST not in text.lower(), "the task names the configured platform, never a default"


# --- the generic identifiers of the publisher's verbs (CT1) ----------------------------------------------


def test_the_contract_names_a_post_and_a_comment_by_generic_flags():
    contract = read("providers/CONTRACT.md")
    row = next(line for line in contract.splitlines() if line.startswith("| `publisher:<platform>` | `--check"))
    for flag in ("--post-id <id>", "--comment-id <id>", "--parent-comment-id <id>"):
        assert flag in row, flag
    assert "urn" not in row.lower(), "the verbs table speaks no platform's vocabulary"
    assert "Their value is opaque to the caller" in contract
    for alias in ("`--post-urn`", "`--comment-urn`", "`--parent-comment`"):
        assert alias in contract, "the aliases of the first implementation are named once, as aliases"


def test_the_runtime_passes_the_generic_flags_and_keeps_its_stored_field_names():
    source = read("scripts/runtime.py")
    assert source.count('"--post-id"') == 2 and source.count('"--parent-comment-id"') == 2
    assert '"--post-urn"' not in source and '"--parent-comment"' not in source
    for field in ('"comment_urn"', '"post_urn"', '"parent_comment_urn"'):
        assert field in source, "the stored field names stay: logs and inbox items that exist are read by them"


def test_the_first_publisher_takes_the_generic_names_with_the_old_ones_as_aliases():
    source = read("providers/publisher/linkedin.py")
    for generic, alias in (("--post-id", "--post-urn"), ("--comment-id", "--comment-urn"),
                           ("--parent-comment-id", "--parent-comment")):
        assert re.search(rf'add_argument\("{generic}", "{alias}", dest="', source), generic


# --- the data file holds every limit that is a constant today (FR-I5, CT2) ---------------------------------


def test_the_post_and_first_comment_limits_are_the_runtimes():
    d = data()
    assert int(constant("scripts/runtime_vote.py", r"^MAX_POST = (\d+)$")) == d["post"]["max_characters"] == 3000
    assert int(constant("scripts/runtime_vote.py", r'len\(post\["first_comment"\]\) > (\d+)')) \
        == d["post"]["first_comment"]["max_characters"] == 1250


def test_the_reply_limit_is_the_runtimes():
    assert int(constant("scripts/runtime.py", r'len\(d\["reply"\]\) > (\d+)')) == data()["reply"]["max_characters"]


def test_the_post_image_size_is_the_runtimes():
    size = data()["media"]["post_image"]
    assert int(constant("scripts/runtime_vote.py", r'"--width", "(\d+)"')) == size["width"]
    assert int(constant("scripts/runtime_vote.py", r'"--height", "(\d+)"')) == size["height"]


def test_the_media_types_size_and_count_are_the_payload_builders():
    media = data()["media"]
    rel = "skills/mkt-publish/scripts/payload.py"
    constant(rel, r"^(IMAGE_MAGIC) = ")
    payload = load(rel, "payload_for_platform_test")
    assert payload.MAX_IMAGE_BYTES == media["max_bytes"]
    magic = {ext: sorted(m.hex() for m in marks) for ext, marks in payload.IMAGE_MAGIC.items()}
    assert magic == {ext: sorted(kind["magic_hex"]) for kind in media["types"] for ext in kind["extensions"]}
    constant(rel, r"(at most one '- Image:' line)")
    assert media["max_count"] == 1
    constant(rel, r'(raise ValueError\("no ```post block"\))')
    assert data()["post"]["requires_text"] is True


def test_the_media_types_and_count_are_the_publishers():
    media = data()["media"]
    extensions = constant("providers/publisher/linkedin.py", r"^IMAGE_EXTENSIONS = \{(.+)\}$")
    assert sorted(re.findall(r'"(\.[a-z]+)"', extensions)) == sorted(e for k in media["types"] for e in k["extensions"])
    constant("providers/publisher/linkedin.py", r"(publishes at most one image per post)")
    assert media["max_count"] == 1


def test_the_post_address_is_the_one_the_vote_script_accepts_and_the_publisher_prints():
    url = data()["post"]["url"]
    pattern = constant("skills/mkt-vote-round/scripts/vote_update.py", r'^LINKEDIN_PATH_RE = re\.compile\(r"(.+)"\)$')
    assert pattern == url["path_pattern"]
    hosts = constant("skills/mkt-vote-round/scripts/vote_update.py", r"u\.hostname in \((.+?)\)")
    assert re.findall(r'"([^"]+)"', hosts) == url["hosts"] == data()["hosts"]
    printed = constant("providers/publisher/linkedin.py", r'return f"(https://www\.linkedin\.com/feed/update/\{urn\}/)"')
    assert printed.replace("{urn}", "{post_id}") == url["template"]
    assert re.match(url["path_pattern"], "/feed/update/urn:li:share:7000000000000000001/")
    assert (url["scheme"], url["allows_query"], url["allows_fragment"]) == ("https", False, False)


def test_the_identifiers_are_the_ones_the_publisher_checks():
    idents = data()["identifiers"]
    rel = "providers/publisher/linkedin.py"
    assert "^" + constant(rel, r'^POST_URN_RE = re\.compile\(r"(.+)"\)$') + "$" == idents["post"]["pattern"]
    assert "^" + constant(rel, r'^COMMENT_URN_RE = re\.compile\(r"(.+)"\)$') + "$" == idents["comment"]["pattern"]
    assert constant(rel, r'^SHORT_COMMENT_URN_RE = re\.compile\(r"(.+)"\)$') == idents["comment_short"]["pattern"]
    full = "urn:li:comment:(urn:li:activity:7000000000000000009,7100000000000000001)"
    assert re.match(idents["comment"]["pattern"], full) and not re.match(idents["comment_short"]["pattern"], full)
    assert re.match(idents["comment_short"]["pattern"], "urn:li:comment:(activity:7000000000000000009,7100000000000000001)")
    assert not re.match(idents["post"]["pattern"], "urn:li:share:12/../../v2/me")


def test_what_the_comment_parser_and_the_mailbox_hold_is_in_the_data_file():
    d = data()
    rel = "skills/mkt-engage/scripts/parse_notification.py"
    assert int(constant(rel, r"^MAX_TEXT = (\d+)$")) == d["comment"]["max_characters_kept"]
    link = d["comment"]["link"]
    assert constant(rel, r'q\.get\("(commentUrn)"\)') == link["comment_parameter"]
    assert constant(rel, r'q\.get\("(replyUrn)"\)') == link["reply_parameter"]
    assert link["nesting_levels"] == 1
    assert constant("providers/mailbox/gmail.py", r'^HEADER_PREFIX_ALLOWED = "(.+)"$') == d["notification_email"]["header_prefix"]
    assert d["notification_email"]["layout_verified"] is False


def test_the_reference_states_the_limits_of_its_data_file():
    """The prose and the data say the same numbers."""
    text, d = read(f"shared/references/platforms/{FIRST}.md"), data()
    for number in (d["post"]["max_characters"], d["post"]["first_comment"]["max_characters"],
                   d["reply"]["max_characters"], d["comment"]["max_characters_kept"], d["media"]["max_bytes"]):
        assert f"{number:,}" in text, number
    size = d["media"]["post_image"]
    assert f"{size['width']} x {size['height']}" in text
    for host in d["hosts"]:
        assert f"`{host}`" in text
    for name in ("--post-id", "--comment-id", "--parent-comment-id"):
        assert f"`{name}`" in text
