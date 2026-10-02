"""Tests for skills/biz-market-analysis/scripts/lint_market.py. Offline; every name and number below is fictional.

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
