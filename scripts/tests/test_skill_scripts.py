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
