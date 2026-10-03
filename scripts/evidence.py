#!/usr/bin/env python3
"""Record field evidence: a real use of a workbench skill in a project, and its verdict (the reliability
model, section 7). Export it from a project, and import a contributed file into the workbench.

Usage:
  python3 <workbench root>/scripts/evidence.py record --start --skill-dir <installed skill folder> --project <dir>
                                                [--model <id>] [--adapter <name>]
  python3 <workbench root>/scripts/evidence.py record --verdict worked|corrected|failed --use <id> --project <dir>
  python3 <workbench root>/scripts/evidence.py record --check-report <file> --use <id> --project <dir>
  python3 <workbench root>/scripts/evidence.py export --project <dir> --out <file> [--skill <name>]
  python3 <workbench root>/scripts/evidence.py import --file <file>

record --start appends a `use` line to <project>/.workbench-local/evidence/<skill>.jsonl, the git-ignored folder
a project keeps its own data in, and prints the use's id (8 random hexadecimal characters) on stdout. It runs
when a use begins, so a use that stops, fails or is abandoned is still counted. The skill's name, version and
content hash are read and computed from the installed skill folder (the installer's marker file left out, so a
copy has the hash of its source). The model id comes from --model only, never from a model's own account of
what it is: an id or an alias of the gate file's model list (evals/eval-gate.json, "models") is written as the
listed id, anything else, or no --model, as "unknown". --adapter names a folder of adapters/, else "unknown".

record --verdict appends a person's verdict on that use: worked 1, corrected 0.5, failed 0 ("judge": "user").
record --check-report appends the verdict of the skill's own check script, read from the report it wrote with
--report (the report convention: "ok" true 1, false 0; "judge": "check"). When a use has both, the person's is
the one shown.

A line holds closed keys and nothing else: record ("use" or "verdict"), skill, version, content_sha256, model,
adapter, use, week (YYYY-Www: the week, never the day), and, for a verdict, score and judge. No free text and
no count; no project, product, person or account name. evals/eval_status.py, field_line_problems, is the one
definition of that form.

export writes one file with the project's lines (of every skill, or of --skill) that have that form and whose
content hash is the one the skill's version file in this workbench gives for that version: a line recorded on a
locally edited skill is dropped. It never overwrites a file.

import validates a contributed file (every line of the form above, of a skill of this workbench, with the
content hash its version file gives for the version) and, only when all of it is valid, writes the lines of
each skill as skills/<name>/evals/evidence/field-<id>.jsonl, <id> being the first 12 characters of the sha256 of
what is written. Nothing names the contributor: the status reads who added a file from git, and stores it
nowhere. The person then opens a pull request with those files.

Flags only, no prompts. Data on stdout as JSON (record prints the id alone), diagnostics on stderr. Standard
library only; it runs on Python 3.9, the interpreter a scheduler starts the runtime with.
Exit codes: 0 ok, 1 refused (an unknown use, a report or a file that is not valid), 2 usage error.
"""
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_REL = os.path.join(".workbench-local", "evidence")
VALUE_FLAGS = ("--skill-dir", "--project", "--model", "--adapter", "--verdict", "--use", "--check-report", "--out",
               "--skill", "--file")


def die(msg, code=2):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_status():
    """evals/eval_status.py of this checkout: the one definition of a field line, the content hash and the model
    list."""
    path = os.path.join(ROOT, "evals", "eval_status.py")
    if not os.path.isfile(path):
        die(f"{path} is missing: run this script from a checkout of the workbench.", 1)
    name = "workbench_eval_status"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return sys.modules[name]


def parse(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if argv else 2)
    cmd, rest, opts, i = argv[0], argv[1:], {}, 0
    if "-h" in rest or "--help" in rest:
        print(__doc__)
        sys.exit(0)
    while i < len(rest):
        flag = rest[i]
        if flag == "--start":
            opts["start"] = True
            i += 1
        elif flag in VALUE_FLAGS:
            if i + 1 >= len(rest) or rest[i + 1].startswith("--"):
                die(f"{flag} needs a value.")
            if flag[2:] in opts:
                die(f"{flag} is given twice.")
            opts[flag[2:]] = rest[i + 1]
            i += 2
        else:
            die(f"unknown option {flag!r}. See --help.")
    return cmd, opts


def need(opts, allowed, required):
    extra = sorted(set(opts) - set(allowed))
    if extra:
        die(f"--{extra[0]} does not go with this command. See --help.")
    for key in required:
        if key not in opts:
            die(f"--{key} is required. See --help.")


def this_week():
    return load_status().week_of(datetime.datetime.now(datetime.timezone.utc).date())


def frontmatter_name(skill_dir):
    """The skill's name: `name:` of its frontmatter, else its folder's name."""
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    head = text.split("\n---", 1)[0] if text.startswith("---") else ""
    for line in head.splitlines():
        if line.startswith("name:"):
            return line[len("name:"):].strip().strip("\"'")
    return os.path.basename(os.path.normpath(skill_dir))


def model_of(cfg, name):
    """The listed id of a model or one of its aliases; "unknown" for anything else, and with no model list."""
    if not name or not cfg:
        return "unknown"
    return load_status().model_id(cfg, name)


def adapter_of(name):
    if name and load_status().NAME_RE.fullmatch(name) and os.path.isdir(os.path.join(ROOT, "adapters", name)):
        return name
    return "unknown"


def project_dir(path):
    if not os.path.isdir(path):
        die(f"--project {path} is not a folder.")
    return os.path.abspath(path)


def append(project, skill, line):
    folder = os.path.join(project, LOCAL_REL)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{skill}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    try:  # the folder holds a project's own data: say so when the project's git would commit it
        r = subprocess.run(["git", "-C", project, "check-ignore", "-q", path], capture_output=True, timeout=30)
        if r.returncode == 1:
            print(f"Note: {os.path.relpath(path, project)} is not ignored by git in this project; add "
                  ".workbench-local/ to .gitignore so that it is never committed.", file=sys.stderr)
    except (OSError, subprocess.SubprocessError):
        pass
    return path


def local_lines(project):
    """[(path, line)] of the project's field files, in file order."""
    folder = os.path.join(project, LOCAL_REL)
    out = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            for raw in f.read().splitlines():
                try:
                    out.append((name, json.loads(raw)))
                except ValueError:
                    out.append((name, None))
    return out


def find_use(project, use):
    es = load_status()
    if not es.USE_ID_RE.fullmatch(use or ""):
        die("--use takes the 8 hexadecimal characters record --start printed.")
    found = [l for _, l in local_lines(project) if isinstance(l, dict) and l.get("record") == "use" and l.get("use") == use]
    if not found:
        die(f"no use {use} in {os.path.join(project, LOCAL_REL)}: record it with record --start first.", 1)
    return found[-1]


def record(opts):
    es = load_status()
    cfg = es.load_gate(ROOT)
    modes = [k for k in ("start", "verdict", "check-report") if k in opts]
    if len(modes) != 1:
        die("record takes exactly one of --start, --verdict and --check-report. See --help.")
    if modes[0] == "start":
        need(opts, ("start", "skill-dir", "project", "model", "adapter"), ("skill-dir", "project"))
        project, skill_dir = project_dir(opts["project"]), opts["skill-dir"]
        name, version = frontmatter_name(skill_dir), es.skill_version(skill_dir)
        if not name or not es.NAME_RE.fullmatch(name) or version is None:
            die(f"{skill_dir} is not a skill folder: its SKILL.md has no name or no metadata.version.", 1)
        line = {"record": "use", "skill": name, "version": version, "content_sha256": es.content_hash(skill_dir),
                "model": model_of(cfg, opts.get("model")), "adapter": adapter_of(opts.get("adapter")),
                "use": os.urandom(4).hex(), "week": this_week()}
        append(project, name, line)
        print(line["use"])
        return 0
    if modes[0] == "verdict":
        need(opts, ("verdict", "use", "project"), ("verdict", "use", "project"))
        if opts["verdict"] not in es.FIELD_SCORES:
            die("--verdict is worked, corrected or failed.")
        score, judge = es.FIELD_SCORES[opts["verdict"]], "user"
    else:
        need(opts, ("check-report", "use", "project"), ("check-report", "use", "project"))
        try:
            with open(opts["check-report"], encoding="utf-8") as f:
                report = json.load(f)
        except (OSError, ValueError) as e:
            die(f"--check-report {opts['check-report']} cannot be read as JSON: {e}", 1)
        if not isinstance(report, dict) or not isinstance(report.get("ok"), bool) or not isinstance(report.get("script"), str):
            die("--check-report is the JSON a check script writes with --report: it has \"script\" and \"ok\" (true or false).", 1)
        score, judge = (1 if report["ok"] else 0), "check"
    project = project_dir(opts["project"])
    use = find_use(project, opts["use"])
    line = {**{k: use[k] for k in es.FIELD_USE_KEYS if k in use}, "record": "verdict", "week": this_week(),
            "score": score, "judge": judge}
    problems = es.field_line_problems(line)
    if problems:
        die(f"the use {opts['use']} is not a valid line ({'; '.join(problems)}): nothing is recorded.", 1)
    append(project, line["skill"], line)
    print(json.dumps({"recorded": "verdict", "use": line["use"], "score": score, "judge": judge}))
    return 0


def known_hashes(es, skill):
    lines, _, _ = es.read_versions(os.path.join(ROOT, "skills", skill))
    return {l.get("version"): l.get("content_sha256") for l in lines}


def canonical(es, line):
    keys = es.FIELD_USE_KEYS if line["record"] == "use" else es.FIELD_VERDICT_KEYS
    return json.dumps({k: line[k] for k in keys})


def export(opts):
    es = load_status()
    need(opts, ("project", "out", "skill"), ("project", "out"))
    project, out = project_dir(opts["project"]), opts["out"]
    if os.path.exists(out):
        die(f"--out {out} exists: an export never overwrites a file.", 1)
    cfg = es.load_gate(ROOT)
    models = set(es.known_models(cfg)) if cfg else None
    kept, dropped, hashes = [], {"not of the closed form": 0, "an edited or unknown skill": 0}, {}
    for _, line in local_lines(project):
        if opts.get("skill") and (not isinstance(line, dict) or line.get("skill") != opts["skill"]):
            continue
        if line is None or es.field_line_problems(line, models):
            dropped["not of the closed form"] += 1
            continue
        if line["skill"] not in hashes:
            hashes[line["skill"]] = known_hashes(es, line["skill"])
        if hashes[line["skill"]].get(line["version"]) != line["content_sha256"]:
            dropped["an edited or unknown skill"] += 1
            continue
        kept.append(canonical(es, line))
    with open(out, "x", encoding="utf-8") as f:
        f.write("".join(l + "\n" for l in kept))
    skills = sorted({json.loads(l)["skill"] for l in kept})
    print(json.dumps({"out": out, "lines": len(kept), "skills": skills, "dropped": dropped}))
    return 0


def import_file(opts):
    es = load_status()
    need(opts, ("file",), ("file",))
    try:
        with open(opts["file"], encoding="utf-8") as f:
            raw = f.read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        die(f"--file {opts['file']} cannot be read: {e}", 1)
    cfg = es.load_gate(ROOT)
    models = set(es.known_models(cfg)) if cfg else None
    names, problems, by_skill, hashes = set(es.skill_names(ROOT)), [], {}, {}
    for n, text in enumerate(raw, 1):
        if not text.strip():
            continue
        try:
            line = json.loads(text)
        except ValueError:
            problems.append(f"line {n}: not valid JSON")
            continue
        found = es.field_line_problems(line, models)
        if not found and line["skill"] not in names:
            found = [f"skill {line['skill']} is not a skill of this workbench"]
        if not found:
            if line["skill"] not in hashes:
                hashes[line["skill"]] = known_hashes(es, line["skill"])
            if hashes[line["skill"]].get(line["version"]) != line["content_sha256"]:
                found = [f"content_sha256 is not the hash the version file gives for {line['skill']} {line['version']}"]
        if found:
            problems += [f"line {n}: {p}" for p in found]
        else:
            by_skill.setdefault(line["skill"], []).append(canonical(es, line))
    if not by_skill and not problems:
        problems.append("the file holds no line")
    if problems:
        for p in problems:
            print(f"{opts['file']}: {p}", file=sys.stderr)
        print(json.dumps({"written": [], "problems": problems}))
        return 1
    written = []
    for skill, lines in sorted(by_skill.items()):
        data = "".join(l + "\n" for l in lines).encode("utf-8")
        folder = os.path.join(ROOT, "skills", skill, "evals", "evidence")
        path = os.path.join(folder, f"field-{hashlib.sha256(data).hexdigest()[:12]}.jsonl")
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(data)
        written.append(os.path.relpath(path, ROOT))
    print(json.dumps({"written": written, "problems": []}))
    return 0


def main(argv):
    cmd, opts = parse(argv)
    if cmd == "record":
        return record(opts)
    if cmd == "export":
        return export(opts)
    if cmd == "import":
        return import_file(opts)
    die(f"unknown command {cmd!r}. See --help.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
