"""Offline tests of the gate file's keys "baseline_runs" and "baseline_margin" in evals/eval_status.py: their
defaults, their ranges, and the committed gate file. No model is called."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "evals" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


es = load("eval_status")


def test_baseline_runs_defaults_to_runs_and_the_margin_to_none():
    assert es.event_config({})["baseline_runs"] == 3
    assert es.event_config({"runs": 2})["baseline_runs"] == 2
    assert es.event_config({"baseline_runs": 1})["baseline_runs"] == 1
    assert es.event_config({})["baseline_margin"] is None
    assert es.event_config({"baseline_margin": 0.2})["baseline_margin"] == 0.2


def test_baseline_runs_is_a_whole_number_from_1_to_runs():
    assert es.event_problems({"baseline_runs": 1}) == []
    assert es.event_problems({"baseline_runs": 0}) != []
    assert es.event_problems({"baseline_runs": True}) != []
    assert es.event_problems({"runs": 2, "baseline_runs": 3}) == ["baseline_runs must not be above runs"]


def test_baseline_margin_is_a_number_from_0_to_1():
    assert es.event_problems({"baseline_margin": 0.2}) == []
    for bad in (-0.1, 1.5, True, "0.2"):
        assert es.event_problems({"baseline_margin": bad}) == ["baseline_margin must be a number from 0 to 1"]

