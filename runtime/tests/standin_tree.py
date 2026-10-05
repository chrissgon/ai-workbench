"""A stand-in workbench tree for the tests of runtime/: an adapter that is a shell script, two invented skills
and one flow file, so that a run executes on this machine with no container and no model. Not a test file.

The stand-in adapter "h" is told what to do by files beside its script (adapters/h/), which a test writes:
  fail-times   a number: the first <n> calls fail as fail-kind says, the next ones behave
  fail-kind    timeout | adapter | refused | auth | limit | early
Each model call is appended to adapters/h/calls.txt as "<the skill staged, or none> <attempt number>".
Otherwise it acts by the skill staged in the copy:
  demo-asks    with no answer in the prompt it asks, with the skills' asking template, and writes nothing;
               with an answer it writes docs/business/market.md and a line in docs/workbench/state.md
  demo-writes  writes docs/business/icp.md from docs/business/market.md; without that input it says so
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"

EVAL_JSON = {"skills_dir": ".h/skills", "settings": [".h", "h-settings.json"],
             "account_limit": ["usage limit reached"], "refusal_markers": ["safeguards flagged this message"]}

ADAPTER = r'''
here="$(dirname "$0")"; prompt="$2"; cwd="$4"; out="$8"
if grep -q "Reply with the single word: ok" "$prompt"; then echo probe >> "$here/probes.txt"; echo ok > "$out/response.md"; exit 0; fi
skill=none
for name in demo-asks demo-writes; do [ -d "$cwd/.h/skills/$name" ] && skill="$name"; done
n=1; while ! mkdir "$here/call-$skill.$n" 2>/dev/null; do n=$((n + 1)); done
echo "$skill $n" >> "$here/calls.txt"
(cd "$cwd" && find . -path ./.git -prune -o -type f -print | sort) > "$out/files.txt"
echo "{\"total_tokens\": 100, \"duration_ms\": 5, \"cost_usd\": 0.01, \"skills_loaded\": [\"$skill\"]}" > "$out/timing.json"
if [ -f "$here/fail-times" ] && [ "$n" -le "$(cat "$here/fail-times")" ]; then
  case "$(cat "$here/fail-kind")" in
    timeout) sleep 30 ;;
    adapter) echo "the provider is down" >&2; exit 1 ;;
    refused) echo "safeguards flagged this message" > "$out/response.md"; exit 1 ;;
    auth) echo "API Error: 401 Unauthorized" >&2; exit 1 ;;
    limit) echo "usage limit reached" >&2; exit 1 ;;
    early) echo "Let me just read the template first." > "$out/response.md"; exit 0 ;;
  esac
fi
if [ -n "${STANDIN_KEY:-}" ]; then echo "the key is $STANDIN_KEY" > "$cwd/leak.txt"; echo "key: $STANDIN_KEY" >> "$out/stderr.log"; fi
case "$skill" in
  demo-asks)
    if grep -q "the user's answer" "$prompt"; then
      mkdir -p "$cwd/docs/business" "$cwd/docs/workbench"
      printf '# Market analysis\n\n- Owner: demo-asks\n- Status: draft\n' > "$cwd/docs/business/market.md"
      echo "- decision recorded by demo-asks" >> "$cwd/docs/workbench/state.md"
      echo "{}" > "$cwd/docs/business/market.lint.json"
      echo "x" > "$cwd/notes.txt"
      printf -- '- Analysis: docs/business/market.md (Status: draft)\n- Next: demo-writes\n' > "$out/response.md"
    else
      printf 'Nothing was searched or written yet: the scope below is your decision.\n\n1. Which country? Recommended: yours, because you sell there.\n' > "$out/response.md"
    fi ;;
  demo-writes)
    if [ -f "$cwd/docs/business/market.md" ]; then
      printf '# Ideal customer profile\n\n- Owner: demo-writes\n- Status: hypothesis\n' > "$cwd/docs/business/icp.md"
      printf -- '- Primary profile: clinics\n- Next: interviews\n' > "$out/response.md"
    else
      echo "There is no market analysis (docs/business/market.md)." > "$out/response.md"
    fi ;;
  *) echo "ok" > "$out/response.md" ;;
esac
'''


def load(name: str):
    """A module of runtime/, imported the way the modules import each other (runtime/ first on the path), so
    that a test and the module under test see the same module objects."""
    if str(RUNTIME) not in sys.path:
        sys.path.insert(0, str(RUNTIME))
    return importlib.import_module(name)


def skill(tree: Path, name: str, inputs: str, outputs: str) -> Path:
    folder = tree / "skills" / name
    (folder / "evals").mkdir(parents=True)
    (folder / "scripts" / "tests").mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: invented\nlicense: MIT\nmetadata:\n  area: business\n  kind: capability\n"
        f"  inputs: [{inputs}]\n  outputs: [{outputs}]\n  updates: [docs/workbench/state.md]\n  requires: []\n"
        f"  side_effects: []\n  version: \"0.1.0\"\n---\n# {name}\n", encoding="utf-8")
    (folder / "evals" / "evals.json").write_text("{}", encoding="utf-8")
    (folder / "scripts" / "check.py").write_text("print(1)\n", encoding="utf-8")
    (folder / "scripts" / "tests" / "test_check_demo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    return folder


def build(tmp_path: Path, monkeypatch, lab) -> dict:
    """The tree, a project and the patches that point the lab facade at them. Returns {"tree", "project",
    "data", "db", "adapter"} as paths. The runner executes on this machine (EXECUTOR "host"), its lock folder is
    the test's own, and nothing waits before a retry."""
    tree, project = tmp_path / "bench-tree", tmp_path / "project"
    adapter = tree / "adapters" / "h"
    adapter.mkdir(parents=True)
    (adapter / "eval.json").write_text(json.dumps(EVAL_JSON), encoding="utf-8")
    (adapter / "run-prompt.sh").write_text(ADAPTER, encoding="utf-8")
    skill(tree, "demo-asks", "docs/workbench/state.md, docs/workbench/research/<topic>.md, AGENTS.md", "docs/business/market.md")
    skill(tree, "demo-writes", "docs/workbench/state.md, docs/business/market.md", "docs/business/icp.md")
    (tree / "flows").mkdir()
    (tree / "flows" / "demo.json").write_text(json.dumps({"flow": "demo", "title": "Demo flow", "tasks": [
        {"key": "market", "skill": "demo-asks", "title": "Market", "text": "do the market analysis."},
        {"key": "profile", "skill": "demo-writes", "title": "Profile", "text": "choose the profile.",
         "depends_on": ["market"], "milestone": True}]}), encoding="utf-8")
    for rel in ("providers/resolve.py", "providers/store/sqlite.py"):
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, tree / rel)
    (project / "docs" / "workbench").mkdir(parents=True)
    data, db = tmp_path / "data", tmp_path / "store" / "tasks.sqlite"
    (project / "docs" / "workbench" / "runtime.json").write_text(json.dumps(
        {"workbench": str(tree), "data_dir": str(data), "store_db": str(db)}), encoding="utf-8")
    (project / "docs" / "workbench" / "state.md").write_text("# Workbench state\n\n## Decisions\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("# Project\n", encoding="utf-8")
    er = lab.load()
    monkeypatch.setattr(er, "ROOT", str(tree))
    monkeypatch.setattr(er, "EXECUTOR", "host")
    monkeypatch.setattr(er, "LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.setattr(er, "RETRY_PAUSE", 0)
    monkeypatch.setattr(er, "PAUSE_POLL", 0.05)
    monkeypatch.setattr(er, "PROBE_SECONDS", 0)
    control = {"total_jobs": 2, "web_jobs": {"strong": 1, "floor": 1}}
    monkeypatch.setattr(lab, "reference", lambda tier="strong": {
        "tier": tier, "model": "m", "adapter": "h", "pass_env": [], "timeout_seconds": 60, "retries": 2, "control": control})
    return {"tree": tree, "project": project, "data": data, "db": db, "adapter": adapter}


def calls(adapter: Path) -> list:
    path = adapter / "calls.txt"
    return path.read_text().split("\n")[:-1] if path.is_file() else []


def fail(adapter: Path, kind: str, times: int) -> None:
    (adapter / "fail-kind").write_text(kind + "\n")
    (adapter / "fail-times").write_text(f"{times}\n")
