"""Tests for skills/design-handoff/scripts: what unpack_export.py lists for the spec and what lint_handoff.py checks.

Run: uv run --with pytest pytest skills/design-handoff/scripts/tests/test_lint_handoff.py

Offline; every name, class, token and requirement below is fictional. The refusals of unpack_export.py
(resource ids, symlinks, decompression cap) are tested in test_unpack_export.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
UNPACK = ROOT / "skills/design-handoff/scripts/unpack_export.py"
LINT = ROOT / "skills/design-handoff/scripts/lint_handoff.py"
FIXTURE = ROOT / "skills/design-handoff/evals/files/landing"
EXPORT = FIXTURE / "docs/design/screens/landing-page/landing.html"
LIBRARY = FIXTURE / "library/plinthui.css"
FLOWS = FIXTURE / "docs/design/flows.md"

PAGE = """<html><head><style>
:root { --kit-ink: #111111; --made-up: #abcdef; }
a { color: var(--kit-ink); border-color: #123456; transition: opacity 200ms ease-out; }
@keyframes rise { from { opacity: 0 } }
</style></head><body><a class="kit-btn">x</a>
<script>
const STATIC_CAPTURE = true; // preview only
let debug = false
const FADE_MS = 200;
const ROWS = [1, 2, 3];
const label = "Copy";
function f() { const inner = compute(); }
</script></body></html>
"""
KIT = ":root { --kit-ink: #111111; }\n"

FLOWS_TEXT = """# Flows

## Screens

- SCREEN-1: Home. Purpose: x. Regions: top banner (headline), sign-up form, footer. States: default. Breakpoints: none. Source: spec.
- SCREEN-2: Other. Purpose: y. Regions: list. States: default.

## Flows

- FLOW-1: x
"""

SPEC = """# Handoff: home

- Status: draft
- Lint: ok (2026-01-05)

## Summary

x

## Sources

- x

## Reference and shipping

- Reference only, never shipped: the tool runtime
- Preview-only switches and placeholders: STATIC_CAPTURE forces the static state; debug is unused; ROWS is placeholder data

## Tokens

| Value | Where | Maps to | Action |
|-------|-------|---------|--------|
| `--made-up` (#abcdef) | link | none | fix in code |
| #123456 | link border | none | fix in code |

## Components

| Region | Unit | Props and data | Content source | States |
|--------|------|----------------|----------------|--------|
| Top banner | Banner | none | content/home.md | default |
| Sign-up form | Form | none | config | default, error |
| Footer | SiteFooter | none | config | default |

## Layout

| Width | Columns and order | Sticky | Collapsed or hidden |
|-------|-------------------|--------|---------------------|
| 1280 | one | none | none |

## Behaviour

| Interaction | Requirement | Rule |
|-------------|-------------|------|
| submit | REQ-1 | sends |

## Motion

| Animation | Trigger | Timing | Final state | Reduced motion |
|-----------|---------|--------|-------------|----------------|
| Link fade | hover | 200 ms ease-out | opaque | no transition |

## Assets

- none

## Deviations

- DEV-1: border colour is not a token, against the design system. Action: fix in code

## Acceptance

- Compare at: 1280 px, light

## Open questions

- none

## Readiness

- Ready for eng-architecture: yes
"""


def run(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=60, cwd=cwd)


def unpack(tmp_path: Path, *extra: str) -> tuple[dict, dict]:
    (tmp_path / "page.html").write_text(PAGE, encoding="utf-8")
    (tmp_path / "kit.css").write_text(KIT, encoding="utf-8")
    r = run(UNPACK, "--file", str(tmp_path / "page.html"), "--out", str(tmp_path / "out"), *extra)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), json.loads((tmp_path / "out" / "inventory.json").read_text())


def lint(tmp_path: Path, spec: str, *extra: str) -> tuple[int, dict]:
    (tmp_path / "home.md").write_text(spec, encoding="utf-8")
    (tmp_path / "flows.md").write_text(FLOWS_TEXT, encoding="utf-8")
    r = run(LINT, "--file", str(tmp_path / "home.md"), "--flows", str(tmp_path / "flows.md"), "--screen", "SCREEN-1", *extra)
    return r.returncode, json.loads(r.stdout)


def with_inventory(tmp_path: Path) -> list[str]:
    unpack(tmp_path)
    return ["--inventory", str(tmp_path / "out" / "inventory.json"), "--library", str(tmp_path / "kit.css")]


# ---------- unpack_export.py ----------

def test_unpack_lists_flags_numbers_and_data_with_their_lines(tmp_path):
    out, inv = unpack(tmp_path)
    assert [(f["name"], f["value"], f["line"]) for f in inv["script_flags"]] == [("STATIC_CAPTURE", "true", 2), ("debug", "false", 3)]
    assert inv["script_flags"][0]["comment"] == "preview only" and inv["script_flags"][0]["script"] == "scripts/01.js"
    written = (tmp_path / "out" / "scripts" / "01.js").read_text().splitlines()
    assert written[inv["script_flags"][0]["line"] - 1].startswith("const STATIC_CAPTURE"), "line numbers are those of the written file"
    assert [(n["name"], n["value"]) for n in inv["script_numbers"]] == [("FADE_MS", "200")]
    assert [d["name"] for d in inv["script_data"]] == ["ROWS"]
    assert out["script_flags"] == inv["script_flags"] and out["script_data"] == inv["script_data"]
    # A string constant and a constant set from a call are neither flags, numbers nor data.
    names = {e["name"] for k in ("script_flags", "script_numbers", "script_data") for e in inv[k]}
    assert "label" not in names and "inner" not in names


def test_unpack_lists_css_motion(tmp_path):
    _, inv = unpack(tmp_path)
    assert inv["css_motion"] == ["transition: opacity 200ms ease-out", "@keyframes rise"]


def test_unpack_to_cover_is_what_the_library_lacks(tmp_path):
    out, inv = unpack(tmp_path, "--library", str(tmp_path / "kit.css"))
    assert inv["to_cover"] == {"custom_properties": ["--made-up"], "fixed_colours": ["#123456", "#abcdef"]}
    assert out["to_cover"] == inv["to_cover"]


def test_unpack_without_library_has_no_to_cover_and_prints_the_date(tmp_path):
    out, inv = unpack(tmp_path)
    assert "to_cover" not in inv and "to_cover" not in out
    assert len(out["date"]) == 10 and out["date"][4] == "-"


def test_unpack_unreadable_library_is_a_usage_error(tmp_path):
    (tmp_path / "page.html").write_text(PAGE, encoding="utf-8")
    r = run(UNPACK, "--file", str(tmp_path / "page.html"), "--out", str(tmp_path / "out"), "--library", str(tmp_path / "missing.css"))
    assert r.returncode == 2 and "library stylesheet" in r.stderr
    assert not (tmp_path / "out").exists(), "nothing is written before the inputs are read"


def test_unpack_reads_the_eval_fixture(tmp_path):
    r = run(UNPACK, "--file", str(EXPORT), "--out", str(tmp_path / "out"), "--class-prefix", "plu", "--library", str(LIBRARY))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["to_cover"] == {"custom_properties": ["--ds-accent-ink", "--ds-font-display", "--ds-space-section", "--hero-glow"],
                               "fixed_colours": ["#e4e7ec", "#ffb020"]}
    assert [f["name"] for f in out["script_flags"]] == ["PREVIEW_STATIC"]
    assert [d["name"] for d in out["script_data"]] == ["SIZE_DATA"]
    assert {n["name"]: n["value"] for n in out["script_numbers"]} == {"REVEAL_STAGGER_MS": "80", "COPIED_MS": "1500"}
    assert "600ms" in out["css_motion"][0]
    assert sorted(p.name for p in (tmp_path / "out" / "resources").iterdir()) == ["designtool-runtime.js", "logo-mark.svg", "plinthui-css.css"]
    assert (tmp_path / "out" / "resources" / "plinthui-css.css").read_bytes() == LIBRARY.read_bytes()


# ---------- lint_handoff.py ----------

def test_lint_passes_a_complete_spec_and_prints_the_summary(tmp_path):
    code, out = lint(tmp_path, SPEC, *with_inventory(tmp_path))
    assert code == 0, out
    assert out["ok"] is True and out["errors"] == []
    assert out["summary"] == ("lint_handoff ok: 0 errors; 3 components, 2 tokens, 1 motion rows, 1 deviations; "
                              "with inventory and library")


def test_lint_without_inventory_says_tokens_were_not_checked(tmp_path):
    code, out = lint(tmp_path, SPEC)
    assert code == 0 and out["summary"].endswith("without inventory (tokens not checked)")


def test_lint_wants_every_flag_and_data_constant_named(tmp_path):
    spec = SPEC.replace("STATIC_CAPTURE forces the static state; ", "").replace("ROWS is placeholder data", "nothing else")
    code, out = lint(tmp_path, spec, *with_inventory(tmp_path))
    assert code == 1
    flagged = [e for e in out["errors"] if e.startswith("script constant")]
    assert len(flagged) == 2 and "STATIC_CAPTURE" in flagged[0] and "ROWS" in flagged[1]


def test_lint_wants_a_token_row_for_what_the_library_lacks(tmp_path):
    spec = SPEC.replace("| #123456 | link border | none | fix in code |\n", "")
    code, out = lint(tmp_path, spec, *with_inventory(tmp_path))
    assert code == 1 and out["errors"] == ["fixed colour #123456 is not in the library and has no Tokens row"]


def test_lint_wants_a_timing_and_a_reduced_motion_entry(tmp_path):
    spec = SPEC.replace("| Link fade | hover | 200 ms ease-out | opaque | no transition |", "| Link fade | hover | quick | opaque | |")
    code, out = lint(tmp_path, spec)
    assert code == 1
    assert any("no reduced-motion entry" in e for e in out["errors"]) and any("no timing in ms or s" in e for e in out["errors"])


def test_lint_wants_a_component_per_region_and_an_action_per_deviation(tmp_path):
    spec = SPEC.replace("| Sign-up form | Form | none | config | default, error |\n", "").replace("Action: fix in code", "Action: later")
    code, out = lint(tmp_path, spec)
    assert code == 1
    assert any("sign-up form" in e for e in out["errors"]) and any(e.startswith("DEV-1 has no Action") for e in out["errors"])


def test_lint_report_records_the_last_result_with_its_arguments(tmp_path):
    report = tmp_path / "home.lint.json"
    code, out = lint(tmp_path, SPEC.replace("## Assets", "## Files"), "--report", str(report))
    assert code == 1
    rec = json.loads(report.read_text())
    assert sorted(rec) == ["arguments", "counts", "date", "errors", "ok", "script", "summary"]
    assert rec["script"] == "lint_handoff.py" and rec["summary"] == out["summary"]
    assert rec["ok"] is False and rec["errors"] == out["errors"] == ["missing section '## Assets'"]
    assert rec["arguments"]["--screen"] == "SCREEN-1" and "--report" not in rec["arguments"] and len(rec["date"]) == 10
    code, out = lint(tmp_path, SPEC, "--report", str(report), "--json")
    rec = json.loads(report.read_text())
    assert code == 0 and rec["ok"] is True and rec["arguments"]["--json"] is True


def test_lint_usage_errors(tmp_path):
    for args in (["--file"], ["--file", "a.md", "--flows", "b.md", "--screen", "SCREEN-1", "--inventory", "i.json"],
                 ["--file", "a.md", "--flows", "b.md", "--screen", "SCREEN-1", "--reprot", "r.json"], []):
        r = run(LINT, *args, cwd=tmp_path)
        assert r.returncode == 2 and r.stdout == "" and r.stderr.startswith("Error:"), args
    assert "unknown argument '--reprot'" in run(LINT, "--file", "a.md", "--reprot", "r.json").stderr
    assert not (tmp_path / "r.json").exists()


def test_lint_finds_the_fixture_screen(tmp_path):
    (tmp_path / "s.md").write_text(SPEC, encoding="utf-8")
    r = run(LINT, "--file", str(tmp_path / "s.md"), "--flows", str(FLOWS), "--screen", "SCREEN-1")
    errors = json.loads(r.stdout)["errors"]
    missing = [e for e in errors if e.startswith("region")]
    assert len(missing) == 5 and not any("not found in the flows" in e for e in errors)
