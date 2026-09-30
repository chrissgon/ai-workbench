"""Offline tests of skills/mkt-publish/scripts/payload.py: build, verify, and the optional post image."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
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


def build(proj, *content):
    return run(proj, "build", *[x for c in content for x in ("--content", c)], "--out", proj / "out", "--workbench", REPO)


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
    code, v, _ = run(proj, "verify", "--manifest", out["manifest"], "--hash", out["plan_hash"])
    assert code == 0 and v["ok"]
    Path(out["posts"][0]["image_file"]).write_bytes(PNG + b"x")
    code, v, _ = run(proj, "verify", "--manifest", out["manifest"], "--hash", out["plan_hash"])
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
