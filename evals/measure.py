#!/usr/bin/env python3
"""What decides what a run measures, in one module (item B10 of docs/architecture/final-plan-2026-10-02.md).

The eval runner (evals/eval_run.py) and the status script (evals/eval_status.py) import it; it imports
neither. It holds:

  - the facts block the grader is given (facts_block), the commands that read the case's repository for it
    (VCS_SCRIPT) and the length they are cut at (VCS_LIMIT);
  - what the grader is shown of a file a run produced (shown, binary_stub, NOT_SHOWN, FILE_LIMIT);
  - the grading prompt (assertion_text, grading_prompt) and the reading of the grader's answer
    (read_grading), with the number of times a refused answer is asked for again (GRADING_RETRIES);
  - the early-end rule (early_end), which decides which runs are made again instead of scored;
  - the replacement of the passed variables' values by a marker (redaction_values, replace_values);
  - the scoring of a run (score, grading_summary) and the unrounded comparisons of the gate (at_threshold,
    within_tolerance, gate_passes).

The constants that no other file owns (the file limit, the early-end phrase lists and the others above) are
data in evals/measurement.json, read once when the module loads. The number of runs, the timeout and the
retries of an event have their home in the gate file (evals/eval-gate.json); what an adapter's harness prints
on a refusal or an exhausted account, in that adapter's adapter.json.

This file and evals/measurement.json are in the measurement fingerprint (eval_status.py, FINGERPRINT_FILES):
a change to either is committed as one of the three kinds of the reliability model's section 8
(`python3 evals/eval_status.py measurement --kind grader|execution|infrastructure`). The rest of the runner
(arguments, concurrency, the shared lock, resuming, the reports) is infrastructure and may change freely.

Standard library only. It has no command line of its own: `--help` prints this text.
"""
import json
import os
import re
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONSTANTS = os.path.join(HERE, "measurement.json")


def _constants(path=CONSTANTS):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    early = data["early_end"]
    return data, early


_DATA, _EARLY = _constants()

# The grader sees each produced file up to this many characters. Plans and reports run to several thousand; at
# 3,000 an early run graded the end of a plan as missing, and at 20,000 an assertion about every source of a
# long research artifact failed as unproven.
FILE_LIMIT = _DATA["file_limit"]
VCS_LIMIT = _DATA["vcs_limit"]  # characters of the version-control facts shown to the grader
GRADING_RETRIES = _DATA["grading_retries"]  # a refused or unparsable grading is made again up to this many times
# A passed variable whose value is shorter than this is not replaced: it is a switch, not a credential, and
# replacing "1" or "true" wherever it occurs would rewrite what a run produced.
REDACT_MIN = _DATA["redact_min"]

# An early end: the model ended its turn before doing the work, with no error (eval_run.py, "Early ends").
# Markup of a tool call or a control block printed as text; it counts only at the start of a line, so a reply
# that quotes such markup inline to the user is left alone. Seen from a floor model: <skill_tool>, and loops
# of <system-reminder> blocks it wrote itself; the last entry is the model's own tool-call token.
EARLY_END_MARKUP = tuple(_EARLY["markup"])
# How a last line announces a next action instead of ending the turn's work. Matched, in lower case, at the
# start of a sentence of the last line ("Let me update the file:", "Now I'll write the spec:").
# Not a bare "i'll": "I'll also need to know where the code should go" ends a reply that states a blocker.
EARLY_END_ANNOUNCE = tuple(_EARLY["announce"])
# A last line with one of these waits for the user ("Let me know which you prefer", "I'll wait for the brief",
# "If you approve it, I'll run it"): never an early end.
EARLY_END_NOT = tuple(_EARLY["not"])
# A reply longer than EARLY_END_BLOCKER_MIN characters that holds one of these states a blocker or asks for an
# input in the imperative ("I can't read the ticket ... paste it"): a stop, never an early end. The length
# keeps a one-line "Now I need the format. Let me update the file:" an early end.
EARLY_END_BLOCKER = tuple(_EARLY["blocker"])
EARLY_END_BLOCKER_MIN = _EARLY["blocker_min"]
# An announcement is an early end in a short reply, or when the last line ends as one that was cut (":", "...").
EARLY_END_SHORT = _EARLY["short"]
PSEUDO_TAG_LINE_RE = re.compile(r"^<([A-Za-z_-]+)>.*</\1>$")
# A trailing line that is only a tag, such as a tool call the model printed as text and never ran
# (<read filePath="...">, </read>): skipped to reach the last line of prose.
TAG_ONLY_LINE_RE = re.compile(r"^</?[A-Za-z_][\w-]*(\s[^<>]*)?/?>$")


def early_end(response, changed):
    """Why a run that exited 0 is an early end, or None. Conservative: a run that wrote a file, a reply that
    asks the user a question and a reply that states a blocker are never one."""
    if changed:
        return None
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    if not lines:
        return "empty response and no file written"
    for line in lines:
        hit = next((m for m in EARLY_END_MARKUP if line.lower().startswith(m)), None)
        if hit:
            return f"tool or control markup printed as text ({hit}) and no file written"
    if "?" in response:
        return None
    while len(lines) > 1 and (PSEUDO_TAG_LINE_RE.match(lines[-1]) or TAG_ONLY_LINE_RE.match(lines[-1])):
        lines.pop()  # a trailing note the model wrapped in a tag of its own
    low = response.lower().replace("’", "'")
    if len(response) > EARLY_END_BLOCKER_MIN and any(phrase in low for phrase in EARLY_END_BLOCKER):
        return None  # states a blocker or asks for an input
    last = lines[-1].lower().replace("’", "'")
    if any(phrase in last for phrase in EARLY_END_NOT):
        return None
    # The FINAL sentence of the last line, not any sentence of it: "I'll fetch it myself. I'll also need to
    # know which project it belongs to." ends on a request.
    final = re.split(r"(?<=[.!:;])\s+", last)[-1].lstrip("-*>#_`0123456789.) ")
    if final.startswith(EARLY_END_ANNOUNCE) and (len(response) <= EARLY_END_SHORT or lines[-1].endswith((":", "...", "…"))):
        return "the reply ends by announcing a next action, no question was asked and no file written"
    return None


# --- the values of the passed variables, replaced by a marker (item B6a) --------------------------------

def redaction_values(names, env=None):
    """[(value, marker)] for the variables passed into a run, longest value first: what replace_values() looks
    for. The marker names the variable, never its value."""
    env = os.environ if env is None else env
    found = {}
    for name in dict.fromkeys(names):
        value = env.get(name) or ""
        if len(value) >= REDACT_MIN:
            found.setdefault(value, f"[redacted:{name}]")
    return sorted(found.items(), key=lambda pair: len(pair[0]), reverse=True)


def replace_values(data, values):
    """Replace each exact value in data (bytes or text) by its marker. Returns (the new data, the number of
    replacements). Exact values only, no pattern of what a credential looks like: a planted fake secret in a
    fixture is not one of the passed values and stays, so an assertion that a reply does not repeat it still
    measures the reply."""
    count = 0
    for value, marker in values:
        if isinstance(data, bytes):
            value, marker = value.encode("utf-8"), marker.encode("utf-8")
        hits = data.count(value)
        if hits:
            data, count = data.replace(value, marker), count + hits
    return data, count


# --- what the grader is given -----------------------------------------------------------------------

# What the harness asks the case's repository after a run, in the case folder, in a container with no
# network. One literal script: nothing of a case or of a run is put into it.
VCS_SCRIPT = """
if ! git rev-parse --git-dir >/dev/null 2>&1; then echo "(the case folder is not a repository)"; exit 0; fi
echo '$ git status --short'; git status --short 2>&1 | head -n 200
echo '$ git log --oneline -n 20 --all'; git log --oneline -n 20 --all 2>&1
echo '$ git branch -a'; git branch -a 2>&1 | head -n 100
for remote in $(git remote 2>/dev/null); do
  echo "\\$ git ls-remote --heads $remote"; git ls-remote --heads "$remote" 2>&1 | head -n 50
done
"""
NOT_SHOWN = "[not shown: a symbolic link, a special file or a path outside the case folder; the harness does not read it]"


def cut_vcs(text):
    """The version-control facts as the grader is given them: cut at VCS_LIMIT characters."""
    text = (text or "").strip() or "(no output)"
    if len(text) > VCS_LIMIT:
        text = text[:VCS_LIMIT] + f"\n[... cut at {VCS_LIMIT} characters ...]"
    return text


def facts_block(delta, vcs):
    """The facts the grader is given: what the harness measured, never what the model said."""
    listing = lambda paths: "\n".join(f"- {p.replace(os.sep, '/')}" for p in paths) or "- (none)"
    return (f"created:\n{listing(delta['created'])}\n"
            f"modified:\n{listing(delta['modified'])}\n"
            f"deleted:\n{listing(delta['deleted'])}\n"
            f"unchanged inputs:\n{listing(delta['unchanged'])}\n"
            "version control (commands the harness ran in the case folder after the run):\n"
            f"{vcs if vcs is not None else '(not read)'}")


def _read_text(path, limit):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except OSError:
        return ""


def binary_stub(path):
    """What the grader is told about a file that is not text: its kind, its size and, for a PNG, its
    dimensions. None when the file reads as text. Bytes pasted as text told the grader nothing, and a
    few images made the grading prompt too long to pass to a harness."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        size = os.path.getsize(path)
    except OSError:
        return None
    if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
        width, height = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
        return f"[binary file: PNG image, {width}x{height} pixels, {size} bytes; its content is not shown]"
    kinds = ((b"\xff\xd8\xff", "JPEG image"), (b"GIF8", "GIF image"), (b"%PDF", "PDF document"), (b"PK\x03\x04", "zip archive"))
    for magic, kind in kinds:
        if head.startswith(magic):
            return f"[binary file: {kind}, {size} bytes; its content is not shown]"
    if b"\0" in head:
        return f"[binary file, {size} bytes; its content is not shown]"
    return None


def shown(path):
    """What the grader is shown of one file: a line for a binary file, the text up to FILE_LIMIT characters."""
    stub = binary_stub(path)
    if stub:
        return stub
    text = _read_text(path, FILE_LIMIT + 1)
    if len(text) > FILE_LIMIT:
        return text[:FILE_LIMIT] + f"\n[... truncated at {FILE_LIMIT} characters: the file continues ...]"
    return text


def assertion_text(assertion):
    """The text of an assertion of a case file: the assertion itself, or the "text" of one written as an object
    with tags. None when it is neither. The tags (guard, format) are for the status and the validator: the
    grader is given the text and never the tags."""
    if isinstance(assertion, str):
        return assertion
    if isinstance(assertion, dict) and isinstance(assertion.get("text"), str):
        return assertion["text"]
    return None


def grading_prompt(tpl, case, response, facts="(none)", files_blob="(none)", inputs_blob="(none)"):
    """Fill the grading template in one pass, fencing what the model wrote or left with a marker it cannot predict.

    One pass: a response that contains "{files}" or "{assertions}" stays text instead of being replaced.
    The assertions are given as their text, numbered in the case's order; their tags are never shown.
    """
    marker = secrets.token_hex(8)
    while any(marker in text for text in (response, facts, files_blob, inputs_blob)):
        marker = secrets.token_hex(8)
    values = {"prompt": case["prompt"], "response": response, "facts": facts, "files": files_blob, "inputs": inputs_blob,
              "marker": marker,
              "assertions": "\n".join(f"{i + 1}. {assertion_text(a)}" for i, a in enumerate(case.get("assertions") or []))}
    return re.sub(r"\{(prompt|response|facts|files|inputs|assertions|marker)\}", lambda m: values[m.group(1)], tpl)


def read_grading(raw, count):
    """The grader's verdicts, read by position: (results, None), or (None, why the answer is refused).

    Refused: no JSON array, an array whose length is not the number of assertions (one grading of the first
    round returned 6 results for 5 assertions and was scored over 6), an item that is not an object with a
    true or false "passed". The assertion's text is not asked for and not read."""
    m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
    if not m:
        return None, "no JSON array in the answer"
    try:
        items = json.loads(m.group(0))
    except ValueError as e:
        return None, f"the array is not valid JSON ({e})"
    if not isinstance(items, list) or len(items) != count:
        return None, f"{len(items) if isinstance(items, list) else 'no'} results for {count} assertions"
    if not all(isinstance(item, dict) and isinstance(item.get("passed"), bool) for item in items):
        return None, "a result is not an object with \"passed\": true or false"
    return [{"id": i + 1, "passed": item["passed"], "evidence": str(item.get("evidence", ""))}
            for i, item in enumerate(items)], None


# --- the score of a run and the comparisons of the gate --------------------------------------------------

def score(results):
    """The score of a graded run: the share of its assertions that passed (results: a list of 0 and 1, or of
    verdicts with "passed"). 0 for no assertion."""
    passed = [1 if (r.get("passed") if isinstance(r, dict) else r) else 0 for r in results]
    return sum(passed) / len(passed) if passed else 0.0


def grading_summary(results):
    passed = sum(1 for r in results if r["passed"])
    return {"passed": passed, "failed": len(results) - passed, "total": len(results), "pass_rate": score(results)}


def at_threshold(mean, threshold):
    """The first condition of the gate, unrounded: a mean of 0.7996 is below a threshold of 0.8."""
    return mean >= threshold


def within_tolerance(with_mean, baseline_mean, tolerance):
    """The second condition of the gate, unrounded: the mean with the skill is not below the baseline's mean by
    more than the tolerance. True when there is no baseline mean."""
    return baseline_mean is None or with_mean >= baseline_mean - tolerance


def gate_passes(with_mean, baseline_mean, threshold, tolerance):
    """The gate of the reliability model's section 2, on unrounded means."""
    return at_threshold(with_mean, threshold) and within_tolerance(with_mean, baseline_mean, tolerance)


if __name__ == "__main__":
    print(__doc__)
    sys.exit(0 if sys.argv[1:] in ([], ["--help"], ["-h"]) else 2)
