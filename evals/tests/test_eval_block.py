"""Offline tests of where an eval adapter's eval block lives: adapters/<harness>/eval.json, read by
evals/eval_run.py adapter_eval(), and no longer an "eval" key of adapter.json. No model is called."""
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KEYS = {"skills_dir", "settings", "account_limit", "refusal_markers"}
HARNESSES = ("claude-code", "agents-dir")


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "evals" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


er = load("eval_run")


def test_adapter_eval_returns_the_four_keys_for_each_eval_adapter():
    for harness in HARNESSES:
        assert set(er.adapter_eval(harness)) == KEYS, harness


def test_no_adapter_json_has_an_eval_key_and_each_eval_json_holds_exactly_the_four_keys():
    for harness in HARNESSES:
        manifest = json.loads((REPO / "adapters" / harness / "adapter.json").read_text(encoding="utf-8"))
        assert "eval" not in manifest, harness
        block = json.loads((REPO / "adapters" / harness / "eval.json").read_text(encoding="utf-8"))
        assert set(block) == KEYS, harness
