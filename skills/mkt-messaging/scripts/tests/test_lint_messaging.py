"""Tests for skills/mkt-messaging/scripts/lint_messaging.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/mkt-messaging/scripts/tests
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


def lint(rel: str, path: Path, text: str, *args: str) -> tuple[int, dict]:
    """Write `text` to `path`, lint it, and return the exit code and the parsed JSON result."""
    path.write_text(text, encoding="utf-8")
    r = run(rel, "--file", str(path), *args)
    return r.returncode, json.loads(r.stdout)


# ---------- mkt-messaging/lint_messaging.py: proof method and date, number words, demos ----------

LINT_MSG = "skills/mkt-messaging/scripts/lint_messaging.py"


MSG_PROOF = ("The stylesheet is 8 kB gzipped. Evidence: size of the built file. "
             "Method: `gzip -c dist/lintel.css | wc -c`. Date: 2026-03-14. Source: build output.")


def messaging(proof: str = MSG_PROOF, headline: str = "Small enough to read", body: str = "The whole stylesheet is 8 kB.",
              demo: str = "the file size next to the built file", tagline: str = "Styles you can read") -> str:
    return f"""# Messaging: Lintel

## Summary

## Sources

## Audience

## Promise

## Voice

## Proof points

- PROOF-1: {proof}

## Sections

- SECTION-1: Hero. Purpose: say what it is. Proof: none. Headline: A stylesheet for docs. Body: Plain CSS. CTA: Install → /install. Source: README.
- SECTION-2: Size. Purpose: show the weight. Proof: PROOF-1. Headline: {headline}. Body: {body} Demo: {demo}. Source: PROOF-1.

## Taglines

- {tagline}

## Words

- Use: stylesheet. Source: README.
- Avoid: blazing

## Open questions

## Assumptions

none

## Readiness
"""


def msg_errors(tmp_path: Path, **parts: str) -> list[str]:
    code, out = lint(LINT_MSG, tmp_path / "messaging.md", messaging(**parts))
    assert code == (1 if out["errors"] else 0)
    return out["errors"]


def test_lint_messaging_accepts_dated_proof_and_a_first_section_without_a_demo(tmp_path):
    assert msg_errors(tmp_path) == []


def test_lint_messaging_needs_a_method_and_a_date_on_every_proof(tmp_path):
    assert msg_errors(tmp_path, proof="The stylesheet is 8 kB gzipped. Evidence: size of the built file. Source: build output.") == [
        "PROOF-1 lacks Method:", "PROOF-1 lacks Date:"]
    assert msg_errors(tmp_path, proof=MSG_PROOF.replace("2026-03-14", "March 2026")) == [
        "PROOF-1: Date: carries no YYYY-MM-DD date"]
    # a date elsewhere in the proof does not stand in for the Date: field
    assert msg_errors(tmp_path, proof=MSG_PROOF.replace("Date: 2026-03-14", "Date: last week").replace(
        "build output", "build output of 2026-03-14")) == ["PROOF-1: Date: carries no YYYY-MM-DD date"]


def test_lint_messaging_checks_number_words_against_the_proofs(tmp_path):
    assert msg_errors(tmp_path, headline="Eight kilobytes, no more") == [], "a word whose digits a PROOF carries"
    assert msg_errors(tmp_path, headline="Three kilobytes, no more") == [
        "SECTION-2: number Three in the copy is not in any PROOF"]
    assert msg_errors(tmp_path, body="Half the weight of a framework.") == [
        "SECTION-2: number Half in the copy is not in any PROOF"]
    assert msg_errors(tmp_path, tagline="Twice as light") == ["Taglines: number Twice is not in any PROOF"]
    assert msg_errors(tmp_path, tagline="Docs in 5 minutes") == ["Taglines: number 5 is not in any PROOF"]
    assert msg_errors(tmp_path, tagline="Half the weight",
                      proof=MSG_PROOF.replace("gzipped.", "gzipped, half of the previous release.")) == []


def test_lint_messaging_does_not_take_a_date_for_a_proof_number(tmp_path):
    assert msg_errors(tmp_path, body="Ships with 14 themes.") == ["SECTION-2: number 14 in the copy is not in any PROOF"]
    assert msg_errors(tmp_path, body="Released in 2026.") == ["SECTION-2: number 2026. in the copy is not in any PROOF"]


def test_lint_messaging_needs_a_demo_on_every_later_section(tmp_path):
    message = "SECTION-2: Demo: must describe what the design shows; a section with nothing to show is merged into another"
    for demo in ("none", "None", "n/a", "no demo needed", ""):
        assert msg_errors(tmp_path, demo=demo) == [message], demo
    # a call to action does not replace the demo of a later section
    text = messaging().replace("Demo: the file size next to the built file.", "CTA: Install → /install.")
    assert lint(LINT_MSG, tmp_path / "messaging.md", text)[1]["errors"] == [message]


def test_lint_messaging_needs_an_assumptions_section(tmp_path):
    text = messaging().replace("## Assumptions\n\nnone\n\n", "")
    assert lint(LINT_MSG, tmp_path / "messaging.md", text)[1]["errors"] == ["missing section '## Assumptions'"]


def test_lint_messaging_prints_a_summary_and_writes_the_report_on_request(tmp_path):
    doc = tmp_path / "messaging.md"
    doc.write_text(messaging(), encoding="utf-8")
    report = tmp_path / "messaging.lint.json"
    r = run(LINT_MSG, "--file", str(doc), "--report", str(report))
    assert r.returncode == 0, r.stderr
    printed = json.loads(r.stdout)
    assert printed["summary"] == "lint_messaging ok: 0 errors, 1 proofs, 2 sections"
    record = json.loads(report.read_text(encoding="utf-8"))
    assert record["script"] == "lint_messaging.py"
    assert record["arguments"] == {"--file": str(doc)}
    assert record["ok"] is True and record["errors"] == []
    assert record["summary"] == printed["summary"]
    assert record["counts"] == {"proofs": 1, "sections": 2}
    # a failing run writes the report too, with ok false and its errors
    doc.write_text(messaging(headline="Three kilobytes, no more"), encoding="utf-8")
    r = run(LINT_MSG, "--file", str(doc), "--report", str(report))
    assert r.returncode == 1
    record = json.loads(report.read_text(encoding="utf-8"))
    assert record["ok"] is False and record["errors"] == ["SECTION-2: number Three in the copy is not in any PROOF"]
    assert record["summary"].startswith("lint_messaging FAILED: 1 errors")


def test_lint_messaging_usage_errors_exit_2_without_a_traceback(tmp_path):
    for args in (["--file"], [], ["--file", "x.md", "--strict"], ["--file", "x.md", "--report"]):
        r = run(LINT_MSG, *args, cwd=tmp_path)
        assert r.returncode == 2, args
        assert "Traceback" not in r.stderr and r.stderr.strip(), args
        assert r.stdout == "", args
    r = run(LINT_MSG, "--file", str(tmp_path / "missing.md"))
    assert r.returncode == 2 and "cannot read" in r.stderr


def test_lint_messaging_json_only_indents(tmp_path):
    doc = tmp_path / "messaging.md"
    doc.write_text(messaging(), encoding="utf-8")
    plain = run(LINT_MSG, "--file", str(doc)).stdout
    pretty = run(LINT_MSG, "--file", str(doc), "--json").stdout
    assert json.loads(plain) == json.loads(pretty)
    assert plain.count("\n") == 1 and pretty.count("\n") > 1
