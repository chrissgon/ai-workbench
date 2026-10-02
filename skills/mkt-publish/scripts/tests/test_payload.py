"""Offline tests of skills/mkt-publish/scripts/payload.py: build, verify, the optional post image, the durable
payload folder and a plan hash that does not depend on where the folder lives."""
import hashlib
import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
PAYLOAD = REPO / "skills/mkt-publish/scripts/payload.py"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

CONTENT = """# Post: launch

- Slot: 2026-10-12T09:00:00-03:00 · Small tools · EN
- Approval: {scope}
{image}
```post
tinykv 0.5 ships TTL with zero dependencies. What would you cut next?
```

```first-comment
https://example.com/tinykv
```
"""


@pytest.fixture
def proj(tmp_path):
    (tmp_path / "content").mkdir()
    (tmp_path / "out").mkdir()
    return tmp_path


def write(proj, name="2026-10-12-tinykv", scope="action", image=""):
    f = proj / "content" / f"{name}.md"
    f.write_text(CONTENT.format(scope=scope, image=image), encoding="utf-8")
    return f


def run(proj, *args):
    r = subprocess.run([sys.executable, str(PAYLOAD), *map(str, args)], capture_output=True, text=True, cwd=proj, timeout=60)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip() else None), r.stderr


def build(proj, *content, out="out"):
    where = ["--out", proj / out] if out else []
    return run(proj, "build", *[x for c in content for x in ("--content", c)], *where, "--workbench", REPO)


def verify(proj, out, *extra):
    return run(proj, "verify", "--manifest", out["manifest"], "--hash", out["plan_hash"], "--workbench", REPO, *extra)


def git_init(proj):
    subprocess.run(["git", "init", "-q", str(proj)], check=True, timeout=60)


def test_a_post_without_an_image_has_no_media(proj):
    code, out, err = build(proj, write(proj))
    assert code == 0, err
    job = json.loads(Path(out["posts"][0]["job_file"]).read_text())
    assert "--media" not in job["argv"] and "image_file" not in out["posts"][0]


def test_the_image_is_copied_hashed_attached_and_snapshotted(proj):
    (proj / "card.png").write_bytes(PNG)
    code, out, err = build(proj, write(proj, image="- Image: card.png"))
    assert code == 0, err
    e = out["posts"][0]
    job = json.loads(Path(e["job_file"]).read_text())
    copy = job["argv"][job["argv"].index("--media") + 1]
    assert copy == e["image_file"] and Path(copy).parent == proj / "out" / "2026-10-12-tinykv"
    assert copy in job["snapshot"] and Path(copy).read_bytes() == PNG
    assert e["image_source"] == "card.png"


def test_a_changed_image_fails_verification(proj):
    (proj / "card.png").write_bytes(PNG)
    code, out, err = build(proj, write(proj, image="- Image: card.png"))
    code, v, _ = verify(proj, out)
    assert code == 0 and v["ok"]
    Path(out["posts"][0]["image_file"]).write_bytes(PNG + b"x")
    code, v, _ = verify(proj, out)
    assert code == 1 and any("image.png changed" in p for p in v["problems"])


@pytest.mark.parametrize("name,data,message", [
    ("card.webp", PNG, "only .png"),
    ("card.png", b"<svg/>", "not a PNG"),
    ("missing.png", None, "not found"),
])
def test_a_bad_image_is_refused(proj, name, data, message):
    if data is not None:
        (proj / name).write_bytes(data)
    code, out, err = build(proj, write(proj, image=f"- Image: {name}"))
    assert code == 2 and message in err


def test_two_image_lines_are_refused(proj):
    (proj / "card.png").write_bytes(PNG)
    code, out, err = build(proj, write(proj, image="- Image: card.png\n- Image: card.png"))
    assert code == 2 and "at most one" in err


def test_without_out_the_payload_goes_to_a_private_durable_folder_named_by_the_first_slot(proj):
    code, out, err = build(proj, write(proj), out=None)
    assert code == 0, err
    folder = proj.resolve() / ".workbench-local" / "payloads" / "2026-10-12"
    assert Path(out["out"]) == folder and Path(out["manifest"]) == folder / "manifest.json"
    for d in (folder, folder.parent, folder.parent.parent):
        assert stat.S_IMODE(d.stat().st_mode) == 0o700
    assert out["git_ignored"] is None  # not a git repository: nothing can commit it
    code, second, err = build(proj, write(proj), out=None)
    assert code == 0 and Path(second["out"]) == folder.with_name("2026-10-12-2")
    assert second["plan_hash"] == out["plan_hash"]


def test_in_a_git_repository_the_payload_folder_must_be_ignored(proj):
    git_init(proj)
    code, out, err = build(proj, write(proj), out=None)
    assert code == 2 and "not git-ignored" in err and ".gitignore" in err
    assert not (proj / ".workbench-local").exists()
    (proj / ".gitignore").write_text(".workbench-local/\n")
    code, out, err = build(proj, write(proj), out=None)
    assert code == 0 and out["git_ignored"] is True, err


def test_the_manifest_holds_no_absolute_path_and_the_hash_survives_a_move(proj):
    (proj / "card.png").write_bytes(PNG)
    code, out, err = build(proj, write(proj, image="- Image: card.png"))
    assert code == 0, err
    text = Path(out["manifest"]).read_text()
    assert str(proj.resolve()) not in text and str(REPO) not in text
    assert out["plan_hash"] == hashlib.sha256(text.encode()).hexdigest()
    code, other, err = build(proj, write(proj, image="- Image: card.png"), out="elsewhere")
    assert code == 0 and other["plan_hash"] == out["plan_hash"], err

    shutil.move(str(proj / "out"), str(proj / "moved"))
    moved = dict(out, manifest=str(proj / "moved" / "manifest.json"))
    code, v, _ = verify(proj, moved)
    assert code == 1 and all("job.json" in p for p in v["problems"])  # the jobs still name the old place
    code, j, err = run(proj, "jobs", "--manifest", moved["manifest"], "--workbench", REPO)
    assert code == 0 and j["plan_hash"] == out["plan_hash"], err
    job = json.loads(Path(j["posts"][0]["job_file"]).read_text())
    assert str((proj / "moved").resolve()) in job["argv"][job["argv"].index("--text-file") + 1]
    code, v, _ = verify(proj, moved)
    assert code == 0 and v["ok"] and v["manifest_version"] == 2


def test_a_changed_job_or_another_workbench_fails_verification(proj):
    code, out, err = build(proj, write(proj))
    job_file = Path(out["posts"][0]["job_file"])
    job = json.loads(job_file.read_text())
    job["argv"][2] = str(proj / "other.py")
    job_file.write_text(json.dumps(job))
    code, v, _ = verify(proj, out)
    assert code == 1 and any("job.json" in p for p in v["problems"])
    code, out, err = build(proj, write(proj), out="second")
    code, v, _ = run(proj, "verify", "--manifest", out["manifest"], "--hash", out["plan_hash"], "--workbench", proj)
    assert code == 1 and any("job.json" in p for p in v["problems"])
    code, v, err = run(proj, "verify", "--manifest", out["manifest"], "--hash", out["plan_hash"])
    assert code == 2 and "--workbench" in err


def test_a_manifest_from_before_the_version_keeps_its_hash_and_is_checked_the_old_way(proj):
    d = proj / "out" / "2026-10-12-tinykv"
    d.mkdir()
    (d / "post.txt").write_text("old post\n")
    (d / "job.json").write_text('{"argv": ["uv"]}\n')
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    manifest = proj / "out" / "manifest.json"
    manifest.write_text(json.dumps({"platform": "linkedin", "posts": [{
        "key": d.name, "post_file": str(d / "post.txt"), "post_sha256": sha(d / "post.txt"),
        "job_file": str(d / "job.json"), "job_sha256": sha(d / "job.json")}]}))
    code, v, err = run(proj, "verify", "--manifest", manifest, "--hash", sha(manifest))
    assert code == 0 and v["ok"] and v["manifest_version"] == 1, err
    (d / "job.json").write_text('{"argv": ["sh"]}\n')
    code, v, _ = run(proj, "verify", "--manifest", manifest, "--hash", sha(manifest))
    assert code == 1 and any("job.json changed" in p for p in v["problems"])
    code, _, err = run(proj, "jobs", "--manifest", manifest, "--workbench", REPO)
    assert code == 2 and "build a new payload" in err
