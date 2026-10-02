"""Tests for skills/biz-market-analysis/scripts/check_refs.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/biz-market-analysis/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


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
