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
import re
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


def test_unpack_lists_the_library_classes_of_the_given_prefix(tmp_path):
    src = tmp_path / "page.html"
    src.write_text('<a class="ui-btn ui-solid grid-2"></a><style>:root{--ui-ink:#111}</style>', encoding="utf-8")
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "a"), "--class-prefix", "ui")
    assert r.returncode == 0, r.stderr
    inv = json.loads((tmp_path / "a" / "inventory.json").read_text())
    assert inv["class_prefix"] == "ui" and inv["library_classes"] == ["ui-btn", "ui-solid"]
    r = run(UNPACK, "--file", str(src), "--out", str(tmp_path / "b"))
    inv = json.loads((tmp_path / "b" / "inventory.json").read_text())
    assert inv["class_prefixes"][0] == ["ui", 2] and "library_classes" not in inv
    assert run(UNPACK, "--file", str(src), "--out", str(tmp_path / "c"), "--class-prefix", "../x").returncode == 2


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


# ---------- biz-market-analysis/rank.py and capacity.py ----------

RANK = "skills/biz-market-analysis/scripts/rank.py"
CAPACITY = "skills/biz-market-analysis/scripts/capacity.py"


def options(a_demand: dict, b_demand: dict) -> str:
    return json.dumps({"criteria": [{"name": "demand"}, {"name": "fit", "weight": 2}],
                       "options": [{"name": "A", "scores": {"demand": a_demand, "fit": {"score": 1, "sources": []}}},
                                   {"name": "B", "scores": {"demand": b_demand, "fit": {"score": 3, "sources": ["2"]}}}]})


def test_rank_orders_by_weighted_total_and_marks_missing_evidence():
    r = run(RANK, stdin=options({"score": 5, "sources": ["1"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert [o["name"] for o in out["ranked"]] == ["B", "A"]
    assert out["ranked"][0]["total"] == 8 and out["ranked"][1]["total"] == 7
    assert out["close_call"] is True
    assert "1 (no evidence)" in out["table"]


def test_rank_refuses_a_score_without_a_source():
    r = run(RANK, stdin=options({"score": 4, "sources": []}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 1
    assert "has no source" in r.stderr
    assert r.stdout == ""


def test_rank_refuses_out_of_range_and_unscored_criteria():
    bad = json.loads(options({"score": 6, "sources": ["1"]}, {"score": 2, "sources": ["3"]}))
    del bad["options"][1]["scores"]["fit"]
    r = run(RANK, stdin=json.dumps(bad))
    assert r.returncode == 1
    assert "integer from 1 to 5" in r.stderr and "is not scored" in r.stderr


def test_capacity_computes_jobs_per_month_and_refuses_bad_values():
    r = run(CAPACITY, "--hours-per-week", "15", "--hours-per-job", "40", "--utilization", "0.7")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["jobs_per_month"] == 1.1
    assert run(CAPACITY, "--hours-per-week", "0", "--hours-per-job", "40").returncode == 2
    assert run(CAPACITY, "--hours-per-week", "15", "--hours-per-job", "40", "--utilization", "2").returncode == 2


def test_rank_translates_the_no_evidence_label():
    r = run(RANK, "--no-evidence-label", "sem evidência",
            stdin=options({"score": 5, "sources": ["1"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 0, r.stderr
    assert "1 (sem evidência)" in json.loads(r.stdout)["table"]


def test_rank_copies_are_identical():
    a = (ROOT / RANK).read_bytes()
    assert (ROOT / "skills/biz-icp-positioning/scripts/rank.py").read_bytes() == a, \
        "copy skills/biz-market-analysis/scripts/rank.py to skills/biz-icp-positioning/scripts/rank.py"


CHECK_REFS = "skills/biz-market-analysis/scripts/check_refs.py"


def test_check_refs_reports_undefined_unused_and_incomplete(tmp_path):
    doc = tmp_path / "market.md"
    doc.write_text("# M\n\n## Buyers\n- 10 firms [1][3]; capacity M1 and M2\n\n## Sources\n"
                   '[1] T, P. https://example.org. Quote: "10 firms"\n[2] T2, P. https://example.org/2. Quote: "x"\n'
                   "[3] T3, P. no link and no quote\n\n## Method\n- M1: `python3 capacity.py`\n", encoding="utf-8")
    r = run(CHECK_REFS, "--file", str(doc))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["undefined"] == ["M2"]
    assert out["unused"] == ["2"]
    assert out["incomplete"] == [{"ref": "3", "missing": ["url", "quote"]}]


def test_check_refs_passes_a_clean_translated_file(tmp_path):
    doc = tmp_path / "market.md"
    doc.write_text('## Resumen\n- dato [1] (M1)\n\n## Fuentes\n[1] T. https://x.org. Cita: "dato"\n\n## Método\n- M1\n',
                   encoding="utf-8")
    r = run(CHECK_REFS, "--file", str(doc), "--sources-heading", "Fuentes", "--method-heading", "Método")
    assert r.returncode == 0, r.stdout + r.stderr
    assert run(CHECK_REFS, "--file", str(doc)).returncode == 2


def test_check_refs_copies_are_identical():
    assert (ROOT / "skills/biz-icp-positioning/scripts/check_refs.py").read_bytes() == (ROOT / CHECK_REFS).read_bytes()


def test_rank_refuses_sources_that_are_not_references():
    r = run(RANK, stdin=options({"score": 4, "sources": ["recurring revenue model"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 1
    assert "are not references" in r.stderr
    ok = run(RANK, stdin=options({"score": 4, "sources": ["2b", "M1"]}, {"score": 2, "sources": [3]}))
    assert ok.returncode == 0, ok.stderr


LINT_MARKET = "skills/biz-market-analysis/scripts/lint_market.py"


def test_lint_market_reports_the_repeated_mistakes(tmp_path):
    doc = tmp_path / "market.md"
    doc.write_text(
        "## Alternatives and competitors per offer\n### Sites\n"
        "| Alternative | Kind | Advertised price (unit, date) | Source |\n|---|---|---|---|\n"
        "| DIY builder | DIY | EUR 10/month (2026) | [1] |\n| Do nothing | do nothing | 0 (staff time) | [2] |\n"
        "| Agency | agency | Custom pricing | [Acme] |\n| Freelancer | freelancer | price not found | [2,3] |\n\n"
        "## Implications for the next decisions\n- Pricing: charge €50 per month?\n- ICP: which segment? [1]\n\n"
        "## Sources\n[1] a [x]\n", encoding="utf-8")
    r = run(LINT_MARKET, "--file", str(doc))
    assert r.returncode == 1
    found = [(f["check"], f["text"]) for f in json.loads(r.stdout)["findings"]]
    assert ("price_cell", "Custom pricing") in found
    assert ("bad_citation", "[Acme]") in found
    assert any(c == "bad_citation" and t.startswith("[2,3]") for c, t in found)
    assert any(c == "implications_currency" for c, _ in found)
    assert ("implications_not_question", "- ICP: which segment? [1]") not in found
    assert len(found) == 5  # the priced Implications bullet is also not a question


def test_lint_market_passes_a_clean_translated_file(tmp_path):
    doc = tmp_path / "market.md"
    doc.write_text(
        "## Alternativas\n| Alternativa | Precio | Fuente |\n|---|---|---|\n| Nada | 0 | [1] |\n| Web | R$ 99/mes | [1] |\n"
        "| Agencia | precio no encontrado | [2] |\n\n## Implicaciones\n- Precio: cuanto cobrar? [2]\n\n## Fuentes\n[1] x\n",
        encoding="utf-8")
    r = run(LINT_MARKET, "--file", str(doc), "--alternatives-heading", "Alternativas", "--implications-heading",
            "Implicaciones", "--price-column", "precio", "--not-found-label", "precio no encontrado",
            "--sources-heading", "Fuentes")
    assert r.returncode == 0, r.stdout
    assert json.loads(run(LINT_MARKET, "--file", str(doc)).stdout)["missing_headings"]


def test_lint_market_flags_statements_and_uncited_figures(tmp_path):
    doc = tmp_path / "market.md"
    doc.write_text("## Summary\n- 62.9% have a website\n- 40% sell online [3]\n\n"
                   "## Implications for the next decisions\n- ICP: target micro firms\n- Channels: which first? [3]\n\n"
                   "## Assumptions\n- Assumption: 20% utilisation\n\n## Sources\n[3] x\n", encoding="utf-8")
    found = [(f["check"], f["text"]) for f in json.loads(run(LINT_MARKET, "--file", str(doc)).stdout)["findings"]]
    assert found == [("uncited_figure", "- 62.9% have a website"),
                     ("implications_not_question", "- ICP: target micro firms")]


LINT_ICP = "skills/biz-icp-positioning/scripts/lint_icp.py"


def test_lint_icp_reports_hypotheticals_criteria_and_status(tmp_path):
    doc = tmp_path / "icp.md"
    doc.write_text("# ICP\n\n- Status: draft\n\n## Primary profile\n- 40% no-show\n\n"
                   "## Validation plan\n- Would you pay for this?\n- Validated if: 3 of 5 name the same task\n\n"
                   "## Sources\n[1] x\n", encoding="utf-8")
    r = run(LINT_ICP, "--file", str(doc), "--kind", "icp")
    assert r.returncode == 1
    checks = sorted(f["check"] for f in json.loads(r.stdout)["findings"])
    assert checks == ["hypothetical_question", "missing_criteria", "status", "uncited_figure"]


def test_lint_icp_positioning_needs_confirmed_claims(tmp_path):
    doc = tmp_path / "positioning.md"
    doc.write_text("- Status: hypothesis\n\n## What we can truly claim\n| Attribute | Against | Why | Confirmed by |\n"
                   "|---|---|---|---|\n| Independent | vendors | trust | user, 2026-09-28 |\n| Best in class | all | - | |\n",
                   encoding="utf-8")
    found = json.loads(run(LINT_ICP, "--file", str(doc), "--kind", "positioning").stdout)["findings"]
    assert [f["check"] for f in found] == ["unconfirmed_claim"]
    assert "Best in class" in found[0]["text"]


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
    assert [(f["path"].split("@")[0], f["rule"], f["kind"]) for f in found] == [("pay.js", "secret-assignment", "real")]
    assert found[0]["action"].startswith("revoke")
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
    (repo / "tests").mkdir()
    (repo / "tests" / "fake.py").write_text(f"API_KEY = '{FAKE}'\n")
    kinds = {f["path"]: f["kind"] for f in json.loads(run(SECRET_SCAN, "--root", str(repo), "--json").stdout)["findings"]}
    assert kinds == {".env": "real", "tests/fake.py": "planted?"}
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


LINKEDIN_EXPORT = "skills/brand-profile/scripts/linkedin_export.py"
CHECK_PROFILE = "skills/brand-profile/scripts/check_profile.py"

# A fictitious export, laid out as LinkedIn's "Save to PDF" text comes out of a PDF reader.
EXPORT_TEXT = "\n".join([
    "Contact", "+44 20 7946 0000 (Mobile)", "dana.example@example.org", "www.linkedin.com/in/dana-example",
    "Top Skills", "Rust", "Languages", "English (Native or Bilingual)",
    "Dana Example", "Staff Engineer | Databases", "Leeds, England, United Kingdom",
    "Summary", "Engineer who likes small tools. Reach me at +44 20 7946 0001.",
    "Experience", "Acme Storage", "Staff Engineer", "March 2023\xa0-\xa0Present\xa0(3 years 7 months)", "Leeds",
    "Built the storage engine.", "\xa0 Page 1 of 2", "Beta Labs", "Engineer",
    "January 2019 - February 2023 (4 years 2 months)", "Remote", "Wrote the query planner.",
    "Education", "Some University", "BSc, Computer Science · (2015 - 2018)",
])


def test_linkedin_export_drops_contact_data_and_computes_durations(tmp_path):
    src = tmp_path / "profile.txt"
    src.write_text(EXPORT_TEXT, encoding="utf-8")
    r = run(LINKEDIN_EXPORT, "--text-file", str(src), "--today", "2026-09-29")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "7946" not in r.stdout and "@" not in r.stdout
    assert out["redacted"] == {"contact_section_dropped": True, "emails": 1, "phones": 2}
    assert out["header_lines"] == ["Dana Example", "Staff Engineer | Databases", "Leeds, England, United Kingdom"]
    assert out["languages"] == ["English (Native or Bilingual)"]
    first, second = out["experience"]
    assert (first["company"], first["title"], first["start"], first["end"], first["months"]) == \
        ("Acme Storage", "Staff Engineer", "2023-03", "present", 43)
    assert (second["company"], second["months"], second["location"]) == ("Beta Labs", 50, "Remote")
    assert out["totals"]["first_start"] == "2019-01" and out["totals"]["years_and_months"] == "7 years 8 months"
    assert "(2015 - 2018)" in out["education"][1]


def test_linkedin_export_refuses_text_without_roles(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("just some notes\nnothing dated", encoding="utf-8")
    assert run(LINKEDIN_EXPORT, "--text-file", str(src)).returncode == 1
    assert run(LINKEDIN_EXPORT, "--text-file", str(src), "--today", "29/09/2026").returncode == 2


PROFILE_OK = "\n".join([
    "# Brand profile: Dana", "", "## Who they are", "- Staff engineer since 2019 [1]", "",
    "## Never expose", "- Employer [2]", "", "## Voice", "- Samples written by them:", "  > hello network [3]", "",
    "## Sources", "[1] Export, provided 2026-09-29.", "[2] User in chat, 2026-09-29.",
    "[3] Post, 2022-11-04, https://www.linkedin.com/feed/update/urn:li:activity:6994304183386443776/",
])


def test_check_profile_passes_a_clean_profile_and_ignores_ids_in_links(tmp_path):
    doc = tmp_path / "profile.md"
    doc.write_text(PROFILE_OK, encoding="utf-8")
    r = run(CHECK_PROFILE, "--file", str(doc))
    assert r.returncode == 0, r.stdout + r.stderr


def test_check_profile_reports_contact_data_refs_and_unmarked_samples(tmp_path):
    doc = tmp_path / "profile.md"
    bad = PROFILE_OK.replace("- Employer [2]", "- nothing listed").replace("- Employer", "") \
        .replace("- Samples written by them:", "- Samples:").replace("since 2019 [1]", "since 2019 [1][4], call +44 20 7946 0000")
    bad = bad.replace("## Never expose\n- nothing listed", "## Never expose\n")
    bad = bad.replace("[3] Post, 2022-11-04,", "[3] Post, undated,")
    doc.write_text(bad, encoding="utf-8")
    r = run(CHECK_PROFILE, "--file", str(doc))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["contact_data"] == ["line 4"]
    assert out["undefined"] == ["4"] and out["unused"] == ["2"]
    assert out["never_empty"] is True and out["samples_unmarked"] is True
    assert out["no_date"] == ["3"]  # digits inside the URL's activity id are not a date


BASELINES = "skills/brand-strategy/scripts/baselines.py"


def test_baselines_refuses_names_that_are_not_package_or_repo_names():
    for args in (["--npm", "../../etc"], ["--github", "owner"], ["--github", "a/b?x=1"], ["--npm", "x", "--today", "yesterday"], []):
        r = run(BASELINES, *args)
        assert r.returncode == 2, (args, r.stdout, r.stderr)
        assert r.stdout == ""


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


SENSITIVE = "skills/brand-profile/scripts/sensitive_topics.py"
LOCK = ('# P\n\n```sensitive-topics\n{"action": "never_reply_escalate_to_user", "topics": {'
        '"family": {"keywords": ["family", "mother"], "exclude": ["font-family"]}, '
        '"politics": {"keywords": ["election"], "exclude": []}}}\n```\n')


def test_sensitive_topics_locks_on_whole_words_and_skips_excluded_phrases(tmp_path):
    prof = tmp_path / "profile.md"
    prof.write_text(LOCK, encoding="utf-8")
    locked = run(SENSITIVE, "--profile", str(prof), stdin="How is your Family? and the Election?")
    assert locked.returncode == 1
    assert json.loads(locked.stdout)["topics"] == {"family": ["family"], "politics": ["election"]}
    for text in ("which font-family do you use?", "familiar with @layer?", "a motherboard question"):
        r = run(SENSITIVE, "--profile", str(prof), stdin=text)
        assert r.returncode == 0, (text, r.stdout)


def test_sensitive_topics_refuses_a_profile_without_a_valid_block(tmp_path):
    prof = tmp_path / "profile.md"
    prof.write_text("# P\nno block\n", encoding="utf-8")
    assert run(SENSITIVE, "--profile", str(prof), "--validate").returncode == 2
    prof.write_text('```sensitive-topics\n{"topics": {"x": {"keywords": []}}}\n```\n', encoding="utf-8")
    assert run(SENSITIVE, "--profile", str(prof), "--validate").returncode == 2


CONTRAST = "skills/brand-identity/scripts/contrast.py"


def test_contrast_computes_wcag_ratios_and_fails_by_use():
    pairs = {"pairs": [{"name": "white on black", "fg": "#FFF", "bg": "#000000", "use": "text"},
                       {"name": "blue on white", "fg": "#0092CD", "bg": "#FFFFFF", "use": "large"},
                       {"name": "blue on white small", "fg": "#0092CD", "bg": "#FFFFFF", "use": "text"}]}
    r = run(CONTRAST, stdin=json.dumps(pairs))
    assert r.returncode == 1
    out = {p["name"]: p for p in json.loads(r.stdout)["pairs"]}
    assert out["white on black"]["ratio"] == 21.0 and out["white on black"]["pass"] is True
    assert out["blue on white"]["ratio"] == 3.5 and out["blue on white"]["pass"] is True
    assert out["blue on white small"]["pass"] is False


def test_contrast_refuses_bad_colours_and_uses():
    for pair in ({"fg": "blue", "bg": "#000"}, {"fg": "#000", "bg": "#FFF", "use": "huge"}):
        assert run(CONTRAST, stdin=json.dumps({"pairs": [pair]})).returncode == 2
    assert run(CONTRAST, stdin="[]").returncode == 2


HANDLE_CHECK = "skills/brand-name/scripts/handle_check.py"


def test_handle_check_refuses_bad_names_and_tlds_before_any_request():
    for args in (["--name", "../etc"], ["--name", "a b"], ["--name", "ok", "--tld", "d.e.v.x"], ["--name", "ok", "--today", "x"]):
        r = run(HANDLE_CHECK, *args)
        assert r.returncode == 2, (args, r.stdout)
        assert r.stdout == ""


def test_handle_check_domain_status_needs_the_control_domain(monkeypatch):
    hc = load(HANDLE_CHECK, "handle_check")
    answers = {"https://rdap.org/domain/google.io": (None, b""), "https://rdap.org/domain/me.io": (404, b""),
               "https://rdap.org/domain/google.dev": (200, b""), "https://rdap.org/domain/me.dev": (404, b"")}
    monkeypatch.setattr(hc, "http_status", lambda url: answers[url])
    assert hc.check_domain("me", "io")["status"] == "unknown"
    assert hc.check_domain("me", "dev")["status"] == "not_found"


CHECK_GUIDE = "skills/brand-guidelines/scripts/check_guide.py"


def test_check_guide_flags_stale_quotes_uncited_files_and_foreign_colours(tmp_path):
    brand = tmp_path / "brand"
    brand.mkdir()
    (brand / "voice.md").write_text('> hello network, today I share\n', encoding="utf-8")
    (brand / "identity.md").write_text("accent #07B6F0\n", encoding="utf-8")
    (brand / "strategy.md").write_text("label: Builder of small tools\n", encoding="utf-8")
    guide = tmp_path / "guide.md"
    guide.write_text('Label "Builder of small tools" [strategy.md]\nDon\'t: "a sentence nobody ever wrote"\n'
                     'Accent #07B6F0 and #FF0000 [identity.md] [voice.md] [ghost.md]\n', encoding="utf-8")
    r = run(CHECK_GUIDE, "--guide", str(guide), "--brand-dir", str(brand))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["stale_quotes"] == ["a sentence nobody ever wrote"]
    assert out["hex_not_in_identity"] == ["#FF0000"]
    assert out["missing_sources"] == ["ghost.md"]
    ok = tmp_path / "ok.md"
    ok.write_text('"Builder of small tools" [strategy.md] [identity.md] [voice.md] #07B6F0; not defined yet: brand-profile, brand-name\n', encoding="utf-8")
    assert run(CHECK_GUIDE, "--guide", str(ok), "--brand-dir", str(brand)).returncode == 0


def test_check_guide_requires_quoted_examples_and_names_the_skill_of_a_missing_file(tmp_path):
    brand = tmp_path / "brand"
    brand.mkdir()
    for f in ("strategy.md", "voice.md", "identity.md", "profile.md"):
        (brand / f).write_text('> "NEW BLOG POST!!!"\n', encoding="utf-8")
    guide = tmp_path / "guide.md"
    guide.write_text('[strategy.md] [voice.md] [identity.md] [profile.md]\n## 8. Do and don\'t\n| Do | Don\'t |\n|---|---|\n'
                     '| "NEW BLOG POST!!!" | Too many emojis |\n', encoding="utf-8")
    out = json.loads(run(CHECK_GUIDE, "--guide", str(guide), "--brand-dir", str(brand)).stdout)
    assert out["unquoted_examples"] == ["Too many emojis"]
    assert out["absent_not_named"] == ["name.md"]
    guide.write_text('[strategy.md] [voice.md] [identity.md] [profile.md] Name: not defined yet, run brand-name.\n'
                     '## 8. Do and don\'t\n| Do | Don\'t |\n|---|---|\n| "NEW BLOG POST!!!" | "NEW BLOG POST!!!" |\n', encoding="utf-8")
    assert run(CHECK_GUIDE, "--guide", str(guide), "--brand-dir", str(brand)).returncode == 0


# ---------- design-brief/lint_brief.py: SCREEN lists from the flows ----------

LINT_BRIEF = "skills/design-brief/scripts/lint_brief.py"

FLOWS_BOTH_SEPARATORS = """# Flows

## Screens

- SCREEN-1: Home. Purpose: introduce the site. Regions: hero (name, role), project list, footer. States: default, no JavaScript (theme toggle inert), reduced motion. Breakpoints: one column. Source: spec REQ-1.
- SCREEN-2: Post. Purpose: read a post. Regions: header, body. States: default; copied (feedback, 1 second); offline, cached copy shown. Breakpoints: one column. Source: spec REQ-2.

## Flows
"""


def screen_errors(tmp_path: Path, screen: str, content: str) -> list[str]:
    flows = tmp_path / "flows.md"
    flows.write_text(FLOWS_BOTH_SEPARATORS, encoding="utf-8")
    brief = tmp_path / "brief.md"
    brief.write_text(f"# Brief\n\n## Content\n\n{content}\n", encoding="utf-8")
    r = run(LINT_BRIEF, "--file", str(brief), "--type", "screen", "--values", "inline",
            "--flows", str(flows), "--screen", screen)
    return [e for e in json.loads(r.stdout)["errors"] if f"of {screen}" in e or "not found" in e]


def test_lint_brief_splits_lists_on_commas_or_semicolons():
    split = load(LINT_BRIEF, "lint_brief").split_list
    assert split("default, no JavaScript (theme toggle inert), reduced motion") == [
        "default", "no JavaScript (theme toggle inert)", "reduced motion"]
    assert split("default; copied (feedback, 1 second); offline, cached copy shown") == [
        "default", "copied (feedback, 1 second)", "offline, cached copy shown"]


def test_lint_brief_accepts_comma_separated_states(tmp_path):
    content = ("- Regions: hero, project list, footer\n- States:\n  - default\n"
               "  - no JavaScript: the toggle is inert\n  - reduced motion: no animation")
    assert screen_errors(tmp_path, "SCREEN-1", content) == []


def test_lint_brief_accepts_semicolon_separated_states(tmp_path):
    content = "- Regions: header, body\n- States:\n  - default\n  - copied: feedback\n  - offline, cached copy shown"
    assert screen_errors(tmp_path, "SCREEN-2", content) == []


def test_lint_brief_reports_a_state_missing_from_content(tmp_path):
    errors = screen_errors(tmp_path, "SCREEN-1", "- Regions: hero, project list, footer\n- States: default")
    assert errors == [
        "state 'no JavaScript (theme toggle inert)' of SCREEN-1 is not named in Content (looked for 'no javascript')",
        "state 'reduced motion' of SCREEN-1 is not named in Content (looked for 'reduced motion')"]


def test_lint_brief_eval_fixture_screens_keep_their_items():
    split = load(LINT_BRIEF, "lint_brief").split_list
    flows = (ROOT / "skills/design-brief/evals/files/flows.md").read_text(encoding="utf-8")
    states = re.search(r"SCREEN-3:.*?States:\s*(.*?)\.\s*Breakpoints:", flows).group(1)
    assert split(states) == ["default", "light and dark (from `data-pui-mode`)", "theme colour applied",
                             "search entry point absent when the build has no search"]


# ---------- design-system/lint_design_system.py: the library prefix ----------

LINT_DS = "skills/design-system/scripts/lint_design_system.py"


def test_lint_design_system_infers_the_library_prefix(tmp_path):
    doc = tmp_path / "ds.md"
    doc.write_text("# Design system\nUses --ui-ink and --ui-bg.\n", encoding="utf-8")
    css = tmp_path / "lib.css"
    css.write_text(":root { --ui-ink: #111; --ui-bg: #fff; --ui-line: #ddd; --x-y: 1px }\n", encoding="utf-8")
    out = json.loads(run(LINT_DS, "--file", str(doc), "--library", str(css)).stdout)
    assert out["library_prefix"] == "ui"
    assert any("['--ui-line']" in e for e in out["errors"])
    listed = tmp_path / "lib.md"
    listed.write_text("| Token | Value |\n| `--ds-bg` | #fff |\n| `--ds-ink` | #111 |\n", encoding="utf-8")
    out = json.loads(run(LINT_DS, "--file", str(doc), "--library", str(listed)).stdout)
    assert out["library_prefix"] == "ds"
    out = json.loads(run(LINT_DS, "--file", str(doc), "--library", str(css), "--prefix", "x").stdout)
    assert out["library_prefix"] == "x" and any("['--x-y']" in e for e in out["errors"])
    assert run(LINT_DS, "--file", str(doc), "--library", str(css), "--prefix", "../a").returncode == 2
