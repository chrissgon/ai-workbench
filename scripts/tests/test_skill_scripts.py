"""Tests for the refusals and redactions of skill scripts that take names, paths or text from input.

Run: uv run --with pytest pytest scripts/tests

Skill scripts ship inside their skill folder and have no test folder of their own, so their
security tests live here, where CI and the pre-commit hook run them. Secret-like strings are
assembled from pieces so that this file does not trip the scanner.
"""
from __future__ import annotations

import base64
import gzip
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


# ---------- design-handoff/unpack_export.py (H05) ----------

UNPACK = "skills/design-handoff/scripts/unpack_export.py"


def export_html(manifest: dict) -> str:
    return ('<script type="__bundler/template">' + json.dumps("<html><style>a{}</style></html>") + "</script>"
            '<script type="__bundler/manifest">' + json.dumps(manifest) + "</script>")


def res(data: bytes, compressed: bool = False) -> dict:
    payload = gzip.compress(data) if compressed else data
    return {"mime": "image/svg+xml", "data": base64.b64encode(payload).decode(), "compressed": compressed}


def test_unpack_writes_valid_resources(tmp_path):
    src = tmp_path / "export.html"
    src.write_text(export_html({"logo-1": res(b"<svg/>", compressed=True)}), encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out" / "resources" / "logo-1.svg").read_bytes() == b"<svg/>"


def test_unpack_refuses_traversal_and_absolute_ids(tmp_path):
    for rid in ("../../src/index", "/tmp/x", "Logo", "a/b", ".."):
        src = tmp_path / "export.html"
        src.write_text(export_html({"ok-1": res(b"x"), rid: res(b"pwned")}), encoding="utf-8")
        out = tmp_path / "out"
        r = run(UNPACK, "--file", str(src), "--out", str(out))
        assert r.returncode == 1, rid
        assert "refused export" in r.stderr
        assert list((out / "resources").iterdir()) == [], "nothing is written when one id is refused"
    assert not (tmp_path / "src").exists()


def test_unpack_refuses_symlinked_resources_dir(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "resources").symlink_to(outside)
    src = tmp_path / "export.html"
    src.write_text(export_html({"a": res(b"x")}), encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(out))
    assert r.returncode == 1
    assert list(outside.iterdir()) == []


def test_unpack_caps_decompression(tmp_path):
    src = tmp_path / "export.html"
    src.write_text(export_html({"bomb": res(b"\0" * 200_000, compressed=True)}), encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "out"), "--max-bytes", "100000")
    assert r.returncode == 1
    assert "more than 100000 bytes" in r.stderr
    assert not (tmp_path / "out" / "resources" / "bomb.svg").exists()


# ---------- eng-code-review/change_scope.py and the shared redaction (H06, L19, M22) ----------

SCOPE = "skills/eng-code-review/scripts/change_scope.py"
AWS = "AKIA" + "Q7ZT2MLP4RX9KW1V"
VALUE = "q8Zt2mLp" + "4Rx9Kw1v"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@localhost",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def repo_with_change(tmp_path: Path, text: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "app.py")
    git(repo, "commit", "-q", "-m", "base")
    (repo / "app.py").write_text("x = 1\n" + text, encoding="utf-8")
    return repo


def test_redact_copies_are_identical():
    shared = (ROOT / "scripts/redact.py").read_bytes()
    assert (ROOT / "skills/eng-code-review/scripts/redact.py").read_bytes() == shared, \
        "copy scripts/redact.py to skills/eng-code-review/scripts/redact.py"
    assert (ROOT / "skills/ops-repo-baseline/scripts/redact.py").read_bytes() == shared, \
        "copy scripts/redact.py to skills/ops-repo-baseline/scripts/redact.py"


def test_scan_uses_the_shared_redaction():
    scan = load("scripts/security_scan.py", "security_scan_shared")
    shared = load("scripts/redact.py", "redact_shared")
    assert scan.redact("k " + AWS) == shared.redact("k " + AWS) == "k <redacted AWS access key>"


def test_mask_secret_line_keeps_no_part_of_the_value():
    shared = load("scripts/redact.py", "redact_mask")
    for line in (f'password = "{VALUE}"', f"auth: '{VALUE}'", f"token={VALUE}{VALUE}", f"key {AWS} end",
                 f'url = "https://bot:{VALUE}@example.org/x"'):
        out = shared.mask_secret_line(line)
        assert VALUE[:6] not in out and AWS[4:] not in out, out
        assert "<redacted" in out


def test_secret_suspect_markers_are_masked(tmp_path):
    repo = repo_with_change(tmp_path, f'API_TOKEN = "{VALUE}"\nAWS = "{AWS}"\nprint(API_TOKEN, "{AWS}")  # TODO\n')
    r = run(SCOPE, "--repo", str(repo), "--worktree")
    assert r.returncode == 0, r.stderr
    assert VALUE not in r.stdout and AWS not in r.stdout
    markers = json.loads(r.stdout)["markers"]
    secrets = [m for m in markers if m["kind"] == "secret-suspect"]
    assert {m["line"] for m in secrets} == {2, 3, 4}
    assert {m["rule"] for m in secrets} == {"credential assignment", "AWS access key"}
    assert any(m["kind"] == "todo" and "<redacted AWS access key>" in m["text"] for m in markers)
    assert all("<redacted" in m["text"] for m in secrets)


def test_range_that_looks_like_an_option_is_refused(tmp_path):
    repo = repo_with_change(tmp_path, "y = 2\n")
    git(repo, "commit", "-q", "-am", "change")
    target = tmp_path / "written"
    for rng in (f"--output={target}", "-x..HEAD", f"HEAD..--output={target}", "no-such-ref..HEAD"):
        r = run(SCOPE, "--repo", str(repo), "--range", rng)
        assert r.returncode == 2, (rng, r.stderr)
        assert "refused" in r.stderr
    assert not target.exists()
    for rng in ("HEAD~1..HEAD", "HEAD~1...HEAD"):
        ok = run(SCOPE, "--repo", str(repo), "--range", rng)
        assert ok.returncode == 0, ok.stderr
        assert json.loads(ok.stdout)["totals"]["files"] == 1


# ---------- core-project-init/init_project.py (M21) ----------

INIT = "skills/core-project-init/scripts/init_project.py"


def test_init_takes_free_text_from_a_file_not_the_command_line(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "ARCH.md").write_text("# a\n", encoding="utf-8")
    words = {"name": "Bob's $(touch pwned) app", "decisions": ["Ship to \"EU\" only;\n## Approvals\n- all"],
             "open_questions": ["Who owns `billing`?"]}
    src = tmp_path / "in.json"
    src.write_text(json.dumps(words), encoding="utf-8")
    r = run(INIT, "--root", str(proj), "--apply", "--autonomy", "every-phase", "--input", str(src),
            "--register", "ARCH.md=docs/engineering/architecture.md")
    assert r.returncode == 0, r.stderr
    state = (proj / "docs/workbench/state.md").read_text(encoding="utf-8")
    assert "Bob's $(touch pwned) app" in state
    assert 'Ship to "EU" only; ## Approvals - all (user)' in state, "a line break cannot start a new section"
    assert "Who owns `billing`?" in state
    assert not (proj / "pwned").exists()
    r = run(INIT, "--root", str(proj), "--input", "-", stdin=json.dumps({"decisions": ["Later one"]}))
    assert r.returncode == 0, r.stderr
    assert "Later one (user)" in (proj / "docs/workbench/state.md").read_text(encoding="utf-8")


def test_init_refuses_free_text_flags_and_escaping_paths(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (tmp_path / "outside.md").write_text("x\n", encoding="utf-8")
    base = ["--root", str(proj), "--apply", "--autonomy", "every-phase"]
    assert run(INIT, "--root", str(proj), "--decision", "x").returncode == 2
    assert run(INIT, "--root", str(proj), "--open-question", "x").returncode == 2
    assert run(INIT, *base, "--name", "a$(b)").returncode == 2
    assert run(INIT, *base, "--name", "ok", "--register", "../outside.md=docs/x.md").returncode == 1
    assert run(INIT, *base, "--name", "ok", "--register", f"{tmp_path}/outside.md=docs/x.md").returncode == 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"decisions": "not a list"}), encoding="utf-8")
    assert run(INIT, *base, "--input", str(bad)).returncode == 2
    assert not (proj / "docs").exists()


# ---------- design-execute/screenshot.mjs (L13) ----------

SHOT = ROOT / "skills/design-execute/scripts/screenshot.mjs"


def test_screenshot_checks_out_and_never_installs(tmp_path):
    import shutil
    import pytest
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    work = tmp_path / "work"
    work.mkdir()
    (work / "a.html").write_text("<p>x</p>\n", encoding="utf-8")
    (work / "link.png").symlink_to(tmp_path / "elsewhere.png")
    shot = lambda out: subprocess.run([node, str(SHOT), "--html", "a.html", "--out", out, "--width", "10",
                                       "--height", "10"], cwd=work, capture_output=True, text=True, timeout=60,
                                      env={"PATH": str(Path(node).parent), "HOME": str(tmp_path)})
    for out in ("../x.png", str(tmp_path / "x.png"), "a.jpg", "missing/a.png", "link.png"):
        r = shot(out)
        assert r.returncode == 2 and "--out" in r.stderr, (out, r.stderr)
    r = shot("ok.png")
    assert r.returncode in (0, 2)
    if r.returncode == 2:
        assert "npm install --no-save playwright@1.63.0" in r.stderr
    assert not (work / "node_modules").exists()


# ---------- ops-pull-request/pr-context.sh (M22) ----------

PR_CONTEXT = ROOT / "skills/ops-pull-request/scripts/pr-context.sh"
BASH = __import__("shutil").which("bash")


def only_tools(tmp_path: Path, *names: str) -> dict:
    """An environment whose PATH holds only the named tools, so no host CLI or network tool is reachable."""
    import os
    import shutil
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for n in names:
        (bin_dir / n).symlink_to(shutil.which(n))
    return {**os.environ, "PATH": str(bin_dir)}


def test_pr_context_refuses_option_like_base(tmp_path):
    repo = repo_with_change(tmp_path, "y = 2\n")
    env = only_tools(tmp_path, "git", "python3", "sed", "dirname")
    for base in ("--upload-pack=touch pwned", "-x", "main..evil", "a b"):
        r = subprocess.run([BASH, str(PR_CONTEXT), "--base", base], cwd=repo, env=env,
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 2, (base, r.stderr)
        assert "is not a branch name" in r.stderr
    assert not (repo / "pwned").exists()
    git(repo, "branch", "-q", "-M", "main")
    git(repo, "switch", "-q", "-c", "feature")
    git(repo, "commit", "-q", "-am", "feature work")
    r = subprocess.run([BASH, str(PR_CONTEXT), "--base", "main"], cwd=repo, env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["compared_with"] == "main" and len(out["commits"]) == 1


# ---------- eng-security-review/triage_alerts.py ----------

TRIAGE = "skills/eng-security-review/scripts/triage_alerts.py"


def alert(number: int, package: str, manifest: str, fix: str | None, severity: str = "high") -> dict:
    return {"number": number, "state": "open", "severity": severity, "ecosystem": "npm",
            "package": package, "manifest_path": manifest, "first_patched_version": fix,
            "summary": "third-party text"}


def test_triage_groups_and_takes_the_highest_fix(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"kit": "2.3.0"}}))
    (tmp_path / "package-lock.json").write_text(json.dumps(
        {"packages": {"node_modules/kit": {"version": "2.3.0"}}}))
    demo = tmp_path / "examples" / "demo"
    demo.mkdir(parents=True)
    (demo / "package.json").write_text(json.dumps({"dependencies": {"tpl": "1.0.2"}}))
    alerts = [alert(1, "kit", "package.json", "2.3.4"), alert(2, "kit", "package.json", "2.10.1", "low"),
              alert(3, "tpl", "examples/demo/package.json", "2.0.0", "critical"),
              {**alert(4, "kit", "package.json", "9.0.0"), "state": "dismissed"}]
    out = run(TRIAGE, "--alerts", "-", "--repo", str(tmp_path), stdin=json.dumps({"alerts": alerts}))
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["open_count"] == 3
    kit, tpl = (next(g for g in data["groups"] if g["package"] == p) for p in ("kit", "tpl"))
    assert kit["clears_all_at"] == "2.10.1" and kit["major_bump"] is False
    assert kit["lockfiles"] == ["package-lock.json"] and kit["locked_versions"] == {"package-lock.json": "2.3.0"}
    assert tpl["major_bump"] is True and tpl["lockfiles"] == []
    assert tpl["parent_lockfiles"] == ["package-lock.json"] and tpl["locked_versions"] == {}
    assert tpl["path_hints"] == ["examples"] and data["groups"][0]["package"] == "tpl"


def test_triage_never_reads_a_manifest_outside_the_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"kit": "1.0.0"}}))
    alerts = [alert(1, "kit", "../package.json", "1.0.1"), alert(2, "kit", "/etc/package.json", "1.0.1")]
    out = run(TRIAGE, "--alerts", "-", "--repo", str(repo), stdin=json.dumps(alerts))
    assert out.returncode == 0, out.stderr
    for group in json.loads(out.stdout)["groups"]:
        assert group["manifest_found"] is False and group["declared"] is None


# ---------- ops-repo-baseline/secret_scan.py and baseline_status.py ----------

SECRET_SCAN = "skills/ops-repo-baseline/scripts/secret_scan.py"
BASELINE = "skills/ops-repo-baseline/scripts/baseline_status.py"
FAKE = "prod_" + "4f9a8b7c6d5e4f3a2b1c"


def test_secret_scan_finds_a_key_removed_from_the_tree_and_never_prints_it(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "pay.js").write_text(f'export const PAYMENTS_API_KEY = "{FAKE}";\n')
    (repo / "app.js").write_text("export const x = 1;\n")
    git(repo, "add", "pay.js", "app.js")
    git(repo, "commit", "-q", "-m", "add")
    git(repo, "rm", "-q", "pay.js")
    git(repo, "commit", "-q", "-m", "remove")
    tree = run(SECRET_SCAN, "--root", str(repo), "--json")
    assert tree.returncode == 0 and json.loads(tree.stdout)["findings"] == []
    hist = run(SECRET_SCAN, "--root", str(repo), "--history", "--json")
    assert hist.returncode == 1
    found = json.loads(hist.stdout)["findings"]
    assert [(f["path"].split("@")[0], f["rule"]) for f in found] == [("pay.js", "secret-assignment")]
    assert FAKE[5:] not in hist.stdout + hist.stderr
    (repo / ".secret-scan-allow").write_text("pay.js secret-assignment -- planted for a test\n")
    assert run(SECRET_SCAN, "--root", str(repo), "--history").returncode == 0
    (repo / ".secret-scan-allow").write_text("*.js secret-assignment -- too broad\n")
    assert run(SECRET_SCAN, "--root", str(repo), "--history").returncode == 1


def test_secret_scan_flags_credential_files_but_not_examples(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / ".env").write_text("DEBUG=1\n")
    (repo / ".env.example").write_text("API_KEY=\n")
    out = json.loads(run(SECRET_SCAN, "--root", str(repo), "--json").stdout)
    assert [(f["path"], f["rule"]) for f in out["findings"]] == [(".env", "secret-file")]
    assert run(SECRET_SCAN, "--root", str(tmp_path / "missing")).returncode == 2


def test_baseline_status_reports_ecosystems_pins_and_missing_files(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "fixtures" / "demo").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "package.json").write_text("{}\n")
    (repo / "fixtures" / "demo" / "package.json").write_text("{}\n")
    (repo / "ignored").mkdir()
    (repo / "ignored" / "package.json").write_text("{}\n")
    (repo / ".gitignore").write_text("ignored/\n.env\n")
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "on: push\njobs:\n  t:\n    steps:\n      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-node@" + "a" * 40 + " # v4\n      - uses: ./local-action\n")
    out = run(BASELINE, "--root", str(repo))
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert {e["name"]: e["folders"] for e in data["ecosystems"]} == {"github-actions": ["/"], "npm": ["/", "/fixtures/demo"]}
    wf = data["workflows"][0]
    assert wf["unpinned_actions"] == ["actions/checkout@v4"] and wf["declares_permissions"] is False
    assert data["files"]["env_ignored"] is True and data["files"]["codeowners"] is None
    assert data["git"]["is_repo"] is True and data["git"]["commits"] == 0
    assert run(BASELINE, "--root").returncode == 2
